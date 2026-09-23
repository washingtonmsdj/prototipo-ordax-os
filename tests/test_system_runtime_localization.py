from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "system" / "surface" / "ui" / "system-overview-controls.mjs"
CATALOG = ROOT / "system" / "services" / "i18n" / "catalog" / "system-runtime.mjs"
SURFACE_I18N = ROOT / "system" / "services" / "i18n" / "surface.mjs"


class SystemRuntimeLocalizationTests(unittest.TestCase):
    def test_about_intelligence_and_capabilities_use_shared_localization(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        for message_id in (
            "system.about.version.kicker",
            "system.about.delivery.kicker",
            "system.about.components.title",
            "system.about.components.health",
            "system.capabilities.title",
            "system.capabilities.networkManagement",
            "system.intelligence.title",
            "system.intelligence.status",
            "system.intelligence.progress",
            "system.intelligence.success",
            "system.intelligence.failed",
        ):
            self.assertIn(message_id, controls)

        about = controls.split("const renderComponentVersions = (view) => {", 1)[1].split(
            "const renderHistory = (view) => {", 1
        )[0]
        capabilities = controls.split("const renderCapabilities = (view) => {", 1)[1].split(
            "const renderIntelligence = (view) => {", 1
        )[0]
        intelligence = controls.split("const renderIntelligence = (view) => {", 1)[1].split(
            "const renderDiagnosticReviewMount = (view) => {", 1
        )[0]
        for source_copy in (
            '"Versão do produto"',
            '"Identidade da entrega"',
            '"Versões e isolamento"',
            '"Capacidades desta execução"',
            '"Explicação local do estado"',
            '"Não exposta neste modo"',
            '"Explicação da Ordax Intelligence"',
        ):
            self.assertNotIn(source_copy, about + capabilities + intelligence)

    def test_intelligence_operation_stores_semantic_message_identity(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        self.assertIn('intelligenceMessage = "system.intelligence.progress"', controls)
        self.assertIn('intelligenceMessage = "system.intelligence.success"', controls)
        self.assertIn('intelligenceMessage = "system.intelligence.failed"', controls)
        self.assertIn("t(intelligenceMessage)", controls)
        self.assertNotIn('intelligenceMessage = "Analisando', controls)
        self.assertNotIn('intelligenceMessage = "Explicação local', controls)

    def test_runtime_catalog_covers_pt_br_and_en_us(self):
        catalog = CATALOG.read_text(encoding="utf-8")
        for expected in (
            '"system.about.version.kicker": "Versão do produto"',
            '"system.about.version.kicker": "Product version"',
            '"system.capabilities.title": "Capacidades desta execução"',
            '"system.capabilities.title": "Capabilities for this run"',
            '"system.intelligence.state.ready": "Pronta"',
            '"system.intelligence.state.ready": "Ready"',
            '"system.intelligence.failed": "Não foi possível obter uma explicação local nesta execução."',
            '"system.intelligence.failed": "A local explanation could not be obtained in this run."',
        ):
            self.assertIn(expected, catalog)
        self.assertEqual(catalog.count('"system.intelligence.status"'), 2)

    def test_surface_aggregates_runtime_catalog_under_existing_owner(self):
        surface = SURFACE_I18N.read_text(encoding="utf-8")
        self.assertIn("SYSTEM_RUNTIME_SOURCE_MESSAGES", surface)
        self.assertIn("SYSTEM_RUNTIME_ENGLISH_MESSAGES", surface)
        self.assertIn("...SYSTEM_RUNTIME_SOURCE_MESSAGES", surface)
        self.assertIn("...SYSTEM_RUNTIME_ENGLISH_MESSAGES", surface)
        self.assertNotIn("createSystemRuntimeLocalization", surface)


if __name__ == "__main__":
    unittest.main()
