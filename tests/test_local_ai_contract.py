import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "local-ai.json"
PORT = ROOT / "system" / "contracts" / "local-ai.mjs"
README = ROOT / "system" / "services" / "local-ai" / "README.md"
SOURCE_LOCK = ROOT / "system" / "services" / "local-ai" / "source-lock.json"


class LocalAiContractTests(unittest.TestCase):
    def test_local_ai_is_default_mvp_backend_but_not_boot_critical(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["$schema"], "prototype-ordax.local-ai/2")
        self.assertTrue(contract["required_for_public_mvp_distribution"])
        self.assertFalse(contract["required_for_boot"])
        self.assertFalse(contract["required_for_surface"])
        self.assertTrue(contract["creator_policy"]["included_by_default"])
        self.assertFalse(contract["creator_policy"]["user_may_omit"])
        self.assertTrue(contract["creator_policy"]["next_media_context_must_bind_signed_ai_bundle"])
        self.assertTrue(contract["mvp_policy"]["installed_by_default"])
        self.assertTrue(contract["mvp_policy"]["mandatory_in_public_mvp_media"])
        self.assertTrue(contract["mvp_policy"]["failure_must_not_block_boot"])
        self.assertTrue(contract["mvp_policy"]["failure_must_not_block_surface"])

    def test_backend_is_offline_and_migratable(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertFalse(contract["runtime"]["internet_required_for_inference"])
        self.assertTrue(contract["runtime"]["engine_migratable"])
        self.assertTrue(contract["runtime"]["model_migratable"])
        self.assertEqual(contract["runtime"]["model_format"], "GGUF")
        self.assertTrue(contract["runtime"]["exact_model_artifact_pinned"])
        self.assertTrue(contract["runtime"]["exact_engine_source_pinned"])
        self.assertFalse(contract["runtime"]["exact_engine_binary_pinned"])
        self.assertEqual(
            contract["runtime"]["source_lock"],
            "system/services/local-ai/source-lock.json",
        )
        self.assertEqual(
            contract["migration"]["stable_intelligence_contract"],
            "ordax.intelligence/1",
        )

    def test_source_lock_pins_model_bytes_without_committing_large_binary(self):
        lock = json.loads(SOURCE_LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["engine"]["commit"], "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2")
        self.assertEqual(lock["model"]["filename"], "Qwen3.5-0.8B-Q4_0.gguf")
        self.assertEqual(lock["model"]["sha256"], "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf")
        self.assertEqual(lock["model"]["size_bytes"], 563036064)
        self.assertFalse(lock["distribution"]["model_committed_to_git"])
        self.assertTrue(lock["distribution"]["signed_component_required"])

    def test_inference_boundary_is_provider_neutral(self):
        port = PORT.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        self.assertIn('LOCAL_AI_PORT_SCHEMA = "ordax.local-ai/1"', port)
        self.assertIn("generate", port)
        for provider in ("llama.cpp", "OpenVINO"):
            self.assertNotIn(provider, port)
            self.assertIn(provider, readme)
        self.assertIn("loopback", readme)
        self.assertIn("no implicit cloud fallback", readme.lower())


if __name__ == "__main__":
    unittest.main()
