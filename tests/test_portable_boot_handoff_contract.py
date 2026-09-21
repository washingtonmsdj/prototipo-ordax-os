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

    def test_ci_boot_handoff_is_implemented_but_physical_promotion_is_blocked(self):
        self.assertEqual(
            self.contract["$schema"],
            "prototype-ordax.portable-boot-handoff/1",
        )
        self.assertEqual(
            self.contract["status"],
            "ci-boot-handoff-proven-runtime-v3-candidate",
        )
        self.assertFalse(self.contract["physical_boot_connected"])
        self.assertTrue(self.contract["bootable_proven"])
        self.assertFalse(self.contract["physical_write_authorized"])
        self.assertTrue(self.contract["activation_selection_implemented"])
        self.assertTrue(self.contract["rollback_selection_implemented"])
        self.assertTrue(self.contract["initramfs_integration_implemented"])
        self.assertEqual(
            self.contract["release_manifest_schema"],
            "prototype-ordax.release-manifest/3",
        )
        self.assertIn(
            "prototype-ordax.release-manifest/2",
            self.contract["compatible_release_manifest_schemas"],
        )
        self.assertEqual(
            self.contract["proof"]["release_verifier_command"],
            "ordax-release-agent verify-portable-v3-exact",
        )
        handoff = self.contract["initramfs_integration_requirements"]
        self.assertEqual(
            handoff["known_good_exact_resolver_signature_handoff"],
            "ordax-release-agent verify-portable-v3-exact",
        )
        self.assertEqual(
            handoff["known_good_exact_resolver_signature_handoff_compatibility"],
            [
                "ordax-release-agent verify-portable-v3-exact",
                "ordax-release-agent verify-portable-exact",
            ],
        )

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
        self.assertEqual(
            proof["runtime_system_view"]["filesystem"],
            "read-only-bind",
        )
        self.assertFalse(proof["runtime_system_view"]["persistent_upper"])
        self.assertFalse(
            self.contract["runtime_boundary"]["system_persistent_overlay_allowed"]
        )
        self.assertTrue(
            self.contract["runtime_boundary"]["stable_base_overlay_required"]
        )
        surface = proof["surface_runtime_mount"]
        self.assertEqual(surface["filesystem"], "erofs")
        self.assertTrue(surface["read_only_lower"])
        self.assertEqual(surface["runtime_view"], "overlayfs")
        self.assertFalse(surface["persistent_upper"])

    def test_initramfs_integration_gap_is_explicit(self):
        requirements = self.contract["initramfs_integration_requirements"]
        self.assertTrue(requirements["busybox_losetup_applet_required"])
        self.assertTrue(requirements["busybox_losetup_applet_currently_enabled"])
        self.assertTrue(requirements["busybox_mount_loop_currently_enabled"])
        self.assertTrue(requirements["busybox_exfat_volume_id_currently_enabled"])
        self.assertTrue(requirements["portable_handoff_helper_required"])
        self.assertTrue(requirements["portable_handoff_helper_currently_installed"])
        self.assertTrue(requirements["activation_state_reader_required"])
        self.assertTrue(requirements["activation_state_reader_currently_installed"])
        self.assertEqual(requirements["activation_state_reader_path"], "/sbin/ordax-portable-state")
        self.assertTrue(requirements["portable_handoff_helper_pid1_connected"])
        self.assertTrue(requirements["activation_selection_helper_pid1_connected"])
        self.assertTrue(requirements["portable_v3_release_verification"])
        self.assertTrue(requirements["surface_runtime_reference_verified"])
        self.assertEqual(
            requirements["surface_runtime_mount_operation"],
            "mount-surface-runtime",
        )
        self.assertFalse(requirements["surface_runtime_persistent_upper"])
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
        self.assertTrue(migration["portable_usb_v2_boot_handoff_implemented"])
        self.assertTrue(migration["portable_release_protocol_v3_implemented"])
        self.assertTrue(
            migration["portable_surface_runtime_v3_boot_handoff_implemented"]
        )
        self.assertFalse(migration["portable_usb_v2_physical_write_enabled"])
        self.assertFalse(migration["public_physical_promotion_allowed"])

    def test_proof_script_rejects_device_paths_and_never_switches_root(self):
        text = PROOF.read_text(encoding="utf-8")
        self.assertIn('startswith("/dev/")', text)
        self.assertIn('"verify-portable-exact"', text)
        self.assertIn('"mount", "-t", "erofs"', text)
        self.assertIn('"mount", "-t", "ext4"', text)
        self.assertIn('"mount", "--bind"', text)
        self.assertIn('"remount,bind,ro,nodev,nosuid"', text)
        self.assertNotIn('"mount", "-t", "overlay"', text)
        self.assertNotIn("switch_root", text)
        self.assertNotIn("PhysicalDrive", text)


if __name__ == "__main__":
    unittest.main()
