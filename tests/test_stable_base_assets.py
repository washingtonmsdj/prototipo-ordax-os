#!/usr/bin/env python3
"""Regress immutable Stable/MVP Base boot asset publication."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/stable-base-assets.yml"
BASE = json.loads(
    (ROOT / "docs/contracts/base-update.json").read_text(encoding="utf-8")
)
DISTRIBUTION = json.loads(
    (ROOT / "docs/contracts/distribution-profiles.json").read_text(encoding="utf-8")
)
CANDIDATE = json.loads(
    (ROOT / "system/base-update/candidate.json").read_text(encoding="utf-8")
)
MINIMAL = json.loads(
    (ROOT / "docs/contracts/minimal-bootstrap.json").read_text(encoding="utf-8")
)


class StableBaseAssetsTests(unittest.TestCase):
    def test_candidate_descriptor_stays_bound_to_canonical_boot_bytes(self):
        self.assertEqual(
            set(CANDIDATE),
            {"$schema", "kernel_sha256", "initramfs_sha256"},
        )
        self.assertEqual(
            CANDIDATE["$schema"],
            "prototype-ordax.base-update-candidate/1",
        )
        groups = {group["id"]: group for group in MINIMAL["artifact_groups"]}
        self.assertEqual(
            CANDIDATE["kernel_sha256"],
            groups["kernel"]["artifacts"][0]["sha256"],
        )
        self.assertEqual(
            CANDIDATE["initramfs_sha256"],
            groups["initramfs"]["artifacts"][0]["sha256"],
        )

    def test_stable_profile_has_no_development_rootfs_artifact(self):
        stable = BASE["stable_profile"]
        self.assertEqual(stable["profile"], "stable-mvp")
        self.assertFalse(stable["operational_git_required"])
        self.assertTrue(stable["signed_runtime_release_is_authenticity_source"])
        self.assertEqual(
            stable["candidate_descriptor"],
            "system/base-update/candidate.json",
        )
        self.assertTrue(stable["candidate_descriptor_is_inside_signed_system_tar"])
        self.assertTrue(stable["candidate_descriptor_binds_kernel_sha256"])
        self.assertTrue(stable["candidate_descriptor_binds_initramfs_sha256"])
        self.assertEqual(
            stable["asset_tag_template"],
            "ordax-stable-base-{source_commit}",
        )
        self.assertEqual(stable["asset_names"], ["vmlinuz", "initrd.gz"])
        self.assertFalse(stable["transport_tag_is_authenticity_source"])
        self.assertTrue(stable["asset_acceptance_requires_signed_descriptor_hash_match"])
        self.assertTrue(stable["source_commit_identity_must_match_signed_runtime_release"])
        self.assertFalse(stable["stable_rootfs_artifact_present"])
        self.assertTrue(stable["persistent_ordax_partition_is_root_substrate"])
        self.assertFalse(stable["development_rootfs_tar_allowed"])
        self.assertFalse(stable["development_dev_base_manifest_allowed"])
        self.assertTrue(stable["source_asset_publication_implemented"])
        self.assertFalse(stable["device_asset_acquisition_implemented"])
        self.assertFalse(stable["esp_staging_connected"])
        self.assertFalse(stable["oneshot_activation_connected"])
        self.assertFalse(stable["reboot_automation_connected"])

    def test_distribution_gate_advances_only_to_signed_acquisition(self):
        stable = DISTRIBUTION["profiles"]["stable-mvp"]
        self.assertEqual(
            stable["stable_base_profile"],
            "kernel-initramfs-plus-persistent-ordax",
        )
        self.assertFalse(stable["stable_base_rootfs_tar_used"])
        self.assertTrue(stable["stable_base_asset_publication_implemented"])
        self.assertEqual(
            stable["stable_base_asset_transport"],
            "ordax-stable-base-<source_commit>",
        )
        self.assertEqual(
            stable["stable_base_transport_authenticity_source"],
            "signed-system-base-candidate-descriptor",
        )
        self.assertFalse(stable["stable_base_device_acquisition_connected"])
        self.assertFalse(stable["stable_base_esp_staging_connected"])
        self.assertFalse(stable["stable_base_activation_connected"])
        gate = DISTRIBUTION["next_gate"]
        self.assertEqual(gate["id"], "stable-base-signed-acquisition")
        self.assertFalse(gate["implemented"])
        self.assertIn("kernel/initramfs", gate["description"])
        self.assertIn("without Git", gate["description"])
        self.assertIn("without", gate["description"])
        self.assertIn("rootfs.tar", gate["description"])

    def test_workflow_rebuilds_and_binds_assets_before_publication(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python bootstrap/kernel/build.py build --jobs 4", workflow)
        self.assertIn("python bootstrap/initramfs/build.py build --jobs 4", workflow)
        self.assertIn("system/base-update/candidate.json", workflow)
        self.assertIn("descriptor.get('kernel_sha256')", workflow)
        self.assertIn("descriptor.get('initramfs_sha256')", workflow)
        self.assertIn('tag="ordax-stable-base-$GITHUB_SHA"', workflow)
        self.assertIn("for asset in vmlinuz initrd.gz", workflow)
        self.assertIn("gh release download", workflow)
        self.assertIn('test "$local_hash" = "$remote_hash"', workflow)
        self.assertNotIn("--clobber", workflow)
        self.assertIn("STABLE_BASE_ROOTFS_ARTIFACT=NO", workflow)
        self.assertIn("STABLE_BASE_ACTIVATION_AUTHORIZED=NO", workflow)

    def test_workflow_does_not_publish_development_base_payload(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("rootfs.tar", workflow)
        self.assertNotIn("dev-base.json", workflow)
        self.assertNotIn("ordax-dev-base-", workflow)
        self.assertNotIn("bootstrap/dev-base/build.py", workflow)
        self.assertNotIn("LoaderEntryOneShot", workflow)
        self.assertNotIn("systemctl reboot", workflow)
        self.assertNotIn("busybox reboot", workflow)
        self.assertNotIn("reboot -f", workflow)


if __name__ == "__main__":
    unittest.main()
