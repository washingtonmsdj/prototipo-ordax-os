from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREPARE_SCRIPT = ROOT / "tools/release-signing/windows/3-Prepare-PortableV4-SigningHandoff.ps1"
SIGN_SCRIPT = ROOT / "tools/release-signing/windows/4-Sign-Initial-OrdaXRelease.ps1"
VERIFY_SCRIPT = ROOT / "tools/release-signing/windows/5-Verify-PortableV4-SignedHandoff.ps1"
SIGN_CMD = ROOT / "tools/release-signing/windows/4-Sign-Initial-OrdaXRelease.cmd"
VERIFY_CMD = ROOT / "tools/release-signing/windows/5-Verify-PortableV4-SignedHandoff.cmd"
SIGNING_WORKFLOW = ROOT / ".github/workflows/release-signing.yml"
SIGNING_DOC = ROOT / "docs/RELEASE-SIGNING.md"
BUNDLE_DOC = ROOT / "docs/RELEASE-BUNDLE.md"
PIPELINE_DOC = ROOT / "docs/RELEASE-PIPELINE.md"
HANDOFF_CONTRACT = ROOT / "docs/contracts/portable-v4-signing-handoff.json"


class ReleaseV4SigningRunbookTests(unittest.TestCase):
    def test_public_v4_handoff_preparer_never_accepts_private_material(self):
        script = PREPARE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--manifest-schema', '4'", script)
        self.assertIn("system.erofs,native-surface-runtime.erofs,local-ai-runtime.erofs", script)
        self.assertIn("Copy-VerifiedFile", script)
        self.assertIn("PRIVATE_KEY_INCLUDED=NO", script)
        self.assertIn("RELEASE_PUBLISHED=NO", script)
        self.assertIn("RELEASE_ACTIVATED=NO", script)
        self.assertIn("PHYSICAL_WRITE_AUTHORIZED=NO", script)
        self.assertIn("must use HTTPS with no embedded credentials", script)
        self.assertNotIn("PrivateKeyPath", script)
        self.assertNotIn("ordax-release-private.pem", script)

    def test_windows_signing_runbook_is_manifest_v4_aware(self):
        script = SIGN_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("prototype-ordax.release-manifest/4", script)
        self.assertIn("RELEASE_MANIFEST_SCHEMA=", script)
        self.assertIn("RELEASE_BOUND_ARTIFACTS=", script)
        self.assertIn("system.erofs, native-surface-runtime.erofs and local-ai-runtime.erofs", script)
        self.assertIn("Signing alone does not publish, activate, authorize physical media", script)
        self.assertNotIn("may be published with system.tar", script)

    def test_public_handoff_includes_official_release_agent_and_post_sign_verifier(self):
        script = PREPARE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("ReleaseAgentPath", script)
        self.assertIn("ordax-release-agent.exe", script)
        self.assertIn("5-Verify-PortableV4-SignedHandoff.ps1", script)
        self.assertIn("5-Verify-PortableV4-SignedHandoff.cmd", script)
        self.assertIn("Copy-VerifiedFile $ReleaseAgentPath", script)
        self.assertNotIn("PrivateKeyPath", script)

    def test_post_sign_verification_uses_agent_and_never_materializes_or_activates(self):
        script = VERIFY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("verify-envelope", script)
        self.assertIn("SIGNED_PAYLOAD_MATCHES_MANIFEST_BYTES=YES", script)
        self.assertIn("LOCAL_ARTIFACTS_MATCH_SIGNED_MANIFEST=YES", script)
        self.assertIn("PORTABLE_MATERIALIZATION_PERFORMED=NO", script)
        self.assertIn("PHYSICAL_TARGET_SELECTED=NO", script)
        self.assertIn("PHYSICAL_WRITE_PERFORMED=NO", script)
        self.assertNotIn("materialize-portable-v4", script)
        self.assertNotIn("activate-exact", script)
        self.assertNotIn("install ", script)
        self.assertNotIn("PrivateKeyPath", script)

    def test_windows_launchers_do_not_advertise_legacy_v1_publication(self):
        sign_cmd = SIGN_CMD.read_text(encoding="utf-8")
        verify_cmd = VERIFY_CMD.read_text(encoding="utf-8")
        self.assertNotIn("system.tar", sign_cmd)
        self.assertIn("tres artefatos v4", sign_cmd)
        self.assertIn("5-Verify-PortableV4-SignedHandoff.cmd", sign_cmd)
        self.assertIn("NAO publica", verify_cmd)
        self.assertIn("NAO seleciona pendrive", verify_cmd)
        self.assertIn("NAO escreve midia fisica", verify_cmd)

    def test_signing_tooling_publishes_windows_release_agent_for_operator_verification(self):
        workflow = SIGNING_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("GOOS=windows GOARCH=amd64", workflow)
        self.assertIn("ordax-release-agent-windows-amd64.exe", workflow)

    def test_signing_doc_describes_v4_ai_binding_and_canonical_boundary(self):
        text = SIGNING_DOC.read_text(encoding="utf-8")
        self.assertIn("For v4", text)
        self.assertIn("local-ai-runtime.erofs", text)
        self.assertIn("ordax.local-ai/1", text)
        self.assertIn("operator-controlled signing/materialization run using the canonical private key", text)
        self.assertIn("does not authorize publication, activation or physical-media writes", text)

    def test_signing_handoff_contract_keeps_pre_publication_boundary_explicit(self):
        import json
        contract = json.loads(HANDOFF_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            contract["$schema"],
            "prototype-ordax.portable-v4-signing-handoff-contract/1",
        )
        self.assertEqual(
            contract["post_sign_verification_receipt_schema"],
            "prototype-ordax.portable-v4-signed-handoff-verification/1",
        )
        self.assertEqual(
            [artifact["name"] for artifact in contract["canonical_artifacts"]],
            ["system.erofs", "native-surface-runtime.erofs", "local-ai-runtime.erofs"],
        )
        self.assertTrue(contract["sign_boundary"]["canonical_private_key_external_to_handoff"])
        self.assertTrue(contract["post_sign_verify_boundary"]["official_release_agent_verify_envelope_required"])
        self.assertFalse(contract["post_sign_verify_boundary"]["portable_materialization_performed"])
        self.assertFalse(contract["post_sign_verify_boundary"]["publication_performed"])
        self.assertFalse(contract["post_sign_verify_boundary"]["activation_performed"])
        self.assertFalse(contract["post_sign_verify_boundary"]["physical_write_performed"])
        self.assertTrue(contract["next_boundary"]["release_agent_materialize_portable_v4_required"])
        self.assertTrue(contract["next_boundary"]["physical_media_authority_separate"])

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
