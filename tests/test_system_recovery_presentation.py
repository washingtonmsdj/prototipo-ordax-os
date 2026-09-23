from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "system/supervisor"
HOST = ROOT / "system/surface/runtime/native_host_server.py"
OVERVIEW = ROOT / "system/surface/ui/system-overview-controls.mjs"
REPORT = ROOT / "system/services/diagnostics/report.mjs"
REVIEW = ROOT / "system/surface/ui/system-diagnostics-review.mjs"


class SystemRecoveryPresentationTests(unittest.TestCase):
    def test_supervisor_projects_canonical_portable_pointers_read_only(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        self.assertIn("derive_recovery_projection()", text)
        self.assertIn('"$PORTABLE_STATE_HELPER" "$PORTABLE_STATE_ROOT" current', text)
        self.assertIn('"$PORTABLE_STATE_HELPER" "$PORTABLE_STATE_ROOT" known-good', text)
        self.assertIn('"$PORTABLE_STATE_HELPER" "$PORTABLE_STATE_ROOT" candidate', text)
        self.assertIn('"$PORTABLE_STATE_HELPER" "$PORTABLE_STATE_ROOT" rejected', text)
        for field in (
            '"recoveryState":"%s"',
            '"recoverySource":"%s"',
            '"currentReleaseSha":"%s"',
            '"knownGoodReleaseSha":"%s"',
            '"candidateReleaseSha":"%s"',
            '"recoveryRejectedSha":"%s"',
            '"rollbackEligible":%s',
        ):
            self.assertIn(field, text)
        self.assertIn('RECOVERY_ROLLBACK_ELIGIBLE=true', text)
        self.assertIn('[ "$RECOVERY_CURRENT_SHA" != "$RECOVERY_KNOWN_GOOD_SHA" ]', text)

    def test_unavailable_native_state_never_invents_known_good(self):
        host = HOST.read_text(encoding="utf-8")
        self.assertIn('"recoveryState": "unavailable"', host)
        self.assertIn('"recoverySource": "none"', host)
        self.assertIn('"knownGoodReleaseSha": ""', host)
        self.assertIn('"rollbackEligible": False', host)

    def test_system_presents_recovery_without_a_rollback_action(self):
        overview = OVERVIEW.read_text(encoding="utf-8")
        self.assertIn("const renderRecovery = (view) =>", overview)
        self.assertIn("system.recovery.knownGood", overview)
        self.assertIn("system.recovery.rollbackAvailable", overview)
        self.assertIn("system.recovery.readOnly", overview)
        self.assertIn("renderRecovery(view);", overview)
        self.assertNotIn("data-system-rollback", overview)
        self.assertNotIn("rollbackRelease(", overview)
        self.assertNotIn("performRollback(", overview)

    def test_diagnostic_report_and_review_include_same_recovery_observation(self):
        report = REPORT.read_text(encoding="utf-8")
        review = REVIEW.read_text(encoding="utf-8")
        self.assertIn("recoveryState: snapshot.recoveryState", report)
        self.assertIn("knownGoodReleaseSha: snapshot.knownGoodReleaseSha", report)
        self.assertIn("rollbackEligible: snapshot.rollbackEligible", report)
        self.assertIn("recovery: freeze({", review)
        self.assertIn('"Known-good"', review)
        self.assertIn('"Fallback observado"', review)


if __name__ == "__main__":
    unittest.main()
