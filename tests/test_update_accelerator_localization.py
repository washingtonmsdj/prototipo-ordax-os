from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "system" / "surface" / "ui" / "update-controls.mjs"
NATIVE = ROOT / "system" / "composition" / "native" / "main.mjs"
CATALOG = ROOT / "system" / "services" / "i18n" / "catalog" / "system-updates.mjs"


class UpdateAcceleratorLocalizationTests(unittest.TestCase):
    def test_accelerator_uses_existing_surface_localization_owner(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        native = NATIVE.read_text(encoding="utf-8")
        self.assertIn("assertSurfaceRenderLifecycle", controls)
        self.assertIn("const localization = lifecycle.localization", controls)
        self.assertIn('t("system.updates.accelerator.label")', controls)
        self.assertIn('t("system.updates.accelerator.aria")', controls)
        self.assertIn('t("system.updates.accelerator.titleBoot"', controls)
        self.assertIn("localization.subscribe(() => render())", controls)
        self.assertIn("unsubscribeLocalization?.()", controls)
        self.assertIn(
            "mountUpdateControls(root, updateWatcher, appActivation, surface)",
            native,
        )
        self.assertNotIn("createUpdateLocalization", controls)

    def test_accelerator_does_not_render_pt_br_copy_directly(self):
        controls = CONTROLS.read_text(encoding="utf-8")
        for source_copy in (
            '"Atualizações"',
            '"Abrir Sistema, Atualizações"',
            '"Há uma atualização que requer atenção. Abrir Sistema > Atualizações."',
        ):
            self.assertNotIn(source_copy, controls)
        self.assertNotIn("updateSummaryLabel", controls)

    def test_catalog_has_pt_br_and_en_us_accelerator_copy(self):
        catalog = CATALOG.read_text(encoding="utf-8")
        for expected in (
            '"system.updates.accelerator.label": "Atualizações"',
            '"system.updates.accelerator.label": "Updates"',
            '"system.updates.accelerator.aria": "Abrir Sistema, Atualizações"',
            '"system.updates.accelerator.aria": "Open System, Updates"',
            '"system.updates.accelerator.titleBoot": "{summary}. Abrir Sistema > Atualizações."',
            '"system.updates.accelerator.titleBoot": "{summary}. Open System > Updates."',
        ):
            self.assertIn(expected, catalog)


if __name__ == "__main__":
    unittest.main()
