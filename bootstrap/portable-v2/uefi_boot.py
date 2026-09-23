#!/usr/bin/env python3
"""OVMF/UEFI proof for the durable OrdaX portable-v2 boot candidate."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any

HERE = Path(__file__).resolve().parent
DIRECT_PATH = HERE / "qemu_boot.py"
spec = importlib.util.spec_from_file_location("ordax_portable_direct_qemu", DIRECT_PATH)
direct = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(direct)

SCHEMA = "prototype-ordax.portable-v2-uefi-boot-proof-result/1"
SUCCESS = "ORDAX_PORTABLE_V2_HANDOFF=VERIFIED"
STABLE = "ORDAX_STABLE_INIT_HANDOFF=VERIFIED"


class ProofError(RuntimeError):
    pass


def run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(argv, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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


def regular(path: Path, label: str, *, minimum: int = 1) -> Path:
    absolute = path.resolve()
    if str(absolute).startswith("/dev/"):
        raise ProofError(f"{label} must never be a device path")
    try:
        info = absolute.lstat()
    except OSError as exc:
        raise ProofError(f"cannot stat {label}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size < minimum:
        raise ProofError(f"{label} must be a regular non-symlink single-link file")
    return absolute


def find_ovmf() -> tuple[Path, Path]:
    pairs = (
        (Path("/usr/share/OVMF/OVMF_CODE.fd"), Path("/usr/share/OVMF/OVMF_VARS.fd")),
        (Path("/usr/share/OVMF/OVMF_CODE_4M.fd"), Path("/usr/share/OVMF/OVMF_VARS_4M.fd")),
    )
    for code, variables in pairs:
        try:
            resolved_code = code.resolve(strict=True)
            resolved_vars = variables.resolve(strict=True)
        except OSError:
            continue
        if resolved_code.is_file() and resolved_vars.is_file():
            return resolved_code, resolved_vars
    raise ProofError("non-Secure-Boot OVMF CODE/VARS pair not found")


def validate_loader(loader_conf: Path, normal_entry: Path, recovery_entry: Path) -> None:
    loader_conf = regular(loader_conf, "portable loader.conf")
    normal_entry = regular(normal_entry, "portable normal loader entry")
    recovery_entry = regular(recovery_entry, "portable recovery loader entry")
    loader = loader_conf.read_text(encoding="utf-8")
    if "default ordax-portable.conf" not in loader or "editor no" not in loader:
        raise ProofError("portable loader.conf does not pin the noninteractive default entry")
    normal = normal_entry.read_text(encoding="utf-8")
    required = ("linux /ordax/vmlinuz", "initrd /ordax/initrd.gz", "rdinit=/sbin/ordax-portable-init", "console=ttyS0")
    for marker in required:
        if marker not in normal:
            raise ProofError(f"portable normal loader entry is missing {marker!r}")
    for marker in ("native-disk", "installer", "ordax.mode=recovery"):
        if marker in normal:
            raise ProofError(f"portable normal loader entry contains forbidden marker {marker!r}")
    recovery = recovery_entry.read_text(encoding="utf-8")
    for marker in required:
        if marker not in recovery:
            raise ProofError(f"portable recovery loader entry is missing {marker!r}")
    if "ordax.mode=recovery" not in recovery:
        raise ProofError("portable recovery entry does not request read-only recovery")


def stage_uefi(disk: Path, *, bootloader: Path, kernel: Path, initramfs: Path, loader_conf: Path, normal_entry: Path, recovery_entry: Path, work: Path) -> None:
    loop = ""
    mounted = False
    mountpoint = work / "uefi-esp"
    mountpoint.mkdir()
    try:
        loop = capture(["losetup", "--find", "--show", "--partscan", str(disk)])
        if not loop.startswith("/dev/loop"):
            raise ProofError("disposable guest disk did not map to a host loop device")
        esp = Path(loop + "p1")
        direct.wait_block(esp)
        run(["mount", "-t", "vfat", "-o", "rw,umask=0022", str(esp), str(mountpoint)])
        mounted = True
        targets = {
            "EFI/BOOT/BOOTX64.EFI": bootloader,
            "loader/loader.conf": loader_conf,
            "loader/entries/ordax-portable.conf": normal_entry,
            "loader/entries/ordax-portable-recovery.conf": recovery_entry,
            "ordax/vmlinuz": kernel,
            "ordax/initrd.gz": initramfs,
        }
        for relative, source in targets.items():
            source = regular(source, f"UEFI source {relative}")
            destination = mountpoint / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        if not (mountpoint / "ordax/bootstrap/bootstrap.erofs").is_file():
            raise ProofError("portable bootstrap capsule disappeared while staging UEFI")
        if not (mountpoint / "ordax/bootstrap/trust/release-ed25519.json").is_file():
            raise ProofError("portable release trust disappeared while staging UEFI")
        run(["sync"])
    finally:
        if mounted:
            direct.unmount(mountpoint)
        if loop:
            run(["losetup", "-d", loop])


def boot_ovmf(
    disk: Path,
    *,
    release_info: dict[str, Any],
    code: Path,
    vars_template: Path,
    work: Path,
) -> tuple[str, str, dict[str, bool]]:
    source_commit = release_info["commit"]
    runtime_sha256 = release_info["runtime_sha256"]
    schema_version = release_info["manifest_schema"]
    ai_runtime_sha256 = release_info["ai_runtime_sha256"]
    ai_required = schema_version == 4

    vars_copy = work / "OVMF_VARS.fd"
    shutil.copyfile(vars_template, vars_copy)
    serial = work / "uefi-serial.log"
    stderr = work / "uefi-qemu.stderr"
    command = [
        "qemu-system-x86_64",
        "-machine", "pc",
        "-accel", "tcg,thread=multi",
        "-m", "1536",
        "-smp", "2",
        "-drive", f"if=pflash,format=raw,readonly=on,file={code}",
        "-drive", f"if=pflash,format=raw,file={vars_copy}",
        "-drive", f"file={disk},format=raw,if=ide,index=0,media=disk",
        "-boot", "order=c,menu=off",
        "-display", "none",
        "-serial", f"file:{serial}",
        "-monitor", "none",
        "-net", "none",
        "-no-reboot",
    ]
    with stderr.open("wb") as error_stream:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=error_stream)
    try:
        deadline = time.monotonic() + 180.0
        while time.monotonic() < deadline:
            text = serial.read_text(encoding="utf-8", errors="replace") if serial.exists() else ""
            source_marker = "ORDAX_PORTABLE_V2_SOURCE_SHA=" + source_commit
            stable_source = "ORDAX_STABLE_INIT_SOURCE_SHA=" + source_commit
            slot = "ORDAX_PORTABLE_V2_SLOT=current"
            schema_marker = f"ORDAX_PORTABLE_RELEASE_MANIFEST_SCHEMA={schema_version}"
            runtime_marker = "ORDAX_SURFACE_RUNTIME_HANDOFF=VERIFIED"
            runtime_sha_marker = "ORDAX_SURFACE_RUNTIME_SHA256=" + runtime_sha256
            ai_marker = "ORDAX_LOCAL_AI_RUNTIME_HANDOFF=VERIFIED"
            ai_sha_marker = (
                "ORDAX_LOCAL_AI_RUNTIME_SHA256=" + ai_runtime_sha256
                if ai_runtime_sha256
                else ""
            )
            ai_ok = not ai_required or (
                ai_marker in text
                and bool(ai_sha_marker)
                and ai_sha_marker in text
            )
            if (
                SUCCESS in text
                and STABLE in text
                and source_marker in text
                and stable_source in text
                and slot in text
                and schema_marker in text
                and runtime_marker in text
                and runtime_sha_marker in text
                and ai_ok
            ):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                return text, direct.sha256_file(vars_copy), {
                    "ovmf_loaded_portable_chain": True,
                    "portable_pid1_handoff_marker": True,
                    "stable_init_handoff_marker": True,
                    "current_slot_selected": True,
                    "portable_source_sha_exact": True,
                    "stable_init_source_sha_exact": True,
                    "portable_manifest_selected": True,
                    "surface_runtime_handoff_marker": True,
                    "surface_runtime_sha_exact": True,
                    "local_ai_runtime_requirement_satisfied": ai_ok,
                    "local_ai_runtime_handoff_marker": (ai_marker in text) if ai_required else True,
                    "local_ai_runtime_sha_exact": (ai_sha_marker in text) if ai_required else True,
                    "qemu_network_disabled": "-net" in command and "none" in command,
                }
            if process.poll() is not None:
                break
            time.sleep(0.25)
        stderr_tail = stderr.read_text(encoding="utf-8", errors="replace")[-5000:] if stderr.exists() else ""
        serial_tail = serial.read_text(encoding="utf-8", errors="replace")[-14000:] if serial.exists() else ""
        raise ProofError(
            "OVMF QEMU did not reach portable-v2 handoff markers "
            f"(schema={schema_version}, exit={process.poll()}, "
            f"stderr_tail={stderr_tail!r}, serial_tail={serial_tail!r})"
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
    if direct.os.name != "posix" or direct.os.geteuid() != 0:
        raise ProofError("portable-v2 UEFI proof requires root on POSIX CI")
    direct.require_programs()
    code, vars_template = find_ovmf()
    inputs = direct.validate_inputs(args)
    bootloader = regular(args.bootloader, "pinned systemd-boot", minimum=64 * 1024)
    validate_loader(args.loader_conf, args.normal_entry, args.recovery_entry)

    work = Path(tempfile.mkdtemp(prefix="ordax-portable-v2-uefi-"))
    disk: Path | None = None
    checks = {
        "real_pinned_inputs_bound": True,
        "final_two_partition_layout": False,
        "fallback_efi_path_staged": False,
        "dedicated_portable_loader_entries_staged": False,
        "ovmf_loaded_portable_chain": False,
        "portable_pid1_handoff_marker": False,
        "stable_init_handoff_marker": False,
        "current_slot_selected": False,
        "portable_source_sha_exact": False,
        "stable_init_source_sha_exact": False,
        "portable_manifest_selected": False,
        "surface_runtime_handoff_marker": False,
        "surface_runtime_sha_exact": False,
        "local_ai_runtime_requirement_satisfied": False,
        "local_ai_runtime_handoff_marker": False,
        "local_ai_runtime_sha_exact": False,
        "qemu_network_disabled": False,
        "physical_target_device_untouched": True,
        "guest_disk_destroyed": False,
        "ovmf_vars_destroyed": False,
    }
    vars_sha = ""
    try:
        disk = direct.stage_disk(args, inputs, work)
        checks["final_two_partition_layout"] = True
        stage_uefi(
            disk,
            bootloader=bootloader,
            kernel=inputs["kernel"],
            initramfs=inputs["initramfs"],
            loader_conf=args.loader_conf,
            normal_entry=args.normal_entry,
            recovery_entry=args.recovery_entry,
            work=work,
        )
        checks["fallback_efi_path_staged"] = True
        checks["dedicated_portable_loader_entries_staged"] = True
        _, vars_sha, qemu_checks = boot_ovmf(
            disk,
            release_info=inputs["candidate"],
            code=code,
            vars_template=vars_template,
            work=work,
        )
        checks.update(qemu_checks)

        disk_sha = direct.sha256_file(disk)
        disk.unlink()
        checks["guest_disk_destroyed"] = not disk.exists()
        vars_copy = work / "OVMF_VARS.fd"
        vars_copy.unlink(missing_ok=True)
        checks["ovmf_vars_destroyed"] = not vars_copy.exists()
        if not all(checks.values()):
            raise ProofError(f"portable-v2 UEFI checks incomplete: {checks}")

        result = {
            "$schema": SCHEMA,
            "status": "pass",
            "source_commit": args.source_commit,
            "firmware": "ovmf-non-secure-boot-ci-only",
            "secure_boot_proven": False,
            "qemu_direct_kernel_prerequisite": True,
            "qemu_uefi_boot_proven": True,
            "physical_usb_boot_proven": False,
            "public_physical_promotion_allowed": False,
            "physical_target_device_touched": False,
            "physical_write_authorized": False,
            "network_required_for_first_boot": False,
            "candidate_pid1_default_changed": False,
            "guest_disk": {"sha256_before_destruction": disk_sha, "retained": False, "layout": ["ORDAX-ESP", "ORDAX-DATA"]},
            "ovmf_vars": {"sha256_before_destruction": vars_sha, "retained": False},
            "artifacts": {
                "systemd_boot_sha256": direct.sha256_file(bootloader),
                "kernel_sha256": direct.sha256_file(inputs["kernel"]),
                "initramfs_sha256": direct.sha256_file(inputs["initramfs"]),
                "capsule_sha256": direct.sha256_file(inputs["capsule"]),
                "stable_base_sha256": direct.sha256_file(inputs["stable_base"]),
                "state_image_sha256": direct.sha256_file(inputs["state_image"]),
                "surface_runtime_sha256": direct.sha256_file(inputs["runtime"]),
                "release_manifest_schema": inputs["manifest_schema"],
                "local_ai_runtime_sha256": (
                    direct.sha256_file(inputs["ai_runtime"])
                    if inputs["ai_runtime"] is not None
                    else None
                ),
            },
            "serial_markers": [
                SUCCESS,
                STABLE,
                "ORDAX_PORTABLE_V2_SLOT=current",
                "ORDAX_PORTABLE_V2_SOURCE_SHA=" + args.source_commit,
                "ORDAX_STABLE_INIT_SOURCE_SHA=" + args.source_commit,
                "ORDAX_PORTABLE_RELEASE_MANIFEST_SCHEMA=" + str(inputs["manifest_schema"]),
                "ORDAX_SURFACE_RUNTIME_HANDOFF=VERIFIED",
                "ORDAX_SURFACE_RUNTIME_SHA256=" + inputs["runtime_sha256"],
            ] + (
                [
                    "ORDAX_LOCAL_AI_RUNTIME_HANDOFF=VERIFIED",
                    "ORDAX_LOCAL_AI_RUNTIME_SHA256=" + inputs["ai_runtime_sha256"],
                ]
                if inputs["manifest_schema"] == 4
                else []
            ),
            "checks": checks,
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
    finally:
        if disk is not None and disk.exists():
            disk.unlink()
        (work / "OVMF_VARS.fd").unlink(missing_ok=True)
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
    parser.add_argument("--bootloader", required=True, type=Path)
    parser.add_argument("--loader-conf", required=True, type=Path)
    parser.add_argument("--normal-entry", required=True, type=Path)
    parser.add_argument("--recovery-entry", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    for name in (
        "kernel", "initramfs", "initramfs_provenance", "capsule", "stable_base",
        "state_image", "portable_root", "trust", "bootloader", "loader_conf",
        "normal_entry", "recovery_entry", "out",
    ):
        setattr(args, name, getattr(args, name).resolve())
    try:
        result = prove(args)
    except (ProofError, direct.ProofError, OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"portable-v2-uefi-boot-proof: ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    print("PORTABLE_V2_QEMU_UEFI_BOOT_PROOF=PASS")
    print("PORTABLE_V2_SECURE_BOOT_PROVEN=NO")
    print("PORTABLE_V2_PHYSICAL_BOOT_PROVEN=NO")
    print("PORTABLE_V2_PUBLIC_PROMOTION=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
