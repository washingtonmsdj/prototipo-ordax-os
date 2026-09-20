#!/usr/bin/env python3
"""Build a deterministic OrdaX portable-v2 bootstrap capsule.

The capsule is a small EROFS support image for the durable USB architecture.
It contains only the release agent, local recovery entrypoint and official
release-channel pointer. It does not contain trust private material, Surface,
apps or a complete product release, and it does not authorize physical boot.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = "prototype-ordax.portable-bootstrap-capsule-result/1"
UUID_NAMESPACE = uuid.UUID("c69ffb52-3d76-5f01-90ef-ae0acbe4f8a5")
VOLUME_LABEL = "ORDAX-BOOTSTRAP"
MAX_AGENT = 128 << 20

PAYLOAD = (
    ("release-agent", "bootstrap/release-acquisition/ordax-release-agent", "bootstrap/release-acquisition/ordax-release-agent", 0o755),
    ("recovery-entrypoint", "bootstrap/recovery/entrypoint", "bootstrap/recovery/entrypoint", 0o755),
    ("release-channel", "bootstrap/config/release-envelope-url", "bootstrap/config/release-envelope-url", 0o644),
)


class CapsuleError(RuntimeError):
    pass


def run(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(argv, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise CapsuleError(f"cannot execute {' '.join(argv)}: {exc}") from exc
    if result.returncode != 0:
        raise CapsuleError(
            f"command failed ({result.returncode}): {' '.join(argv)}: "
            f"stdout={result.stdout.decode('utf-8', 'replace')!r} "
            f"stderr={result.stderr.decode('utf-8', 'replace')!r}"
        )
    return result


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular_file(path: Path, label: str, *, executable: bool | None = None) -> Path:
    absolute = path.resolve()
    try:
        info = absolute.lstat()
    except OSError as exc:
        raise CapsuleError(f"cannot stat {label}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise CapsuleError(f"{label} must be a regular non-symlink single-link file")
    if executable is True and info.st_mode & 0o111 == 0:
        raise CapsuleError(f"{label} must be executable")
    if executable is False and info.st_mode & 0o111:
        raise CapsuleError(f"{label} must not be executable")
    return absolute


def payload_sources(agent: Path) -> list[tuple[str, Path, str, int]]:
    agent = regular_file(agent, "release agent", executable=True)
    if agent.stat().st_size <= 0 or agent.stat().st_size > MAX_AGENT:
        raise CapsuleError("release agent size is outside allowed range")
    values: list[tuple[str, Path, str, int]] = []
    for logical, source, target, mode in PAYLOAD:
        path = agent if logical == "release-agent" else ROOT / source
        path = regular_file(
            path,
            logical,
            executable=(mode == 0o755),
        )
        values.append((logical, path, target, mode))
    return values


def safe_output(path: Path) -> Path:
    absolute = path.absolute()
    parent = absolute.parent.resolve()
    if not parent.is_dir() or parent.is_symlink():
        raise CapsuleError("output parent must be a real directory")
    absolute = parent / absolute.name
    if absolute.name != "bootstrap.erofs":
        raise CapsuleError("capsule output must be named bootstrap.erofs")
    if absolute.exists() or absolute.is_symlink():
        raise CapsuleError("capsule output already exists")
    return absolute


def add_dir(archive: tarfile.TarFile, name: str) -> None:
    info = tarfile.TarInfo(name.rstrip("/"))
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = 0
    archive.addfile(info)


def add_file(archive: tarfile.TarFile, name: str, data: bytes, mode: int) -> None:
    info = tarfile.TarInfo(name)
    info.mode = mode
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = 0
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def normalized_tar(agent: Path, destination: Path) -> dict:
    payload = payload_sources(agent)
    entries = []
    for logical, path, target, mode in payload:
        data = path.read_bytes()
        entries.append({
            "logical_name": logical,
            "target": target,
            "mode": f"{mode:04o}",
            "sha256": sha256_bytes(data),
            "size": len(data),
        })

    manifest = {
        "$schema": "prototype-ordax.portable-bootstrap-capsule-manifest/1",
        "status": "candidate-proof-only",
        "product_scope": "stable-mvp-usb-only",
        "physical_write_authorized": False,
        "physical_boot_connected": False,
        "canonical_trust_embedded": False,
        "publisher_private_key_embedded": False,
        "entries": entries,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")

    directories = {
        "bootstrap",
        "bootstrap/release-acquisition",
        "bootstrap/recovery",
        "bootstrap/config",
    }
    with tarfile.open(destination, "w", format=tarfile.USTAR_FORMAT) as archive:
        for directory in sorted(directories):
            add_dir(archive, directory)
        for logical, path, target, mode in sorted(payload, key=lambda item: item[2]):
            add_file(archive, target, path.read_bytes(), mode)
        add_file(archive, "bootstrap/capsule-manifest.json", manifest_bytes, 0o644)
    return manifest


def deterministic_uuid(tar_sha256: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", tar_sha256):
        raise CapsuleError("normalized tar SHA-256 is invalid")
    return str(uuid.uuid5(UUID_NAMESPACE, tar_sha256))


def parse_blkid(path: Path) -> dict[str, str]:
    result = run(["blkid", "-p", "-o", "export", str(path)])
    values: dict[str, str] = {}
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def build(agent: Path, output: Path) -> dict:
    output = safe_output(output)
    with tempfile.TemporaryDirectory(prefix="ordax-bootstrap-capsule-") as temporary:
        temp = Path(temporary)
        tar_path = temp / "bootstrap-capsule.tar"
        manifest = normalized_tar(agent, tar_path)
        tar_sha = sha256_file(tar_path)
        image_uuid = deterministic_uuid(tar_sha)
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
                str(tar_path),
            ])
            run(["fsck.erofs", str(output)])
            identity = parse_blkid(output)
            if identity.get("TYPE") != "erofs":
                raise CapsuleError("bootstrap capsule is not EROFS")
            if identity.get("LABEL") != VOLUME_LABEL:
                raise CapsuleError("bootstrap capsule label mismatch")
            if identity.get("UUID", "").lower() != image_uuid:
                raise CapsuleError("bootstrap capsule UUID mismatch")

            result = {
                "$schema": SCHEMA,
                "status": "candidate-built",
                "normalized_tar_sha256": tar_sha,
                "image_sha256": sha256_file(output),
                "image_size": output.stat().st_size,
                "filesystem": "erofs",
                "label": VOLUME_LABEL,
                "uuid": image_uuid,
                "compression": "lz4",
                "manifest": manifest,
                "physical_write_authorized": False,
                "physical_boot_connected": False,
                "pid1_verified_mount_connected": False,
                "canonical_trust_embedded": False,
                "publisher_private_key_embedded": False,
            }
            return result
        except Exception:
            output.unlink(missing_ok=True)
            raise


def verify(agent: Path, image: Path) -> dict:
    image = regular_file(image, "bootstrap capsule")
    if image.name != "bootstrap.erofs":
        raise CapsuleError("capsule image must be named bootstrap.erofs")
    with tempfile.TemporaryDirectory(prefix="ordax-bootstrap-capsule-verify-") as temporary:
        tar_path = Path(temporary) / "bootstrap-capsule.tar"
        manifest = normalized_tar(agent, tar_path)
        expected_uuid = deterministic_uuid(sha256_file(tar_path))
    run(["fsck.erofs", str(image)])
    identity = parse_blkid(image)
    if identity.get("TYPE") != "erofs" or identity.get("LABEL") != VOLUME_LABEL:
        raise CapsuleError("bootstrap capsule filesystem identity mismatch")
    if identity.get("UUID", "").lower() != expected_uuid:
        raise CapsuleError("bootstrap capsule deterministic UUID mismatch")
    return {
        "$schema": SCHEMA,
        "status": "candidate-verified",
        "image_sha256": sha256_file(image),
        "image_size": image.stat().st_size,
        "uuid": expected_uuid,
        "payload_entry_count": len(manifest["entries"]),
        "physical_write_authorized": False,
        "physical_boot_connected": False,
        "pid1_verified_mount_connected": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--release-agent", required=True, type=Path)
    b.add_argument("--out", required=True, type=Path)
    v = sub.add_parser("verify")
    v.add_argument("--release-agent", required=True, type=Path)
    v.add_argument("--image", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = (
            build(args.release_agent, args.out)
            if args.command == "build"
            else verify(args.release_agent, args.image)
        )
    except (CapsuleError, OSError, tarfile.TarError) as exc:
        print(f"portable-bootstrap-capsule: ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
