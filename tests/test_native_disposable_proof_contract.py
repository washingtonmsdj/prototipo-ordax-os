#!/usr/bin/env python3
"""Contract regressions for the Native disposable storage proof."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROOF = json.loads(
    (ROOT / "docs" / "contracts" / "native-disposable-proof.json").read_text(
        encoding="utf-8"
    )
)
STORAGE = json.loads(
    (ROOT / "docs" / "contracts" / "storage-architecture.json").read_text(
        encoding="utf-8"
    )
)
SCRIPT = (ROOT / "tools" / "creator" / "proof" / "native_disposable.py").read_text(
    encoding="utf-8"
)


class NativeDisposableProofContractTests(unittest.TestCase):
    def test_proof_is_non_physical_and_not_a_boot_claim(self):
        self.assertEqual(PROOF["$schema"], "prototype-ordax.native-disposable-proof/1")
        self.assertEqual(PROOF["status"], "proof-only")
        self.assertFalse(PROOF["physical_write_allowed"])
        self.assertFalse(PROOF["physical_device_paths_allowed"])
        self.assertFalse(PROOF["bootable_proof"])
        self.assertEqual(
            PROOF["boot_integration_status"],
            "pending-native-luks2-btrfs-bootstrap",
        )

    def test_partition_identity_matches_durable_storage_contract(self):
        expected = PROOF["expected"]["partitions"]
        native = STORAGE["profiles"]["native-disk"]["physical_layout"]
        self.assertEqual([p["name"] for p in expected], [p["name"] for p in native])
        for proof_partition, storage_partition in zip(expected, native, strict=True):
            self.assertEqual(
                proof_partition["type_guid"],
                storage_partition["gpt_type_guid"],
            )
        self.assertEqual(
            expected[1]["type_guid"],
            "ca7d7ccb-63ed-4c53-861c-1742536059cc",
        )
        self.assertEqual(expected[1]["encryption"], "luks2")
        self.assertEqual(expected[1]["filesystem"], "btrfs")

    def test_subvolume_set_matches_storage_architecture(self):
        native = STORAGE["profiles"]["native-disk"]
        names = [entry["name"] for entry in native["pool_model"]["recommended_subvolumes"]]
        self.assertEqual(PROOF["expected"]["subvolumes"], names)

    def test_product_mode_runtime_path_is_translated_to_pool_root(self):
        self.assertEqual(
            PROOF["expected"]["target_product_mode_path"],
            "/ordax/bootstrap/config/product-mode",
        )
        self.assertIn('runtime_prefix = "/ordax/"', SCRIPT)
        self.assertIn('expected_relative = target_mode_path[len(runtime_prefix):]', SCRIPT)
        self.assertIn('logical = target_mode_pool_relative_path', SCRIPT)
        self.assertIn('logical != expected_relative', SCRIPT)
        self.assertNotIn('logical = target_mode_path.lstrip("/")', SCRIPT)
        self.assertIn('marker = mountpoint / logical', SCRIPT)

    def test_proof_tool_refuses_physical_device_semantics(self):
        self.assertIn('str(path).startswith("/dev/")', SCRIPT)
        self.assertIn("stat.S_ISREG", SCRIPT)
        self.assertIn("stat.S_ISLNK", SCRIPT)
        self.assertIn("stat.S_ISBLK", SCRIPT)
        self.assertIn('"physical_write_authorized": False', SCRIPT)
        self.assertIn('"physical_device_touched": False', SCRIPT)
        self.assertIn('"bootable_proven": False', SCRIPT)
        self.assertIn("ephemeral LUKS key survived proof construction", SCRIPT)


if __name__ == "__main__":
    unittest.main()
