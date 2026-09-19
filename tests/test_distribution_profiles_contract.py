#!/usr/bin/env python3
"""Regress the Owner/Development vs Stable/MVP distribution boundary."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "docs/contracts/distribution-profiles.json").read_text(encoding="utf-8")
)
RELEASE_CHANNEL = json.loads(
    (ROOT / "docs/contracts/release-channel.json").read_text(encoding="utf-8")
)
PUBLIC_SITE = json.loads(
    (ROOT / "docs/contracts/public-site.json").read_text(encoding="utf-8")
)


class DistributionProfilesContractTests(unittest.TestCase):
    def test_single_product_source_authority(self):
        source = CONTRACT["source_authority"]
        self.assertEqual(source["repository"], "washingtonmsdj/prototipo-ordax-os")
        self.assertEqual(source["branch"], "main")
        self.assertTrue(source["single_product_codebase"])
        self.assertFalse(source["permanent_profile_forks_allowed"])

    def test_owner_profile_is_internal_git_first(self):
        owner = CONTRACT["profiles"]["owner-development"]
        self.assertFalse(owner["public_distribution"])
        self.assertTrue(owner["operational_git_allowed"])
        self.assertTrue(owner["full_git_client_allowed"])
        self.assertTrue(owner["source_checkout_allowed"])
        self.assertEqual(owner["normal_update_transport"], "git-main")
        self.assertEqual(
            owner["normal_update_owner"],
            "bootstrap/dev-base/ordax-pull",
        )
        self.assertEqual(owner["runtime_update_owner"], "system/supervisor")
        self.assertEqual(
            owner["base_update_owner"],
            "system/services/base-update/agent.sh",
        )
        self.assertTrue(owner["diagnostic_source_sha_visible"])

    def test_stable_profile_has_no_operational_git_dependency(self):
        stable = CONTRACT["profiles"]["stable-mvp"]
        self.assertTrue(stable["public_distribution"])
        self.assertFalse(stable["operational_git_allowed"])
        self.assertFalse(stable["full_git_client_required"])
        self.assertFalse(stable["source_checkout_required"])
        self.assertEqual(
            stable["normal_update_transport"],
            "official-signed-release-channel",
        )
        self.assertEqual(
            stable["normal_update_owner"],
            "bootstrap/release-acquisition",
        )
        self.assertTrue(stable["signed_envelope_required"])
        self.assertTrue(stable["artifact_hash_and_size_required"])
        self.assertTrue(stable["known_good_preservation_required"])
        self.assertTrue(stable["base_ab_health_rollback_required"])
        self.assertFalse(stable["git_branch_pr_details_in_normal_ux"])
        self.assertTrue(stable["creator_is_primary_media_path"])
        self.assertFalse(stable["production_release_published"])
        self.assertTrue(stable["runtime_profile_selection_implemented"])
        self.assertEqual(stable["runtime_source_identity"], "verified-release-sha")
        self.assertFalse(stable["git_update_polling_enabled"])
        self.assertFalse(stable["development_git_rescue_enabled"])
        self.assertFalse(stable["development_base_channel_enabled"])
        self.assertTrue(stable["shared_surface_health_supervision_enabled"])
        self.assertFalse(stable["continuous_signed_runtime_update_connected"])
        self.assertFalse(stable["base_update_owner_active"])
        self.assertEqual(
            stable["base_update_owner_activation_gate"],
            "stable-continuous-signed-update",
        )
        self.assertEqual(
            stable["signed_release_discovery_primitive"],
            "ordax-release-agent inspect",
        )
        self.assertTrue(stable["signed_release_discovery_implemented"])
        self.assertFalse(stable["signed_release_discovery_downloads_artifact"])
        self.assertFalse(stable["signed_release_discovery_changes_current"])
        self.assertTrue(stable["signed_release_discovery_requires_trust"])
        self.assertTrue(stable["signed_release_discovery_source_implemented"])
        self.assertFalse(stable["signed_release_discovery_physical_agent_ready"])
        self.assertTrue(stable["signed_release_discovery_asset_published"])
        self.assertEqual(
            stable["signed_release_discovery_asset_sha256"],
            "1a124616c95ee79be1fb50b00205cb5f9f5382bcb4144b36020fcd5d3be04596",
        )
        self.assertTrue(stable["signed_release_seed_media_includes_inspect"])
        self.assertEqual(
            stable["signed_release_discovery_physical_agent_target_sha256"],
            "1a124616c95ee79be1fb50b00205cb5f9f5382bcb4144b36020fcd5d3be04596",
        )
        self.assertTrue(stable["periodic_signed_channel_polling_connected"])
        self.assertEqual(stable["periodic_signed_channel_default_seconds"], 60)
        self.assertTrue(stable["signed_release_materialization_connected"])
        self.assertTrue(stable["signed_release_materialization_exact_commit_required"])
        self.assertFalse(stable["signed_release_staging_changes_current"])
        self.assertFalse(stable["signed_release_staging_activation_performed"])
        self.assertFalse(stable["signed_release_activation_connected"])

    def test_stable_profile_reuses_existing_release_authorities(self):
        stable = CONTRACT["profiles"]["stable-mvp"]
        self.assertEqual(
            stable["release_channel_contract"],
            "docs/contracts/release-channel.json",
        )
        self.assertEqual(
            stable["release_protocol_contract"],
            "docs/contracts/release-protocol.json",
        )
        self.assertEqual(
            stable["trust_policy_contract"],
            "docs/contracts/release-trust-policy.json",
        )
        self.assertEqual(
            stable["base_update_contract"],
            "docs/contracts/base-update.json",
        )
        self.assertFalse(RELEASE_CHANNEL["device_pre_release"]["full_git_client_required"])
        self.assertFalse(RELEASE_CHANNEL["device_pre_release"]["source_checkout_required"])

    def test_public_site_is_stable_only(self):
        stable = CONTRACT["profiles"]["stable-mvp"]
        self.assertEqual(stable["public_site_contract"], "docs/contracts/public-site.json")
        distribution = PUBLIC_SITE["product_distribution"]
        self.assertEqual(distribution["public_profile"], "stable-mvp")
        self.assertFalse(distribution["owner_development_profile_public"])
        self.assertFalse(distribution["public_runtime_depends_on_git"])
        self.assertTrue(distribution["public_updates_use_official_channels"])

    def test_next_gate_is_candidate_health_before_activation(self):
        gate = CONTRACT["next_gate"]
        self.assertEqual(gate["id"], "stable-staged-release-health")
        self.assertFalse(gate["implemented"])
        self.assertIn("candidate Surface/runtime health", gate["description"])
        self.assertIn("before any exact activation", gate["description"])
        self.assertTrue(CONTRACT["invariants"]["same_main_source_authority"])
        self.assertTrue(CONTRACT["invariants"]["stable_must_not_require_git_client"])
        self.assertTrue(CONTRACT["invariants"]["stable_must_not_require_source_checkout"])


if __name__ == "__main__":
    unittest.main()
