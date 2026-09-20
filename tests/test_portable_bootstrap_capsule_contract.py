#!/usr/bin/env python3
"""Regression tests for the durable USB portable bootstrap capsule."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/contracts/portable-bootstrap-capsule.json"
BUILDER = ROOT / "bootstrap/portable-v2/capsule/build.py"
BOOTSTRAP = ROOT / "docs/contracts/portable-bootstrap-v2.json"

spec = importlib.util.spec_from_file_location("ordax_portable_capsule", BUILDER)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class PortableBootstrapCapsuleTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def make_agent(self, root: Path) -> Path:
        path = root / "ordax-release-agent"
        path.write_bytes(b"#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
        return path

    def test_contract_is_candidate_only_and_excludes_product_payload(self):
        self.assertEqual(
            self.contract["$schema"],
            "prototype-ordax.portable-bootstrap-capsule/1",
        )
        self.assertEqual(self.contract["status"], "candidate-proof-only")
        self.assertFalse(self.contract["physical_write_authorized"])
        self.assertFalse(self.contract["physical_boot_connected"])
        self.assertFalse(self.contract["pid1_verified_mount_connected"])
        self.assertFalse(self.contract["canonical_trust_embedded"])
        self.assertFalse(self.contract["publisher_private_key_embedded"])
        self.assertFalse(self.contract["first_boot_network_required"])
        excluded = set(self.contract["explicitly_excluded"])
        self.assertIn("surface-runtime", excluded)
        self.assertIn("normal-apps", excluded)
        self.assertIn("publisher-private-key", excluded)
        self.assertIn("git-checkout", excluded)

    def test_normalized_tar_contains_only_minimal_bootstrap_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agent = self.make_agent(root)
            archive = root / "capsule.tar"
            manifest = module.normalized_tar(agent, archive)
            self.assertEqual(len(manifest["entries"]), 3)
            self.assertFalse(manifest["canonical_trust_embedded"])
            self.assertFalse(manifest["publisher_private_key_embedded"])
            with tarfile.open(archive, "r:") as handle:
                names = set(handle.getnames())
                self.assertIn("bootstrap/release-acquisition/ordax-release-agent", names)
                self.assertIn("bootstrap/recovery/entrypoint", names)
                self.assertIn("bootstrap/config/release-envelope-url", names)
                self.assertIn("bootstrap/capsule-manifest.json", names)
                self.assertFalse(any("surface" in name for name in names))
                self.assertFalse(any("private" in name.lower() for name in names))

    def test_uuid_is_deterministic_but_content_sensitive(self):
        first = module.deterministic_uuid("a" * 64)
        second = module.deterministic_uuid("a" * 64)
        other = module.deterministic_uuid("b" * 64)
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)

    def test_bootstrap_contract_keeps_capsule_unconnected_to_pid1(self):
        bootstrap = json.loads(BOOTSTRAP.read_text(encoding="utf-8"))
        capsule = bootstrap["esp_substrate"]["bootstrap_capsule"]
        self.assertEqual(
            capsule["contract"],
            "docs/contracts/portable-bootstrap-capsule.json",
        )
        self.assertTrue(capsule["candidate_builder_implemented"])
        self.assertTrue(capsule["deterministic_proof_implemented"])
        self.assertFalse(capsule["esp_materialization_implemented"])
        self.assertTrue(capsule["initramfs_hash_pin_builder_support"])
        self.assertTrue(capsule["initramfs_hash_pin_disposable_proof_implemented"])
        self.assertTrue(capsule["initramfs_hash_pin_implemented"])
        self.assertTrue(capsule["initramfs_hash_pin_candidate_only"])
        self.assertFalse(capsule["initramfs_hash_pin_default_candidate_build_enabled"])
        self.assertFalse(capsule["pid1_hash_enforcement_implemented"])
        self.assertFalse(capsule["pid1_verified_mount_implemented"])
        self.assertFalse(capsule["implemented"])


if __name__ == "__main__":
    unittest.main()
