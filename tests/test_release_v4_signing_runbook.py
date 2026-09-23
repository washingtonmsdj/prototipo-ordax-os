from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SIGN_SCRIPT = ROOT / "tools/release-signing/windows/4-Sign-Initial-OrdaXRelease.ps1"
SIGNING_DOC = ROOT / "docs/RELEASE-SIGNING.md"
BUNDLE_DOC = ROOT / "docs/RELEASE-BUNDLE.md"
PIPELINE_DOC = ROOT / "docs/RELEASE-PIPELINE.md"


class ReleaseV4SigningRunbookTests(unittest.TestCase):
    def test_windows_signing_runbook_is_manifest_v4_aware(self):
        script = SIGN_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("prototype-ordax.release-manifest/4", script)
        self.assertIn("RELEASE_MANIFEST_SCHEMA=", script)
        self.assertIn("RELEASE_BOUND_ARTIFACTS=", script)
        self.assertIn("system.erofs, native-surface-runtime.erofs and local-ai-runtime.erofs", script)
        self.assertIn("Signing alone does not publish, activate, authorize physical media", script)
        self.assertNotIn("may be published with system.tar", script)

    def test_signing_doc_describes_v4_ai_binding_and_canonical_boundary(self):
        text = SIGNING_DOC.read_text(encoding="utf-8")
        self.assertIn("For v4", text)
        self.assertIn("local-ai-runtime.erofs", text)
        self.assertIn("ordax.local-ai/1", text)
        self.assertIn("operator-controlled signing/materialization run using the canonical private key", text)
        self.assertIn("does not authorize publication, activation or physical-media writes", text)

    def test_bundle_and_pipeline_identify_v4_as_mvp_path(self):
        bundle = BUNDLE_DOC.read_text(encoding="utf-8")
        pipeline = PIPELINE_DOC.read_text(encoding="utf-8")
        for text in (bundle, pipeline):
            self.assertIn("system.erofs", text)
            self.assertIn("native-surface-runtime.erofs", text)
            self.assertIn("local-ai-runtime.erofs", text)
            self.assertIn("release-manifest/4", text)
        self.assertIn("materialize-portable-v4", pipeline)
        self.assertIn("verify-portable-v4-exact", pipeline)
        self.assertIn("separate physical-write authorization gate", pipeline)


if __name__ == "__main__":
    unittest.main()
