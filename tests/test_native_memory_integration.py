from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "system" / "surface" / "runtime" / "native_host_server.py"
COMPOSITION = ROOT / "system" / "composition" / "native" / "main.mjs"
WORKFLOW = ROOT / ".github" / "workflows" / "intelligence-foundation.yml"


class NativeMemoryIntegrationTests(unittest.TestCase):
    def test_native_host_wires_memory_endpoint_without_cors_or_generic_authority(self):
        host = HOST.read_text(encoding="utf-8")

        self.assertIn('MEMORY_PATH = "/__ordax/native/intelligence-memory"', host)
        self.assertIn("MAX_MEMORY_REQUEST_BODY_BYTES", host)
        self.assertIn("MemoryEndpointRequestError", host)
        self.assertIn("read_memory_endpoint()", host)
        self.assertIn("write_memory_endpoint(", host)
        self.assertIn("MEMORY_PATH, FILES_PATH", host)
        self.assertNotIn("Access-Control-Allow-Origin", host)

    def test_native_composition_probes_memory_fail_soft_and_keeps_prompt_injection_explicit(self):
        composition = COMPOSITION.read_text(encoding="utf-8")

        self.assertIn("createNativeMemoryStore", composition)
        self.assertIn("createMemoryRuntime", composition)
        self.assertIn('"OrdaX native Intelligence memory persistence unavailable"', composition)
        self.assertIn("memoryStore,", composition)
        self.assertIn("createMemoryRuntime({ store: memoryStore })", composition)
        self.assertIn("createIntelligenceRuntime({ inferencePort: localAi })", composition)
        self.assertNotIn("createIntelligenceRuntime({ inferencePort: localAi, memory", composition)

    def test_intelligence_workflow_covers_host_composition_and_integration_regression(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("'system/surface/runtime/native_host_server.py'", workflow)
        self.assertIn("'system/composition/native/main.mjs'", workflow)
        self.assertIn("'tests/test_native_memory_integration.py'", workflow)
        self.assertIn("python -m unittest tests.test_native_memory_integration -v", workflow)


if __name__ == "__main__":
    unittest.main()
