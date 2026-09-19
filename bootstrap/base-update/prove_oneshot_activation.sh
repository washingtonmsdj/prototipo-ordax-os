#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROOF="${1:-$ROOT/out/base-update/oneshot-activation-proof.json}"
RELEASE_SHA="dddddddddddddddddddddddddddddddddddddddd"

for command in losetup mkfs.vfat fsck.vfat mount umount mountpoint sha256sum python3 sync; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "oneshot-activation-proof: required program not found: $command" >&2
    exit 1
  }
done

mkdir -p "$ROOT/out"
WORK="$(mktemp -d "$ROOT/out/oneshot-activation.XXXXXX")"
IMAGE="$WORK/esp.raw"
MOUNT="$WORK/mnt"
EFIVARS="$WORK/efivars"
KERNEL="$WORK/candidate-kernel"
INITRAMFS="$WORK/candidate-initramfs"
STAGE_RESULT="$WORK/stage-result.json"
ACTIVATE_RESULT="$WORK/activate-result.json"
LOOP=""

cleanup() {
  set +e
  if [[ -d "$MOUNT" ]] && mountpoint -q "$MOUNT"; then
    sudo umount "$MOUNT" >/dev/null 2>&1 || true
  fi
  if [[ -n "$LOOP" ]]; then
    sudo losetup -d "$LOOP" >/dev/null 2>&1 || true
  fi
  rm -rf "$WORK"
}
trap cleanup EXIT

mkdir -p "$MOUNT" "$EFIVARS" "$(dirname "$PROOF")"
truncate -s 64M "$IMAGE"
LOOP="$(sudo losetup --find --show "$IMAGE")"
sudo mkfs.vfat -F 32 -n ORDAX-ESP "$LOOP" >/dev/null
sudo mount -t vfat -o rw,umask=0022 "$LOOP" "$MOUNT"

sudo mkdir -p "$MOUNT/loader/entries" "$MOUNT/ordax/base/a"
printf 'default ordax.conf\ntimeout 0\neditor no\n'   | sudo tee "$MOUNT/loader/loader.conf" >/dev/null
printf 'title OrdaX Current\nlinux /ordax/base/a/vmlinuz\ninitrd /ordax/base/a/initrd.gz\noptions console=tty0 ordax.mode=normal ordax.base_slot=a\n'   | sudo tee "$MOUNT/loader/entries/ordax.conf" >/dev/null
printf 'title OrdaX Recovery\nlinux /ordax/base/a/vmlinuz\ninitrd /ordax/base/a/initrd.gz\noptions console=tty0 ordax.mode=recovery ordax.base_slot=a\n'   | sudo tee "$MOUNT/loader/entries/ordax-recovery.conf" >/dev/null
printf 'known-good-kernel\n' | sudo tee "$MOUNT/ordax/base/a/vmlinuz" >/dev/null
printf 'known-good-initramfs\n' | sudo tee "$MOUNT/ordax/base/a/initrd.gz" >/dev/null
sync

printf 'activation-proof-candidate-kernel\n' >"$KERNEL"
printf 'activation-proof-candidate-initramfs\n' >"$INITRAMFS"
KERNEL_SHA="$(sha256sum "$KERNEL" | awk '{print $1}')"
INITRAMFS_SHA="$(sha256sum "$INITRAMFS" | awk '{print $1}')"

sudo python3 -   "$ROOT/bootstrap/base-update/stage.py"   "$MOUNT" "$KERNEL" "$INITRAMFS"   "$KERNEL_SHA" "$INITRAMFS_SHA" "$RELEASE_SHA" >"$STAGE_RESULT" <<'PY'
import importlib.util
import json
from pathlib import Path
import sys

module_path, esp_root, kernel, initramfs, kernel_sha, initramfs_sha, release_sha = sys.argv[1:]
spec = importlib.util.spec_from_file_location("ordax_activation_stage_proof", module_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

candidate = {
    "release_sha": release_sha,
    "kernel_sha256": kernel_sha,
    "initramfs_sha256": initramfs_sha,
}
result = module.stage(
    Path(esp_root),
    "a",
    candidate,
    Path(kernel),
    Path(initramfs),
)
assert result["candidate_slot"] == "b"
assert result["activation_ready"] is True
assert result["efi_variable_written"] is False
assert result["reboot_requested"] is False
print(json.dumps(result, sort_keys=True))
PY

LOADER_BEFORE="$(sudo sha256sum "$MOUNT/loader/loader.conf" | awk '{print $1}')"
CURRENT_BEFORE="$(sudo sha256sum "$MOUNT/loader/entries/ordax.conf" | awk '{print $1}')"
RECOVERY_BEFORE="$(sudo sha256sum "$MOUNT/loader/entries/ordax-recovery.conf" | awk '{print $1}')"
CANDIDATE_BEFORE="$(sudo sha256sum "$MOUNT/loader/entries/ordax-candidate+01-00.conf" | awk '{print $1}')"
sync
sudo umount "$MOUNT"
sudo fsck.vfat -n "$LOOP" >/dev/null

IMAGE_BEFORE="$(sha256sum "$IMAGE" | awk '{print $1}')"

sudo mount -t vfat -o ro,nosuid,nodev,noexec,umask=0022 "$LOOP" "$MOUNT"
sudo python3 "$ROOT/bootstrap/base-update/activate.py"   --esp-root "$MOUNT"   --efivarfs-root "$EFIVARS"   --release-sha "$RELEASE_SHA"   --candidate-slot b   >"$ACTIVATE_RESULT"

test "$(sudo sha256sum "$MOUNT/loader/loader.conf" | awk '{print $1}')" = "$LOADER_BEFORE"
test "$(sudo sha256sum "$MOUNT/loader/entries/ordax.conf" | awk '{print $1}')" = "$CURRENT_BEFORE"
test "$(sudo sha256sum "$MOUNT/loader/entries/ordax-recovery.conf" | awk '{print $1}')" = "$RECOVERY_BEFORE"
test "$(sudo sha256sum "$MOUNT/loader/entries/ordax-candidate+01-00.conf" | awk '{print $1}')" = "$CANDIDATE_BEFORE"
sudo umount "$MOUNT"

IMAGE_AFTER="$(sha256sum "$IMAGE" | awk '{print $1}')"
test "$IMAGE_BEFORE" = "$IMAGE_AFTER"
sudo fsck.vfat -n "$LOOP" >/dev/null

sudo python3 - "$ACTIVATE_RESULT" "$EFIVARS" "$PROOF" "$RELEASE_SHA" "$IMAGE_AFTER" <<'PY'
import json
import pathlib
import struct
import sys

result_path = pathlib.Path(sys.argv[1])
efivars = pathlib.Path(sys.argv[2])
proof_path = pathlib.Path(sys.argv[3])
release_sha = sys.argv[4]
image_sha = sys.argv[5]

result = json.loads(result_path.read_text(encoding="utf-8"))
assert result["$schema"] == "prototype-ordax.base-update-activation-result/1"
assert result["release_sha"] == release_sha
assert result["candidate_slot"] == "b"
assert result["entry_id"] == "ordax-candidate.conf"
assert result["selector"] == "LoaderEntryOneShot"
assert result["default_entry_changed"] is False
assert result["reboot_requested"] is False
assert result["armed"] is True

variables = list(efivars.iterdir())
assert len(variables) == 1
variable = variables[0]
assert variable.name == "LoaderEntryOneShot-4a67b082-0a4c-41cf-b6c7-440b29bb8c4f"
payload = variable.read_bytes()
assert struct.unpack("<I", payload[:4])[0] == 0x00000007
assert payload[4:].decode("utf-16-le") == "ordax-candidate.conf\x00"

proof = {
    "$schema": "prototype-ordax.base-update-oneshot-activation-proof/1",
    "status": "pass",
    "scope": "disposable-efivar-selection-only",
    "release_sha": release_sha,
    "candidate_slot": "b",
    "selector": "LoaderEntryOneShot",
    "entry_id": "ordax-candidate.conf",
    "esp_image_sha256_after_activation": image_sha,
    "checks": {
        "staged_candidate_identity_validated": True,
        "esp_mounted_read_only_for_activation": True,
        "loader_default_preserved": True,
        "current_entry_preserved": True,
        "recovery_entry_preserved": True,
        "candidate_entry_preserved": True,
        "esp_image_byte_identical_before_after_activation": True,
        "only_loader_entry_oneshot_variable_written": True,
        "efivar_attributes_nv_bs_rt": True,
        "oneshot_entry_id_exact": True,
        "reboot_not_requested": True,
    },
    "real_efivarfs_touched": False,
    "physical_hardware_touched": False,
    "physical_hardware_proven": False,
    "runtime_owner_activation_wiring_enabled": False,
    "reboot_authorized": False,
}
proof_path.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("BASE_UPDATE_ONESHOT_ACTIVATION_PROOF=PASS")
PY
