#!/usr/bin/env python3
"""Regress the Native LUKS2/Btrfs boot and initramfs contracts."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOT = json.loads((ROOT / "docs/contracts/native-boot.json").read_text(encoding="utf-8"))
SOURCE = json.loads((ROOT / "bootstrap/native-initramfs/source.json").read_text(encoding="utf-8"))
ENV = json.loads(
    (ROOT / "docs/contracts/native-initramfs-build-environment.json").read_text(
        encoding="utf-8"
    )
)
INIT = ROOT / SOURCE["root_init"]
BUILDER = ROOT / "bootstrap/native-initramfs/build.py"
NORMAL = ROOT / "boot/native/loader/ordax-native.conf.in"
RECOVERY = ROOT / "boot/native/loader/ordax-native-recovery.conf.in"


class NativeBootContractTests(unittest.TestCase):
    def test_shared_kernel_has_explicit_native_prerequisites(self):
        self.assertTrue(BOOT["shared_kernel"])
        self.assertFalse(BOOT["separate_native_kernel"])
        self.assertEqual(BOOT["kernel_contract"], "bootstrap/kernel/source.json")
        self.assertEqual(
            BOOT["kernel_required_builtins"],
            [
                "CONFIG_BLK_DEV_DM=y",
                "CONFIG_DM_CRYPT=y",
                "CONFIG_CRYPTO_AES=y",
                "CONFIG_CRYPTO_XTS=y",
                "CONFIG_BTRFS_FS=y",
                "CONFIG_BTRFS_FS_POSIX_ACL=y",
            ],
        )

    def test_loader_templates_bind_mode_and_exact_public_luks_uuid(self):
        for path, boot_mode in ((NORMAL, "normal"), (RECOVERY, "recovery")):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("@ORDAX_POOL_UUID@"), 1)
            self.assertIn(f"ordax.mode={boot_mode}", text)
            self.assertIn("ordax.product_mode=native-disk", text)
            self.assertIn("ordax.pool_uuid=@ORDAX_POOL_UUID@", text)
            for forbidden in ("passphrase", "key=", "keyfile", "password"):
                self.assertNotIn(forbidden, text.lower())

    def test_initramfs_entrypoint_is_fail_closed_and_network_free(self):
        text = INIT.read_text(encoding="utf-8")
        subprocess.run(["sh", "-n", str(INIT)], check=True)
        self.assertIn("cmdline_value ordax.product_mode", text)
        self.assertIn("cmdline_value ordax.pool_uuid", text)
        self.assertIn("find_pool_device()", text)
        self.assertIn('for sys_path in /sys/class/block/*; do', text)
        self.assertIn('[ -e "$sys_path/partition" ] || continue', text)
        self.assertIn('cryptsetup isLuks --type luks2 "$candidate"', text)
        self.assertIn('[ "$matches" -eq 1 ] || return 1', text)
        self.assertNotIn("findfs ", text)
        self.assertIn('cryptsetup isLuks --type luks2 "$POOL_DEVICE"', text)
        self.assertIn("cryptsetup open --readonly --type luks2", text)
        self.assertIn('mount -t btrfs -o ro,subvolid=5 "$MAPPER_DEVICE" /ordax', text)
        self.assertIn("persistent_product_mode", text)
        self.assertIn("ORDAX_STATE_DIR=/var/lib/ordax", text)
        self.assertIn("ORDAX_USER_HOME=/var/home", text)
        for name in (
            "ordax-state",
            "ordax-home",
            "ordax-apps",
            "ordax-containers",
            "ordax-snapshots",
        ):
            self.assertIn(name, text)
        for forbidden in ("--key-file", "curl ", "wget ", "git ", "ssh ", "https://", "http://"):
            self.assertNotIn(forbidden, text)

    def test_recovery_is_read_only_and_normal_boot_revalidates_before_rw(self):
        text = INIT.read_text(encoding="utf-8")
        self.assertIn('if [ "$BOOT_MODE" = "recovery" ]; then', text)
        self.assertIn("cryptsetup open --readonly --type luks2", text)
        self.assertIn('mount -t btrfs -o ro,subvolid=5 "$MAPPER_DEVICE" /ordax', text)
        self.assertIn("umount /ordax", text)
        self.assertIn('mount -t btrfs -o rw,compress=zstd:1,subvolid=5 "$MAPPER_DEVICE" /ordax', text)
        self.assertGreaterEqual(text.count("persistent_product_mode >/dev/null"), 2)

    def test_secret_policy_never_puts_unlock_material_in_boot_artifacts(self):
        policy = BOOT["secret_policy"]
        self.assertFalse(policy["luks_passphrase_in_kernel_cmdline"])
        self.assertFalse(policy["luks_key_in_esp"])
        self.assertFalse(policy["luks_key_in_repository"])
        self.assertFalse(policy["luks_key_in_release_artifact"])
        self.assertFalse(policy["interactive_secret_echo"])
        self.assertTrue(policy["tpm2_future_allowed"])
        self.assertTrue(policy["tpm2_requires_recovery_key"])

    def test_pool_discovery_uses_cryptsetup_not_busybox_volume_id_heuristics(self):
        discovery = BOOT["initramfs"]["pool_device_discovery"]
        self.assertEqual(discovery["authority"], "cryptsetup-luksUUID")
        self.assertEqual(discovery["candidate_scope"], "sysfs-partitions-only")
        self.assertTrue(discovery["exact_uuid_required"])
        self.assertTrue(discovery["exactly_one_match_required"])
        self.assertFalse(discovery["busybox_findfs_authoritative"])
        self.assertIn("duplicate-pool-uuid", BOOT["fail_closed"])

    def test_build_stays_blocked_until_exact_environment_is_observed(self):
        self.assertEqual(ENV["status"], "observation-required")
        self.assertFalse(ENV["gate"]["environment_observation_complete"])
        self.assertFalse(ENV["gate"]["versions_pinned"])
        self.assertFalse(ENV["gate"]["artifact_build_allowed"])
        self.assertFalse(ENV["gate"]["physical_artifact_authorized"])
        result = subprocess.run(
            ["python3", str(BUILDER), "check"],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        self.assertFalse(data["artifact_build_allowed"])
        self.assertFalse(data["physical_artifact_authorized"])

    def test_environment_owner_resolution_handles_usrmerge_aliases(self):
        observer = (ROOT / "bootstrap/native-initramfs/observe_environment.py").read_text(
            encoding="utf-8"
        )
        builder = BUILDER.read_text(encoding="utf-8")
        for text in (observer, builder):
            self.assertIn("resolve(strict=True)", text)
            self.assertIn('capture(["dpkg-query", "-S", candidate])', text)
            self.assertIn("dict.fromkeys(candidates)", text)

    def test_native_initramfs_python_sources_contain_no_literal_nul_bytes(self):
        for path in (BUILDER, ROOT / ".github/workflows/native-initramfs-environment.yml"):
            self.assertNotIn(b"\x00", path.read_bytes(), str(path))


if __name__ == "__main__":
    unittest.main()
