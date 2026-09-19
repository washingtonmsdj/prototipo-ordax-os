#!/usr/bin/env python3
"""Arm an exact development Base candidate for one boot attempt.

This helper is intentionally not wired into the persistent owner yet. It
requires exact staged/readiness state, revalidates the candidate manifest,
versioned rootfs and live ORDAX-ESP read-only, then delegates the single efivar
write to bootstrap/base-update/activate.py. It never changes ESP bytes and
never requests reboot.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import stat
import sys

HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE.parents[2]
SCHEMA = "prototype-ordax.dev-base-activation-arm/1"
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_STATE_BYTES = 64 * 1024
RO_MOUNT_OPTIONS = {"ro", "nosuid", "nodev", "noexec"}


class DevelopmentActivationArmError(RuntimeError):
    pass


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DevelopmentActivationArmError(
            f"cannot load dependency: {path.name}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_channel = _load(HERE / "dev_channel.py", "ordax_dev_activation_arm_channel")
_readonly = _load(HERE / "esp_readonly.py", "ordax_dev_activation_arm_esp")
_layout = _load(HERE / "esp_layout.py", "ordax_dev_activation_arm_layout")
_activate = _load(
    SOURCE_ROOT / "bootstrap/base-update/activate.py",
    "ordax_dev_activation_arm_activate",
)


def _regular_file(path: Path, label: str, max_bytes: int = MAX_STATE_BYTES) -> Path:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise DevelopmentActivationArmError(f"{label} is unavailable") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise DevelopmentActivationArmError(
            f"{label} must be a regular non-symlink file"
        )
    if metadata.st_size <= 0 or metadata.st_size > max_bytes:
        raise DevelopmentActivationArmError(
            f"{label} size is outside the allowed range"
        )
    return path


def _read_exact_sha(path: Path, label: str, expected: str) -> None:
    _regular_file(path, label, 256)
    try:
        value = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise DevelopmentActivationArmError(f"{label} cannot be read") from exc
    if value != expected:
        raise DevelopmentActivationArmError(f"{label} does not match candidate")


def _read_readiness(path: Path, source_commit: str) -> dict:
    _regular_file(path, "activation readiness state")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DevelopmentActivationArmError(
            "activation readiness state is invalid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise DevelopmentActivationArmError(
            "activation readiness state must be an object"
        )
    required = {
        "$schema": "prototype-ordax.dev-base-activation-readiness/1",
        "status": "ready",
        "source_commit": source_commit,
        "candidate_manifest_verified": True,
        "versioned_rootfs_verified": True,
        "persisted_stage_result_verified": True,
        "live_esp_candidate_verified": True,
        "live_kernel_hash_verified": True,
        "live_initramfs_hash_verified": True,
        "mount_released": True,
        "ready_for_activation_gate": True,
        "activation_authorized": False,
        "runtime_activation_wiring_enabled": False,
        "efi_variable_written": False,
        "reboot_requested": False,
        "blocker": "runtime-activation-wiring-disabled",
    }
    for key, expected in required.items():
        if value.get(key) != expected:
            raise DevelopmentActivationArmError(
                f"activation readiness field is invalid: {key}"
            )
    if value.get("candidate_slot") not in {"a", "b"}:
        raise DevelopmentActivationArmError(
            "activation readiness candidate slot is invalid"
        )
    if value.get("active_slot") not in {"legacy", "a", "b"}:
        raise DevelopmentActivationArmError(
            "activation readiness active slot is invalid"
        )
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise DevelopmentActivationArmError(
            f"cannot hash live candidate artifact: {path.name}"
        ) from exc
    return digest.hexdigest()


def arm_ready_candidate(
    *,
    root_source: Path,
    mount_root: Path,
    efivarfs_root: Path,
    candidate_root: Path,
    version_root: Path,
    source_commit: str,
    staged_sha_file: Path,
    readiness_sha_file: Path,
    readiness_file: Path,
    dev_root: Path = Path("/dev"),
    by_label_root: Path = Path("/dev/disk/by-label"),
    sys_class_block: Path = Path("/sys/class/block"),
    mountinfo: Path = Path("/proc/self/mountinfo"),
    mount_command: Path = Path("/bin/mount"),
    umount_command: Path = Path("/bin/umount"),
) -> dict:
    if SHA40_RE.fullmatch(source_commit) is None:
        raise DevelopmentActivationArmError("candidate SHA is invalid")

    _read_exact_sha(staged_sha_file, "staged SHA state", source_commit)
    _read_exact_sha(
        readiness_sha_file,
        "activation readiness SHA state",
        source_commit,
    )
    readiness = _read_readiness(readiness_file, source_commit)

    try:
        manifest = _channel.verify_materialized(
            candidate_root / source_commit,
            source_commit,
        )
        _channel.verify_versioned_rootfs(
            version_root / source_commit,
            source_commit,
        )
    except _channel.DevBaseChannelError as exc:
        raise DevelopmentActivationArmError(str(exc)) from exc

    try:
        preflight = _readonly.readonly_preflight(
            root_source=root_source,
            mount_root=mount_root,
            dev_root=dev_root,
            by_label_root=by_label_root,
            sys_class_block=sys_class_block,
            mountinfo=mountinfo,
            mount_command=mount_command,
            umount_command=umount_command,
        )
    except _readonly.EspReadonlyPreflightError as exc:
        raise DevelopmentActivationArmError(str(exc)) from exc

    layout = preflight["layout"]
    candidate_slot = readiness["candidate_slot"]
    if not layout["candidate_entry_present"]:
        raise DevelopmentActivationArmError(
            "live ESP no longer contains a candidate entry"
        )
    if layout["candidate_release_sha"] != source_commit:
        raise DevelopmentActivationArmError(
            "live ESP candidate SHA changed after readiness"
        )
    if layout["candidate_slot"] != candidate_slot:
        raise DevelopmentActivationArmError(
            "live ESP candidate slot changed after readiness"
        )

    esp_device = Path(preflight["esp_device"])
    _readonly._run_mount_command(
        [
            str(mount_command),
            "-t",
            "vfat",
            "-o",
            "ro,nosuid,nodev,noexec",
            str(esp_device),
            str(mount_root),
        ],
        "development activation ESP mount",
    )

    armed = None
    try:
        record = _readonly._mount_record(mountinfo, mount_root)
        if record is None:
            raise DevelopmentActivationArmError(
                "activation ESP mount is not observable"
            )
        if record["root"] != "/" or record["filesystem"] != "vfat":
            raise DevelopmentActivationArmError(
                "activation ESP mount identity is invalid"
            )
        if record["source"] != str(esp_device):
            raise DevelopmentActivationArmError(
                "activation ESP mount source changed"
            )
        if not RO_MOUNT_OPTIONS.issubset(record["options"]):
            raise DevelopmentActivationArmError(
                "activation ESP mount is not sufficiently restricted"
            )

        current = _layout.inspect_layout(mount_root)
        for key in (
            "layout",
            "stage_active_slot",
            "active_slot",
            "recovery_slot",
            "candidate_entry_present",
            "candidate_slot",
            "candidate_release_sha",
        ):
            if current.get(key) != layout.get(key):
                raise DevelopmentActivationArmError(
                    "ESP layout changed during activation validation"
                )

        kernel = mount_root / f"ordax/base/{candidate_slot}/vmlinuz"
        initramfs = mount_root / f"ordax/base/{candidate_slot}/initrd.gz"
        if _sha256(kernel) != manifest["kernel"]["sha256"]:
            raise DevelopmentActivationArmError(
                "live staged kernel hash differs from candidate manifest"
            )
        if _sha256(initramfs) != manifest["initramfs"]["sha256"]:
            raise DevelopmentActivationArmError(
                "live staged initramfs hash differs from candidate manifest"
            )

        try:
            armed = _activate.arm(
                mount_root,
                efivarfs_root,
                source_commit,
                candidate_slot,
            )
        except _activate.ActivateError as exc:
            raise DevelopmentActivationArmError(str(exc)) from exc

        if armed.get("armed") is not True:
            raise DevelopmentActivationArmError(
                "one-shot activation helper did not arm candidate"
            )
        if armed.get("default_entry_changed") is not False:
            raise DevelopmentActivationArmError(
                "one-shot activation changed default entry"
            )
        if armed.get("reboot_requested") is not False:
            raise DevelopmentActivationArmError(
                "one-shot activation unexpectedly requested reboot"
            )
    finally:
        _readonly._run_mount_command(
            [str(umount_command), str(mount_root)],
            "ESP unmount",
        )

    if _readonly._mount_record(mountinfo, mount_root) is not None:
        raise DevelopmentActivationArmError(
            "ESP remained mounted after one-shot activation"
        )

    return {
        "$schema": SCHEMA,
        "status": "armed",
        "source_commit": source_commit,
        "candidate_slot": candidate_slot,
        "entry_id": armed["entry_id"],
        "selector": armed["selector"],
        "staged_sha_verified": True,
        "readiness_sha_verified": True,
        "readiness_state_verified": True,
        "candidate_manifest_revalidated": True,
        "versioned_rootfs_revalidated": True,
        "live_esp_revalidated": True,
        "live_kernel_hash_revalidated": True,
        "live_initramfs_hash_revalidated": True,
        "esp_mounted_read_only": True,
        "mount_released": True,
        "default_entry_changed": False,
        "efi_variable_written": True,
        "reboot_requested": False,
        "runtime_owner_wiring_enabled": False,
        "automatic_reboot_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-source", type=Path, required=True)
    parser.add_argument("--mount-root", type=Path, required=True)
    parser.add_argument("--efivarfs-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--version-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--staged-sha-file", type=Path, required=True)
    parser.add_argument("--readiness-sha-file", type=Path, required=True)
    parser.add_argument("--readiness-file", type=Path, required=True)
    parser.add_argument("--dev-root", type=Path, default=Path("/dev"))
    parser.add_argument(
        "--by-label-root",
        type=Path,
        default=Path("/dev/disk/by-label"),
    )
    parser.add_argument(
        "--sys-class-block",
        type=Path,
        default=Path("/sys/class/block"),
    )
    parser.add_argument(
        "--mountinfo",
        type=Path,
        default=Path("/proc/self/mountinfo"),
    )
    args = parser.parse_args()

    try:
        result = arm_ready_candidate(
            root_source=args.root_source,
            mount_root=args.mount_root,
            efivarfs_root=args.efivarfs_root,
            candidate_root=args.candidate_root,
            version_root=args.version_root,
            source_commit=args.source_commit,
            staged_sha_file=args.staged_sha_file,
            readiness_sha_file=args.readiness_sha_file,
            readiness_file=args.readiness_file,
            dev_root=args.dev_root,
            by_label_root=args.by_label_root,
            sys_class_block=args.sys_class_block,
            mountinfo=args.mountinfo,
        )
    except DevelopmentActivationArmError as exc:
        print(f"dev-base-activation-arm: ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
