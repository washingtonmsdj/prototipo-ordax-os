#!/usr/bin/env python3
"""Direct-kernel QEMU proof for the durable OrdaX portable-v2 PID1 handoff.

This proof deliberately does not prove UEFI. It creates one sparse regular RAW
disk with ORDAX-ESP + ORDAX-DATA, stages already-built real candidate artifacts,
boots the exact OrdaX kernel/initramfs with rdinit=/sbin/ordax-portable-init,
requires the portable PID1 and Stable Base handoff serial markers, disables
networking, and destroys the guest disk afterward. No physical target device is
accepted or retained.
"""

from __future__ import annotations

import argparse
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
import time
from typing import Any

SCHEMA = "prototype-ordax.portable-v2-qemu-boot-proof-result/1"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DISK_BYTES = 3 * 1024 * 1024 * 1024
ESP_BYTES = 512 * 1024 * 1024
SUCCESS = "ORDAX_PORTABLE_V2_HANDOFF=VERIFIED"
STABLE = "ORDAX_STABLE_INIT_HANDOFF=VERIFIED"


class ProofError(RuntimeError):
    pass


def run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ProofError(f"cannot execute {' '.join(argv)}: {exc}") from exc
    if check and result.returncode != 0:
        raise ProofError(
            f"command failed ({result.returncode}): {' '.join(argv)}: "
            f"stdout={result.stdout.decode('utf-8', 'replace')!r} "
            f"stderr={result.stderr.decode('utf-8', 'replace')!r}"
        )
    return result


def capture(argv: list[str]) -> str:
    return run(argv).stdout.decode("utf-8", "replace").strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular(path: Path, label: str, *, minimum: int = 1) -> Path:
    absolute = path.resolve()
    if str(absolute).startswith("/dev/"):
        raise ProofError(f"{label} must never be a device path")
    try:
        info = absolute.lstat()
    except OSError as exc:
        raise ProofError(f"cannot stat {label}: {exc}") from exc
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_size < minimum
    ):
        raise ProofError(f"{label} must be a regular non-symlink single-link file")
    return absolute


def real_dir(path: Path, label: str) -> Path:
    absolute = path.resolve()
    try:
        info = absolute.lstat()
    except OSError as exc:
        raise ProofError(f"cannot stat {label}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ProofError(f"{label} must be a real directory")
    return absolute


def load_json(path: Path, label: str) -> dict[str, Any]:
    path = regular(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProofError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProofError(f"{label} must be a JSON object")
    return value


def require_programs() -> None:
    names = (
        "sgdisk", "losetup", "mkfs.vfat", "mkfs.exfat", "mount.exfat-fuse",
        "mount", "umount", "qemu-system-x86_64",
    )
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise ProofError("missing portable-v2 QEMU proof programs: " + ", ".join(missing))


def wait_block(path: Path, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if path.is_block_device():
                return
        except OSError:
            pass
        time.sleep(0.1)
    raise ProofError(f"loop partition did not appear: {path}")


def unmount(path: Path) -> None:
    subprocess.run(
        ["umount", "-l", str(path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def validate_inputs(args: argparse.Namespace) -> dict[str, Any]:
    if COMMIT_RE.fullmatch(args.source_commit) is None:
        raise ProofError("source commit must be lowercase 40-hex")
    kernel = regular(args.kernel, "kernel", minimum=1024 * 1024)
    initramfs = regular(args.initramfs, "pinned initramfs", minimum=1024)
    capsule = regular(args.capsule, "bootstrap capsule", minimum=4096)
    base = regular(args.stable_base, "Stable Base", minimum=4096)
    state = regular(args.state_image, "persistent-state image", minimum=16 * 1024 * 1024)
    trust = regular(args.trust, "release trust", minimum=2)
    portable = real_dir(args.portable_root, "portable release root")
    provenance = load_json(args.initramfs_provenance, "initramfs provenance")

    if provenance.get("$schema") != "prototype-ordax.initramfs-provenance/1":
        raise ProofError("unexpected initramfs provenance schema")
    if provenance.get("source_commit") != args.source_commit:
        raise ProofError("initramfs source commit differs from QEMU source")
    if provenance.get("promotable_to_physical") is not False:
        raise ProofError("pinned initramfs unexpectedly authorizes physical promotion")

    capsule_pin = provenance.get("portable_bootstrap_capsule_pin")
    base_pin = provenance.get("portable_stable_base_pin")
    if not isinstance(capsule_pin, dict) or capsule_pin.get("provided") is not True:
        raise ProofError("initramfs does not contain a real capsule pin")
    if not isinstance(base_pin, dict) or base_pin.get("provided") is not True:
        raise ProofError("initramfs does not contain a real Stable Base pin")
    if capsule_pin.get("sha256") != sha256_file(capsule):
        raise ProofError("initramfs capsule pin differs from staged capsule")
    if base_pin.get("sha256") != sha256_file(base):
        raise ProofError("initramfs Stable Base pin differs from staged base")
    if capsule_pin.get("pid1_enforced") is not False or base_pin.get("pid1_enforced") is not False:
        raise ProofError("candidate pin provenance crossed its promotion boundary")

    release = portable / "releases" / args.source_commit
    if release.is_symlink() or not release.is_dir():
        raise ProofError("exact portable release directory is missing")
    for name in ("system.erofs", "release-manifest.json", "release-envelope.json"):
        regular(release / name, f"portable release {name}", minimum=2)
    return {
        "kernel": kernel,
        "initramfs": initramfs,
        "capsule": capsule,
        "stable_base": base,
        "state_image": state,
        "trust": trust,
        "portable_root": portable,
        "provenance": provenance,
    }


def stage_disk(args: argparse.Namespace, inputs: dict[str, Any], work: Path) -> Path:
    disk = work / "portable-v2-qemu.raw"
    with disk.open("wb") as handle:
        handle.truncate(DISK_BYTES)
    regular(disk, "disposable guest disk", minimum=DISK_BYTES)

    run(["sgdisk", "--zap-all", str(disk)])
    run([
        "sgdisk",
        "--new=1:2048:+512M",
        "--typecode=1:c12a7328-f81f-11d2-ba4b-00a0c93ec93b",
        "--change-name=1:ORDAX-ESP",
        str(disk),
    ])
    run([
        "sgdisk",
        "--new=2:0:0",
        "--typecode=2:ebd0a0a2-b9e5-4433-87c0-68b6b72699c7",
        "--change-name=2:ORDAX-DATA",
        str(disk),
    ])
    run(["sgdisk", "--verify", str(disk)])

    loop = ""
    esp_mounted = False
    data_mounted = False
    esp_mount = work / "esp"
    data_mount = work / "data"
    esp_mount.mkdir()
    data_mount.mkdir()
    try:
        loop = capture(["losetup", "--find", "--show", "--partscan", str(disk)])
        if not loop.startswith("/dev/loop"):
            raise ProofError("disposable guest disk did not map to a host loop device")
        esp = Path(loop + "p1")
        data = Path(loop + "p2")
        wait_block(esp)
        wait_block(data)
        run(["mkfs.vfat", "-F", "32", "-n", "ORDAX-ESP", str(esp)])
        run(["mkfs.exfat", "-L", "ORDAX-DATA", str(data)])

        run(["mount", "-t", "vfat", "-o", "rw,umask=0022", str(esp), str(esp_mount)])
        esp_mounted = True
        capsule_target = esp_mount / "ordax/bootstrap/bootstrap.erofs"
        trust_target = esp_mount / "ordax/bootstrap/trust/release-ed25519.json"
        capsule_target.parent.mkdir(parents=True)
        trust_target.parent.mkdir(parents=True)
        shutil.copyfile(inputs["capsule"], capsule_target)
        shutil.copyfile(inputs["trust"], trust_target)

        run(["mount.exfat-fuse", str(data), str(data_mount)])
        data_mounted = True
        internal = data_mount / ".ordax"
        (internal / "base").mkdir(parents=True)
        (internal / "state").mkdir(parents=True)
        (internal / "releases").mkdir(parents=True)
        shutil.copyfile(inputs["stable_base"], internal / "base/stable-base.erofs")
        shutil.copyfile(inputs["state_image"], internal / "state/persistent-state.img")
        shutil.copytree(
            inputs["portable_root"] / "releases" / args.source_commit,
            internal / "releases" / args.source_commit,
            symlinks=False,
        )
        os.sync()
    finally:
        if data_mounted:
            unmount(data_mount)
        if esp_mounted:
            unmount(esp_mount)
        if loop:
            run(["losetup", "-d", loop])

    return disk


def boot_qemu(args: argparse.Namespace, inputs: dict[str, Any], disk: Path, work: Path) -> tuple[str, dict[str, bool]]:
    serial = work / "serial.log"
    stderr = work / "qemu.stderr"
    command = [
        "qemu-system-x86_64",
        "-machine", "pc",
        "-accel", "tcg,thread=multi",
        "-m", "1536",
        "-smp", "2",
        "-kernel", str(inputs["kernel"]),
        "-initrd", str(inputs["initramfs"]),
        "-append", "console=ttyS0 rdinit=/sbin/ordax-portable-init loglevel=6",
        "-drive", f"file={disk},format=raw,if=ide,index=0,media=disk",
        "-display", "none",
        "-serial", f"file:{serial}",
        "-monitor", "none",
        "-net", "none",
        "-no-reboot",
    ]
    with stderr.open("wb") as error_stream:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=error_stream,
        )
    try:
        deadline = time.monotonic() + 150.0
        while time.monotonic() < deadline:
            text = serial.read_text(encoding="utf-8", errors="replace") if serial.exists() else ""
            source_marker = "ORDAX_PORTABLE_V2_SOURCE_SHA=" + args.source_commit
            stable_source_marker = "ORDAX_STABLE_INIT_SOURCE_SHA=" + args.source_commit
            slot_marker = "ORDAX_PORTABLE_V2_SLOT=current"
            if (
                SUCCESS in text
                and STABLE in text
                and source_marker in text
                and stable_source_marker in text
                and slot_marker in text
            ):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                checks = {
                    "portable_pid1_handoff_marker": True,
                    "stable_init_handoff_marker": True,
                    "qemu_network_disabled": "-net" in command and "none" in command,
                    "candidate_rdinit_used": any("rdinit=/sbin/ordax-portable-init" in item for item in command),
                    "current_slot_selected": slot_marker in text,
                    "portable_source_sha_exact": source_marker in text,
                    "stable_init_source_sha_exact": stable_source_marker in text,
                }
                return text, checks
            if process.poll() is not None:
                break
            time.sleep(0.25)

        tail = stderr.read_text(encoding="utf-8", errors="replace")[-4000:] if stderr.exists() else ""
        serial_tail = serial.read_text(encoding="utf-8", errors="replace")[-12000:] if serial.exists() else ""
        raise ProofError(
            "QEMU did not reach portable-v2 handoff markers "
            f"(exit={process.poll()}, stderr_tail={tail!r}, serial_tail={serial_tail!r})"
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def prove(args: argparse.Namespace) -> dict[str, Any]:
    if os.name != "posix" or os.geteuid() != 0:
        raise ProofError("portable-v2 QEMU proof requires root on POSIX CI")
    require_programs()
    inputs = validate_inputs(args)
    work = Path(tempfile.mkdtemp(prefix="ordax-portable-v2-qemu-"))
    disk: Path | None = None
    checks = {
        "real_pinned_inputs_bound": True,
        "regular_sparse_guest_disk_only": False,
        "final_two_partition_layout": False,
        "portable_pid1_handoff_marker": False,
        "stable_init_handoff_marker": False,
        "qemu_network_disabled": False,
        "candidate_rdinit_used": False,
        "current_slot_selected": False,
        "portable_source_sha_exact": False,
        "stable_init_source_sha_exact": False,
        "physical_target_device_untouched": True,
        "guest_disk_destroyed": False,
    }
    try:
        disk = stage_disk(args, inputs, work)
        checks["regular_sparse_guest_disk_only"] = True
        checks["final_two_partition_layout"] = True
        serial_text, qemu_checks = boot_qemu(args, inputs, disk, work)
        checks.update(qemu_checks)
        disk_sha = sha256_file(disk)
        disk.unlink()
        checks["guest_disk_destroyed"] = not disk.exists()
        if not all(checks.values()):
            raise ProofError(f"portable-v2 QEMU checks incomplete: {checks}")

        result = {
            "$schema": SCHEMA,
            "status": "pass",
            "source_commit": args.source_commit,
            "physical_target_device_touched": False,
            "host_loop_devices_used": True,
            "physical_write_authorized": False,
            "qemu_direct_kernel_boot_proven": True,
            "qemu_uefi_boot_proven": False,
            "physical_usb_boot_proven": False,
            "public_physical_promotion_allowed": False,
            "candidate_pid1_default_changed": False,
            "network_required_for_first_boot": False,
            "serial_markers": [
                SUCCESS,
                STABLE,
                "ORDAX_PORTABLE_V2_SLOT=current",
                "ORDAX_PORTABLE_V2_SOURCE_SHA=" + args.source_commit,
                "ORDAX_STABLE_INIT_SOURCE_SHA=" + args.source_commit,
            ],
            "guest_disk": {
                "sha256_before_destruction": disk_sha,
                "retained": False,
                "layout": ["ORDAX-ESP", "ORDAX-DATA"],
            },
            "artifacts": {
                "kernel_sha256": sha256_file(inputs["kernel"]),
                "initramfs_sha256": sha256_file(inputs["initramfs"]),
                "capsule_sha256": sha256_file(inputs["capsule"]),
                "stable_base_sha256": sha256_file(inputs["stable_base"]),
                "state_image_sha256": sha256_file(inputs["state_image"]),
            },
            "checks": checks,
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
    finally:
        if disk is not None and disk.exists():
            disk.unlink()
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", required=True, type=Path)
    parser.add_argument("--initramfs", required=True, type=Path)
    parser.add_argument("--initramfs-provenance", required=True, type=Path)
    parser.add_argument("--capsule", required=True, type=Path)
    parser.add_argument("--stable-base", required=True, type=Path)
    parser.add_argument("--state-image", required=True, type=Path)
    parser.add_argument("--portable-root", required=True, type=Path)
    parser.add_argument("--trust", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    for name in (
        "kernel", "initramfs", "initramfs_provenance", "capsule",
        "stable_base", "state_image", "portable_root", "trust", "out",
    ):
        setattr(args, name, getattr(args, name).resolve())
    try:
        result = prove(args)
    except (ProofError, OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"portable-v2-qemu-boot-proof: ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    print("PORTABLE_V2_QEMU_DIRECT_KERNEL_BOOT_PROOF=PASS")
    print("PORTABLE_V2_UEFI_BOOT_PROVEN=NO")
    print("PORTABLE_V2_PHYSICAL_BOOT_PROVEN=NO")
    print("PORTABLE_V2_PHYSICAL_WRITE_AUTHORIZED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
