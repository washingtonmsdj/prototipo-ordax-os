#!/usr/bin/env python3
"""Contract tests for canonical runtime-component trust policy."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "docs" / "contracts" / "runtime-component-trust-policy.json").read_text(
        encoding="utf-8"
    )
)


class RuntimeComponentTrustPolicyTests(unittest.TestCase):
    def test_component_trust_is_separate_and_operator_owned(self):
        self.assertEqual(
            CONTRACT["$schema"],
            "prototype-ordax.runtime-component-trust-policy/1",
        )
        self.assertEqual(CONTRACT["status"], "operator-ceremony-pending")
        self.assertEqual(CONTRACT["trust_domain"], "runtime-components")
        self.assertEqual(CONTRACT["key_id"], "ordax-runtime-components-v1")

        separation = CONTRACT["separation"]
        self.assertFalse(separation["whole_os_release_key_reuse_allowed"])
        self.assertFalse(separation["whole_os_release_trust_alias_allowed"])
        self.assertFalse(separation["ci_ephemeral_key_may_be_canonical"])
        self.assertTrue(
            separation["component_publication_authority_separate_from_os_release_publication"]
        )

    def test_private_key_never_enters_repository_or_device(self):
        private_key = CONTRACT["private_key"]
        self.assertFalse(private_key["repository_allowed"])
        self.assertFalse(private_key["device_allowed"])
        self.assertFalse(private_key["actions_artifact_allowed"])
        self.assertFalse(private_key["chat_allowed"])
        self.assertTrue(private_key["external_custody_required"])
        self.assertTrue(private_key["encrypted_recovery_copy_required"])
        self.assertTrue(private_key["recovery_proof_required_before_public_anchor_pin"])

    def test_anchor_target_is_public_only_and_not_pinned_yet(self):
        anchor = CONTRACT["public_anchor"]
        self.assertEqual(
            anchor["repository_path"],
            "system/trust/runtime-components-ed25519.json",
        )
        self.assertEqual(
            anchor["runtime_path"],
            "/srv/ordax-system/trust/runtime-components-ed25519.json",
        )
        self.assertFalse(anchor["pinned"])
        self.assertIsNone(anchor["sha256"])

    def test_pinning_does_not_authorize_publish_activation_or_physical_write(self):
        promotion = CONTRACT["promotion"]
        self.assertTrue(promotion["canonical_anchor_pin_requires_completed_ceremony"])
        self.assertFalse(promotion["pinning_enables_publication"])
        self.assertFalse(promotion["pinning_enables_activation"])
        self.assertFalse(promotion["pinning_authorizes_physical_write"])
        self.assertTrue(
            promotion["component_slot_activation_requires_separate_runtime_health_proof"]
        )
        self.assertEqual(
            promotion["public_promoter_source_path"],
            "tools/runtime-component-channel/promote_public_trust.py",
        )
        self.assertTrue(promotion["public_handoff_zip_required"])
        self.assertTrue(promotion["public_reverification_required"])
        self.assertTrue(promotion["check_before_apply_required"])

        gates = CONTRACT["current_gates"]
        self.assertFalse(gates["canonical_component_trust_anchor_pinned"])
        self.assertFalse(gates["component_publish_allowed"])
        self.assertFalse(gates["production_component_slot_activation_allowed"])


if __name__ == "__main__":
    unittest.main()
