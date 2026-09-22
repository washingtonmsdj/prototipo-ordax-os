import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "docs" / "contracts" / "ai-native.json"
LOCAL = ROOT / "docs" / "contracts" / "local-ai.json"
CORE = ROOT / "system" / "services" / "components" / "manifests" / "core.mjs"
ASSISTANT = ROOT / "system" / "apps" / "assistant" / "app.mjs"


class AiNativeFoundationTests(unittest.TestCase):
    def test_ai_is_platform_foundation_not_assistant_identity(self):
        ai = json.loads(AI.read_text(encoding="utf-8"))
        self.assertEqual(ai["$schema"], "prototype-ordax.ai-native/1")
        self.assertEqual(ai["product_role"], "platform-foundation")
        self.assertTrue(ai["not_an_app"])
        self.assertEqual(ai["runtime_contract"], "ordax.ai-runtime/1")
        self.assertEqual(ai["first_ui_client"], "assistant")
        self.assertFalse(ai["authority"]["model_is_authority"])
        self.assertTrue(ai["authority"]["typed_capability_required_for_effects"])

    def test_local_ai_is_replaceable_optional_provider(self):
        ai = json.loads(AI.read_text(encoding="utf-8"))
        local = json.loads(LOCAL.read_text(encoding="utf-8"))
        self.assertEqual(local["role"], "replaceable-local-inference-provider")
        self.assertEqual(local["platform_runtime"]["contract"], ai["runtime_contract"])
        self.assertFalse(ai["local_provider"]["required_for_boot"])
        self.assertFalse(ai["local_provider"]["required_for_os_use"])
        self.assertTrue(ai["local_provider"]["replaceable"])
        self.assertTrue(local["platform_runtime"]["assistant_is_only_one_client"])

    def test_component_graph_puts_local_provider_below_ai_runtime(self):
        core = CORE.read_text(encoding="utf-8")
        self.assertIn('id: "ai-runtime-service"', core)
        self.assertIn('id: "local-ai-service"', core)
        local_start = core.index('id: "local-ai-service"')
        local_end = core.index("}),", local_start)
        self.assertIn('dependencies: ["ai-runtime-service"]', core[local_start:local_end])

    def test_assistant_is_described_as_client_not_platform_authority(self):
        assistant = ASSISTANT.read_text(encoding="utf-8")
        self.assertIn('id: "assistant"', assistant)
        self.assertNotIn("raw-disk", assistant.lower())


if __name__ == "__main__":
    unittest.main()
