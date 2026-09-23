from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOME_PENDING = ROOT / "system/surface/ui/home-pending.mjs"
HOME_CONTINUATION = ROOT / "system/surface/ui/home-continuation.mjs"
POWER = ROOT / "system/surface/ui/power-controls.mjs"
UPDATE = ROOT / "system/surface/ui/update-controls.mjs"
BOOT = ROOT / "system/surface/ui/boot-screen.mjs"
SURFACE_CATALOG = ROOT / "system/services/i18n/surface.mjs"
POWER_CATALOG = ROOT / "system/services/i18n/catalog/power.mjs"
SYSTEM_CATALOG = ROOT / "system/services/i18n/catalog/system.mjs"
NATIVE = ROOT / "system/composition/native/main.mjs"


class ShellDeepLocalizationTests(unittest.TestCase):
    def test_home_pending_and_continuation_are_semantic(self):
        pending = HOME_PENDING.read_text(encoding="utf-8")
        continuation = HOME_CONTINUATION.read_text(encoding="utf-8")
        for marker in (
            '"home.pending.notifications.title.one"',
            '"home.pending.sync.transport.unavailable"',
            't("home.pending.heading")',
        ):
            self.assertIn(marker, pending)
        for marker in (
            '"home.continuation.project.detail"',
            '"home.continuation.recent.action"',
            't("home.continuation.heading")',
            "localization.getLocale()",
        ):
            self.assertIn(marker, continuation)
        for forbidden in (
            '"Pendências"',
            '"Não perturbe ativo"',
            '"Abrir Conta em Sincronização"',
            '"Continuar trabalho"',
            '"Arquivo recente ·',
            '"Projeto ·',
        ):
            self.assertNotIn(forbidden, pending + continuation)

    def test_power_feedback_keeps_semantic_identity_across_locale_changes(self):
        source = POWER.read_text(encoding="utf-8")
        for marker in (
            "assertSurfaceRenderLifecycle",
            "let messageId = null;",
            '"power.controls.restart.confirmation"',
            '"power.controls.request.restart"',
            '"power.controls.accepted"',
            "unsubscribeLocalization",
        ):
            self.assertIn(marker, source)
        for forbidden in (
            '"Reiniciar"',
            '"Desligar"',
            '"Solicitação aceita pelo host."',
            '"A ação de energia não pôde ser concluída."',
        ):
            self.assertNotIn(forbidden, source)

    def test_update_accelerator_uses_system_catalog(self):
        source = UPDATE.read_text(encoding="utf-8")
        self.assertIn("assertSurfaceRenderLifecycle", source)
        self.assertIn('t("system.tray.updates.openAria")', source)
        self.assertIn('"system.overview.update.summary.activationReady"', source)
        self.assertIn("unsubscribeLocalization", source)
        for forbidden in (
            '"Atualizações"',
            '"Abrir Sistema, Atualizações"',
            '"Há uma atualização que requer atenção.',
        ):
            self.assertNotIn(forbidden, source)

    def test_boot_screen_reuses_surface_catalog_and_persisted_locale(self):
        source = BOOT.read_text(encoding="utf-8")
        native = NATIVE.read_text(encoding="utf-8")
        self.assertIn("translateSurfaceMessage", source)
        self.assertIn("setLocale(nextLocale)", source)
        self.assertIn('fail(messageId = "boot.failed")', source)
        self.assertIn("regionalRecovery.snapshot[REGIONAL_LOCALE_PREFERENCE_ID]", native)
        self.assertIn('bootScreen.setStage("boot.loadingSurface")', native)
        self.assertIn('bootScreen.setStage("boot.loadingApps")', native)
        self.assertNotIn("Carregando superfície", native)
        self.assertNotIn("Não foi possível iniciar a interface", native)

    def test_catalogs_pair_pt_br_and_en_us_shell_copy(self):
        surface = SURFACE_CATALOG.read_text(encoding="utf-8")
        power = POWER_CATALOG.read_text(encoding="utf-8")
        system = SYSTEM_CATALOG.read_text(encoding="utf-8")
        pairs = (
            (surface, '"home.pending.heading": "Pendências"', '"home.pending.heading": "Pending"'),
            (surface, '"home.continuation.heading": "Continuar trabalho"', '"home.continuation.heading": "Continue working"'),
            (surface, '"boot.failed": "Não foi possível iniciar a interface"', '"boot.failed": "The interface could not be started"'),
            (power, '"power.controls.restart.label": "Reiniciar"', '"power.controls.restart.label": "Restart"'),
            (system, '"system.tray.updates": "Atualizações"', '"system.tray.updates": "Updates"'),
        )
        for catalog, source, english in pairs:
            self.assertIn(source, catalog)
            self.assertIn(english, catalog)


if __name__ == "__main__":
    unittest.main()
