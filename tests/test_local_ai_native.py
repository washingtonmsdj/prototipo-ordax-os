import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "system" / "surface" / "runtime" / "native_host_server.py"
AGENT = ROOT / "system" / "services" / "local-ai" / "agent.sh"
CONTRACT = ROOT / "docs" / "contracts" / "local-ai-pack.json"

spec = importlib.util.spec_from_file_location("ordax_native_host_local_ai_test", HOST)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class FakeAIHandler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return

    def do_GET(self):
        if self.path == "/v1/models":
            body = json.dumps({"data": [{"id": "default.gguf"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        value = json.loads(self.rfile.read(length))
        assert value["stream"] is False
        body = json.dumps({
            "choices": [{"message": {"content": "resposta local"}}],
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class LocalAINativeTests(unittest.TestCase):
    def setUp(self):
        self.original_config = module.LOCAL_AI_CONFIG_FILE

    def tearDown(self):
        module.LOCAL_AI_CONFIG_FILE = self.original_config

    def test_pack_contract_keeps_ai_optional_and_migratable(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["partition"], "ORDAX-DATA")
        self.assertTrue(contract["selection"]["may_be_disabled_by_user"])
        self.assertTrue(contract["selection"]["base_mvp_must_boot_without_pack"])
        self.assertTrue(contract["integrity"]["canonical_15_system_artifacts_unchanged"])
        self.assertTrue(contract["migration"]["replace_engine_without_surface_rewrite"])
        self.assertTrue(contract["migration"]["replace_model_without_surface_rewrite"])

    def test_config_rejects_remote_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local-ai.json"
            module.LOCAL_AI_CONFIG_FILE = str(path)
            path.write_text(json.dumps({
                "schema": "ordax.local-ai-config/1",
                "enabled": True,
                "endpoint": "https://example.com:443",
                "engine": "llama.cpp",
                "model": "default.gguf",
            }), encoding="utf-8")
            self.assertIsNone(module.read_local_ai_config())

    def test_openai_compatible_loopback_backend_completes(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeAIHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "local-ai.json"
                module.LOCAL_AI_CONFIG_FILE = str(path)
                path.write_text(json.dumps({
                    "schema": "ordax.local-ai-config/1",
                    "enabled": True,
                    "endpoint": f"http://127.0.0.1:{server.server_port}",
                    "engine": "llama.cpp",
                    "model": "default.gguf",
                }), encoding="utf-8")
                status = module.local_ai_status_snapshot()
                self.assertEqual(status["state"], "ready")
                response = module.complete_local_ai([
                    {"role": "user", "content": "Olá"},
                ])
                self.assertEqual(response["text"], "resposta local")
                self.assertEqual(response["backend"], "llama.cpp")
        finally:
            server.shutdown()
            server.server_close()

    def test_agent_is_loopback_only_and_optional(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("--host 127.0.0.1", text)
        self.assertIn("--no-webui", text)
        self.assertIn("/ordax/ai/current", text)
        self.assertIn('rm -f "$STATE_CONFIG"', text)
        self.assertNotIn("0.0.0.0", text)


if __name__ == "__main__":
    unittest.main()
