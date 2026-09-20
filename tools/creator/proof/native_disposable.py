#!/usr/bin/env python3
"""Disposable proof for the durable OrdaX Native storage layout.

The proof consumes the Creator Core materialization plan and operates only on
new regular files. It deliberately never accepts a physical block-device path.
The produced RAW image is ephemeral CI evidence, not installation media.
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

SCHEMA = "prototype-ordax.native-disposable-proof/1"
PLAN_SCHEMA = "prototype-ordax.native-materialization-plan/1"
ESP_GUID = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
LUKS_GUID = "ca7d7ccb-63ed-4c53-861c-1742536059cc"
REQUIRED_TOOLS = (
    "sgdisk",
    "mkfs.vfat",
    "blkid",
    "cryptsetup",
    "mkfs.btrfs",
    "btrfs",
    "mount",
    "umount",
    "dd",
)
MAX_PROOF_BYTES = 8 * 1024 * 1024 * 1024


class ProofError(RuntimeError):
    pass


def run(args: list[str], *, text: bool = True) -> subprocess.CompletedProcess[Any]:
    try:
        return subprocess.run(
            args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=text,
        )
    except subprocess.CalledProcessError as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else exc.stdout
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else exc.stderr
        raise ProofError(
            f"command failed ({' '.join(args)}): stdout={stdout!r} stderr={stderr!r}"
        ) from exc


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ProofError(f"cannot stat {label}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ProofError(f"{label} must be a regular non-symlink file")
    if info.st_size <= 0 or info.st_size > 1024 * 1024:
        raise ProofError(f"{label} has an invalid size")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProofError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProofError(f"{label} must be a JSON object")
    return value


def require_tools() -> None:
    missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        raise ProofError("missing Native disposable proof tools: " + ", ".join(missing))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_region(path: Path, offset: int, length: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        handle.seek(offset)
        remaining = length
        while remaining:
            chunk = handle.read(min(4 * 1024 * 1024, remaining))
            if not chunk:
                raise ProofError("RAW image ended before partition region")
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def safe_output_root(value: Path) -> Path:
    path = value.absolute()
    if str(path).startswith("/dev/") or str(path) == "/dev":
        raise ProofError("physical /dev paths are forbidden")
    parent = path.parent
    try:
        parent_info = parent.lstat()
    except OSError as exc:
        raise ProofError(f"cannot stat output parent: {exc}") from exc
    if stat.S_ISLNK(parent_info.st_mode) or not stat.S_ISDIR(parent_info.st_mode):
        raise ProofError("output parent must be a real directory")
    if path.exists() or path.is_symlink():
        try:
            info = path.lstat()
        except OSError as exc:
            raise ProofError(f"cannot stat output root: {exc}") from exc
        if stat.S_ISBLK(info.st_mode):
            raise ProofError("physical block devices are forbidden")
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode) or any(path.iterdir()):
            raise ProofError("output root must be an empty real directory")
    else:
        path.mkdir(mode=0o700)
    return path


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("$schema") != SCHEMA or contract.get("status") != "proof-only":
        raise ProofError("unexpected Native disposable proof contract")
    if contract.get("physical_write_allowed") is not False:
        raise ProofError("proof contract must forbid physical write")
    if contract.get("physical_device_paths_allowed") is not False:
        raise ProofError("proof contract must forbid physical device paths")
    if contract.get("bootable_proof") is not False:
        raise ProofError("storage proof must not claim bootability")
    target = contract.get("target_bytes")
    if not isinstance(target, int) or target <= 0 or target > MAX_PROOF_BYTES or target % 512:
        raise ProofError("invalid disposable Native target capacity")


def validate_plan(plan: dict[str, Any], contract: dict[str, Any]) -> None:
    if plan.get("schema") != PLAN_SCHEMA or plan.get("status") != "plan-only":
        raise ProofError("unexpected Native materialization plan")
    if plan.get("physical_write_allowed") is not False or plan.get("disposable_proof_only") is not True:
        raise ProofError("Native plan crossed proof-only boundary")
    if plan.get("boot_integration_status") != contract["boot_integration_status"]:
        raise ProofError("Native boot integration status mismatch")
    if plan.get("target_bytes") != contract["target_bytes"]:
        raise ProofError("Native proof target capacity does not match Core plan")
    if plan.get("partition_table") != "gpt" or plan.get("logical_sector_bytes") != 512:
        raise ProofError("Native plan physical geometry is unsupported")
    if plan.get("alignment_bytes") != 1024 * 1024:
        raise ProofError("Native plan alignment is not canonical")
    if plan.get("source_product_mode") != "usb" or plan.get("target_product_mode") != "native-disk":
        raise ProofError("Native product-mode transition is invalid")
    if plan.get("target_product_mode_path") != "/ordax/bootstrap/config/product-mode":
        raise ProofError("Native product-mode materialization path is invalid")

    partitions = plan.get("partitions")
    if not isinstance(partitions, list) or len(partitions) != 2:
        raise ProofError("Native plan must contain exactly two partitions")
    expected = contract["expected"]["partitions"]
    for actual, required in zip(partitions, expected, strict=True):
        for field in ("index", "name", "type_guid", "filesystem", "filesystem_label"):
            if actual.get(field) != required.get(field):
                raise ProofError(f"Native partition {field} does not match contract")
        if required.get("encryption") and actual.get("encryption") != required["encryption"]:
            raise ProofError("Native pool encryption does not match contract")
        for field in ("start_lba", "last_lba", "size_bytes"):
            if not isinstance(actual.get(field), int) or actual[field] <= 0:
                raise ProofError(f"Native partition {field} is invalid")
        sectors = actual["last_lba"] - actual["start_lba"] + 1
        if sectors * 512 != actual["size_bytes"]:
            raise ProofError("Native partition byte geometry is inconsistent")

    if partitions[0]["type_guid"] != ESP_GUID or partitions[1]["type_guid"] != LUKS_GUID:
        raise ProofError("Native GPT type GUID policy is invalid")
    if partitions[0]["start_lba"] != 2048:
        raise ProofError("Native ESP must start at the canonical 1 MiB boundary")
    if partitions[1]["start_lba"] % 2048:
        raise ProofError("Native pool start is not 1 MiB aligned")
    if partitions[0]["last_lba"] >= partitions[1]["start_lba"]:
        raise ProofError("Native partitions overlap")

    subvolumes = plan.get("subvolumes")
    if not isinstance(subvolumes, list):
        raise ProofError("Native Btrfs subvolume plan is missing")
    names = [item.get("name") for item in subvolumes if isinstance(item, dict)]
    if names != contract["expected"]["subvolumes"]:
        raise ProofError("Native subvolume set does not match storage contract")


def parse_sgdisk_info(raw: Path, index: int) -> dict[str, Any]:
    output = run(["sgdisk", f"--info={index}", str(raw)]).stdout
    fields = {}
    patterns = {
        "type_guid": r"Partition GUID code:\s+([0-9A-Fa-f-]{36})",
        "first_lba": r"First sector:\s+(\d+)",
        "last_lba": r"Last sector:\s+(\d+)",
        "name": r"Partition name:\s+'([^']*)'",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, output)
        if not match:
            raise ProofError(f"cannot parse GPT partition {index} field {key}")
        fields[key] = match.group(1)
    fields["type_guid"] = fields["type_guid"].lower()
    fields["first_lba"] = int(fields["first_lba"])
    fields["last_lba"] = int(fields["last_lba"])
    return fields


def blkid_values(path: Path | str) -> dict[str, str]:
    output = run(["blkid", "-p", "-o", "export", str(path)]).stdout
    values = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def write_partition_to_raw(source: Path, raw: Path, start_lba: int) -> None:
    run([
        "dd",
        f"if={source}",
        f"of={raw}",
        "bs=512",
        f"seek={start_lba}",
        "conv=notrunc,sparse",
        "status=none",
    ])


def create_gpt(raw: Path, plan: dict[str, Any]) -> list[dict[str, Any]]:
    target_bytes = plan["target_bytes"]
    with raw.open("wb") as handle:
        handle.truncate(target_bytes)
    run(["sgdisk", "--zap-all", str(raw)])
    for partition in plan["partitions"]:
        run([
            "sgdisk",
            f"--new={partition['index']}:{partition['start_lba']}:{partition['last_lba']}",
            f"--typecode={partition['index']}:{partition['type_guid']}",
            f"--change-name={partition['index']}:{partition['name']}",
            str(raw),
        ])
    run(["sgdisk", "--verify", str(raw)])
    verified = []
    for partition in plan["partitions"]:
        actual = parse_sgdisk_info(raw, partition["index"])
        if (
            actual["name"] != partition["name"]
            or actual["type_guid"] != partition["type_guid"]
            or actual["first_lba"] != partition["start_lba"]
            or actual["last_lba"] != partition["last_lba"]
        ):
            raise ProofError(f"GPT partition {partition['index']} disagrees with Core plan")
        verified.append(actual)
    return verified


def create_esp(path: Path, partition: dict[str, Any]) -> dict[str, str]:
    with path.open("wb") as handle:
        handle.truncate(partition["size_bytes"])
    run(["mkfs.vfat", "-F", "32", "-n", "ORDAX-ESP", str(path)])
    values = blkid_values(path)
    if values.get("TYPE") != "vfat" or values.get("LABEL") != "ORDAX-ESP":
        raise ProofError("ESP filesystem identity mismatch")
    return values


def create_pool(
    path: Path,
    partition: dict[str, Any],
    subvolumes: list[dict[str, Any]],
    target_mode_path: str,
    output_root: Path,
) -> dict[str, Any]:
    with path.open("wb") as handle:
        handle.truncate(partition["size_bytes"])

    key = output_root / ".ephemeral-luks-key"
    key.write_bytes(os.urandom(64))
    key.chmod(0o600)
    mapper = f"ordax_native_proof_{os.getpid()}_{int(time.time())}"
    mapper_path = Path("/dev/mapper") / mapper
    mountpoint = output_root / "pool-mount"
    mountpoint.mkdir(mode=0o700)
    opened = False
    mounted = False
    try:
        run([
            "cryptsetup", "luksFormat",
            "--type", "luks2",
            "--batch-mode",
            "--pbkdf", "pbkdf2",
            "--key-file", str(key),
            str(path),
        ])
        run(["cryptsetup", "isLuks", "--type", "luks2", str(path)])
        run([
            "cryptsetup", "open",
            "--type", "luks2",
            "--key-file", str(key),
            str(path),
            mapper,
        ])
        opened = True

        run(["mkfs.btrfs", "-f", "-L", "ORDAX-POOL", str(mapper_path)])
        fs = blkid_values(mapper_path)
        if fs.get("TYPE") != "btrfs" or fs.get("LABEL") != "ORDAX-POOL":
            raise ProofError("decrypted ORDAX-POOL filesystem identity mismatch")

        run(["mount", "-t", "btrfs", str(mapper_path), str(mountpoint)])
        mounted = True
        for item in subvolumes:
            run(["btrfs", "subvolume", "create", str(mountpoint / item["name"])])

        runtime_prefix = "/ordax/"
        if not target_mode_path.startswith(runtime_prefix):
            raise ProofError("Native product-mode path is outside mounted ORDAX pool")
        logical = target_mode_path[len(runtime_prefix):]
        if not logical or logical.startswith("/") or ".." in Path(logical).parts:
            raise ProofError("Native product-mode path is not safely pool-relative")
        marker = mountpoint / logical
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("native-disk\n", encoding="utf-8")
        os.sync()

        listing = run(["btrfs", "subvolume", "list", str(mountpoint)]).stdout
        for item in subvolumes:
            if re.search(rf"\bpath {re.escape(item['name'])}$", listing, re.MULTILINE) is None:
                raise ProofError(f"Btrfs subvolume was not read back: {item['name']}")
        if marker.read_text(encoding="utf-8") != "native-disk\n":
            raise ProofError("Native product-mode marker readback failed")

        luks_uuid = run(["cryptsetup", "luksUUID", str(path)]).stdout.strip()
        if re.fullmatch(r"[0-9a-fA-F-]{36}", luks_uuid) is None:
            raise ProofError("LUKS2 UUID is invalid")
        return {
            "luks_uuid": luks_uuid.lower(),
            "btrfs_uuid": fs.get("UUID", ""),
            "subvolumes": [item["name"] for item in subvolumes],
            "product_mode": "native-disk",
            "product_mode_path": target_mode_path,
        }
    finally:
        if mounted:
            subprocess.run(["umount", str(mountpoint)], check=False)
        if opened:
            subprocess.run(["cryptsetup", "close", mapper], check=False)
        try:
            key.unlink()
        except FileNotFoundError:
            pass
        try:
            mountpoint.rmdir()
        except OSError:
            pass


def prove(contract_path: Path, plan_path: Path, output_root: Path) -> dict[str, Any]:
    if os.name != "posix":
        raise ProofError("Native disposable proof requires a Linux/POSIX CI host")
    if os.geteuid() != 0:
        raise ProofError("Native disposable proof must run as root for disposable dm-crypt/mount operations")
    require_tools()
    contract = load_json(contract_path, "Native disposable proof contract")
    plan = load_json(plan_path, "Native materialization plan")
    validate_contract(contract)
    validate_plan(plan, contract)
    root = safe_output_root(output_root)

    raw = root / "ordax-native-disposable.raw"
    esp = root / "ordax-esp.img"
    pool = root / "ordax-pool.luks2"
    proof_path = root / "proof.json"

    gpt = create_gpt(raw, plan)
    esp_identity = create_esp(esp, plan["partitions"][0])
    pool_identity = create_pool(
        pool,
        plan["partitions"][1],
        plan["subvolumes"],
        plan["target_product_mode_path"],
        root,
    )
    if (root / ".ephemeral-luks-key").exists():
        raise ProofError("ephemeral LUKS key survived proof construction")

    write_partition_to_raw(esp, raw, plan["partitions"][0]["start_lba"])
    write_partition_to_raw(pool, raw, plan["partitions"][1]["start_lba"])

    esp_hash = sha256_file(esp)
    pool_hash = sha256_file(pool)
    esp_region_hash = sha256_region(
        raw,
        plan["partitions"][0]["start_lba"] * 512,
        plan["partitions"][0]["size_bytes"],
    )
    pool_region_hash = sha256_region(
        raw,
        plan["partitions"][1]["start_lba"] * 512,
        plan["partitions"][1]["size_bytes"],
    )
    if esp_hash != esp_region_hash or pool_hash != pool_region_hash:
        raise ProofError("RAW partition region does not match generated filesystem/container bytes")

    result = {
        "$schema": SCHEMA,
        "status": "pass",
        "physical_write_authorized": False,
        "physical_device_touched": False,
        "bootable_proven": False,
        "boot_integration_status": plan["boot_integration_status"],
        "target_bytes": plan["target_bytes"],
        "partition_table": "gpt",
        "partitions": [
            {
                "index": 1,
                "name": "ORDAX-ESP",
                "type_guid": gpt[0]["type_guid"],
                "start_lba": gpt[0]["first_lba"],
                "last_lba": gpt[0]["last_lba"],
                "filesystem": {"type": esp_identity["TYPE"], "label": esp_identity["LABEL"]},
                "region_sha256": esp_region_hash,
            },
            {
                "index": 2,
                "name": "ORDAX-POOL",
                "type_guid": gpt[1]["type_guid"],
                "start_lba": gpt[1]["first_lba"],
                "last_lba": gpt[1]["last_lba"],
                "encryption": "luks2",
                "luks_uuid": pool_identity["luks_uuid"],
                "filesystem": {"type": "btrfs", "label": "ORDAX-POOL", "uuid": pool_identity["btrfs_uuid"]},
                "subvolumes": pool_identity["subvolumes"],
                "product_mode": pool_identity["product_mode"],
                "product_mode_path": pool_identity["product_mode_path"],
                "region_sha256": pool_region_hash,
            },
        ],
        "checks": {
            "core_plan_consumed": True,
            "regular_sparse_raw_only": True,
            "gpt_exactly_two_partitions": True,
            "partition_geometry_matches_core_plan": True,
            "esp_fat32_verified": True,
            "pool_luks2_verified": True,
            "pool_btrfs_verified": True,
            "subvolumes_read_back": True,
            "native_product_mode_read_back": True,
            "raw_partition_regions_match": True,
            "ephemeral_luks_key_destroyed": True,
            "physical_write_blocked": True,
            "bootability_not_claimed": True,
        },
    }
    proof_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    proof_path.chmod(0o644)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prove(args.contract, args.plan, args.output_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ProofError, OSError) as exc:
        print(f"native-disposable-proof: ERROR: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
