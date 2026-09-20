#!/usr/bin/env python3
"""Build/read-back proof for the disposable OrdaX Native ESP.

This proof consumes only regular files. It verifies the exact bootloader,
kernel and Native initramfs bytes, Creator-rendered boot entries bound to a
real disposable LUKS2 UUID, then materializes a sparse FAT32 image and reads
every controlled file back before destroying the image.
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
from typing import Any

PROOF_SCHEMA = "prototype-ordax.native-esp-proof/1"
ESP_SCHEMA = "prototype-ordax.native-esp/1"
BOOTLOADER_SCHEMA = "prototype-ordax.esp-bootloader-provenance/1"
KERNEL_SCHEMA = "prototype-ordax.kernel-provenance/1"
INITRAMFS_SCHEMA = "prototype-ordax.native-initramfs-provenance/1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")


class ProofError(RuntimeError):
    pass


def run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ProofError(f"cannot execute {' '.join(argv)}: {exc}") from exc
    if check and result.returncode != 0:
        raise ProofError(
            f"command failed ({result.returncode}): {' '.join(argv)}: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    return result


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
    if str(path).startswith("/dev/"):
        raise ProofError(f"{label} must never be a physical device path")


def load_json(path: Path, label: str) -> dict[str, Any]:
    regular(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProofError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProofError(f"{label} must be a JSON object")
    return value


def checked_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ProofError(f"invalid SHA-256 in {label}")
    return value


def verify_source_configs(root: Path, contract: dict[str, Any]) -> None:
    configuration = contract.get("configuration")
    if not isinstance(configuration, dict):
        raise ProofError("Native ESP configuration contract is missing")
    for key in ("loader_conf", "normal_entry_template", "recovery_entry_template"):
        item = configuration.get(key)
        if not isinstance(item, dict):
            raise ProofError(f"Native ESP configuration item missing: {key}")
        source = item.get("source")
        expected = checked_digest(item.get("sha256"), f"Native ESP {key}")
        if not isinstance(source, str) or not source:
            raise ProofError(f"Native ESP source path missing: {key}")
        path = (root / source).resolve()
        if root.resolve() not in path.parents:
            raise ProofError(f"Native ESP source escaped repository: {source}")
        regular(path, f"Native ESP source {key}")
        if sha256_file(path) != expected:
            raise ProofError(f"Native ESP source hash mismatch: {source}")


def verify_bootloader(path: Path, provenance_path: Path) -> str:
    regular(path, "systemd-boot candidate")
    provenance = load_json(provenance_path, "systemd-boot provenance")
    if provenance.get("$schema") != BOOTLOADER_SCHEMA:
        raise ProofError("unexpected systemd-boot provenance schema")
    if provenance.get("physical_artifact_authorized") is not False:
        raise ProofError("systemd-boot candidate crossed physical authorization boundary")
    artifact = provenance.get("artifact")
    if not isinstance(artifact, dict):
        raise ProofError("systemd-boot artifact provenance missing")
    digest = checked_digest(artifact.get("sha256"), "systemd-boot artifact")
    if artifact.get("name") != path.name or artifact.get("size") != path.stat().st_size:
        raise ProofError("systemd-boot artifact identity disagrees with provenance")
    if sha256_file(path) != digest:
        raise ProofError("systemd-boot artifact bytes disagree with provenance")
    return digest


def verify_kernel(path: Path, provenance_path: Path, source_commit: str) -> str:
    regular(path, "kernel candidate")
    provenance = load_json(provenance_path, "kernel provenance")
    if provenance.get("$schema") != KERNEL_SCHEMA:
        raise ProofError("unexpected kernel provenance schema")
    if provenance.get("physical_artifact_authorized") is not False:
        raise ProofError("kernel candidate crossed physical authorization boundary")
    if provenance.get("source_commit") != source_commit:
        raise ProofError("kernel candidate was not built from the exact OrdaX source commit")
    artifacts = provenance.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ProofError("kernel artifact map missing")
    digest = checked_digest(artifacts.get(path.name), "kernel artifact")
    if sha256_file(path) != digest:
        raise ProofError("kernel artifact bytes disagree with provenance")
    return digest


def verify_initramfs(path: Path, provenance_path: Path, source_commit: str) -> str:
    regular(path, "Native initramfs candidate")
    provenance = load_json(provenance_path, "Native initramfs provenance")
    if provenance.get("$schema") != INITRAMFS_SCHEMA:
        raise ProofError("unexpected Native initramfs provenance schema")
    if provenance.get("physical_artifact_authorized") is not False:
        raise ProofError("Native initramfs crossed physical authorization boundary")
    if provenance.get("source_commit") != source_commit:
        raise ProofError("Native initramfs was not built from the exact OrdaX source commit")
    artifact = provenance.get("artifact")
    if not isinstance(artifact, dict):
        raise ProofError("Native initramfs artifact record missing")
    digest = checked_digest(artifact.get("sha256"), "Native initramfs artifact")
    if artifact.get("name") != path.name or artifact.get("size") != path.stat().st_size:
        raise ProofError("Native initramfs identity disagrees with provenance")
    if sha256_file(path) != digest:
        raise ProofError("Native initramfs bytes disagree with provenance")
    return digest


def verify_pool_identity(pool_container: Path, pool_uuid: str) -> None:
    regular(pool_container, "disposable LUKS2 identity container")
    if UUID_RE.fullmatch(pool_uuid) is None:
        raise ProofError("disposable pool UUID is not canonical")
    run(["cryptsetup", "isLuks", "--type", "luks2", str(pool_container)])
    observed = run(["cryptsetup", "luksUUID", str(pool_container)]).stdout.strip().lower()
    if observed != pool_uuid:
        raise ProofError("rendered pool UUID does not equal disposable LUKS2 UUID")


def verify_rendered_entries(
    rendered_root: Path,
    contract: dict[str, Any],
    pool_uuid: str,
) -> dict[str, Path]:
    if rendered_root.is_symlink() or not rendered_root.is_dir():
        raise ProofError("rendered Native boot root must be a real directory")
    result: dict[str, Path] = {}
    for key, expected_mode in (
        ("normal_entry_template", "normal"),
        ("recovery_entry_template", "recovery"),
    ):
        item = contract["configuration"][key]
        target = item["target"]
        path = rendered_root / Path(target)
        regular(path, f"rendered Native {expected_mode} entry")
        text = path.read_text(encoding="utf-8")
        if "@ORDAX_POOL_UUID@" in text:
            raise ProofError("Native boot placeholder survived Creator rendering")
        token = f"ordax.pool_uuid={pool_uuid}"
        if text.count(token) != 1:
            raise ProofError("Native boot entry does not bind exact LUKS2 UUID once")
        if text.count(f"ordax.mode={expected_mode}") != 1:
            raise ProofError("Native boot entry mode is not exact")
        if text.count("ordax.product_mode=native-disk") != 1:
            raise ProofError("Native boot entry product mode is not exact")
        if "linux /ordax/vmlinuz" not in text or "initrd /ordax/native-initrd.gz" not in text:
            raise ProofError("Native boot entry artifact paths are not canonical")
        lower = text.lower()
        for forbidden in ("passphrase", "password=", "keyfile", "key-file", "ordax.pool_key"):
            if forbidden in lower:
                raise ProofError("secret material leaked into rendered Native boot entry")
        result[target] = path
    return result


def copy_stage(files: dict[str, Path], stage: Path) -> dict[str, str]:
    if stage.exists():
        raise ProofError("Native ESP stage must start absent")
    stage.mkdir(parents=True)
    hashes: dict[str, str] = {}
    for target, source in sorted(files.items()):
        relative = Path(target)
        if relative.is_absolute() or ".." in relative.parts or str(relative) == ".":
            raise ProofError(f"unsafe Native ESP target path: {target}")
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        destination.chmod(0o644)
        hashes[target] = sha256_file(destination)
    return hashes


def build_fat32_image(stage: Path, image: Path, size_bytes: int) -> None:
    if image.exists():
        raise ProofError("Native ESP disposable image already exists")
    image.parent.mkdir(parents=True, exist_ok=True)
    with image.open("wb") as handle:
        handle.truncate(size_bytes)
    regular(image, "Native ESP disposable image")
    run(["mkfs.vfat", "-F", "32", "-n", "ORDAX-ESP", str(image)])
    for directory in (
        "EFI",
        "EFI/BOOT",
        "loader",
        "loader/entries",
        "ordax",
    ):
        run(["mmd", "-i", str(image), f"::/{directory}"])
    for source in sorted(path for path in stage.rglob("*") if path.is_file()):
        relative = source.relative_to(stage).as_posix()
        run(["mcopy", "-i", str(image), "-o", str(source), f"::/{relative}"])


def readback_image(
    image: Path,
    expected_hashes: dict[str, str],
    readback: Path,
) -> dict[str, str]:
    if run(["blkid", "-p", "-o", "value", "-s", "TYPE", str(image)]).stdout.strip() != "vfat":
        raise ProofError("Native ESP disposable image is not FAT")
    if run(["blkid", "-p", "-o", "value", "-s", "LABEL", str(image)]).stdout.strip() != "ORDAX-ESP":
        raise ProofError("Native ESP disposable image label mismatch")

    readback.mkdir(parents=True)
    observed: dict[str, str] = {}
    for target, expected in sorted(expected_hashes.items()):
        destination = readback / Path(target)
        destination.parent.mkdir(parents=True, exist_ok=True)
        run(["mcopy", "-i", str(image), f"::/{target}", str(destination)])
        regular(destination, f"Native ESP readback {target}")
        actual = sha256_file(destination)
        if actual != expected:
            raise ProofError(f"Native ESP readback hash mismatch: {target}")
        observed[target] = actual

    for forbidden in (
        "loader/entries/ordax.conf",
        "loader/entries/ordax-recovery.conf",
        "ordax/initrd.gz",
    ):
        probe = run(["mtype", "-i", str(image), f"::/{forbidden}"], check=False)
        if probe.returncode == 0:
            raise ProofError(f"portable USB boot path leaked into Native ESP: {forbidden}")
    return observed


def prove(args: argparse.Namespace) -> dict[str, Any]:
    root = args.repository.resolve()
    contract = load_json(args.contract.resolve(), "Native ESP contract")
    proof_contract = load_json(args.proof_contract.resolve(), "Native ESP proof contract")
    storage = load_json(args.storage_contract.resolve(), "storage architecture contract")
    if contract.get("$schema") != ESP_SCHEMA:
        raise ProofError("unexpected Native ESP contract schema")
    if proof_contract.get("$schema") != PROOF_SCHEMA:
        raise ProofError("unexpected Native ESP proof schema")
    if proof_contract.get("physical_write_authorized") is not False:
        raise ProofError("Native ESP proof contract crossed physical boundary")
    if COMMIT_RE.fullmatch(args.source_commit) is None:
        raise ProofError("exact OrdaX source commit is invalid")

    verify_source_configs(root, contract)
    bootloader_hash = verify_bootloader(args.bootloader.resolve(), args.bootloader_provenance.resolve())
    kernel_hash = verify_kernel(args.kernel.resolve(), args.kernel_provenance.resolve(), args.source_commit)
    initramfs_hash = verify_initramfs(
        args.initramfs.resolve(),
        args.initramfs_provenance.resolve(),
        args.source_commit,
    )
    verify_pool_identity(args.pool_container.resolve(), args.pool_uuid)
    rendered = verify_rendered_entries(args.rendered_root.resolve(), contract, args.pool_uuid)

    loader_source = (root / contract["configuration"]["loader_conf"]["source"]).resolve()
    files: dict[str, Path] = {
        "EFI/BOOT/BOOTX64.EFI": args.bootloader.resolve(),
        "loader/loader.conf": loader_source,
        "ordax/vmlinuz": args.kernel.resolve(),
        "ordax/native-initrd.gz": args.initramfs.resolve(),
        **rendered,
    }
    target_layout = contract.get("target_layout")
    if not isinstance(target_layout, list) or set(files) != set(target_layout) or len(files) != len(target_layout):
        raise ProofError("Native ESP staged file set disagrees with exact target layout")

    native_layout = storage["profiles"]["native-disk"]["physical_layout"]
    esp_layout = next(item for item in native_layout if item["name"] == "ORDAX-ESP")
    size_bytes = esp_layout["size_policy"]["minimum_bytes"]
    if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 64 * 1024 * 1024:
        raise ProofError("Native ESP minimum size policy is invalid")

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="ordax-native-esp-proof-", dir=out.parent))
    image = work / "native-esp.img"
    stage = work / "stage"
    readback = work / "readback"
    checks = {
        "source_configuration_hashes": False,
        "bootloader_provenance": False,
        "kernel_exact_source_provenance": False,
        "initramfs_exact_source_provenance": False,
        "real_luks2_uuid_bound": False,
        "creator_rendered_entries": False,
        "fat32_label": False,
        "exact_target_layout": False,
        "readback_sha256": False,
        "portable_usb_entries_absent": False,
        "physical_device_untouched": False,
        "image_destroyed": False,
    }
    try:
        checks["source_configuration_hashes"] = True
        checks["bootloader_provenance"] = True
        checks["kernel_exact_source_provenance"] = True
        checks["initramfs_exact_source_provenance"] = True
        checks["real_luks2_uuid_bound"] = True
        checks["creator_rendered_entries"] = True

        staged_hashes = copy_stage(files, stage)
        checks["exact_target_layout"] = set(staged_hashes) == set(target_layout)
        build_fat32_image(stage, image, size_bytes)
        checks["fat32_label"] = True
        image_hash = sha256_file(image)
        image_size = image.stat().st_size
        observed = readback_image(image, staged_hashes, readback)
        checks["readback_sha256"] = observed == staged_hashes
        checks["portable_usb_entries_absent"] = True
        checks["physical_device_untouched"] = True

        image.unlink()
        checks["image_destroyed"] = not image.exists()
        if not all(checks.values()):
            raise ProofError(f"Native ESP proof checks incomplete: {checks}")

        proof = {
            "$schema": "prototype-ordax.native-esp-proof-result/1",
            "status": "pass",
            "source_commit": args.source_commit,
            "pool_uuid": args.pool_uuid,
            "pool_uuid_is_secret": False,
            "physical_device_touched": False,
            "physical_write_authorized": False,
            "qemu_uefi_boot_proven": False,
            "physical_native_boot_proven": False,
            "esp": {
                "filesystem": "fat32",
                "label": "ORDAX-ESP",
                "size_bytes": image_size,
                "sha256_before_destruction": image_hash,
                "retained": False,
            },
            "artifacts": {
                "bootloader_sha256": bootloader_hash,
                "kernel_sha256": kernel_hash,
                "initramfs_sha256": initramfs_hash,
            },
            "files": dict(sorted(staged_hashes.items())),
            "checks": checks,
        }
        out.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return proof
    finally:
        if image.exists():
            image.unlink()
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--proof-contract", type=Path, required=True)
    parser.add_argument("--storage-contract", type=Path, required=True)
    parser.add_argument("--bootloader", type=Path, required=True)
    parser.add_argument("--bootloader-provenance", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--kernel-provenance", type=Path, required=True)
    parser.add_argument("--initramfs", type=Path, required=True)
    parser.add_argument("--initramfs-provenance", type=Path, required=True)
    parser.add_argument("--rendered-root", type=Path, required=True)
    parser.add_argument("--pool-container", type=Path, required=True)
    parser.add_argument("--pool-uuid", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prove(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        print("NATIVE_ESP_DISPOSABLE_PROOF=PASS")
        print("NATIVE_ESP_QEMU_UEFI_BOOT_PROVEN=NO")
        print("NATIVE_ESP_PHYSICAL_WRITE_AUTHORIZED=NO")
        return 0
    except (ProofError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"native-esp-proof: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
