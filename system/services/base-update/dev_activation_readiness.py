#!/usr/bin/env python3
"""Validate that a staged development Base is coherent for a later activation.

This helper is evidence-only. It revalidates the exact development candidate,
versioned rootfs, persisted stage result and live read-only ESP layout. Passing
this gate does not authorize LoaderEntryOneShot, EFI variable writes, or reboot.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE.parents[2]
SCHEMA = "prototype-ordax.dev-base-activation-readiness/1"
MAX_STAGE_RESULT_BYTES = 64 * 1024


class ActivationReadinessError(RuntimeError):
    pass


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ActivationReadinessError(f"cannot load dependency: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_channel = _load(HERE / "dev_channel.py", "ordax_activation_readiness_channel")
_readonly = _load(HERE / "esp_readonly.py", "ordax_activation_readiness_esp")
_physical_stage = _load(
    HERE / "dev_physical_stage.py",
    "ordax_activation_readiness_physical_stage",
)


def _regular_file(path: Path, label: str, max_bytes: int) -> Path:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ActivationReadinessError(f"{label} is unavailable") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ActivationReadinessError(f"{label} must be a regular non-symlink file")
    if metadata.st_size <= 0 or metadata.st_size > max_bytes:
        raise ActivationReadinessError(f"{label} size is outside the allowed range")
    return path


def _read_sha(path: Path, expected: str) -> None:
    _regular_file(path, "staged SHA state", 256)
    try:
        value = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise ActivationReadinessError("staged SHA state cannot be read") from exc
    if value != expected:
        raise ActivationReadinessError("staged SHA does not match ready candidate")


def _read_stage_result(path: Path, source_commit: str) -> dict:
    _regular_file(path, "physical stage result", MAX_STAGE_RESULT_BYTES)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActivationReadinessError("physical stage result is invalid JSON") from exc
    if not isinstance(value, dict):
        raise ActivationReadinessError("physical stage result must be an object")
    if value.get("$schema") != "prototype-ordax.dev-base-physical-stage/1":
        raise ActivationReadinessError("physical stage result schema is invalid")
    if value.get("status") not in {"staged", "already-staged"}:
        raise ActivationReadinessError("physical stage result status is invalid")
    if value.get("source_commit") != source_commit:
        raise ActivationReadinessError("physical stage result commit does not match")
    if value.get("candidate_manifest_verified") is not True:
        raise ActivationReadinessError("physical stage did not verify candidate manifest")
    if value.get("versioned_rootfs_verified") is not True:
        raise ActivationReadinessError("physical stage did not verify versioned rootfs")
    if value.get("activation_ready") is not True:
        raise ActivationReadinessError("physical stage is not activation-ready")
    for key in ("activation_performed", "efi_variable_written", "reboot_requested"):
        if value.get(key) is not False:
            raise ActivationReadinessError(f"physical stage unexpectedly reports {key}")
    if value.get("candidate_slot") not in {"a", "b"}:
        raise ActivationReadinessError("physical stage candidate slot is invalid")
    if value.get("active_slot") not in {"legacy", "a", "b"}:
        raise ActivationReadinessError("physical stage active slot is invalid")
    return value


def activation_readiness(
    *,
    root_source: Path,
    mount_root: Path,
    candidate_root: Path,
    version_root: Path,
    source_commit: str,
    staged_sha_file: Path,
    stage_result_file: Path,
    dev_root: Path = Path("/dev"),
    by_label_root: Path = Path("/dev/disk/by-label"),
    sys_class_block: Path = Path("/sys/class/block"),
    mountinfo: Path = Path("/proc/self/mountinfo"),
    mount_command: Path = Path("/bin/mount"),
    umount_command: Path = Path("/bin/umount"),
) -> dict:
    try:
        _channel.candidate_tag(source_commit)
        manifest = _channel.verify_materialized(
            candidate_root / source_commit,
            source_commit,
        )
        _channel.verify_versioned_rootfs(
            version_root / source_commit,
            source_commit,
        )
    except _channel.DevBaseChannelError as exc:
        raise ActivationReadinessError(str(exc)) from exc

    _read_sha(staged_sha_file, source_commit)
    stage_result = _read_stage_result(stage_result_file, source_commit)

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
        raise ActivationReadinessError(str(exc)) from exc

    layout = preflight["layout"]
    if not layout["candidate_entry_present"]:
        raise ActivationReadinessError("staged candidate entry is absent from live ESP")
    if layout["candidate_release_sha"] != source_commit:
        raise ActivationReadinessError("live ESP candidate commit does not match")
    expected_slot = _physical_stage._expected_candidate_slot(
        layout["stage_active_slot"]
    )
    if layout["candidate_slot"] != expected_slot:
        raise ActivationReadinessError("live ESP candidate is not in the inactive slot")
    if stage_result["candidate_slot"] != expected_slot:
        raise ActivationReadinessError("stage result candidate slot differs from live ESP")
    if stage_result["active_slot"] != layout["stage_active_slot"]:
        raise ActivationReadinessError("stage result active slot differs from live ESP")

    # readonly_preflight validates entry paths and artifact presence. Reopen the
    # ESP read-only once more only to bind hashes to the exact manifest.
    try:
        discovered = _physical_stage._discovery.discover_esp(
            root_source=root_source,
            dev_root=dev_root,
            by_label_root=by_label_root,
            sys_class_block=sys_class_block,
        )
    except _physical_stage._discovery.EspDiscoveryError as exc:
        raise ActivationReadinessError(str(exc)) from exc

    esp_device = Path(discovered["esp_device"])
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
        "activation-readiness ESP mount",
    )
    try:
        current = _physical_stage._layout.inspect_layout(mount_root)
        if current["candidate_release_sha"] != source_commit:
            raise ActivationReadinessError("candidate changed during readiness validation")
        if current["candidate_slot"] != expected_slot:
            raise ActivationReadinessError("candidate slot changed during readiness validation")
        kernel = mount_root / f"ordax/base/{expected_slot}/vmlinuz"
        initramfs = mount_root / f"ordax/base/{expected_slot}/initrd.gz"
        if _physical_stage._sha256(kernel) != manifest["kernel"]["sha256"]:
            raise ActivationReadinessError("live staged kernel hash does not match manifest")
        if _physical_stage._sha256(initramfs) != manifest["initramfs"]["sha256"]:
            raise ActivationReadinessError("live staged initramfs hash does not match manifest")
    finally:
        _readonly._run_mount_command(
            [str(umount_command), str(mount_root)],
            "ESP unmount",
        )

    if _readonly._mount_record(mountinfo, mount_root) is not None:
        raise ActivationReadinessError("ESP remained mounted after readiness validation")

    return {
        "$schema": SCHEMA,
        "status": "ready",
        "source_commit": source_commit,
        "active_slot": layout["stage_active_slot"],
        "candidate_slot": expected_slot,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-source", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--version-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--staged-sha-file", type=Path, required=True)
    parser.add_argument("--stage-result-file", type=Path, required=True)
    parser.add_argument(
        "--mount-root",
        type=Path,
        default=Path("/run/ordax-base-owner/esp-activation-readiness"),
    )
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
        result = activation_readiness(
            root_source=args.root_source,
            mount_root=args.mount_root,
            candidate_root=args.candidate_root,
            version_root=args.version_root,
            source_commit=args.source_commit,
            staged_sha_file=args.staged_sha_file,
            stage_result_file=args.stage_result_file,
            dev_root=args.dev_root,
            by_label_root=args.by_label_root,
            sys_class_block=args.sys_class_block,
            mountinfo=args.mountinfo,
        )
    except ActivationReadinessError as exc:
        print(f"dev-base-activation-readiness: ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
