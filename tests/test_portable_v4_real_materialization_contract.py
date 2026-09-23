from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/local-ai-runtime-candidate.yml"


class PortableV4RealMaterializationContractTests(unittest.TestCase):
    def test_real_runtime_bytes_are_signed_materialized_and_reverified(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('cp "$work/build-a/local-ai-runtime.erofs" "$proof/local-ai-runtime.erofs"', text)
        self.assertIn("--manifest-schema 4", text)
        self.assertIn("--local-ai-source-lock system/services/local-ai/source-lock.json", text)
        self.assertIn("materialize-portable-v4", text)
        self.assertIn("verify-portable-v4-exact", text)
        self.assertIn('stored_ai="$proof/materialized/ai-runtimes/sha256/$ai_sha/local-ai-runtime.erofs"', text)
        self.assertIn('cmp "$proof/local-ai-runtime.erofs" "$stored_ai"', text)

    def test_proof_is_non_promotional_and_non_destructive(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        step = text.split("- name: Prove signed v4 materialization with real local AI bytes", 1)[1]
        step = step.split("- name: Remove unpromoted runtime bytes", 1)[0]
        self.assertIn('test ! -e "$proof/materialized/current"', step)
        self.assertIn('test ! -e "$proof/materialized/candidate"', step)
        self.assertIn('PORTABLE_V4_ACTIVATION_ALLOWED=NO', step)
        self.assertIn('PHYSICAL_WRITE_AUTHORIZED=NO', step)
        self.assertIn('PORTABLE_V4_SIGNING_KEY=EPHEMERAL_CI_ONLY', step)
        self.assertNotIn("activate-exact", step)
        self.assertNotIn("/dev/sd", step)
        self.assertNotIn("physical target", step.lower())

    def test_https_transport_is_local_and_ephemeral(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('https://127.0.0.1:18443/release-envelope-v4.json', text)
        self.assertIn('SSL_CERT_FILE="$proof/https-cert.pem"', text)
        self.assertIn('subjectAltName=IP:127.0.0.1', text)
        self.assertIn('rm -f "$proof/private-v4.pem"', text)


if __name__ == "__main__":
    unittest.main()
