from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "system/surface/ui/system-overview-controls.mjs"
CATALOG = ROOT / "system/services/i18n/catalog/system.mjs"


class SystemUpdateDetailsLocalizationTests(unittest.TestCase):
    def test_update_details_use_shared_localization_owner(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        block = controls.split("const renderUpdateDetails = (view) => {", 1)[1].split(
            "\n  const renderRecovery = (view) => {", 1
        )[0]
        for message_id in (
            "system.updates.kicker",
            "system.updates.title",
            "system.updates.unavailable",
            "system.updates.fact.delivery",
            "system.updates.fact.commit",
            "system.updates.fact.status",
            "system.updates.fact.phase",
            "system.updates.fact.applyMode",
            "system.updates.fact.boot",
            "system.updates.duration",
            "system.updates.attention.generic",
        ):
            self.assertIn(f't("{message_id}"', block)
        for hardcoded in (
            '"Atualização"',
            '"Entrega e recuperação"',
            '"Commit técnico"',
            '"Última verificação"',
            '"Commit bloqueado"',
            '"Progresso da Base"',
        ):
            self.assertNotIn(hardcoded, block)

    def test_update_semantics_are_localized_not_pretranslated(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        block = controls.split("const renderUpdateDetails = (view) => {", 1)[1].split(
            "\n  const renderRecovery = (view) => {", 1
        )[0]
        self.assertIn("overviewUpdateStatusMessageId(updateSnapshot.status)", block)
        self.assertIn("overviewUpdateModeMessageId(updateSnapshot.applyMode)", block)
        self.assertIn("UPDATE_PHASE_MESSAGE_IDS[updateSnapshot.phase]", block)
        self.assertIn("BASE_PHASE_MESSAGE_IDS[updateSnapshot.baseUpdatePhase]", block)
        self.assertIn("BOOT_MESSAGE_IDS[updateSnapshot.baseUpdatePhase]", block)
        self.assertNotIn("updateStatusLabel(updateSnapshot.status)", block)
        self.assertNotIn("readableUpdatePhase(updateSnapshot.phase)", block)
        self.assertNotIn("readableUpdateMode(updateSnapshot.applyMode)", block)
        self.assertNotIn("readableBaseUpdatePhase(updateSnapshot.baseUpdatePhase)", block)
        self.assertNotIn("updateBootLabel(updateSnapshot)", block)
        self.assertNotIn("updateAttentionMessage(updateSnapshot)", block)

    def test_catalog_has_pt_br_and_en_us_update_details(self):
        catalog = CATALOG.read_text(encoding="utf-8")
        self.assertIn('"system.updates.title": "Entrega e recuperação"', catalog)
        self.assertIn('"system.updates.title": "Delivery and recovery"', catalog)
        self.assertIn('"system.updates.phase.healthWait": "Aguardando confirmação de saúde"', catalog)
        self.assertIn('"system.updates.phase.healthWait": "Waiting for health confirmation"', catalog)
        self.assertIn('"system.updates.boot.pendingActivation": "Base pendente de ativação"', catalog)
        self.assertIn('"system.updates.boot.pendingActivation": "Base pending activation"', catalog)
        self.assertEqual(catalog.count('"system.updates.attention.generic"'), 2)


if __name__ == "__main__":
    unittest.main()
