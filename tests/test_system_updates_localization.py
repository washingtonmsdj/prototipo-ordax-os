from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "system" / "surface" / "ui" / "system-overview-controls.mjs"
CATALOG = ROOT / "system" / "services" / "i18n" / "catalog" / "system-updates.mjs"
SURFACE_I18N = ROOT / "system" / "services" / "i18n" / "surface.mjs"


class SystemUpdatesLocalizationTests(unittest.TestCase):
    def test_updates_history_and_component_scope_use_shared_localization(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        for message_id in (
            "system.updates.kicker",
            "system.updates.fact.delivery",
            "system.updates.phase.checking",
            "system.updates.fact.baseProgress",
            "system.updates.scope.kicker",
            "system.updates.scope.policy",
            "system.updates.component.channel.developmentGit",
            "system.updates.history.kicker",
            "system.updates.history.applicationDetail",
            "system.updates.history.readFailed",
        ):
            self.assertIn(message_id, controls)

        update_block = controls.split("const renderUpdateDetails = (view) => {", 1)[1].split(
            "const renderRecovery = (view) => {", 1
        )[0]
        scope_block = controls.split("const renderComponentUpdateScopes = (view) => {", 1)[1].split(
            "const renderComponentVersions = (view) => {", 1
        )[0]
        history_block = controls.split("const renderHistory = (view) => {", 1)[1].split(
            "const renderCapabilities = (view) => {", 1
        )[0]
        for source_copy in (
            '"Entrega e recuperação"',
            '"Progresso da Base"',
            '"OrdaX e sistema"',
            '"não representa uma Loja"',
            '"Histórico de atualizações"',
            '"Aplicações neste notebook"',
        ):
            self.assertNotIn(source_copy, update_block + scope_block + history_block)

    def test_catalog_covers_pt_br_and_en_us_semantic_states(self):
        catalog = CATALOG.read_text(encoding="utf-8")
        for expected in (
            '"system.updates.phase.checking": "Verificando atualizações"',
            '"system.updates.phase.checking": "Checking for updates"',
            '"system.updates.history.result.applied": "Aplicada"',
            '"system.updates.history.result.applied": "Applied"',
            '"system.updates.component.health.healthy": "Saudável"',
            '"system.updates.component.health.healthy": "Healthy"',
            '"system.updates.scope.channelPolicy"',
        ):
            self.assertIn(expected, catalog)
        self.assertEqual(catalog.count('"system.updates.history.applicationDetail"'), 2)

    def test_surface_aggregates_updates_catalog_under_existing_owner(self):
        surface = SURFACE_I18N.read_text(encoding="utf-8")
        self.assertIn("SYSTEM_UPDATES_SOURCE_MESSAGES", surface)
        self.assertIn("SYSTEM_UPDATES_ENGLISH_MESSAGES", surface)
        self.assertIn("...SYSTEM_UPDATES_SOURCE_MESSAGES", surface)
        self.assertIn("...SYSTEM_UPDATES_ENGLISH_MESSAGES", surface)
        self.assertNotIn("createSystemUpdatesLocalization", surface)


if __name__ == "__main__":
    unittest.main()
