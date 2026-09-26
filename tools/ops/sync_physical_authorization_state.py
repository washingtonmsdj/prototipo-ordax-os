#!/usr/bin/env python3
"""One-shot regression transition after explicit owner authorization."""

from pathlib import Path
import re
import textwrap

AUTH_CONTEXT = "b5803154eed8a85962b5c2dddbfff29f2ff408c92b63247ca62d1c5ca71eda10"


def regex_replace(path: str, pattern: str, replacement: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{path}: expected one regex replacement, got {count}")
    target.write_text(updated, encoding="utf-8")


stable_method = textwrap.indent(
    textwrap.dedent(
        '''\
def test_current_repository_is_source_ready_and_owner_authorized_for_separate_physical_flow(self):
    status = readiness.evaluate(ROOT)

    self.assertTrue(status["source_ready"], status["blockers"])
    self.assertTrue(status["pre_usb_product_source_complete"])
    self.assertEqual(
        status["stage"],
        "authorized-candidate-ready-for-separate-physical-flow",
    )
    self.assertTrue(status["canonical_v4_release_proof_valid"])
    self.assertTrue(status["canonical_v4_release_binding_resolved"])
    self.assertTrue(status["pre_authorization_ready"])
    self.assertFalse(status["owner_authorization_required"])
    self.assertTrue(status["owner_authorization_recorded"])
    self.assertTrue(status["authorized_candidate_materialization_allowed"])
    self.assertEqual(status["proof_boundaries"]["pre_usb_product_source"], "pass")
    self.assertEqual(status["proof_boundaries"]["canonical_v4_release_candidate"], "pass")
    self.assertEqual(status["proof_boundaries"]["physical_write_authorization"], "pass")
    self.assertEqual(
        status["proof_boundaries"]["canonical_stable_graphical_session"],
        "requires-physical-proof",
    )
    self.assertEqual(
        status["proof_boundaries"]["canonical_system_runtime"],
        "requires-physical-proof",
    )
    self.assertEqual(
        status["proof_boundaries"]["stable_publication"],
        "requires-separate-post-physical-promotion",
    )
    self.assertEqual(status["handoff_document"], "docs/MVP-PRE-PHYSICAL-HANDOFF.md")
    self.assertTrue((ROOT / status["handoff_document"]).is_file())
    self.assertEqual(
        status["remaining_gates"][0],
        "physical-target-selection-and-live-revalidation",
    )
    self.assertFalse(status["physical_target_selected"])
    self.assertFalse(status["target_specific_destructive_confirmation_recorded"])
    self.assertFalse(status["writer_invoked"])
    self.assertFalse(status["physical_write_performed"])
    self.assertFalse(status["physical_proof_completed"])

'''
    ),
    "    ",
)
regex_replace(
    "tests/test_stable_mvp_usb_readiness.py",
    r"    def test_current_repository_is_source_ready_but_owner_consent_pending\(self\):.*?(?=    def test_ready_stage_still_does_not_claim_physical_proof)",
    stable_method,
)

promotion_method = textwrap.indent(
    textwrap.dedent(
        f'''\
def test_repository_v4_media_scope_records_owner_authorization_without_selecting_a_device(self):
    auth = json.loads(
        (ROOT / "docs/contracts/physical-write-authorization.json").read_text(
            encoding="utf-8"
        )
    )
    self.assertEqual(auth["status"], "authorized")
    self.assertTrue(auth["physical_write_allowed"])
    self.assertTrue(auth["explicit_owner_authorization"])
    self.assertEqual(auth["authorization_context_sha256"], "{AUTH_CONTEXT}")
    self.assertEqual(auth["scope"], "first-real-stable-mvp-usb-proof")
    self.assertEqual(auth["release_sequence"], 1)
    self.assertTrue(
        auth["requirements"]["writer_requires_exact_17_artifact_readback"]
    )
    self.assertNotIn(
        "writer_requires_exact_15_artifact_readback",
        auth["requirements"],
    )
    status = promotion.evaluate(ROOT)
    self.assertTrue(status["ready"], status["blockers"])
    self.assertTrue(status["pre_authorization_ready"])
    self.assertTrue(status["canonical_v4_release_proof_valid"])
    self.assertTrue(status["canonical_v4_release_binding_resolved"])
    self.assertTrue(status["physical_authorization_bindings_resolved"])
    self.assertTrue(status["authorization_context_matches_current_source"])
    self.assertEqual(status["pre_authorization_blockers"], [])
    self.assertEqual(status["authorization_blockers"], [])
    self.assertFalse(status["owner_authorization_required"])
    self.assertTrue(status["authorized_candidate_materialization_allowed"])
    self.assertEqual(status["next_stage"], "authorized-candidate-materialization")
    for forbidden in ("physical_path", "device_path", "disk_number", "volume_id"):
        self.assertNotIn(forbidden, auth)

'''
    ),
    "    ",
)
regex_replace(
    "tests/test_physical_promotion_boundary.py",
    r"    def test_repository_v4_media_scope_requires_fresh_owner_authorization_after_proof\(self\):.*?(?=    def _set_pending_owner_authorization)",
    promotion_method,
)
