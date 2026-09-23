from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "system/surface/ui/system-overview-controls.mjs"
CATALOG = ROOT / "system/services/i18n/catalog/system.mjs"


class SystemResourceLocalizationTests(unittest.TestCase):
    def test_memory_and_storage_views_use_shared_localization_owner(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        for message_id in (
            "system.resources.memory.kicker",
            "system.resources.memory.title",
            "system.resources.action.refresh",
            "system.resources.memory.reading",
            "system.resources.memory.unavailable",
            "system.resources.stale",
            "system.resources.memory.used",
            "system.resources.memory.availableOf",
            "system.resources.storage.kicker",
            "system.resources.storage.title",
            "system.resources.storage.reading",
            "system.resources.storage.unavailable",
            "system.resources.storage.used",
            "system.resources.storage.freeOf",
            "system.resources.storage.scope",
            "system.resources.readFailedPrevious",
            "system.resources.readFailedNoData",
        ):
            self.assertIn(f't("{message_id}"', controls)
        for rendered_source_copy in (
            '"Uso do dispositivo"',
            '"Memória em uso"',
            '"Espaço usado"',
            '"Lendo armazenamento do usuário…"'
        ):
            self.assertNotIn(rendered_source_copy, controls)

    def test_resource_catalog_has_pt_br_and_en_us(self):
        catalog = CATALOG.read_text(encoding="utf-8")
        self.assertIn('"system.resources.memory.used": "Memória em uso"', catalog)
        self.assertIn('"system.resources.memory.used": "Memory in use"', catalog)
        self.assertIn('"system.resources.storage.used": "Espaço usado"', catalog)
        self.assertIn('"system.resources.storage.used": "Space used"', catalog)
        self.assertEqual(catalog.count('"system.resources.storage.scope"'), 2)
        self.assertIn('"system.resources.readFailedPrevious": "The current reading failed', catalog)
        self.assertIn('"system.resources.readFailedNoData": "A valid resource reading', catalog)


if __name__ == "__main__":
    unittest.main()
