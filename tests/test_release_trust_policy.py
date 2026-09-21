import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "docs" / "contracts" / "release-trust-policy.json"
TRUST_PATH = ROOT / "bootstrap" / "trust" / "release-ed25519.json"


class ReleaseTrustPolicyTests(unittest.TestCase):
    def load_policy(self):
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_policy_resolves_custody_without_faking_key_material(self):
        policy = self.load_policy()
        self.assertEqual(policy["$schema"], "prototype-ordax.release-trust-policy/1")
        self.assertEqual(policy["status"], "prototype-recovery-verified-external-backup-pending")
        self.assertEqual(policy["algorithm"], "ed25519")
        self.assertEqual(policy["canonical_key_id"], "ordax-prototype-release-v1")
        self.assertEqual(policy["private_key"]["custody_owner"], "repository-owner-developer")
        self.assertTrue(policy["private_key"]["offline_encrypted_backup_required"])
        self.assertEqual(policy["recovery"]["minimum_offline_backups"], 1)
        self.assertFalse(policy["recovery"]["silent_key_replacement_allowed"])
        self.assertTrue(policy["rotation"]["signed_trust_transition_required_for_production"])
        self.assertFalse(policy["rotation"]["production_rotation_implemented"])

    def test_recovery_requires_distinct_cryptographic_proof_without_private_hashes(self):
        recovery = self.load_policy()["recovery"]
        self.assertEqual(recovery["minimum_offline_backups"], 1)
        self.assertEqual(recovery["verification_host"], "developer-windows-machine")
        self.assertTrue(recovery["recovered_private_path_must_be_distinct"])
        self.assertTrue(recovery["recovered_public_derivation_must_match"])
        self.assertTrue(recovery["recovered_signing_proof_required"])
        self.assertEqual(
            recovery["public_evidence_schema"],
            "prototype-ordax.release-trust-ceremony-evidence/1",
        )
        self.assertFalse(recovery["private_key_hash_in_public_evidence_allowed"])
        self.assertTrue(recovery["cryptographic_recovery_verified"])
        self.assertFalse(recovery["external_offline_backup_custody_confirmed"])
        self.assertFalse(recovery["ready_to_pin_public_anchor"])
        self.assertEqual(
            recovery["verification_evidence_repository_path"],
            "docs/evidence/canonical-trust-local-progress-2026-09-21.json",
        )
        self.assertEqual(
            recovery["public_trust_sha256"],
            "d2836df77a3d5a54ccf64cc5643cfd5c19052efc83f2e3e2666c6d3197fce250",
        )
        self.assertEqual(
            recovery["public_handoff_zip_sha256"],
            "85d4f8430f0a4066ebed84a410071409c112c65aa72a5818483a664a41b91e20",
        )

    def test_first_canonical_identity_requires_one_shot_fallback_proof(self):
        prerequisites = self.load_policy()["canonical_ceremony_prerequisites"]
        self.assertEqual(
            prerequisites,
            [
                "portable_runtime_v3_direct_kernel_proven",
                "portable_runtime_v3_uefi_ovmf_proven",
                "portable_v3_one_shot_failure_fallback_proven",
                "portable_writer_v2_implemented_fail_closed",
                "physical_authorization_still_fail_closed",
            ],
        )

    def test_custody_evolution_is_provider_neutral_and_not_single_host_bound(self):
        policy = self.load_policy()
        private_key = policy["private_key"]
        rotation = policy["rotation"]
        self.assertEqual(private_key["current_backend"], "local-pem")
        self.assertFalse(private_key["local_private_key_is_production_single_source_of_truth"])
        self.assertEqual(private_key["managed_backend_target"], "kms-hsm")
        self.assertFalse(private_key["github_is_key_custodian"])
        self.assertTrue(rotation["provider_neutral_signing_backend_required"])
        self.assertFalse(rotation["managed_kms_hsm_required_for_first_physical_proof"])
        self.assertTrue(rotation["signed_rotation_required_before_broad_public_distribution"])
        self.assertTrue(rotation["single_lost_key_or_host_must_not_permanently_block_updates"])

    def test_signed_transition_protocol_does_not_claim_production_activation(self):
        rotation = self.load_policy()["rotation"]
        self.assertTrue(rotation["signed_transition_protocol_source_implemented"])
        self.assertEqual(
            rotation["signed_transition_protocol_schema"],
            "prototype-ordax.release-trust-transition/1",
        )
        self.assertEqual(
            rotation["signed_transition_envelope_schema"],
            "prototype-ordax.release-trust-transition-envelope/1",
        )
        self.assertTrue(
            rotation["signed_transition_protocol_ci_cross_compatibility_required"]
        )
        self.assertTrue(rotation["signed_transition_protocol_ci_cross_compatibility_proven"])
        self.assertEqual(rotation["signed_transition_protocol_ci_run_id"], 35640416446)
        self.assertEqual(rotation["release_agent_transition_ci_run_id"], 35640416481)
        self.assertFalse(rotation["device_stateful_rotation_activation_implemented"])
        self.assertFalse(rotation["bootstrap_effective_trust_selection_implemented"])
        self.assertFalse(rotation["production_rotation_implemented"])

    def test_private_key_locations_explicitly_forbid_repository_and_usb(self):
        forbidden = set(self.load_policy()["private_key"]["forbidden_locations"])
        for location in {"git", "usb-bootstrap", "github-actions-artifacts", "logs", "chat"}:
            self.assertIn(location, forbidden)

    def test_public_anchor_path_matches_runtime_contract(self):
        anchor = self.load_policy()["public_anchor"]
        self.assertEqual(anchor["schema"], "prototype-ordax.release-trust/1")
        self.assertEqual(anchor["repository_path"], "bootstrap/trust/release-ed25519.json")
        self.assertEqual(anchor["runtime_path"], "/ordax/bootstrap/trust/release-ed25519.json")
        self.assertTrue(anchor["pin_only_after_private_custody_ready"])

    def test_recovery_verified_policy_keeps_public_promotion_gates_closed(self):
        policy = self.load_policy()
        gates = policy["gates"]
        self.assertTrue(gates["key_material_generated"])
        self.assertFalse(gates["public_anchor_pinned"])
        self.assertFalse(gates["minimal_bootstrap_resolved"])
        self.assertFalse(gates["physical_authorization_eligible"])
        self.assertNotIn("physical_write_allowed", gates)
        self.assertFalse(TRUST_PATH.exists(), "generated local key must not imply a pinned public anchor")


if __name__ == "__main__":
    unittest.main()
