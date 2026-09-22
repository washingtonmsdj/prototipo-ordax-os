import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "local-ai.json"
PORT = ROOT / "system" / "contracts" / "local-ai.mjs"
README = ROOT / "system" / "services" / "local-ai" / "README.md"


class LocalAiContractTests(unittest.TestCase):
    def test_local_ai_is_optional_offline_and_migratable(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["$schema"], "prototype-ordax.local-ai/1")
        self.assertFalse(contract["required_for_boot"])
        self.assertFalse(contract["required_for_offline_use"])
        self.assertTrue(contract["runtime"]["internet_required_for_inference"] is False)
        self.assertTrue(contract["runtime"]["engine_migratable"])
        self.assertTrue(contract["runtime"]["model_migratable"])
        self.assertEqual(contract["runtime"]["model_format"], "GGUF")
        self.assertFalse(contract["runtime"]["exact_model_artifact_pinned"])
        self.assertFalse(contract["runtime"]["exact_engine_artifact_pinned"])
        self.assertTrue(contract["creator_toggle"]["user_may_disable"])
        self.assertTrue(contract["mvp_policy"]["failure_must_not_block_surface"])

    def test_surface_boundary_is_provider_neutral(self):
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
