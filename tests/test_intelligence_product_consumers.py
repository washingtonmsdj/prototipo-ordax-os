from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "system/composition/native/main.mjs"
NOTES_RUNTIME = ROOT / "system/apps/notes/runtime.mjs"
NOTES_UI = ROOT / "system/apps/notes/ui/workspace-controls.mjs"
SYSTEM_UI = ROOT / "system/surface/ui/system-overview-controls.mjs"
CLIENT_ACTIONS = ROOT / "system/services/intelligence/client-actions.mjs"
SYSTEM_RUNTIME_I18N = ROOT / "system/services/i18n/catalog/system-runtime.mjs"


class IntelligenceProductConsumerTests(unittest.TestCase):
    def test_native_composes_intelligence_once_and_injects_consumers(self):
        text = NATIVE.read_text(encoding="utf-8")
        self.assertEqual(text.count("createLocalAiRuntime({"), 1)
        self.assertEqual(text.count("createIntelligenceRuntime({ inferencePort: localAi })"), 1)
        self.assertIn("void localAi.probe();", text)
        self.assertIn("intelligenceSystemAvailable = true", text)
        self.assertIn("componentManager.setCurrentHealth(", text)
        self.assertIn('"local-ai-service"', text)
        self.assertIn('"ordax-intelligence"', text)
        self.assertIn("intelligence,", text)

    def test_notes_consumes_intelligence_not_local_ai(self):
        runtime = NOTES_RUNTIME.read_text(encoding="utf-8")
        ui = NOTES_UI.read_text(encoding="utf-8")
        self.assertIn("intelligence = null", runtime)
        self.assertIn("{ fileSpace, appActivation, intelligence }", runtime)
        self.assertIn("assertIntelligencePort", ui)
        self.assertIn("summarizeDocumentWithIntelligence", ui)
        self.assertIn('data.notesIntelligence', ui.replace("dataset", "data"))
        self.assertIn('"intelligence-summary"', ui)
        self.assertNotIn("local-ai", runtime)
        self.assertNotIn("local-ai", ui)
        self.assertNotIn("llama", runtime.lower())
        self.assertNotIn("llama", ui.lower())
        self.assertNotIn("qwen", runtime.lower())
        self.assertNotIn("qwen", ui.lower())

    def test_system_explanation_is_consultative_and_provider_neutral(self):
        ui = SYSTEM_UI.read_text(encoding="utf-8")
        actions = CLIENT_ACTIONS.read_text(encoding="utf-8")
        catalog = SYSTEM_RUNTIME_I18N.read_text(encoding="utf-8")
        self.assertIn("assertIntelligencePort", ui)
        self.assertIn("explainSystemStateWithIntelligence", ui)
        self.assertIn("systemIntelligenceExplain", ui)
        self.assertIn('t("system.intelligence.source")', ui)
        self.assertIn("autoridade: nenhuma", catalog)
        self.assertIn("authority: none", catalog)
        self.assertIn('"ordax-system-local-snapshot"', actions)
        self.assertIn('intent: "diagnose"', actions)
        self.assertNotIn("local-ai", ui)
        self.assertNotIn("llama", ui.lower())
        self.assertNotIn("qwen", ui.lower())


if __name__ == "__main__":
    unittest.main()
