#!/usr/bin/env python3
"""Regress the Native ESP source/materialization contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "docs/contracts/native-esp.json").read_text(encoding="utf-8"))
BOOT = json.loads((ROOT / "docs/contracts/native-boot.json").read_text(encoding="utf-8"))


class NativeESPContractTests(unittest.TestCase):
    def test_native_esp_reuses_shared_bootloader_source_without_reusing_usb_entries(self):
        self.assertEqual(CONTRACT["$schema"], "prototype-ordax.native-esp/1")
        self.assertFalse(CONTRACT["physical_write_authorized"])
        self.assertEqual(
            CONTRACT["bootloader"]["shared_source_contract"],
            "boot/esp/source.json",
        )
        self.assertFalse(CONTRACT["bootloader"]["duplicate_bootloader_policy_implementation"])
        self.assertIn("portable-usb-entry-reuse", CONTRACT["forbidden"])

    def test_configuration_sources_are_hash_pinned(self):
        for key in ("loader_conf", "normal_entry_template", "recovery_entry_template"):
            item = CONTRACT["configuration"][key]
            path = ROOT / item["source"]
            self.assertTrue(path.is_file(), path)
            self.assertFalse(path.is_symlink(), path)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                item["sha256"],
                item["source"],
            )

    def test_native_loader_defaults_to_native_entry_only(self):
        loader = (ROOT / CONTRACT["configuration"]["loader_conf"]["source"]).read_text(
            encoding="utf-8"
        )
        self.assertIn("default ordax-native.conf", loader)
        self.assertIn("auto-entries no", loader)
        self.assertIn("auto-firmware no", loader)
        self.assertIn("editor no", loader)
        self.assertNotIn("default ordax.conf", loader)

    def test_entry_templates_bind_exact_public_pool_identity_without_secret(self):
        for key, mode in (
            ("normal_entry_template", "normal"),
            ("recovery_entry_template", "recovery"),
        ):
            item = CONTRACT["configuration"][key]
            text = (ROOT / item["source"]).read_text(encoding="utf-8")
            self.assertEqual(text.count(item["placeholder"]), 1)
            self.assertIn(f"ordax.mode={mode}", text)
            self.assertIn("ordax.product_mode=native-disk", text)
            self.assertIn("ordax.pool_uuid=@ORDAX_POOL_UUID@", text)
            for forbidden in ("passphrase", "password=", "keyfile", "key-file", "pool_key"):
                self.assertNotIn(forbidden, text.lower())
        self.assertFalse(CONTRACT["identity"]["pool_uuid_is_secret"])
        self.assertFalse(BOOT["bootloader"]["pool_uuid_is_secret"])

    def test_target_layout_has_no_portable_usb_entry_names(self):
        self.assertEqual(
            CONTRACT["target_layout"],
            [
                "EFI/BOOT/BOOTX64.EFI",
                "loader/loader.conf",
                "loader/entries/ordax-native.conf",
                "loader/entries/ordax-native-recovery.conf",
                "ordax/vmlinuz",
                "ordax/native-initrd.gz",
            ],
        )
        self.assertNotIn("loader/entries/ordax.conf", CONTRACT["target_layout"])
        self.assertNotIn("ordax/initrd.gz", CONTRACT["target_layout"])


if __name__ == "__main__":
    unittest.main()
