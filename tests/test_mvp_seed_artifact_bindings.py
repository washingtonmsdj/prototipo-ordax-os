#!/usr/bin/env python3
"""Regress exact resolved bytes for the current minimal MVP bootstrap seed."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MINIMAL = ROOT / "docs/contracts/minimal-bootstrap.json"


class MVPSeedArtifactBindingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(MINIMAL.read_text(encoding="utf-8"))
        cls.groups = {group["id"]: group for group in cls.contract["artifact_groups"]}

    def artifact(self, group: str):
        artifacts = self.groups[group]["artifacts"]
        self.assertEqual(len(artifacts), 1)
        return artifacts[0]

    def test_current_kernel_binding_matches_portable_v2_capable_kernel(self):
        artifact = self.artifact("kernel")
        self.assertEqual(artifact["source_path"], "bootstrap/kernel/vmlinuz-6.6.52")
        self.assertEqual(artifact["sha256"], "43652d59b476e5c1db159ddd39b99bec40cc7e7f1d8879be393ac87534233ee0")

    def test_current_initramfs_binding_matches_portable_v2_capable_capsule(self):
        artifact = self.artifact("initramfs")
        self.assertEqual(artifact["source_path"], "bootstrap/initramfs/initramfs.cpio.gz")
        self.assertEqual(artifact["sha256"], "11ea01da99a7c1002f218abe6112908cb458ddac1d602b624c2bb5780653dc16")

    def test_current_release_agent_seed_is_explicit_v3_refresh_source(self):
        artifact = self.artifact("bootstrap-release-acquisition")
        refresh = json.loads(
            (ROOT / "system/services/base-update/release-agent-refresh.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(artifact["sha256"], "102c9aeb531b582b4b60d8e808da7f50871c3ea2353c2dc82bd6373f9edc28da")
        self.assertEqual(refresh["target_sha256"], "ece358c676d6248798bc53f4f5ac52a4e6bc06cda3111b7978acbc917059bf4c")
        self.assertNotEqual(artifact["sha256"], refresh["target_sha256"])
        self.assertIn(artifact["sha256"], refresh["allowed_from_sha256"])
        self.assertIn(
            "ba633274ee2b9497a75a1b287979900ac31611ff93ec52179bd704daf0a6dbce",
            refresh["allowed_from_sha256"],
        )

    def test_only_canonical_release_trust_remains_unresolved(self):
        unresolved = [g["id"] for g in self.contract["artifact_groups"] if not g["resolved"]]
        self.assertEqual(unresolved, ["bootstrap-release-trust"])
        self.assertFalse(self.contract["physical_write_allowed"])


if __name__ == "__main__":
    unittest.main()
