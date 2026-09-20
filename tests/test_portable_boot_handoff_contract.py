#!/usr/bin/env python3
"""Regress the portable USB v2 disposable boot-handoff boundary."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/contracts/portable-boot-handoff.json"
PROOF = ROOT / "bootstrap/portable-v2/proof.py"
INITRAMFS_BUILD = ROOT / "bootstrap/initramfs/build.py"
STORAGE = ROOT / "docs/contracts/storage-architecture.json"


class PortableBootHandoffContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_proof_is_nonphysical_and_does_not_claim_boot(self):
        self.assertEqual(
            self.contract["$schema"],
            "prototype-ordax.portable-boot-handoff/1",
        )
        self.assertEqual(self.contract["status"], "disposable-mount-proof-only")
        self.assertFalse(self.contract["physical_boot_connected"])
        self.assertFalse(self.contract["bootable_proven"])
        self.assertFalse(self.contract["physical_write_authorized"])
        self.assertFalse(self.contract["activation_selection_implemented"])
        self.assertFalse(self.contract["initramfs_integration_implemented"])

    def test_release_is_system_tree_not_a_fake_rootfs(self):
        boundary = self.contract["runtime_boundary"]
        self.assertFalse(boundary["system_erofs_is_complete_rootfs"])
        self.assertTrue(boundary["system_erofs_contains_shared_product_system_tree"])
        self.assertTrue(boundary["minimal_os_base_remains_separate"])
        self.assertFalse(boundary["switch_root_to_system_erofs_allowed"])

    def test_mount_graph_keeps_exfat_out_of_overlay_upper(self):
        proof = self.contract["proof"]
        self.assertEqual(proof["release_mount"]["filesystem"], "erofs")
        self.assertTrue(proof["release_mount"]["read_only"])
        self.assertEqual(proof["state_mount"]["filesystem"], "ext4")
        self.assertEqual(proof["runtime_system_view"]["filesystem"], "overlayfs")
        self.assertIn("persistent-state", proof["runtime_system_view"]["upper"])
        self.assertIn("persistent-state", proof["runtime_system_view"]["work"])

    def test_initramfs_integration_gap_is_explicit(self):
        requirements = self.contract["initramfs_integration_requirements"]
        self.assertTrue(requirements["busybox_losetup_applet_required"])
        self.assertTrue(requirements["busybox_losetup_applet_currently_enabled"])
        self.assertTrue(requirements["busybox_mount_loop_currently_enabled"])
        self.assertTrue(requirements["busybox_exfat_volume_id_currently_enabled"])
        self.assertTrue(requirements["portable_handoff_helper_required"])
        self.assertFalse(requirements["portable_handoff_helper_currently_installed"])
        initramfs = INITRAMFS_BUILD.read_text(encoding="utf-8")
        applets = initramfs.split("REQUIRED_APPLETS", 1)[1].split("}", 1)[0]
        self.assertIn('"losetup"', applets)
        self.assertIn('"CONFIG_LOSETUP": "y"', initramfs)
        self.assertIn('"CONFIG_FEATURE_MOUNT_LOOP": "y"', initramfs)
        self.assertIn('"CONFIG_FEATURE_VOLUMEID_EXFAT": "y"', initramfs)

    def test_storage_contract_still_blocks_real_boot_promotion(self):
        storage = json.loads(STORAGE.read_text(encoding="utf-8"))
        migration = storage["prototype_migration"]
        self.assertTrue(migration["portable_usb_v2_mount_handoff_disposable_proof_implemented"])
        self.assertFalse(migration["portable_usb_v2_boot_handoff_implemented"])
        self.assertFalse(migration["portable_usb_v2_physical_write_enabled"])

    def test_proof_script_rejects_device_paths_and_never_switches_root(self):
        text = PROOF.read_text(encoding="utf-8")
        self.assertIn('startswith("/dev/")', text)
        self.assertIn('"verify-portable-exact"', text)
        self.assertIn('"mount", "-t", "erofs"', text)
        self.assertIn('"mount", "-t", "ext4"', text)
        self.assertIn('"mount", "-t", "overlay"', text)
        self.assertNotIn("switch_root", text)
        self.assertNotIn("PhysicalDrive", text)


if __name__ == "__main__":
    unittest.main()
