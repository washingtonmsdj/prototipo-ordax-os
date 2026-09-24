#!/usr/bin/env python3
"""Materialize a Creator Core portable-media plan into a disposable RAW image.

This proof consumes the Core-generated plan as policy authority. It does not
derive partition geometry or target paths independently. Source files are
provided only as ID=PATH transport bindings and must match the exact SHA-256
and size already present in the plan.

The output is always a new regular sparse RAW file. Physical device paths are
rejected. CI may attach that regular file via host loop devices, format the
planned FAT32/exFAT filesystems, copy the planned artifacts, unmount/remount,
and verify every artifact byte-for-byte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any

PLAN_SCHEMA = "prototype-ordax.portable-media-plan/1"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ESP_GUID = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
DATA_GUID = "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7"


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


def regular(path: Path, label: str) -> Path:
    absolute = path.resolve()
    if str(absolute).startswith("/dev/"):
        raise ProofError(f"{label} must never be a device path")
    try:
        info = absolute.lstat()
    except OSError as exc:
        raise ProofError(f"cannot stat {label}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ProofError(f"{label} must be a regular non-symlink single-link file")
    if info.st_size <= 0:
        raise ProofError(f"{label} must be non-empty")
    return absolute


def safe_new_raw(path: Path, target_bytes: int) -> Path:
    if str(path).startswith("/dev/"):
        raise ProofError("RAW output must never be a device path")
    absolute = path.absolute()
    parent = absolute.parent.resolve()
    if not parent.is_dir() or parent.is_symlink():
        raise ProofError("RAW output parent must be a real directory")
    absolute = parent / absolute.name
    if absolute.exists() or absolute.is_symlink():
        raise ProofError("RAW output must not already exist")
    if not absolute.name.endswith(".raw"):
        raise ProofError("RAW output must use .raw suffix")
    with absolute.open("xb") as handle:
        handle.truncate(target_bytes)
    return absolute


def load_plan(path: Path) -> dict[str, Any]:
    path = regular(path, "portable media plan")
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProofError(f"decode portable media plan: {exc}") from exc
    if not isinstance(plan, dict) or plan.get("$schema") != PLAN_SCHEMA:
        raise ProofError("portable media plan schema is not canonical")
    if plan.get("profile") != "portable-usb":
        raise ProofError("portable media plan profile is not portable-usb")
    if plan.get("physical_write_authorized") is not False:
        raise ProofError("portable media plan unexpectedly authorizes physical write")
    commit = plan.get("source_commit")
    if not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None:
        raise ProofError("portable media plan source commit is invalid")
    target_bytes = plan.get("target_bytes")
    if not isinstance(target_bytes, int) or target_bytes <= 0 or target_bytes % 512:
        raise ProofError("portable media plan target capacity is invalid")
    artifacts = plan.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 17:
        raise ProofError("portable media plan must contain exactly 17 artifacts")
    seen_ids: set[str] = set()
    seen_targets: set[tuple[str, str]] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ProofError("portable media artifact plan entry must be an object")
        artifact_id = artifact.get("id")
        partition = artifact.get("partition")
        target = artifact.get("target_path")
        digest = artifact.get("sha256")
        size = artifact.get("size_bytes")
        if not isinstance(artifact_id, str) or not artifact_id or artifact_id in seen_ids:
            raise ProofError("portable media artifact IDs must be unique non-empty strings")
        seen_ids.add(artifact_id)
        if partition not in {"ORDAX-ESP", "ORDAX-DATA"}:
            raise ProofError(f"artifact {artifact_id!r} targets unknown partition")
        if not isinstance(target, str) or not target.startswith("/") or "\\" in target:
            raise ProofError(f"artifact {artifact_id!r} has unsafe target path")
        pure = PurePosixPath(target)
        if ".." in pure.parts or str(pure) != target:
            raise ProofError(f"artifact {artifact_id!r} target path is not canonical")
        key = (partition, target)
        if key in seen_targets:
            raise ProofError("portable media plan contains duplicate target path")
        seen_targets.add(key)
        if not isinstance(digest, str) or SHA_RE.fullmatch(digest) is None:
            raise ProofError(f"artifact {artifact_id!r} has invalid digest")
        if not isinstance(size, int) or size <= 0 or size > 16 << 30:
            raise ProofError(f"artifact {artifact_id!r} has invalid size")
    return plan


def parse_sources(values: list[str], plan: dict[str, Any]) -> dict[str, Path]:
    expected = {artifact["id"] for artifact in plan["artifacts"]}
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ProofError("source binding must use ID=PATH")
        artifact_id, raw_path = value.split("=", 1)
        if artifact_id not in expected:
            raise ProofError(f"source binding uses unknown artifact id {artifact_id!r}")
        if artifact_id in result:
            raise ProofError(f"duplicate source binding for {artifact_id!r}")
        result[artifact_id] = regular(Path(raw_path), f"source {artifact_id}")
    missing = sorted(expected - result.keys())
    if missing:
        raise ProofError("missing source bindings: " + ", ".join(missing))

    by_id = {artifact["id"]: artifact for artifact in plan["artifacts"]}
    for artifact_id, path in result.items():
        expected_artifact = by_id[artifact_id]
        if path.stat().st_size != expected_artifact["size_bytes"]:
            raise ProofError(f"source size mismatch for {artifact_id}")
        if sha256_file(path) != expected_artifact["sha256"]:
            raise ProofError(f"source digest mismatch for {artifact_id}")
    return result


def require_programs() -> None:
    names = (
        "sgdisk", "losetup", "mkfs.vfat", "mkfs.exfat", "mount.exfat-fuse",
        "mount", "umount", "blkid",
    )
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise ProofError("missing portable prepared-media proof programs: " + ", ".join(missing))


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


def mount_data(device: Path, target: Path, *, read_only: bool) -> None:
    argv = ["mount.exfat-fuse"]
    if read_only:
        argv.extend(["-o", "ro"])
    argv.extend([str(device), str(target)])
    run(argv)


def target_under(root: Path, target: str) -> Path:
    relative = target.lstrip("/")
    destination = (root / relative).resolve()
    root_resolved = root.resolve()
    if destination == root_resolved or root_resolved not in destination.parents:
        raise ProofError(f"target escaped partition root: {target}")
    return destination


def copy_and_verify(plan: dict[str, Any], sources: dict[str, Path], roots: dict[str, Path]) -> None:
    for artifact in plan["artifacts"]:
        source = sources[artifact["id"]]
        destination = target_under(roots[artifact["partition"]], artifact["target_path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            raise ProofError(f"destination already exists: {artifact['target_path']}")
        with source.open("rb") as src, destination.open("xb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        if destination.stat().st_size != artifact["size_bytes"]:
            raise ProofError(f"materialized size mismatch for {artifact['id']}")
        if sha256_file(destination) != artifact["sha256"]:
            raise ProofError(f"materialized digest mismatch for {artifact['id']}")


def reverify(plan: dict[str, Any], roots: dict[str, Path]) -> None:
    for artifact in plan["artifacts"]:
        destination = target_under(roots[artifact["partition"]], artifact["target_path"])
        if not destination.is_file() or destination.is_symlink():
            raise ProofError(f"readback target missing or unsafe for {artifact['id']}")
        if destination.stat().st_size != artifact["size_bytes"]:
            raise ProofError(f"readback size mismatch for {artifact['id']}")
        if sha256_file(destination) != artifact["sha256"]:
            raise ProofError(f"readback digest mismatch for {artifact['id']}")


def prove(plan_path: Path, source_values: list[str], output: Path, proof_path: Path) -> dict[str, Any]:
    if os.name != "posix" or os.geteuid() != 0:
        raise ProofError("portable prepared-media proof requires root on a POSIX CI host")
    require_programs()
    plan = load_plan(plan_path)
    sources = parse_sources(source_values, plan)
    raw = safe_new_raw(output, plan["target_bytes"])

    work = Path(tempfile.mkdtemp(prefix="ordax-portable-prepared-", dir=str(raw.parent)))
    esp_mount = work / "esp"
    data_mount = work / "data"
    esp_ro = work / "esp-ro"
    data_ro = work / "data-ro"
    for path in (esp_mount, data_mount, esp_ro, data_ro):
        path.mkdir()
    loop = ""
    esp_mounted = data_mounted = esp_ro_mounted = data_ro_mounted = False

    checks = {
        "creator_core_plan_consumed_without_geometry_replanning": True,
        "regular_sparse_raw_file_only": True,
        "exact_two_partition_gpt": False,
        "fat32_esp": False,
        "exfat_data": False,
        "all_17_source_bindings_verified": True,
        "all_17_artifacts_materialized_from_core_targets": False,
        "read_only_remount_readback_verified": False,
        "physical_target_device_untouched": True,
        "physical_write_unauthorized": True,
    }
    try:
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
            f"--new=2:{plan['data_start_lba']}:{plan['data_last_lba']}",
            f"--typecode=2:{DATA_GUID}",
            "--change-name=2:ORDAX-DATA",
            str(raw),
        ])
        run(["sgdisk", "--verify", str(raw)])
        printed = capture(["sgdisk", "--print", str(raw)])
        if "ORDAX-ESP" not in printed or "ORDAX-DATA" not in printed:
            raise ProofError("prepared GPT does not contain canonical portable partitions")
        checks["exact_two_partition_gpt"] = True

        loop = capture(["losetup", "--find", "--show", "--partscan", str(raw)])
        if not loop.startswith("/dev/loop"):
            raise ProofError("RAW image did not map to a host loop device")
        esp = Path(loop + "p1")
        data = Path(loop + "p2")
        wait_block(esp)
        wait_block(data)

        run(["mkfs.vfat", "-F", "32", "-n", "ORDAX-ESP", str(esp)])
        run(["mkfs.exfat", "-L", "ORDAX-DATA", str(data)])
        checks["fat32_esp"] = True
        checks["exfat_data"] = True

        run(["mount", "-t", "vfat", "-o", "rw,umask=0022", str(esp), str(esp_mount)])
        esp_mounted = True
        mount_data(data, data_mount, read_only=False)
        data_mounted = True
        copy_and_verify(plan, sources, {"ORDAX-ESP": esp_mount, "ORDAX-DATA": data_mount})
        os.sync()
        checks["all_17_artifacts_materialized_from_core_targets"] = True

        unmount(data_mount); data_mounted = False
        unmount(esp_mount); esp_mounted = False

        run(["mount", "-t", "vfat", "-o", "ro,umask=0022", str(esp), str(esp_ro)])
        esp_ro_mounted = True
        mount_data(data, data_ro, read_only=True)
        data_ro_mounted = True
        reverify(plan, {"ORDAX-ESP": esp_ro, "ORDAX-DATA": data_ro})
        checks["read_only_remount_readback_verified"] = True

        if not all(checks.values()):
            raise ProofError(f"portable prepared-media checks incomplete: {checks}")
        proof = {
            "$schema": "prototype-ordax.creator-portable-prepared-media-proof/1",
            "status": "pass",
            "source_commit": plan["source_commit"],
            "target_bytes": plan["target_bytes"],
            "artifact_count": len(plan["artifacts"]),
            "partitions": ["ORDAX-ESP", "ORDAX-DATA"],
            "raw_image_sha256": sha256_file(raw),
            "physical_target_device_touched": False,
            "physical_write_authorized": False,
            "public_physical_promotion_allowed": False,
            "checks": checks,
        }
        proof_path.parent.mkdir(parents=True, exist_ok=True)
        proof_path.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return proof
    finally:
        if data_ro_mounted: unmount(data_ro)
        if esp_ro_mounted: unmount(esp_ro)
        if data_mounted: unmount(data_mount)
        if esp_mounted: unmount(esp_mount)
        if loop:
            subprocess.run(["losetup", "-d", loop], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--source", action="append", default=[], help="artifact binding ID=PATH; repeat exactly once per planned artifact")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--proof", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = prove(args.plan.resolve(), args.source, args.out, args.proof.resolve())
    except (ProofError, OSError, json.JSONDecodeError) as exc:
        print(f"portable-prepared-media-proof: ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    print("CREATOR_PORTABLE_V2_PREPARED_MEDIA_PROOF=PASS")
    print("PHYSICAL_TARGET_DEVICE_TOUCHED=NO")
    print("PHYSICAL_WRITE_AUTHORIZED=NO")
    print("PUBLIC_PHYSICAL_PROMOTION=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
