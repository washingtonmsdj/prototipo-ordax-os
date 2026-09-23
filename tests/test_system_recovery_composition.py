from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
NATIVE_MAIN = ROOT / "system/composition/native/main.mjs"
SYSTEM_UI = ROOT / "system/surface/ui/system-overview-controls.mjs"
RECOVERY_ADAPTER = ROOT / "system/adapters/native/recovery-status.mjs"


class SystemRecoveryCompositionTests(unittest.TestCase):
    def test_native_composes_existing_diagnostic_controller_instead_of_null(self):
        text = NATIVE_MAIN.read_text(encoding="utf-8")
        self.assertIn('from "./diagnostics.mjs"', text)
        self.assertIn("createNativeDiagnosticReviewComposition({", text)
        self.assertIn("diagnosticReviewController,", text)
        self.assertNotIn(
            "appActivation,\n    null,\n    componentManager,\n    intelligence,",
            text,
        )

    def test_recovery_observer_is_optional_read_only_and_presented_by_system(self):
        native = NATIVE_MAIN.read_text(encoding="utf-8")
        ui = SYSTEM_UI.read_text(encoding="utf-8")
        adapter = RECOVERY_ADAPTER.read_text(encoding="utf-8")
        self.assertIn("createNativeRecoveryStatus", native)
        self.assertIn("recoveryStatus,", native)
        self.assertIn("assertRecoveryStatusPort", ui)
        self.assertIn("renderRecovery(view)", ui)
        self.assertIn("systemRecoveryRefresh", ui)
        self.assertIn('"/__ordax/native/recovery-status"', adapter)
        self.assertNotIn("rollback(", adapter)
        self.assertNotIn("reboot(", adapter)
        self.assertNotIn("recover(", adapter)


if __name__ == "__main__":
    unittest.main()
