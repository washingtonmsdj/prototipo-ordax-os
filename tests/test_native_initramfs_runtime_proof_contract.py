#!/usr/bin/env python3
"""Regression tests for the Native initramfs packaged-runtime proof boundary."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "docs/contracts/native-initramfs-runtime-proof.json").read_text(
        encoding="utf-8"
    )
)
SCRIPT = (ROOT / "bootstrap/native-initramfs/prove_runtime.py").read_text(
    encoding="utf-8"
)


class NativeInitramfsRuntimeProofContractTests(unittest.TestCase):
    def test_proof_is_disposable_and_does_not_claim_boot(self):
        self.assertEqual(
            CONTRACT["$schema"],
            "prototype-ordax.native-initramfs-runtime-proof/1",
        )
        self.assertFalse(CONTRACT["physical_device_paths_allowed"])
        self.assertFalse(CONTRACT["physical_write_authorized"])
        self.assertFalse(CONTRACT["qemu_uefi_boot_proven"])
        self.assertFalse(CONTRACT["pid1_kernel_cmdline_boot_proven"])
        self.assertIn("uefi-boot-proven", CONTRACT["forbidden_claims"])
        self.assertIn("physical-apply-authorized", CONTRACT["forbidden_claims"])

    def test_proof_executes_packaged_runtime_and_destroys_ephemeral_material(self):
        for marker in (
            '"/usr/sbin/cryptsetup", "luksFormat"',
            '"/usr/sbin/cryptsetup", "open"',
            '"/usr/bin/btrfs", "subvolume", "create"',
            '"mkfs.btrfs"',
            '"--readonly"',
            '"readonly_mount_rejects_write"',
            '"ephemeral_key_destroyed"',
            '"disposable_container_destroyed"',
        ):
            self.assertIn(marker, SCRIPT)
        self.assertIn("physical_device_touched", SCRIPT)
        self.assertIn("physical_write_authorized", SCRIPT)

    def test_subvolume_and_product_mode_expectations_match_native_contract(self):
        self.assertEqual(
            CONTRACT["expected_subvolumes"],
            [
                "ordax-state",
                "ordax-home",
                "ordax-apps",
                "ordax-containers",
                "ordax-snapshots",
            ],
        )
        self.assertEqual(CONTRACT["expected_product_mode"], "native-disk")
        self.assertEqual(CONTRACT["expected_pool_label"], "ORDAX-POOL")


if __name__ == "__main__":
    unittest.main()
