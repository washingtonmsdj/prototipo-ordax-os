#!/usr/bin/env python3
"""Measure the exact Native initramfs userspace closure inside the pinned snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

SCHEMA = "prototype-ordax.native-initramfs-build-environment/1"
OBSERVATION_SCHEMA = "prototype-ordax.native-initramfs-environment-observation/1"
PRIMARY_BINARIES = ("/usr/sbin/cryptsetup", "/usr/bin/btrfs")
REQUIRED_BUSYBOX_APPLETS = {"sh", "mount", "umount", "cat", "mkdir", "tr"}
PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")


class ObservationError(RuntimeError):
    pass


def capture(argv: list[str]) -> str:
    try:
        return subprocess.run(
            argv,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", "") or ""
        raise ObservationError(
            f"command failed: {' '.join(argv)}: {stderr.strip()}"
        ) from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObservationError(f"cannot load environment contract: {exc}") from exc
    if not isinstance(value, dict) or value.get("$schema") != SCHEMA:
        raise ObservationError("unexpected Native initramfs environment contract")
    return value


def installed_version(package: str) -> str:
    if not PACKAGE_RE.fullmatch(package):
        raise ObservationError(f"unsafe package name: {package!r}")
    return capture(["dpkg-query", "-W", "-f=${Version}", package])


def runtime_files(binary: str) -> list[str]:
    path = Path(binary)
    if not path.is_file() or path.is_symlink():
        raise ObservationError(f"required runtime binary missing or unsafe: {binary}")
    files = {
        line.strip()
        for line in capture(["lddtree", "-l", binary]).splitlines()
        if line.strip()
    }
    files.add(binary)
    for item in files:
        candidate = Path(item)
        if not candidate.is_absolute() or not candidate.exists():
            raise ObservationError(f"runtime closure contains invalid path: {item}")
    return sorted(files)


def package_owner(path: str) -> str:
    output = capture(["dpkg-query", "-S", path])
    first = output.splitlines()[0]
    owner, separator, _ = first.partition(": ")
    if not separator:
        raise ObservationError(f"cannot parse package owner for runtime path: {path}")
    owner = owner.split(":", 1)[0]
    if not PACKAGE_RE.fullmatch(owner):
        raise ObservationError(f"unsafe package owner for runtime path: {path}")
    return owner


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base-image", required=True)
    parser.add_argument("--snapshot-id", required=True)
    args = parser.parse_args()

    try:
        contract = load_contract(args.contract)
        expected_image = (
            contract["base_image"]["repository"]
            + "@"
            + contract["base_image"]["manifest_digest"]
        )
        if args.base_image != expected_image:
            raise ObservationError("base image identity does not match contract")
        if args.snapshot_id != contract["apt"]["snapshot_id"]:
            raise ObservationError("APT snapshot identity does not match contract")

        top_level = {}
        for package in sorted(contract["apt"]["top_level_packages"]):
            top_level[package] = installed_version(package)

        files: set[str] = set()
        for binary in PRIMARY_BINARIES:
            files.update(runtime_files(binary))

        closure_packages = {}
        file_hashes = {}
        for runtime_path in sorted(files):
            owner = package_owner(runtime_path)
            closure_packages[owner] = installed_version(owner)
            file_hashes[runtime_path] = sha256_file(Path(runtime_path))

        busybox = Path("/bin/busybox")
        if not busybox.is_file() or busybox.is_symlink():
            raise ObservationError("busybox-static binary is missing or unsafe")
        applets = set(capture([str(busybox), "--list"]).splitlines())
        missing_applets = sorted(REQUIRED_BUSYBOX_APPLETS - applets)
        if missing_applets:
            raise ObservationError(
                "busybox-static is missing required applets: "
                + ", ".join(missing_applets)
            )

        observation = {
            "$schema": OBSERVATION_SCHEMA,
            "status": "observation",
            "base_image": args.base_image,
            "apt_snapshot_id": args.snapshot_id,
            "top_level_versions": dict(sorted(top_level.items())),
            "runtime_closure_packages": dict(sorted(closure_packages.items())),
            "runtime_files": sorted(files),
            "runtime_file_sha256": dict(sorted(file_hashes.items())),
            "required_busybox_applets": sorted(REQUIRED_BUSYBOX_APPLETS),
            "busybox_sha256": sha256_file(busybox),
            "primary_binary_sha256": {
                binary: sha256_file(Path(binary))
                for binary in PRIMARY_BINARIES
            },
        }

        args.out.mkdir(parents=True, exist_ok=True)
        output = args.out / "observation.json"
        output.write_text(
            json.dumps(observation, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(observation, indent=2, sort_keys=True))
        print("NATIVE_INITRAMFS_ENVIRONMENT_OBSERVATION=PASS")
        print("NATIVE_INITRAMFS_ARTIFACT_BUILD_ALLOWED=NO")
        return 0
    except (ObservationError, KeyError, OSError) as exc:
        print(f"native-initramfs-observe: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
