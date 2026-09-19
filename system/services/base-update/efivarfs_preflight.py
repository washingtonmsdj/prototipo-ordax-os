#!/usr/bin/env python3
"""Evidence-only preflight for the UEFI efivarfs activation target.

The probe validates that the requested path is a real, directly mounted,
writable efivarfs filesystem. It never creates, truncates, removes, or writes
an EFI variable and never authorizes activation by itself.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import stat
import sys

SCHEMA = "prototype-ordax.efivarfs-preflight/1"
DEFAULT_EFIVARFS_ROOT = Path("/sys/firmware/efi/efivars")
DEFAULT_EFI_ROOT = Path("/sys/firmware/efi")


class EfivarfsPreflightError(RuntimeError):
    pass


def _unescape_mountinfo(value: str) -> str:
    return (
        value.replace(r"\040", " ")
        .replace(r"\011", "\t")
        .replace(r"\012", "\n")
        .replace(r"\134", "\\")
    )


def _mount_record(mountinfo: Path, mountpoint: Path) -> dict:
    try:
        lines = mountinfo.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise EfivarfsPreflightError("mountinfo is unavailable") from exc

    target = str(mountpoint)
    matches: list[dict] = []
    for line in lines:
        fields = line.split()
        if len(fields) < 10:
            continue
        decoded_mountpoint = _unescape_mountinfo(fields[4])
        if decoded_mountpoint != target:
            continue
        try:
            separator = fields.index("-")
        except ValueError as exc:
            raise EfivarfsPreflightError("efivarfs mountinfo record is malformed") from exc
        if separator + 3 >= len(fields):
            raise EfivarfsPreflightError("efivarfs mountinfo record is incomplete")
        matches.append(
            {
                "root": _unescape_mountinfo(fields[3]),
                "mountpoint": decoded_mountpoint,
                "mount_options": set(fields[5].split(",")),
                "filesystem": fields[separator + 1],
                "source": _unescape_mountinfo(fields[separator + 2]),
                "super_options": set(fields[separator + 3].split(",")),
            }
        )

    if not matches:
        raise EfivarfsPreflightError("efivarfs target is not a direct mountpoint")
    if len(matches) != 1:
        raise EfivarfsPreflightError("efivarfs target appears multiple times in mountinfo")
    return matches[0]


def _require_directory(path: Path, label: str) -> Path:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise EfivarfsPreflightError(f"{label} is unavailable") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise EfivarfsPreflightError(f"{label} must be a non-symlink directory")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise EfivarfsPreflightError(f"{label} cannot be resolved") from exc
    if resolved != path:
        raise EfivarfsPreflightError(f"{label} path must resolve to itself")
    return resolved


def preflight(
    *,
    efivarfs_root: Path = DEFAULT_EFIVARFS_ROOT,
    efi_root: Path = DEFAULT_EFI_ROOT,
    mountinfo: Path = Path("/proc/self/mountinfo"),
) -> dict:
    efi_root = _require_directory(efi_root, "UEFI firmware directory")
    efivarfs_root = _require_directory(efivarfs_root, "efivarfs directory")

    try:
        efivarfs_root.relative_to(efi_root)
    except ValueError as exc:
        raise EfivarfsPreflightError(
            "efivarfs directory is outside the UEFI firmware directory"
        ) from exc
    if efivarfs_root.parent != efi_root:
        raise EfivarfsPreflightError(
            "efivarfs directory must be the direct efivars child of UEFI firmware"
        )
    if efivarfs_root.name != "efivars":
        raise EfivarfsPreflightError("efivarfs directory name must be efivars")

    record = _mount_record(mountinfo, efivarfs_root)
    if record["root"] != "/":
        raise EfivarfsPreflightError("efivarfs mount exposes a non-root subpath")
    if record["filesystem"] != "efivarfs":
        raise EfivarfsPreflightError("activation target filesystem is not efivarfs")
    if record["source"] != "efivarfs":
        raise EfivarfsPreflightError("efivarfs mount source is unexpected")

    mount_options = record["mount_options"]
    super_options = record["super_options"]
    if "ro" in mount_options or "ro" in super_options:
        raise EfivarfsPreflightError("efivarfs mount is read-only")
    if "rw" not in mount_options and "rw" not in super_options:
        raise EfivarfsPreflightError("efivarfs mount does not advertise writable mode")

    return {
        "$schema": SCHEMA,
        "status": "valid",
        "uefi_boot_environment_present": True,
        "efivarfs_root": str(efivarfs_root),
        "filesystem": "efivarfs",
        "source": "efivarfs",
        "mount_root": "/",
        "writable_mount": True,
        "direct_mountpoint": True,
        "probe_only": True,
        "write_authorized": False,
        "activation_authorized": False,
        "variable_written": False,
        "reboot_requested": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--efivarfs-root",
        type=Path,
        default=DEFAULT_EFIVARFS_ROOT,
    )
    parser.add_argument(
        "--efi-root",
        type=Path,
        default=DEFAULT_EFI_ROOT,
    )
    parser.add_argument(
        "--mountinfo",
        type=Path,
        default=Path("/proc/self/mountinfo"),
    )
    args = parser.parse_args()

    try:
        value = preflight(
            efivarfs_root=args.efivarfs_root,
            efi_root=args.efi_root,
            mountinfo=args.mountinfo,
        )
    except EfivarfsPreflightError as exc:
        print(f"efivarfs-preflight: ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
