from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "system" / "surface" / "ui"
WEB_INDEX = ROOT / "system" / "composition" / "web" / "index.html"
NATIVE_INDEX = ROOT / "system" / "composition" / "native" / "index.html"
APPEARANCE = ROOT / "system" / "services" / "preferences" / "appearance.mjs"
DESKTOP_IDENTITY = ROOT / "docs" / "DESKTOP-IDENTITY.md"
INTER_LICENSE = SURFACE / "fonts" / "INTER-OFL.txt"


class SurfaceVisualIdentityTests(unittest.TestCase):
    def test_graphite_glacial_tokens_are_canonical(self):
        tokens = (SURFACE / "tokens.css").read_text(encoding="utf-8")
        for declaration in (
            "--ordax-bg: #080f19",
            "--ordax-app-bg: #090f1b",
            "--ordax-panel: #111e30",
            "--ordax-text: #e2ebf7",
            "--ordax-muted: #8e9db4",
            "--ordax-accent: #a9c9f7",
            "--ordax-button-bg: #d1e4ff",
            "--ordax-button-text: #172b47",
            "--ordax-border: #243249",
            "--ordax-font: Inter, system-ui, \"Segoe UI\", sans-serif",
            "--ordax-font-display: Inter, system-ui, \"Segoe UI\", sans-serif",
            "--ordax-motion-fast: 150ms",
            "--ordax-motion-base: 200ms",
            "--ordax-motion-slow: 250ms",
        ):
            self.assertIn(declaration, tokens)

    def test_graphite_is_visual_reference_without_changing_theme_default(self):
        appearance = APPEARANCE.read_text(encoding="utf-8")
        self.assertIn('defaultValue: "light"', appearance)
        self.assertIn('{ value: "light", label: "Claro" }', appearance)
        self.assertIn('{ value: "dark", label: "Escuro" }', appearance)

    def test_semantic_states_and_light_theme_remain_independent(self):
        tokens = (SURFACE / "tokens.css").read_text(encoding="utf-8")
        self.assertIn('[data-ordax-theme="light"]', tokens)
        self.assertIn("--ordax-success:", tokens)
        self.assertIn("--ordax-warning:", tokens)
        self.assertIn("--ordax-danger:", tokens)
        self.assertIn('[data-ordax-theme="dark"][data-ordax-contrast="high"]', tokens)
        self.assertIn("prefers-reduced-motion", tokens)

    def test_shared_identity_layers_are_loaded_by_web_and_native(self):
        identity = SURFACE / "identity.css"
        app_identity = SURFACE / "app-identity.css"
        self.assertTrue(identity.is_file())
        self.assertTrue(app_identity.is_file())

        css = identity.read_text(encoding="utf-8")
        self.assertIn("var(--ordax-accent)", css)
        self.assertIn("var(--ordax-panel)", css)
        self.assertIn(".ordax-window", css)
        self.assertIn(".ordax-rail", css)
        self.assertIn(".ordax-launcher-panel", css)
        self.assertIn("prefers-reduced-motion", css)

        app_css = app_identity.read_text(encoding="utf-8")
        self.assertIn(".ordax-projects-view", app_css)
        self.assertIn(".ordax-notes-workspace", app_css)
        self.assertIn(".ordax-internet-view", app_css)
        self.assertIn("var(--ordax-button-bg)", app_css)

        for index in (WEB_INDEX, NATIVE_INDEX):
            html = index.read_text(encoding="utf-8")
            self.assertIn('../../surface/ui/identity.css', html)
            self.assertIn('../../surface/ui/app-identity.css', html)
            self.assertIn('name="theme-color" content="#080f19"', html)

    def test_inter_license_is_shipped_with_surface_assets(self):
        license_text = INTER_LICENSE.read_text(encoding="utf-8")
        self.assertIn("The Inter Project Authors", license_text)
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", license_text)

    def test_landing_is_reference_not_product_capability(self):
        docs = DESKTOP_IDENTITY.read_text(encoding="utf-8")
        self.assertIn("aesthetic reference only", docs)
        self.assertIn("must not be imported into `system/`", docs)
        self.assertIn("single source of visual policy", docs)


if __name__ == "__main__":
    unittest.main()
