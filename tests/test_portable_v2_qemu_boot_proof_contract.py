#!/usr/bin/env python3
"""Regress the portable-v2 direct-kernel QEMU proof boundary."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "docs/contracts/portable-v2-qemu-boot-proof.json").read_text(
        encoding="utf-8"
    )
)
SCRIPT = ROOT / "bootstrap/portable-v2/qemu_boot.py"
WORKFLOW = (
    ROOT / ".github/workflows/portable-v2-qemu-boot-proof.yml"
).read_text(encoding="utf-8")


class PortableV2QEMUBootProofTests(unittest.TestCase):
    def test_contract_does_not_overclaim_uefi_or_physical_boot(self):
        self.assertEqual(
            CONTRACT["$schema"],
            "prototype-ordax.portable-v2-qemu-boot-proof/1",
        )
        self.assertEqual(CONTRACT["boot_mode"], "direct-kernel-candidate-only")
        self.assertFalse(CONTRACT["uefi_boot_proven"])
        self.assertFalse(CONTRACT["qemu_direct_kernel_boot_proven"])
        self.assertFalse(CONTRACT["physical_boot_proven"])
        self.assertFalse(CONTRACT["physical_write_authorized"])
        self.assertFalse(CONTRACT["physical_target_device_touched"])

    def test_harness_uses_final_two_partition_layout_and_candidate_rdinit(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--change-name=1:ORDAX-ESP", text)
        self.assertIn("--change-name=2:ORDAX-DATA", text)
        self.assertIn("rdinit=/sbin/ordax-portable-init", text)
        self.assertIn("if=ide,index=0", text)
        self.assertNotIn("if=virtio", text)
        self.assertIn('"system.erofs"', text)
        self.assertIn('"stable-base.erofs"', text)
        self.assertIn('"persistent-state.img"', text)
        self.assertIn('"release-ed25519.json"', text)

    def test_harness_requires_both_handoff_markers_and_disables_network(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("ORDAX_PORTABLE_V2_HANDOFF=VERIFIED", text)
        self.assertIn("ORDAX_STABLE_INIT_HANDOFF=VERIFIED", text)
        self.assertIn("ORDAX_PORTABLE_V2_SLOT=current", text)
        self.assertIn("ORDAX_PORTABLE_V2_SOURCE_SHA=", text)
        self.assertIn("ORDAX_STABLE_INIT_SOURCE_SHA=", text)
        self.assertIn('"-net", "none"', text)
        self.assertIn('"qemu_direct_kernel_boot_proven": True', text)
        self.assertIn('"qemu_uefi_boot_proven": False', text)
        self.assertIn('"physical_usb_boot_proven": False', text)

    def test_workflow_builds_signed_release_real_base_capsule_and_pinned_initramfs(self):
        for marker in (
            "bootstrap/kernel/build.py build",
            "bootstrap/stable-base/build.py build",
            "bootstrap/portable-v2/capsule/build.py build",
            "tools/portable-release-image/build.py build",
            "--manifest-schema 2",
            "release-signing",
            "--portable-bootstrap-capsule",
            "--portable-stable-base",
            "bootstrap/portable-v2/qemu_boot.py",
        ):
            self.assertIn(marker, WORKFLOW)
        self.assertNotIn("OVMF", WORKFLOW)
        self.assertNotIn("/dev/sd", WORKFLOW)
        self.assertNotIn("PhysicalDrive", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
