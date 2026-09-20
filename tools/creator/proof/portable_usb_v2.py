#!/usr/bin/env python3
"""Prove the durable OrdaX portable-USB v2 storage layout on a disposable RAW file.

The command accepts no device path. It creates one regular sparse RAW file,
attaches only that file through a host loop device, formats real FAT32/exFAT
filesystems, stores a real EROFS release image and an ext4 persistent-state
image inside ORDAX-DATA, then remounts the data partition read-only and
re-verifies the contained bytes. It never authorizes physical writes.
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
import tempfile
import time
from typing import Any

SCHEMA = "prototype-ordax.portable-usb-v2/1"
PLAN_PROFILE = "portable-usb"
ESP_GUID = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
DATA_GUID = "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7"
REQUIRED_TOOLS = (
    "sgdisk",
    "losetup",
    "mkfs.vfat",
    "mkfs.exfat",
    "mkfs.erofs",
    "fsck.erofs",
    "mkfs.ext4",
    "e2fsck",
    "debugfs",
    "blkid",
    "mount",
    "umount",
)


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


def require_root_and_tools() -> None:
    if os.name != "posix" or os.geteuid() != 0:
        raise ProofError("portable USB v2 disposable proof requires root on a POSIX CI host")
    missing = [name for name in REQUIRED_TOOLS if shutil.which(name) is None]
    if missing:
        raise ProofError("missing portable USB v2 proof tools: " + ", ".join(missing))


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ProofError(f"cannot stat {label}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ProofError(f"{label} must be a regular non-symlink file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProofError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProofError(f"{label} must be a JSON object")
    return value


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("$schema") != SCHEMA:
        raise ProofError("unsupported portable USB v2 contract schema")
    if contract.get("status") != "disposable-proof-only":
        raise ProofError("portable USB v2 contract must remain disposable-proof-only")
    if contract.get("physical_write_authorized") is not False:
        raise ProofError("portable USB v2 contract must not authorize physical write")
    if contract.get("physical_device_paths_allowed") is not False:
        raise ProofError("portable USB v2 proof must reject physical device paths")
    if contract.get("host_loop_devices_allowed") is not True:
        raise ProofError("portable USB v2 proof requires bounded host-loop permission")
    if contract.get("bootable_proven") is not False:
        raise ProofError("storage proof must not claim bootability")
    if contract.get("logical_sector_bytes") != 512:
        raise ProofError("portable USB v2 logical sector size must be 512")
    if contract.get("alignment_bytes") != 1024 * 1024:
        raise ProofError("portable USB v2 alignment must be 1 MiB")
    target = contract.get("target_bytes")
    if not isinstance(target, int) or target < 2 * 1024 * 1024 * 1024 or target % 512:
        raise ProofError("portable USB v2 disposable target capacity is invalid")

    parts = contract.get("partitions")
    if not isinstance(parts, list) or len(parts) != 2:
        raise ProofError("portable USB v2 must contain exactly two partitions")
    esp, data = parts
    if [esp.get("name"), data.get("name")] != ["ORDAX-ESP", "ORDAX-DATA"]:
        raise ProofError("portable USB v2 partition names are not canonical")
    if [esp.get("filesystem"), data.get("filesystem")] != ["fat32", "exfat"]:
        raise ProofError("portable USB v2 filesystem types are not canonical")
    if str(esp.get("gpt_type_guid", "")).lower() != ESP_GUID:
        raise ProofError("portable USB v2 ESP type GUID is invalid")
    if str(data.get("gpt_type_guid", "")).lower() != DATA_GUID:
        raise ProofError("portable USB v2 data type GUID is invalid")
    if esp.get("start_lba") != 2048 or esp.get("size_bytes") != 512 * 1024 * 1024:
        raise ProofError("portable USB v2 ESP geometry is invalid")
    if data.get("size_policy") != "fill-all-remaining-usable-capacity":
        raise ProofError("portable USB v2 data partition must fill remaining capacity")
    if data.get("direct_overlayfs_upper") is not False:
        raise ProofError("exFAT must never be used directly as OverlayFS upper")

    internal = contract.get("ordax_internal_layout")
    if not isinstance(internal, dict):
        raise ProofError("portable USB v2 internal layout is missing")
    release = internal.get("release_image")
    state = internal.get("persistent_state_image")
    if not isinstance(release, dict) or release.get("filesystem") != "erofs":
        raise ProofError("portable USB v2 release image must be EROFS")
    if release.get("read_only") is not True or release.get("compressed") is not True:
        raise ProofError("portable USB v2 EROFS release must be compressed/read-only")
    if not isinstance(state, dict) or state.get("filesystem") != "ext4":
        raise ProofError("portable USB v2 persistent state must be ext4")
    if state.get("filesystem_label") != "ORDAX-STATE":
        raise ProofError("portable USB v2 persistent state label is invalid")
    if state.get("overlayfs_upper_owner") is not True:
        raise ProofError("portable USB v2 persistent state must own OverlayFS upper")
    if not isinstance(state.get("size_bytes"), int) or state["size_bytes"] < 128 * 1024 * 1024:
        raise ProofError("portable USB v2 state image is too small for proof")


def validate_plan(plan: dict[str, Any], contract: dict[str, Any]) -> None:
    if plan.get("profile") != PLAN_PROFILE:
        raise ProofError("Creator plan is not portable-usb")
    if plan.get("target_bytes") != contract["target_bytes"]:
        raise ProofError("Creator plan target capacity differs from contract")
    if plan.get("esp_start_lba") != contract["partitions"][0]["start_lba"]:
        raise ProofError("Creator plan ESP start differs from contract")
    if plan.get("esp_bytes") != contract["partitions"][0]["size_bytes"]:
        raise ProofError("Creator plan ESP size differs from contract")
    if plan.get("payload_name") != "ORDAX-DATA":
        raise ProofError("Creator plan payload must be ORDAX-DATA")
    if plan.get("payload_last_lba") != plan.get("last_usable_lba"):
        raise ProofError("Creator portable data area must fill all usable capacity")
    if plan.get("payload_start_lba", 0) % (1024 * 1024 // 512):
        raise ProofError("Creator portable data area is not 1 MiB aligned")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_blkid(path: Path) -> dict[str, str]:
    output = capture(["blkid", "-p", "-o", "export", str(path)])
    result: dict[str, str] = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def wait_block(path: Path, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if path.is_block_device():
                return
        except OSError:
            pass
        time.sleep(0.1)
    raise ProofError(f"loop partition did not appear: {path}")


def partition_info(raw: Path, index: int) -> dict[str, Any]:
    text = capture(["sgdisk", f"--info={index}", str(raw)])
    def match(pattern: str, label: str) -> str:
        value = re.search(pattern, text)
        if value is None:
            raise ProofError(f"cannot parse GPT {label} for partition {index}")
        return value.group(1)
    first = int(match(r"First sector:\s+(\d+)", "first LBA"))
    last = int(match(r"Last sector:\s+(\d+)", "last LBA"))
    return {
        "name": match(r"Partition name:\s+'([^']*)'", "name"),
        "type_guid": match(r"Partition GUID code:\s+([0-9A-Fa-f-]{36})", "type GUID").lower(),
        "first_lba": first,
        "last_lba": last,
        "sector_count": last - first + 1,
    }


def unmount(path: Path) -> None:
    subprocess.run(["umount", "-l", str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_proof(contract_path: Path, plan_path: Path, output_root: Path) -> dict[str, Any]:
    require_root_and_tools()
    contract = load_json(contract_path.resolve(), "portable USB v2 contract")
    plan = load_json(plan_path.resolve(), "Creator portable plan")
    validate_contract(contract)
    validate_plan(plan, contract)

    output_root = output_root.resolve()
    if str(output_root).startswith("/dev/"):
        raise ProofError("output root must never be a device path")
    if output_root.exists():
        if output_root.is_symlink() or not output_root.is_dir() or any(output_root.iterdir()):
            raise ProofError("output root must be an absent or empty real directory")
    else:
        output_root.mkdir(parents=True)

    work = Path(tempfile.mkdtemp(prefix="ordax-portable-v2-", dir=str(output_root.parent)))
    raw = output_root / "portable-usb-v2.raw"
    esp_mount = work / "esp"
    data_mount = work / "data"
    verify_data_mount = work / "data-ro"
    release_root = work / "release-root"
    release_image = work / "proof-system.erofs"
    state_image = work / "persistent-state.img"
    state_marker = work / "state-marker.txt"
    loop = ""
    data_mounted = False
    esp_mounted = False
    data_ro_mounted = False

    checks = {
        "regular_sparse_raw_file_only": False,
        "gpt_valid": False,
        "exactly_two_partitions": False,
        "planner_geometry_matches_contract": False,
        "fat32_esp_identity": False,
        "exfat_data_identity": False,
        "no_fixed_physical_system_partition": False,
        "real_erofs_release_image": False,
        "real_ext4_persistent_state_image": False,
        "state_image_is_overlay_owner_not_exfat": False,
        "user_file_coexists_with_internal_data": False,
        "read_only_remount_reverified_hashes": False,
        "physical_device_untouched": True,
        "physical_write_unauthorized": True,
    }

    try:
        with raw.open("wb") as handle:
            handle.truncate(contract["target_bytes"])
        info = raw.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise ProofError("disposable RAW target is not a regular file")
        checks["regular_sparse_raw_file_only"] = True

        run(["sgdisk", "--zap-all", str(raw)])
        run([
            "sgdisk",
            f"--new=1:{plan['esp_start_lba']}:{plan['esp_last_lba']}",
            f"--typecode=1:{ESP_GUID}",
            "--change-name=1:ORDAX-ESP",
            str(raw),
        ])
        run([
            "sgdisk",
            f"--new=2:{plan['payload_start_lba']}:{plan['payload_last_lba']}",
            f"--typecode=2:{DATA_GUID}",
            "--change-name=2:ORDAX-DATA",
            str(raw),
        ])
        run(["sgdisk", "--verify", str(raw)])
        checks["gpt_valid"] = True

        p1_info = partition_info(raw, 1)
        p2_info = partition_info(raw, 2)
        if p1_info["name"] != "ORDAX-ESP" or p2_info["name"] != "ORDAX-DATA":
            raise ProofError("portable USB v2 GPT names differ from plan")
        if p1_info["type_guid"] != ESP_GUID or p2_info["type_guid"] != DATA_GUID:
            raise ProofError("portable USB v2 GPT type GUID differs from contract")
        if p1_info["first_lba"] != plan["esp_start_lba"] or p1_info["last_lba"] != plan["esp_last_lba"]:
            raise ProofError("portable USB v2 ESP geometry differs from Creator plan")
        if p2_info["first_lba"] != plan["payload_start_lba"] or p2_info["last_lba"] != plan["payload_last_lba"]:
            raise ProofError("portable USB v2 DATA geometry differs from Creator plan")
        checks["exactly_two_partitions"] = True
        checks["planner_geometry_matches_contract"] = True
        checks["no_fixed_physical_system_partition"] = True

        loop = capture(["losetup", "--find", "--show", "--partscan", str(raw)])
        if not loop.startswith("/dev/loop"):
            raise ProofError("disposable RAW did not map to a host loop device")
        esp = Path(loop + "p1")
        data = Path(loop + "p2")
        wait_block(esp)
        wait_block(data)

        run(["mkfs.vfat", "-F", "32", "-n", "ORDAX-ESP", str(esp)])
        run(["mkfs.exfat", "-L", "ORDAX-DATA", str(data)])
        esp_id = parse_blkid(esp)
        data_id = parse_blkid(data)
        if esp_id.get("TYPE") != "vfat" or esp_id.get("LABEL") != "ORDAX-ESP":
            raise ProofError("portable USB v2 ESP filesystem identity mismatch")
        if data_id.get("TYPE") != "exfat" or data_id.get("LABEL") != "ORDAX-DATA":
            raise ProofError("portable USB v2 DATA filesystem identity mismatch")
        checks["fat32_esp_identity"] = True
        checks["exfat_data_identity"] = True

        esp_mount.mkdir()
        data_mount.mkdir()
        run(["mount", str(esp), str(esp_mount)])
        esp_mounted = True
        run(["mount", str(data), str(data_mount)])
        data_mounted = True

        (esp_mount / "ordax").mkdir()
        (esp_mount / "ordax/storage-v2-proof.txt").write_text(
            "ORDAX_PORTABLE_USB_V2_STORAGE=PROOF_ONLY\n",
            encoding="utf-8",
        )

        (release_root / "usr/lib/ordax").mkdir(parents=True)
        (release_root / "etc").mkdir()
        release_marker = b"ORDAX_PORTABLE_USB_V2_RELEASE=PASS\n"
        (release_root / "usr/lib/ordax/proof-release.txt").write_bytes(release_marker)
        (release_root / "etc/ordax-release").write_text(
            "mode=usb\nstorage=portable-v2\n",
            encoding="utf-8",
        )
        run(["mkfs.erofs", "-zlz4", str(release_image), str(release_root)])
        run(["fsck.erofs", str(release_image)])
        release_id = parse_blkid(release_image)
        if release_id.get("TYPE") != "erofs":
            raise ProofError("portable USB v2 release artifact is not EROFS")
        release_sha = sha256_file(release_image)
        checks["real_erofs_release_image"] = True

        state_bytes = contract["ordax_internal_layout"]["persistent_state_image"]["size_bytes"]
        with state_image.open("wb") as handle:
            handle.truncate(state_bytes)
        run(["mkfs.ext4", "-q", "-F", "-L", "ORDAX-STATE", str(state_image)])
        state_marker.write_text("ORDAX_PORTABLE_USB_V2_STATE=PASS\n", encoding="utf-8")
        run(["debugfs", "-w", "-R", "mkdir /upper", str(state_image)])
        run(["debugfs", "-w", "-R", "mkdir /work", str(state_image)])
        run(["debugfs", "-w", "-R", "mkdir /home", str(state_image)])
        run([
            "debugfs",
            "-w",
            "-R",
            f"write {state_marker} /ordax-state-proof.txt",
            str(state_image),
        ])
        run(["e2fsck", "-fn", str(state_image)])
        state_id = parse_blkid(state_image)
        if state_id.get("TYPE") != "ext4" or state_id.get("LABEL") != "ORDAX-STATE":
            raise ProofError("portable USB v2 persistent-state image identity mismatch")
        state_sha = sha256_file(state_image)
        checks["real_ext4_persistent_state_image"] = True
        checks["state_image_is_overlay_owner_not_exfat"] = True

        releases = data_mount / ".ordax/releases"
        state_dir = data_mount / ".ordax/state"
        releases.mkdir(parents=True)
        state_dir.mkdir(parents=True)
        release_target = releases / "proof-system.erofs"
        state_target = state_dir / "persistent-state.img"
        shutil.copyfile(release_image, release_target)
        shutil.copyfile(state_image, state_target)
        user_file = data_mount / "USER-FILES-STAY-HERE.txt"
        user_file.write_text(
            "This file represents user-visible capacity outside .ordax.\n",
            encoding="utf-8",
        )
        os.sync()
        checks["user_file_coexists_with_internal_data"] = True

        unmount(data_mount)
        data_mounted = False
        unmount(esp_mount)
        esp_mounted = False

        verify_data_mount.mkdir()
        run(["mount", "-o", "ro", str(data), str(verify_data_mount)])
        data_ro_mounted = True
        verified_release = verify_data_mount / ".ordax/releases/proof-system.erofs"
        verified_state = verify_data_mount / ".ordax/state/persistent-state.img"
        verified_user = verify_data_mount / "USER-FILES-STAY-HERE.txt"
        if sha256_file(verified_release) != release_sha:
            raise ProofError("EROFS release image changed after exFAT materialization")
        if sha256_file(verified_state) != state_sha:
            raise ProofError("ext4 state image changed after exFAT materialization")
        if "user-visible capacity" not in verified_user.read_text(encoding="utf-8"):
            raise ProofError("portable user file is missing after read-only remount")
        if parse_blkid(verified_release).get("TYPE") != "erofs":
            raise ProofError("contained release image lost EROFS identity")
        contained_state = parse_blkid(verified_state)
        if contained_state.get("TYPE") != "ext4" or contained_state.get("LABEL") != "ORDAX-STATE":
            raise ProofError("contained persistent-state image lost ext4 identity")
        marker = capture(["debugfs", "-R", "cat /ordax-state-proof.txt", str(verified_state)])
        if marker != "ORDAX_PORTABLE_USB_V2_STATE=PASS":
            raise ProofError("contained persistent-state marker verification failed")
        run(["fsck.erofs", str(verified_release)])
        run(["e2fsck", "-fn", str(verified_state)])
        checks["read_only_remount_reverified_hashes"] = True

        proof = {
            "$schema": "prototype-ordax.portable-usb-v2-proof-result/1",
            "status": "pass",
            "source_contract": str(contract_path),
            "creator_plan_profile": plan["profile"],
            "target_bytes": contract["target_bytes"],
            "physical_write_authorized": False,
            "physical_device_touched": False,
            "host_loop_devices_used": True,
            "bootable_proven": False,
            "mvp_boot_handoff_connected": False,
            "partitions": [
                {
                    "name": "ORDAX-ESP",
                    "type_guid": p1_info["type_guid"],
                    "first_lba": p1_info["first_lba"],
                    "last_lba": p1_info["last_lba"],
                    "filesystem": {"type": "vfat", "label": "ORDAX-ESP"},
                },
                {
                    "name": "ORDAX-DATA",
                    "type_guid": p2_info["type_guid"],
                    "first_lba": p2_info["first_lba"],
                    "last_lba": p2_info["last_lba"],
                    "filesystem": {"type": "exfat", "label": "ORDAX-DATA"},
                },
            ],
            "contained_artifacts": {
                "release": {
                    "path": ".ordax/releases/proof-system.erofs",
                    "filesystem": "erofs",
                    "sha256": release_sha,
                    "compressed": True,
                    "read_only": True,
                },
                "persistent_state": {
                    "path": ".ordax/state/persistent-state.img",
                    "filesystem": "ext4",
                    "filesystem_label": "ORDAX-STATE",
                    "sha256": state_sha,
                    "overlayfs_upper_owner": True,
                },
            },
            "checks": checks,
        }
        if not all(checks.values()):
            raise ProofError("portable USB v2 proof has incomplete checks")
        proof_path = output_root / "proof.json"
        proof_path.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return proof
    finally:
        if data_ro_mounted:
            unmount(verify_data_mount)
        if data_mounted:
            unmount(data_mount)
        if esp_mounted:
            unmount(esp_mount)
        if loop:
            subprocess.run(
                ["losetup", "-d", loop],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        proof = build_proof(args.contract, args.plan, args.output_root)
    except ProofError as exc:
        print(f"portable-usb-v2-proof: ERROR: {exc}", file=os.sys.stderr)
        return 1
    print("PORTABLE_USB_V2_STORAGE_PROOF=PASS")
    print("PARTITIONS=ORDAX-ESP,ORDAX-DATA")
    print("FILESYSTEMS=FAT32,EXFAT")
    print("RELEASE_IMAGE=EROFS")
    print("PERSISTENT_STATE_IMAGE=EXT4")
    print("BOOTABLE_PROVEN=NO")
    print("PHYSICAL_WRITE_AUTHORIZED=NO")
    print(f"PROOF_CHECKS={len(proof['checks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
