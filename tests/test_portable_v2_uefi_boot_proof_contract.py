#!/usr/bin/env python3
"""Regress the portable-v2 OVMF/UEFI proof boundary."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "docs/contracts/portable-v2-uefi-boot-proof.json").read_text(encoding="utf-8"))
SCRIPT = (ROOT / "bootstrap/portable-v2/uefi_boot.py").read_text(encoding="utf-8")


class PortableV2UEFIBootProofTests(unittest.TestCase):
    def test_contract_records_uefi_proof_without_claiming_secure_or_physical_boot(self):
        self.assertEqual(CONTRACT["$schema"], "prototype-ordax.portable-v2-uefi-boot-proof/1")
        self.assertEqual(CONTRACT["firmware"], "ovmf-non-secure-boot-ci-only")
        self.assertFalse(CONTRACT["secure_boot_proven"])
        self.assertTrue(CONTRACT["qemu_uefi_boot_proven"])
        self.assertFalse(CONTRACT["physical_usb_boot_proven"])
        self.assertFalse(CONTRACT["physical_write_authorized"])
        self.assertFalse(CONTRACT["public_physical_promotion_allowed"])
        self.assertEqual(
            CONTRACT["release_manifest_schema"],
            "prototype-ordax.release-manifest/3",
        )
        self.assertTrue(CONTRACT["surface_runtime_required"])
        self.assertTrue(CONTRACT["surface_runtime_content_addressed"])
        self.assertEqual(CONTRACT["last_proven_source_commit"], "b9e1b164d7510f2dfc7572e473642b8fb885fa8c")
        self.assertEqual(CONTRACT["proof_artifact_sha256"], "0f5b922cb3f24c1c339e7c0c5f4abe9d9b72322ee1da527aee6f54fc65fc730c")
        self.assertEqual(
            CONTRACT["last_proven_surface_runtime_sha256"],
            "5b44729139777b610c300864d6f41c0580a3d6ca0b694b8dc53e38f505f99236",
        )
        self.assertFalse(CONTRACT["last_proven_network_required_for_first_boot"])
        self.assertFalse(CONTRACT["last_proven_physical_target_device_touched"])
        self.assertFalse(CONTRACT["last_proven_guest_disk_retained"])
        self.assertFalse(CONTRACT["last_proven_ovmf_vars_retained"])

    def test_loader_entries_are_portable_only(self):
        normal = (ROOT / CONTRACT["loader"]["normal_entry"]).read_text(encoding="utf-8")
        recovery = (ROOT / CONTRACT["loader"]["recovery_entry"]).read_text(encoding="utf-8")
        loader = (ROOT / CONTRACT["loader"]["config"]).read_text(encoding="utf-8")
        self.assertIn("default ordax-portable.conf", loader)
        self.assertIn("editor no", loader)
        for text in (normal, recovery):
            self.assertIn("linux /ordax/vmlinuz", text)
            self.assertIn("initrd /ordax/initrd.gz", text)
            self.assertIn("rdinit=/sbin/ordax-portable-init", text)
            self.assertIn("console=ttyS0", text)
        self.assertNotIn("ordax.mode=recovery", normal)
        self.assertIn("ordax.mode=recovery", recovery)
        self.assertNotIn("native-disk", normal)

    def test_harness_reuses_direct_final_disk_and_never_touches_physical_media(self):
        for marker in (
            "direct.stage_disk(args, inputs, work)",
            "EFI/BOOT/BOOTX64.EFI",
            "ordax/vmlinuz",
            "ordax/initrd.gz",
            "find_ovmf()",
            '"-net", "none"',
            "ORDAX_PORTABLE_V2_HANDOFF=VERIFIED",
            "ORDAX_STABLE_INIT_HANDOFF=VERIFIED",
            "ORDAX_PORTABLE_RELEASE_MANIFEST_SCHEMA=",
            "ORDAX_SURFACE_RUNTIME_HANDOFF=VERIFIED",
            "ORDAX_SURFACE_RUNTIME_SHA256=",
            "ORDAX_LOCAL_AI_RUNTIME_HANDOFF=VERIFIED",
            "ORDAX_LOCAL_AI_RUNTIME_SHA256=",
            '"surface_runtime_sha_exact": True',
            '"local_ai_runtime_sha_exact":',
            '"qemu_uefi_boot_proven": True',
            '"secure_boot_proven": False',
            '"physical_usb_boot_proven": False',
        ):
            self.assertIn(marker, SCRIPT)
        self.assertNotIn("/dev/sd", SCRIPT)
        self.assertNotIn("PhysicalDrive", SCRIPT)


if __name__ == "__main__":
    unittest.main()
