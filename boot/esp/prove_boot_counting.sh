#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTCTL="${1:-}"
PROOF="${2:-$ROOT/out/esp/boot-counting-proof.json}"

[[ -n "$BOOTCTL" && -x "$BOOTCTL" ]] || {
  echo "boot-counting-proof: pinned bootctl executable is required" >&2
  exit 1
}
for command in losetup mkfs.vfat mount umount mountpoint python3; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "boot-counting-proof: required program not found: $command" >&2
    exit 1
  }
done

mkdir -p "$ROOT/out"
WORK="$(mktemp -d "$ROOT/out/boot-counting.XXXXXX")"
IMAGE="$WORK/esp.raw"
MOUNT="$WORK/esp"
LIST_OUTPUT="$WORK/bootctl-list.txt"
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

mkdir -p "$MOUNT" "$(dirname "$PROOF")"
truncate -s 64M "$IMAGE"
LOOP="$(sudo losetup --find --show "$IMAGE")"
sudo mkfs.vfat -F 32 -n ORDAX-ESP "$LOOP" >/dev/null
sudo mount -t vfat -o rw,umask=0022 "$LOOP" "$MOUNT"

sudo mkdir -p "$MOUNT/loader/entries" "$MOUNT/ordax/base/a" "$MOUNT/ordax/base/b"
printf 'default ordax.conf\ntimeout 0\neditor no\n'   | sudo tee "$MOUNT/loader/loader.conf" >/dev/null
printf 'title OrdaX Current\nlinux /ordax/base/a/vmlinuz\ninitrd /ordax/base/a/initrd.gz\noptions console=tty0 ordax.mode=normal ordax.base_slot=a\n'   | sudo tee "$MOUNT/loader/entries/ordax.conf" >/dev/null
printf 'title OrdaX Recovery\nlinux /ordax/base/a/vmlinuz\ninitrd /ordax/base/a/initrd.gz\noptions console=tty0 ordax.mode=recovery ordax.base_slot=a\n'   | sudo tee "$MOUNT/loader/entries/ordax-recovery.conf" >/dev/null
printf 'title OrdaX Candidate\nlinux /ordax/base/b/vmlinuz\ninitrd /ordax/base/b/initrd.gz\noptions console=tty0 ordax.mode=normal ordax.base_slot=b ordax.base_candidate=eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\n'   | sudo tee "$MOUNT/loader/entries/ordax-candidate+01-00.conf" >/dev/null
printf 'known-good-kernel\n' | sudo tee "$MOUNT/ordax/base/a/vmlinuz" >/dev/null
printf 'known-good-initramfs\n' | sudo tee "$MOUNT/ordax/base/a/initrd.gz" >/dev/null
printf 'candidate-kernel\n' | sudo tee "$MOUNT/ordax/base/b/vmlinuz" >/dev/null
printf 'candidate-initramfs\n' | sudo tee "$MOUNT/ordax/base/b/initrd.gz" >/dev/null
sync

sudo env SYSTEMD_RELAX_ESP_CHECKS=1 SYSTEMD_COLORS=0   "$BOOTCTL"   --esp-path="$MOUNT"   --no-variables   --no-pager   list >"$LIST_OUTPUT"

grep -Fq 'id: ordax-candidate.conf' "$LIST_OUTPUT"
grep -Fq 'ordax-candidate+01-00.conf' "$LIST_OUTPUT"
grep -Eq 'tries:[[:space:]]+1 left([,;][[:space:]]*0 done)?' "$LIST_OUTPUT"
grep -Fq 'id: ordax.conf' "$LIST_OUTPUT"
grep -Fq 'id: ordax-recovery.conf' "$LIST_OUTPUT"

python3 - "$LIST_OUTPUT" "$PROOF" "$BOOTCTL" <<'PY'
import json
import pathlib
import subprocess
import sys

listing = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="strict")
proof_path = pathlib.Path(sys.argv[2])
bootctl = pathlib.Path(sys.argv[3])

version = subprocess.run(
    [str(bootctl), "--version"],
    check=True,
    capture_output=True,
    text=True,
).stdout.splitlines()[0].strip()

proof = {
    "$schema": "prototype-ordax.systemd-boot-counting-parser-proof/1",
    "status": "pass",
    "scope": "pinned-systemd-userspace-entry-parser",
    "bootctl_version": version,
    "candidate_filename": "ordax-candidate+01-00.conf",
    "canonical_entry_id": "ordax-candidate.conf",
    "tries_left": 1,
    "tries_done": 0,
    "default_entry": "ordax.conf",
    "checks": {
        "pinned_source_bootctl_executed": True,
        "candidate_counter_filename_recognized": True,
        "canonical_counterless_entry_id_recognized": True,
        "single_try_counter_recognized": True,
        "current_entry_recognized": True,
        "recovery_entry_recognized": True,
    },
    "actual_uefi_boot_performed": False,
    "actual_counter_decrement_performed": False,
    "failed_candidate_fallback_proven": False,
    "physical_hardware_touched": False,
}
proof_path.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("SYSTEMD_BOOT_COUNTING_PARSER_PROOF=PASS")
PY

sudo umount "$MOUNT"
