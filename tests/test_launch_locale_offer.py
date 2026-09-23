from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "system/contracts/first-run-state-store.mjs"
REGIONAL = ROOT / "system/services/preferences/regional.mjs"
FIRST_RUN_I18N = ROOT / "system/services/i18n/first-run.mjs"


class LaunchLocaleOfferTests(unittest.TestCase):
    def test_legacy_supported_locales_remain_accepted(self):
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn(
            'FIRST_RUN_SUPPORTED_LOCALES = Object.freeze(["pt-BR", "en-US", "es-ES", "de-DE", "fr-FR"])',
            contract,
        )
        self.assertIn(
            'FIRST_RUN_PUBLIC_MVP_LOCALES = Object.freeze(["pt-BR", "en-US"])',
            contract,
        )
        self.assertIn("const SUPPORTED_LOCALES = new Set(FIRST_RUN_SUPPORTED_LOCALES)", contract)
        self.assertIn("SUPPORTED_LOCALES.has(value.locale)", contract)

    def test_oobe_and_regional_selector_offer_only_launch_complete_locales(self):
        regional = REGIONAL.read_text(encoding="utf-8")
        self.assertIn("FIRST_RUN_PUBLIC_MVP_LOCALES.map", regional)
        self.assertIn("const LOCALES = new Set(FIRST_RUN_SUPPORTED_LOCALES)", regional)
        self.assertIn("Português (Brasil) e English", regional)
        self.assertIn("permanecem aceitos para compatibilidade", regional)

    def test_existing_oobe_translation_tables_are_preserved(self):
        i18n = FIRST_RUN_I18N.read_text(encoding="utf-8")
        for locale in ("en-US", "es-ES", "de-DE", "fr-FR"):
            self.assertIn(f'"{locale}": Object.freeze({{', i18n)


if __name__ == "__main__":
    unittest.main()
