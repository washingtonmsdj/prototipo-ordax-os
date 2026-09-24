#!/usr/bin/env python3
"""Assemble the signed Native system release source tree.

This recipe is intentionally separate from tools/release-bundle: it prepares
the Native-specific system/ tree, while release-bundle remains the canonical
deterministic tar owner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "system"
CREATOR = ROOT / "tools" / "creator"
RUNTIME_COMPONENT_CHANNEL = ROOT / "tools" / "runtime-component-channel"
PROVENANCE_RELATIVE = Path("system/.ordax/native-release-tools.json")
SCHEMA = "prototype-ordax.native-release-assembly/2"

HELPERS = (
    {
        "relative": Path("system/bin/ordax-native-install-targets"),
        "module": CREATOR,
        "package": "./cmd/ordax-creator-native-targets",
        "role": "native-install-read-only-target-discovery",
        "source_package": "tools/creator/cmd/ordax-creator-native-targets",
        "physical_apply_authorized": False,
        "component_publish_authorized": False,
    },
    {
        "relative": Path("system/bin/ordax-runtime-component-channel"),
        "module": RUNTIME_COMPONENT_CHANNEL,
        "package": ".",
        "role": "runtime-component-verifier-and-activation-state-owner",
        "source_package": "tools/runtime-component-channel",
        "physical_apply_authorized": False,
        "component_publish_authorized": False,
    },
)


class AssemblyError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head() -> str:
    try:
        value = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AssemblyError("cannot resolve source commit") from exc
    if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise AssemblyError("source commit is not a lowercase 40-hex SHA")
    return value


def ensure_clean_destination(destination: Path) -> Path:
    absolute = destination.resolve()
    if absolute == ROOT or ROOT in absolute.parents:
        raise AssemblyError("assembly destination must be outside repository source")
    if absolute.exists() or absolute.is_symlink():
        raise AssemblyError("assembly destination already exists")
    absolute.parent.mkdir(parents=True, exist_ok=True)
    return absolute


def validate_source_tree() -> None:
    if not SYSTEM.is_dir() or SYSTEM.is_symlink():
        raise AssemblyError("system source root is missing or unsafe")
    entrypoint = SYSTEM / "entrypoint"
    if not entrypoint.is_file() or entrypoint.is_symlink():
        raise AssemblyError("system entrypoint is missing or unsafe")
    if stat.S_IMODE(entrypoint.stat().st_mode) != 0o755:
        raise AssemblyError("system entrypoint must be mode 0755")
    for helper in HELPERS:
        module = helper["module"]
        if not isinstance(module, Path) or not (module / "go.mod").is_file():
            raise AssemblyError(
                f"Native helper Go module is missing: {module.relative_to(ROOT)}"
            )
    for path in SYSTEM.rglob("*"):
        if path.is_symlink():
            raise AssemblyError(f"symlink is forbidden in Native release source: {path}")


def copy_system_tree(destination: Path) -> Path:
    target = destination / "system"
    shutil.copytree(
        SYSTEM,
        target,
        symlinks=False,
        copy_function=shutil.copy2,
    )
    for path in target.rglob("*"):
        if path.is_symlink():
            raise AssemblyError(f"symlink leaked into Native release staging: {path}")
    return target


def build_helper(destination: Path, spec: dict) -> Path:
    relative = spec["relative"]
    module = spec["module"]
    package = spec["package"]
    output = destination / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "CGO_ENABLED": "0",
        "GOOS": "linux",
        "GOARCH": "amd64",
        "GOTOOLCHAIN": "local",
    })
    argv = [
        "go",
        "build",
        "-trimpath",
        "-buildvcs=false",
        "-ldflags=-s -w",
        "-o",
        str(output),
        package,
    ]
    try:
        subprocess.run(argv, cwd=module, env=env, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AssemblyError(f"failed to build Native helper: {relative}") from exc
    if not output.is_file() or output.is_symlink() or output.stat().st_size <= 0:
        raise AssemblyError(f"Native helper build did not produce a safe file: {relative}")
    output.chmod(0o755)
    return output


def tool_provenance(spec: dict, helper: Path) -> dict:
    return {
        "path": spec["relative"].as_posix(),
        "role": spec["role"],
        "source_package": spec["source_package"],
        "sha256": sha256_file(helper),
        "size": helper.stat().st_size,
        "mode": "0755",
        "physical_apply_authorized": spec["physical_apply_authorized"],
        "component_publish_authorized": spec["component_publish_authorized"],
    }


def write_provenance(
    destination: Path,
    built_helpers: list[tuple[dict, Path]],
    source_commit: str,
) -> Path:
    provenance = {
        "$schema": SCHEMA,
        "status": "assembled",
        "source_commit": source_commit,
        "recipe": "tools/native-release-assembly/build.py",
        "target": "linux/amd64",
        "cgo_enabled": False,
        "system_source": "system/",
        "physical_apply_authorized": False,
        "component_publish_authorized": False,
        "injected_tools": [
            tool_provenance(spec, helper)
            for spec, helper in built_helpers
        ],
    }
    path = destination / PROVENANCE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o644)
    return path


def assemble(destination: Path) -> dict:
    validate_source_tree()
    destination = ensure_clean_destination(destination)
    destination.mkdir(mode=0o755)
    copy_system_tree(destination)
    built_helpers = [(spec, build_helper(destination, spec)) for spec in HELPERS]
    source_commit = git_head()
    provenance = write_provenance(destination, built_helpers, source_commit)
    tools = [tool_provenance(spec, helper) for spec, helper in built_helpers]
    return {
        "schema": SCHEMA,
        "status": "assembled",
        "source_commit": source_commit,
        "root": str(destination),
        "helpers": tools,
        "provenance": PROVENANCE_RELATIVE.as_posix(),
        "provenance_sha256": sha256_file(provenance),
        "physical_apply_authorized": False,
        "component_publish_authorized": False,
    }


def verify_tool(destination: Path, spec: dict, record: object) -> dict:
    if not isinstance(record, dict):
        raise AssemblyError("Native helper provenance record is invalid")
    helper = destination / spec["relative"]
    if not helper.is_file() or helper.is_symlink():
        raise AssemblyError(f"assembled Native helper is missing or unsafe: {spec['relative']}")
    if stat.S_IMODE(helper.stat().st_mode) != 0o755:
        raise AssemblyError(f"assembled Native helper must be mode 0755: {spec['relative']}")
    expected = {
        "path": spec["relative"].as_posix(),
        "role": spec["role"],
        "source_package": spec["source_package"],
        "sha256": sha256_file(helper),
        "size": helper.stat().st_size,
        "mode": "0755",
        "physical_apply_authorized": spec["physical_apply_authorized"],
        "component_publish_authorized": spec["component_publish_authorized"],
    }
    if record != expected:
        raise AssemblyError(
            f"Native helper provenance does not match assembled bytes: {spec['relative']}"
        )
    return expected


def verify(destination: Path) -> dict:
    destination = destination.resolve()
    provenance_path = destination / PROVENANCE_RELATIVE
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssemblyError("Native assembly provenance is unreadable") from exc
    if (
        provenance.get("$schema") != SCHEMA
        or provenance.get("physical_apply_authorized") is not False
        or provenance.get("component_publish_authorized") is not False
    ):
        raise AssemblyError("Native assembly provenance policy is invalid")
    tools = provenance.get("injected_tools")
    if not isinstance(tools, list) or len(tools) != len(HELPERS):
        raise AssemblyError(
            f"Native assembly must contain exactly {len(HELPERS)} injected tools"
        )
    by_path = {
        record.get("path"): record
        for record in tools
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    }
    if len(by_path) != len(HELPERS):
        raise AssemblyError("Native helper provenance paths must be unique and complete")
    verified = [
        verify_tool(destination, spec, by_path.get(spec["relative"].as_posix()))
        for spec in HELPERS
    ]
    return {
        "status": "verified",
        "source_commit": provenance.get("source_commit"),
        "helpers": verified,
        "physical_apply_authorized": False,
        "component_publish_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    assemble_parser = sub.add_parser("assemble")
    assemble_parser.add_argument("--out", type=Path, required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = assemble(args.out) if args.command == "assemble" else verify(args.root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (AssemblyError, OSError) as exc:
        print(f"native-release-assembly: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
