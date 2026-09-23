from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/canonical-portable-v4-public-proof.yml"
SIGNING_DOC = ROOT / "docs/RELEASE-SIGNING.md"


class CanonicalPortableV4PublicProofTests(unittest.TestCase):
    def test_manual_proof_accepts_only_public_release_identity(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("expected_commit:", text)
        self.assertIn("envelope_url:", text)
        self.assertIn("Checkout exact signed source commit", text)
        self.assertIn("bootstrap/trust/release-ed25519.json", text)
        for forbidden in (
            "PrivateKeyPath",
            "private-key",
            "generate-key",
            "ordax-release-signing",
            "release-signing.exe",
            "secrets.",
        ):
            self.assertNotIn(forbidden, text)

    def test_public_release_is_verified_materialized_and_reverified_as_v4(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("ordax-release-agent\" inspect", text)
        self.assertIn("materialize-portable-v4", text)
        self.assertIn("verify-portable-v4-exact", text)
        self.assertIn('prototype-ordax.release-manifest/4', text)
        self.assertIn('local-ai-runtime', text)
        self.assertIn('activation_allowed', text)

    def test_same_disposable_qemu_and_ovmf_harnesses_are_reused(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("bootstrap/portable-v2/qemu_boot.py", text)
        self.assertIn("bootstrap/portable-v2/uefi_boot.py", text)
        self.assertIn('"release_manifest_schema"] == 4', text)
        self.assertIn('"local_ai_runtime_handoff_marker"] is True', text)
        self.assertIn('"local_ai_backend_started"] is True', text)
        self.assertIn("physical_target_device_touched", text)
        self.assertIn("physical_write_authorized", text)
        for forbidden in ("/dev/sda", "/dev/sdb", "PhysicalDrive", "prepare-portable", "apply-portable"):
            self.assertNotIn(forbidden, text)

    def test_receipt_explicitly_denies_secret_and_physical_authority(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('"private_key_received": False', text)
        self.assertIn('"release_signed_in_ci": False', text)
        self.assertIn('"release_activated": False', text)
        self.assertIn('"physical_write_authorized": False', text)
        self.assertIn("PRIVATE_KEY_RECEIVED=NO", text)
        self.assertIn("PHYSICAL_WRITE_AUTHORIZED=NO", text)

    def test_signing_doc_points_operator_to_public_proof_after_external_signing(self):
        text = SIGNING_DOC.read_text(encoding="utf-8")
        self.assertIn("Canonical v4 public proof", text)
        self.assertIn("canonical-portable-v4-public-proof.yml", text)
        self.assertIn("private key", text.lower())
        self.assertIn("physical", text.lower())


if __name__ == "__main__":
    unittest.main()
