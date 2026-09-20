#!/usr/bin/env python3
"""Build a deterministic portable OrdaX EROFS image from canonical system.tar.

This is a candidate-only bridge for portable USB v2. The signed release
protocol v1 remains system.tar. The builder validates that the input tar still
has the canonical release-bundle metadata boundary, then feeds that exact tar
to mkfs.erofs with fixed timestamp/UUID/ownership and verifies the resulting
EROFS image. It never signs, publishes, activates or authorizes physical media.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
from typing import Any
import uuid

SCHEMA = "prototype-ordax.portable-release-image-result/1"
UUID_NAMESPACE = uuid.UUID("7a471b52-6f72-5d61-9f58-2fb58012e6d1")
VOLUME_LABEL = "ORDAX-SYSTEM"
MAX_ENTRIES = 100000
MAX_TOTAL_BYTES = 16 << 30


class ImageError(RuntimeError):
    pass


def run(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ImageError(f"cannot execute {' '.join(argv)}: {exc}") from exc
    if result.returncode != 0:
        raise ImageError(
            f"command failed ({result.returncode}): {' '.join(argv)}: "
            f"stdout={result.stdout.decode('utf-8', 'replace')!r} "
            f"stderr={result.stderr.decode('utf-8', 'replace')!r}"
        )
    return result


def require_regular(path: Path, label: str) -> Path:
    absolute = path.resolve()
    try:
        info = absolute.lstat()
    except OSError as exc:
        raise ImageError(f"cannot stat {label}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ImageError(f"{label} must be a regular non-symlink file")
    return absolute


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_image_uuid(source_sha256: str) -> str:
    if len(source_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in source_sha256):
        raise ImageError("source SHA-256 is not canonical lowercase hex")
    return str(uuid.uuid5(UUID_NAMESPACE, source_sha256))


def validate_tar(path: Path) -> dict[str, Any]:
    path = require_regular(path, "system.tar")
    if path.name != "system.tar":
        raise ImageError("portable EROFS input must be named system.tar")

    entrypoint_seen = False
    previous = ""
    total = 0
    count = 0
    try:
        archive = tarfile.open(path, mode="r:")
    except (tarfile.TarError, OSError) as exc:
        raise ImageError(f"cannot open canonical system.tar: {exc}") from exc

    with archive:
        for member in archive:
            count += 1
            if count > MAX_ENTRIES:
                raise ImageError("system.tar exceeds maximum entry count")
            name = member.name
            if (
                not name
                or name.startswith("/")
                or "\\" in name
                or name == ".."
                or name.startswith("../")
                or "/../" in name
            ):
                raise ImageError(f"unsafe system.tar path: {name!r}")
            if previous and name < previous:
                raise ImageError("system.tar entries are not in canonical lexical order")
            previous = name

            if member.uid != 0 or member.gid != 0 or member.uname not in ("", None) or member.gname not in ("", None):
                raise ImageError(f"system.tar ownership is not normalized: {name}")
            if int(member.mtime) != 0:
                raise ImageError(f"system.tar timestamp is not normalized: {name}")
            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise ImageError(f"system.tar special/link member is forbidden: {name}")

            mode = member.mode & 0o7777
            if member.isdir():
                if mode != 0o755:
                    raise ImageError(f"system.tar directory mode is not 0755: {name}")
            elif member.isfile():
                if mode not in (0o644, 0o755):
                    raise ImageError(f"system.tar file mode is not canonical: {name}")
                if member.size < 0:
                    raise ImageError(f"negative file size in system.tar: {name}")
                total += member.size
                if total > MAX_TOTAL_BYTES:
                    raise ImageError("system.tar extracted size exceeds limit")
                if name == "system/entrypoint":
                    if mode != 0o755 or member.size <= 0:
                        raise ImageError("system/entrypoint must be non-empty mode 0755")
                    entrypoint_seen = True
            else:
                raise ImageError(f"unsupported system.tar member type: {name}")

    if not entrypoint_seen:
        raise ImageError("system.tar is missing executable system/entrypoint")
    return {
        "entry_count": count,
        "extracted_bytes": total,
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
    }


def output_path(path: Path, source: Path) -> Path:
    if path.name != "system.erofs":
        raise ImageError("portable release output must be named system.erofs")
    absolute = path.absolute()
    parent = absolute.parent.resolve()
    try:
        parent_info = parent.lstat()
    except OSError as exc:
        raise ImageError(f"cannot stat output parent: {exc}") from exc
    if stat.S_ISLNK(parent_info.st_mode) or not stat.S_ISDIR(parent_info.st_mode):
        raise ImageError("output parent must be a real directory")
    absolute = parent / absolute.name
    if absolute.exists() or absolute.is_symlink():
        raise ImageError("output already exists; overwrite is forbidden")
    if absolute == source:
        raise ImageError("output must differ from source")
    return absolute


def parse_blkid(image: Path) -> dict[str, str]:
    result = run(["blkid", "-p", "-o", "export", str(image)])
    values: dict[str, str] = {}
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def build(source_tar: Path, output: Path) -> dict[str, Any]:
    source_tar = require_regular(source_tar, "system.tar")
    source = validate_tar(source_tar)
    image_uuid = deterministic_image_uuid(source["sha256"])
    output = output_path(output, source_tar)
    try:
        run([
            "mkfs.erofs",
            "--tar=f",
            "-zlz4",
            "-T", "0",
            "-U", image_uuid,
            "-L", VOLUME_LABEL,
            "--all-root",
            str(output),
            str(source_tar),
        ])
        require_regular(output, "system.erofs")
        run(["fsck.erofs", "--extract", str(output)])
        identity = parse_blkid(output)
        if identity.get("TYPE") != "erofs":
            raise ImageError("portable release output is not EROFS")
        if identity.get("LABEL") != VOLUME_LABEL:
            raise ImageError("portable release EROFS label mismatch")
        if identity.get("UUID", "").lower() != image_uuid:
            raise ImageError("portable release EROFS UUID mismatch")

        result = {
            "$schema": SCHEMA,
            "status": "candidate-built",
            "source": {
                "name": "system.tar",
                **source,
            },
            "image": {
                "name": "system.erofs",
                "filesystem": "erofs",
                "label": VOLUME_LABEL,
                "uuid": image_uuid,
                "compression": "lz4",
                "timestamp": 0,
                "sha256": sha256_file(output),
                "size": output.stat().st_size,
            },
            "release_protocol_v1_changed": False,
            "signed_publication_enabled": False,
            "portable_boot_handoff_connected": False,
            "physical_write_authorized": False,
        }
        return result
    except Exception:
        try:
            output.unlink()
        except FileNotFoundError:
            pass
        raise


def verify(source_tar: Path, image: Path) -> dict[str, Any]:
    source = validate_tar(source_tar)
    image = require_regular(image, "system.erofs")
    if image.name != "system.erofs":
        raise ImageError("portable release image must be named system.erofs")
    run(["fsck.erofs", "--extract", str(image)])
    identity = parse_blkid(image)
    if identity.get("TYPE") != "erofs" or identity.get("LABEL") != VOLUME_LABEL:
        raise ImageError("portable release image filesystem identity mismatch")
    expected_uuid = deterministic_image_uuid(source["sha256"])
    if identity.get("UUID", "").lower() != expected_uuid:
        raise ImageError("portable release image UUID mismatch")
    return {
        "$schema": SCHEMA,
        "status": "candidate-verified",
        "source_sha256": source["sha256"],
        "image_sha256": sha256_file(image),
        "image_size": image.stat().st_size,
        "release_protocol_v1_changed": False,
        "signed_publication_enabled": False,
        "portable_boot_handoff_connected": False,
        "physical_write_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--tar", type=Path, required=True)
    build_parser.add_argument("--out", type=Path, required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--tar", type=Path, required=True)
    verify_parser.add_argument("--image", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = build(args.tar, args.out) if args.command == "build" else verify(args.tar, args.image)
    except (ImageError, OSError, tarfile.TarError) as exc:
        print(f"portable-release-image: ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
