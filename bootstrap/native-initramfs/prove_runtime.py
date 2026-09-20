#!/usr/bin/env python3
"""Disposable runtime proof for the packaged OrdaX Native initramfs userspace.

This proof does not boot a kernel and never opens a physical disk. It verifies
that the exact candidate archive can execute its packaged cryptsetup, BusyBox
mount, and btrfs tooling against a regular-file-backed LUKS2 container.
"""

from __future__ import annotations

import argparse
import errno
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any

SCHEMA = "prototype-ordax.native-initramfs-runtime-proof/1"
PROVENANCE_SCHEMA = "prototype-ordax.native-initramfs-provenance/1"
UUID_RE = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
POOL_BYTES = 384 * 1024 * 1024
SUBVOLUMES = (
    "ordax-state",
    "ordax-home",
    "ordax-apps",
    "ordax-containers",
    "ordax-snapshots",
)


class ProofError(RuntimeError):
    pass


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[Any]:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise ProofError(f"cannot execute {' '.join(argv)}: {exc}") from exc
    if check and completed.returncode != 0:
        raise ProofError(
            f"command failed ({completed.returncode}): {' '.join(argv)}: "
            f"stdout={completed.stdout.decode('utf-8', 'replace')!r} "
            f"stderr={completed.stderr.decode('utf-8', 'replace')!r}"
        )
    return completed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ProofError(f"cannot stat {label}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ProofError(f"{label} must be a regular non-symlink file")


def load_json(path: Path, label: str) -> dict[str, Any]:
    regular(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProofError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProofError(f"{label} must be a JSON object")
    return value


def require_tools() -> None:
    missing = [
        name for name in ("cpio", "chroot", "mount", "umount", "mkfs.btrfs")
        if shutil.which(name) is None
    ]
    if missing:
        raise ProofError("missing disposable proof tools: " + ", ".join(missing))


def verify_candidate(archive: Path, provenance_path: Path) -> dict[str, Any]:
    regular(archive, "Native initramfs candidate")
    provenance = load_json(provenance_path, "Native initramfs provenance")
    if provenance.get("$schema") != PROVENANCE_SCHEMA:
        raise ProofError("unexpected Native initramfs provenance schema")
    if provenance.get("physical_artifact_authorized") is not False:
        raise ProofError("candidate provenance crossed physical authorization boundary")
    artifact = provenance.get("artifact")
    if not isinstance(artifact, dict):
        raise ProofError("candidate provenance artifact record is missing")
    if artifact.get("name") != archive.name:
        raise ProofError("candidate provenance artifact name mismatch")
    expected_hash = artifact.get("sha256")
    expected_size = artifact.get("size")
    if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
        raise ProofError("candidate provenance artifact hash is invalid")
    if not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size <= 0:
        raise ProofError("candidate provenance artifact size is invalid")
    if archive.stat().st_size != expected_size:
        raise ProofError("candidate artifact size differs from provenance")
    if sha256_file(archive) != expected_hash:
        raise ProofError("candidate artifact hash differs from provenance")
    source_commit = provenance.get("source_commit")
    if not isinstance(source_commit, str) or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        raise ProofError("candidate provenance source commit is invalid")
    return provenance


def safe_archive_entries(archive: Path) -> list[str]:
    with gzip.open(archive, "rb") as handle:
        raw = handle.read()
    listing = run(["cpio", "-it", "--quiet"], input_bytes=raw).stdout.decode("utf-8")
    entries = [line.strip() for line in listing.splitlines() if line.strip()]
    if not entries:
        raise ProofError("candidate cpio archive is empty")
    for item in entries:
        normalized = item[2:] if item.startswith("./") else item
        path = Path(normalized)
        if item.startswith("/") or not normalized or ".." in path.parts or "\x00" in item:
            raise ProofError(f"unsafe candidate archive entry: {item!r}")
    return entries


def extract_candidate(archive: Path, root: Path) -> None:
    entries = safe_archive_entries(archive)
    with gzip.open(archive, "rb") as handle:
        raw = handle.read()
    run(["cpio", "-idmu", "--quiet"], cwd=root, input_bytes=raw)
    for required in ("init", "bin/busybox", "usr/sbin/cryptsetup", "usr/bin/btrfs"):
        path = root / required
        regular(path, f"packaged {required}")
        if required != "init" and not os.access(path, os.X_OK):
            raise ProofError(f"packaged runtime is not executable: {required}")
    normalized_entries = {e[2:] if e.startswith("./") else e for e in entries}
    if "init" not in normalized_entries:
        raise ProofError("candidate archive did not contain init")


def chroot_run(root: Path, argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[Any]:
    return run(["chroot", str(root), *argv], check=check)


def mount_bind(source: str, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    run(["mount", "--rbind", source, str(target)])
    run(["mount", "--make-rslave", str(target)])


def cleanup_mount(target: Path) -> None:
    subprocess.run(
        ["umount", "-R", "-l", str(target)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def prove(archive: Path, provenance_path: Path, output: Path) -> dict[str, Any]:
    if os.geteuid() != 0:
        raise ProofError("runtime proof must run as root inside a private mount namespace")
    require_tools()
    provenance = verify_candidate(archive, provenance_path)
    work = Path(tempfile.mkdtemp(prefix="ordax-native-initramfs-runtime-"))
    root = work / "rootfs"
    root.mkdir()
    mapper = f"ordax_initrd_proof_{os.getpid()}"
    mapper_path = Path("/dev/mapper") / mapper
    mapper_open = False
    pool: Path | None = None
    key: Path | None = None
    checks = {
        "candidate_provenance_verified": False,
        "packaged_cryptsetup_luks2": False,
        "packaged_btrfs_subvolume_operations": False,
        "product_mode_readback": False,
        "readonly_reopen": False,
        "readonly_mount_rejects_write": False,
        "ephemeral_key_destroyed": False,
        "disposable_container_destroyed": False,
    }
    public_uuid = ""
    try:
        extract_candidate(archive, root)
        checks["candidate_provenance_verified"] = True

        for directory in ("dev", "proc", "sys", "proof", "mnt"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        mount_bind("/dev", root / "dev")
        mount_bind("/proc", root / "proc")
        mount_bind("/sys", root / "sys")

        pool = root / "proof" / "pool.luks2"
        key = root / "proof" / "key"
        with pool.open("wb") as handle:
            handle.truncate(POOL_BYTES)
        key.write_bytes(os.urandom(64))
        key.chmod(0o600)

        chroot_run(root, [
            "/usr/sbin/cryptsetup", "luksFormat",
            "--type", "luks2",
            "--batch-mode",
            "--pbkdf", "pbkdf2",
            "--key-file", "/proof/key",
            "/proof/pool.luks2",
        ])
        chroot_run(root, [
            "/usr/sbin/cryptsetup", "isLuks",
            "--type", "luks2",
            "/proof/pool.luks2",
        ])
        public_uuid = chroot_run(root, [
            "/usr/sbin/cryptsetup", "luksUUID", "/proof/pool.luks2",
        ]).stdout.decode("utf-8").strip().lower()
        if UUID_RE.fullmatch(public_uuid) is None:
            raise ProofError("packaged cryptsetup returned invalid LUKS2 UUID")

        chroot_run(root, [
            "/usr/sbin/cryptsetup", "open",
            "--type", "luks2",
            "--key-file", "/proof/key",
            "/proof/pool.luks2",
            mapper,
        ])
        mapper_open = True
        if not mapper_path.is_block_device():
            raise ProofError("packaged cryptsetup did not create dm-crypt mapper")
        checks["packaged_cryptsetup_luks2"] = True

        run(["mkfs.btrfs", "-f", "-L", "ORDAX-POOL", str(mapper_path)])
        chroot_run(root, [
            "/bin/mount", "-t", "btrfs", "-o", "rw,subvolid=5",
            f"/dev/mapper/{mapper}", "/mnt",
        ])
        for name in SUBVOLUMES:
            chroot_run(root, ["/usr/bin/btrfs", "subvolume", "create", f"/mnt/{name}"])
        listing = chroot_run(root, ["/usr/bin/btrfs", "subvolume", "list", "/mnt"]).stdout.decode("utf-8")
        for name in SUBVOLUMES:
            if re.search(rf"\bpath {re.escape(name)}$", listing, re.MULTILINE) is None:
                raise ProofError(f"packaged btrfs did not read back subvolume: {name}")
        checks["packaged_btrfs_subvolume_operations"] = True

        marker = root / "mnt" / "bootstrap" / "config" / "product-mode"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("native-disk\n", encoding="utf-8")
        os.sync()
        if marker.read_text(encoding="utf-8") != "native-disk\n":
            raise ProofError("Native product mode readback failed before remount")
        checks["product_mode_readback"] = True

        chroot_run(root, ["/bin/umount", "/mnt"])
        chroot_run(root, ["/usr/sbin/cryptsetup", "close", mapper])
        mapper_open = False

        chroot_run(root, [
            "/usr/sbin/cryptsetup", "open",
            "--readonly",
            "--type", "luks2",
            "--key-file", "/proof/key",
            "/proof/pool.luks2",
            mapper,
        ])
        mapper_open = True
        chroot_run(root, [
            "/bin/mount", "-t", "btrfs", "-o", "ro,subvolid=5",
            f"/dev/mapper/{mapper}", "/mnt",
        ])
        if marker.read_text(encoding="utf-8") != "native-disk\n":
            raise ProofError("Native product mode readback failed after read-only reopen")
        listing = chroot_run(root, ["/usr/bin/btrfs", "subvolume", "list", "/mnt"]).stdout.decode("utf-8")
        for name in SUBVOLUMES:
            if re.search(rf"\bpath {re.escape(name)}$", listing, re.MULTILINE) is None:
                raise ProofError(f"read-only reopen lost subvolume: {name}")
        checks["readonly_reopen"] = True

        try:
            (root / "mnt" / ".ordax-write-probe").write_text("forbidden\n", encoding="utf-8")
        except OSError as exc:
            if exc.errno != errno.EROFS:
                raise
            checks["readonly_mount_rejects_write"] = True
        else:
            raise ProofError("read-only Btrfs mount unexpectedly accepted a write")

        chroot_run(root, ["/bin/umount", "/mnt"])
        chroot_run(root, ["/usr/sbin/cryptsetup", "close", mapper])
        mapper_open = False

        key.unlink()
        checks["ephemeral_key_destroyed"] = not key.exists()
        pool.unlink()
        checks["disposable_container_destroyed"] = not pool.exists()
        if not all(checks.values()):
            raise ProofError(f"runtime proof checks incomplete: {checks}")

        result = {
            "$schema": SCHEMA,
            "status": "pass",
            "candidate_source_commit": provenance["source_commit"],
            "candidate_artifact_sha256": provenance["artifact"]["sha256"],
            "candidate_artifact_size": provenance["artifact"]["size"],
            "public_ephemeral_luks_uuid": public_uuid,
            "physical_device_touched": False,
            "physical_write_authorized": False,
            "qemu_uefi_boot_proven": False,
            "pid1_kernel_cmdline_boot_proven": False,
            "expected_pool_label": "ORDAX-POOL",
            "subvolumes": list(SUBVOLUMES),
            "product_mode": "native-disk",
            "checks": checks,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
    finally:
        cleanup_mount(root / "mnt")
        if mapper_open:
            subprocess.run(
                ["chroot", str(root), "/usr/sbin/cryptsetup", "close", mapper],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if mapper_path.exists() and shutil.which("cryptsetup"):
                subprocess.run(
                    ["cryptsetup", "close", mapper],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        for target in (root / "sys", root / "proc", root / "dev"):
            cleanup_mount(target)
        if key is not None:
            try:
                key.unlink()
            except FileNotFoundError:
                pass
        if pool is not None:
            try:
                pool.unlink()
            except FileNotFoundError:
                pass
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prove(
            args.candidate.resolve(),
            args.provenance.resolve(),
            args.out.resolve(),
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        print("NATIVE_INITRAMFS_RUNTIME_PROOF=PASS")
        print("NATIVE_INITRAMFS_QEMU_UEFI_BOOT_PROVEN=NO")
        print("NATIVE_INITRAMFS_PHYSICAL_WRITE_AUTHORIZED=NO")
        return 0
    except (ProofError, OSError, json.JSONDecodeError) as exc:
        print(f"native-initramfs-runtime-proof: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
