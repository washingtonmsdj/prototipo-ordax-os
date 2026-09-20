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
HELPER_PACKAGE = "./cmd/ordax-creator-native-targets"
HELPER_RELATIVE = Path("system/bin/ordax-native-install-targets")
PROVENANCE_RELATIVE = Path("system/.ordax/native-release-tools.json")
SCHEMA = "prototype-ordax.native-release-assembly/1"


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
        # Generated output inside repository source would risk accidental
        # inclusion or mutation of tracked files.
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
    if not (CREATOR / "go.mod").is_file():
        raise AssemblyError("Creator Go module is missing")
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


def build_helper(destination: Path) -> Path:
    output = destination / HELPER_RELATIVE
    output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "CGO_ENABLED": "0",
        "GOOS": "linux",
        "GOARCH": "amd64",
        "GOTOOLCHAIN": "local",
    })
    argv = [
        "go", "build",
        "-trimpath",
        "-buildvcs=false",
        "-ldflags=-s -w",
        "-o", str(output),
        HELPER_PACKAGE,
    ]
    try:
        subprocess.run(argv, cwd=CREATOR, env=env, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AssemblyError("failed to build Native install helper") from exc
    if not output.is_file() or output.is_symlink() or output.stat().st_size <= 0:
        raise AssemblyError("Native install helper build did not produce a safe file")
    output.chmod(0o755)
    return output


def write_provenance(destination: Path, helper: Path, source_commit: str) -> Path:
    relative_helper = HELPER_RELATIVE.as_posix()
    provenance = {
        "$schema": SCHEMA,
        "status": "assembled",
        "source_commit": source_commit,
        "recipe": "tools/native-release-assembly/build.py",
        "target": "linux/amd64",
        "cgo_enabled": False,
        "system_source": "system/",
        "physical_apply_authorized": False,
        "injected_tools": [
            {
                "path": relative_helper,
                "role": "native-install-read-only-target-discovery",
                "source_package": "tools/creator/cmd/ordax-creator-native-targets",
                "sha256": sha256_file(helper),
                "size": helper.stat().st_size,
                "mode": "0755",
                "physical_apply_authorized": False,
            }
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
    helper = build_helper(destination)
    source_commit = git_head()
    provenance = write_provenance(destination, helper, source_commit)
    return {
        "schema": SCHEMA,
        "status": "assembled",
        "source_commit": source_commit,
        "root": str(destination),
        "helper": HELPER_RELATIVE.as_posix(),
        "helper_sha256": sha256_file(helper),
        "helper_size": helper.stat().st_size,
        "provenance": PROVENANCE_RELATIVE.as_posix(),
        "provenance_sha256": sha256_file(provenance),
        "physical_apply_authorized": False,
    }


def verify(destination: Path) -> dict:
    destination = destination.resolve()
    helper = destination / HELPER_RELATIVE
    provenance_path = destination / PROVENANCE_RELATIVE
    if not helper.is_file() or helper.is_symlink():
        raise AssemblyError("assembled Native helper is missing or unsafe")
    if stat.S_IMODE(helper.stat().st_mode) != 0o755:
        raise AssemblyError("assembled Native helper must be mode 0755")
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssemblyError("Native assembly provenance is unreadable") from exc
    if provenance.get("$schema") != SCHEMA or provenance.get("physical_apply_authorized") is True:
        raise AssemblyError("Native assembly provenance policy is invalid")
    tools = provenance.get("injected_tools")
    if not isinstance(tools, list) or len(tools) != 1:
        raise AssemblyError("Native assembly must contain exactly one injected tool")
    tool = tools[0]
    if (
        tool.get("path") != HELPER_RELATIVE.as_posix()
        or tool.get("role") != "native-install-read-only-target-discovery"
        or tool.get("physical_apply_authorized") is not False
        or tool.get("sha256") != sha256_file(helper)
        or tool.get("size") != helper.stat().st_size
        or tool.get("mode") != "0755"
    ):
        raise AssemblyError("Native helper provenance does not match assembled bytes")
    return {
        "status": "verified",
        "source_commit": provenance.get("source_commit"),
        "helper_sha256": tool["sha256"],
        "physical_apply_authorized": False,
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
