from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "system/apps/internet/ui/browser-controls.mjs"
CATALOG = ROOT / "system/services/i18n/catalog/internet.mjs"


class InternetDeepLocalizationTests(unittest.TestCase):
    def test_project_home_favorites_and_history_are_localized(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        for marker in (
            't("internet.project.localContext"',
            't("internet.project.catalogUnavailable")',
            '"internet.home.status.tabs"',
            '"internet.project.saveReference"',
            't("internet.favorite.headingCount"',
            't("internet.history.headingCount"',
            't("internet.history.clear")',
            't("internet.favorite.removeNamed"',
        ):
            self.assertIn(marker, controls)
        for hardcoded in (
            '"Nenhum projeto selecionado"',
            '"Catálogo de projetos indisponível neste host."',
            '"Nenhum favorito salvo."',
            '"Nenhuma visita registrada."',
            '"Histórico salvo neste dispositivo."',
            '"Favoritos salvos neste dispositivo."',
        ):
            self.assertNotIn(hardcoded, controls)

    def test_feedback_state_is_semantic_and_live_rerenderable(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        for marker in (
            "let messageId = null;",
            "let messageParams = Object.freeze({});",
            "let externalMessage =",
            "const setMessage =",
            "const setExternalMessage =",
            "const renderedMessage =",
            '"internet.reference.savedProject"',
            'setMessage("internet.reference.removed")',
            '"internet.favorite.savedSession"',
            '"internet.favorite.savedDeviceMessage"',
        ):
            self.assertIn(marker, controls)
        self.assertNotIn('let message = ""', controls)
        self.assertNotIn('message = t("internet.', controls)
        self.assertNotIn('"Não foi possível salvar a referência."', controls)
        self.assertNotIn('"Não foi possível atualizar os favoritos."', controls)

    def test_display_host_has_no_translated_default(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        self.assertIn('function displayHost(url, emptyLabel = "")', controls)
        self.assertNotIn('function displayHost(url, emptyLabel = "Nova aba")', controls)
        self.assertIn('displayHost(entry.url, t("internet.tab.new"))', controls)

    def test_catalog_has_pt_br_and_en_us_deep_internet_copy(self):
        catalog = CATALOG.read_text(encoding="utf-8")
        pairs = (
            ('"internet.project.folder": "Pasta do projeto"', '"internet.project.folder": "Project folder"'),
            ('"internet.home.status.historyNone": "Nenhuma visita registrada"', '"internet.home.status.historyNone": "No recorded visits"'),
            ('"internet.favorite.empty": "Nenhum favorito salvo."', '"internet.favorite.empty": "No saved favorites."'),
            ('"internet.history.clear": "Limpar"', '"internet.history.clear": "Clear"'),
            ('"internet.reference.saveFailed": "Não foi possível salvar a referência."', '"internet.reference.saveFailed": "The reference could not be saved."'),
        )
        for source, english in pairs:
            self.assertIn(source, catalog)
            self.assertIn(english, catalog)


if __name__ == "__main__":
    unittest.main()
