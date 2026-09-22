import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "intelligence.json"
PORT = ROOT / "system" / "contracts" / "intelligence.mjs"
RUNTIME = ROOT / "system" / "services" / "intelligence" / "runtime.mjs"
README = ROOT / "system" / "services" / "intelligence" / "README.md"


class IntelligenceContractTests(unittest.TestCase):
    def test_intelligence_is_system_capability_not_application(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["$schema"], "prototype-ordax.intelligence/1")
        self.assertTrue(contract["system_layer"])
        self.assertFalse(contract["application_identity"])
        self.assertFalse(contract["surface_dependency"])
        self.assertEqual(contract["runtime_contract"], "ordax.intelligence/1")
        self.assertEqual(contract["inference_backend_contract"], "ordax.local-ai/1")
        self.assertTrue(contract["mvp"]["included_in_product"])
        self.assertFalse(contract["mvp"]["failure_blocks_boot"])
        self.assertFalse(contract["mvp"]["failure_blocks_surface"])

    def test_initial_intelligence_is_read_only_and_permission_neutral(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertTrue(contract["mvp"]["read_answer_available"])
        self.assertFalse(contract["mvp"]["typed_tools_enabled"])
        self.assertFalse(contract["mvp"]["implicit_file_access"])
        self.assertFalse(contract["mvp"]["implicit_shell_access"])
        self.assertFalse(contract["mvp"]["implicit_power_control"])
        self.assertTrue(contract["context"]["context_is_never_authority"])
        self.assertTrue(contract["context"]["prompt_injection_must_not_grant_capabilities"])

    def test_runtime_uses_provider_neutral_contract(self):
        port = PORT.read_text(encoding="utf-8")
        runtime = RUNTIME.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        self.assertIn('ORDAX_INTELLIGENCE_PORT_SCHEMA = "ordax.intelligence/1"', port)
        self.assertIn("createOrdaxIntelligence", runtime)
        self.assertIn("assertLocalAiPort", runtime)
        self.assertNotIn("llama.cpp", port)
        self.assertNotIn("Qwen", port)
        self.assertIn("system capability", readme)


if __name__ == "__main__":
    unittest.main()
