#!/usr/bin/env python3
"""Regression tests for Git-driven, binary release delivery."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "docs/contracts/release-channel.json").read_text(encoding="utf-8")
)


class ReleaseChannelContractTest(unittest.TestCase):
    def test_git_main_remains_source_authority(self):
        source = CONTRACT["source_authority"]
        self.assertEqual(source["kind"], "git")
        self.assertEqual(source["repository"], "washingtonmsdj/prototipo-ordax-os")
        self.assertEqual(source["branch"], "main")

    def test_bootstrap_does_not_need_git_checkout_or_compiler(self):
        device = CONTRACT["device_pre_release"]
        self.assertFalse(device["full_git_client_required"])
        self.assertFalse(device["source_checkout_required"])
        self.assertFalse(device["compiler_required"])
        self.assertFalse(device["codex_required"])
        self.assertTrue(device["https_release_resolver_required"])
        self.assertTrue(device["public_trust_anchor_required"])

    def test_release_is_commit_bound_and_fail_closed(self):
        release = CONTRACT["release"]
        self.assertTrue(release["exact_source_commit_required"])
        self.assertTrue(release["immutable_after_verification"])
        self.assertTrue(release["artifact_sha256_required"])
        self.assertTrue(release["manifest_authenticity_required_before_production"])
        self.assertFalse(release["custom_crypto_allowed"])
        self.assertTrue(release["atomic_activation_required"])
        self.assertTrue(release["known_good_preservation_required"])
        self.assertTrue(release["offline_known_good_boot_required"])

    def test_stable_runtime_health_gate_never_activates_current(self):
        health = CONTRACT["runtime_health_gate"]
        self.assertEqual(health["profile"], "stable-mvp")
        self.assertEqual(health["owner"], "system/supervisor")
        self.assertEqual(
            health["candidate_source"],
            "/ordax/releases/<source_commit>/system",
        )
        self.assertEqual(health["candidate_entrypoint"], "surface/entrypoint")
        self.assertFalse(health["system_entrypoint_invoked"])
        self.assertTrue(health["source_sha_must_match_candidate"])
        self.assertTrue(health["process_survival_required"])
        self.assertTrue(health["surface_health_required"])
        self.assertTrue(health["known_good_surface_restored_after_probe"])
        self.assertTrue(health["known_good_health_required_after_restore"])
        self.assertEqual(
            health["candidate_update_state_source_sha"],
            "candidate-source-commit",
        )
        self.assertEqual(
            health["known_good_restore_update_state_source_sha"],
            "current-source-commit",
        )
        self.assertTrue(health["health_ready_written_only_after_known_good_restore"])
        self.assertFalse(health["repeat_failed_candidate"])
        self.assertFalse(health["current_pointer_changed"])
        self.assertFalse(health["activation_performed"])
        self.assertFalse(health["reboot_requested"])

    def test_exact_activation_primitive_is_not_yet_supervisor_wired(self):
        activation = CONTRACT["runtime_activation_primitive"]
        self.assertEqual(activation["profile"], "stable-mvp")
        self.assertEqual(activation["owner"], "bootstrap/release-acquisition")
        self.assertEqual(
            activation["command"],
            "ordax-release-agent activate-exact",
        )
        self.assertTrue(activation["exact_expected_commit_required"])
        self.assertFalse(activation["network_required"])
        self.assertFalse(activation["latest_pointer_re_resolved"])
        self.assertTrue(activation["materialized_release_reverified"])
        self.assertTrue(activation["previous_current_commit_reported"])
        self.assertTrue(activation["atomic_current_pointer_replace"])
        self.assertFalse(activation["supervisor_health_ready_gate_connected"])
        self.assertFalse(activation["cold_health_rollback_connected"])
        self.assertFalse(activation["reboot_requested"])

    def test_kernel_is_compiled_in_repository_ci_not_on_device(self):
        kernel = CONTRACT["kernel"]
        self.assertFalse(kernel["compiled_on_device"])
        self.assertTrue(kernel["compiled_in_repository_ci"])
        self.assertTrue(kernel["delivered_as_verified_artifact"])

    def test_codex_is_not_publication_dependency(self):
        publication = CONTRACT["publication"]
        self.assertTrue(publication["ci_owned"])
        self.assertFalse(publication["codex_required"])


if __name__ == "__main__":
    unittest.main()
