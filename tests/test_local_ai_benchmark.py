import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "local-ai-benchmark" / "benchmark.py"
SPEC = importlib.util.spec_from_file_location("ordax_local_ai_benchmark", MODULE_PATH)
BENCH = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(BENCH)


class FakeLlamaHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    model_id = "qwen3.5-0.8b-q4_0"
    completion_calls = 0

    def log_message(self, format, *args):
        return

    def _send_json(self, value):
        payload = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_error(404)
            return
        self._send_json({"data": [{"id": self.model_id}]})

    def do_POST(self):
        if self.path != "/completion":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length).decode("utf-8"))
        self.__class__.completion_calls += 1
        tokens = min(4, request["n_predict"])
        self._send_json({
            "content": "OK",
            "tokens_predicted": tokens,
            "timings": {"predicted_per_second": 20.0},
        })


class ServerFixture:
    def __enter__(self):
        FakeLlamaHandler.completion_calls = 0
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeLlamaHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.url = f"http://{host}:{port}"
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class LocalAiBenchmarkTests(unittest.TestCase):
    def test_endpoint_policy_is_exact_ipv4_loopback_http(self):
        self.assertEqual(
            BENCH.validate_base_url("http://127.0.0.1:17865"),
            "http://127.0.0.1:17865",
        )
        for invalid in (
            "http://localhost:17865",
            "https://127.0.0.1:17865",
            "http://[::1]:17865",
            "http://127.0.0.1:17865/path",
            "http://127.0.0.1",
            "http://user@127.0.0.1:17865",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(BENCH.BenchmarkError):
                    BENCH.validate_base_url(invalid)

    def test_benchmark_warms_once_and_reports_measured_medians(self):
        with ServerFixture() as fixture:
            result = BENCH.benchmark(
                fixture.url,
                runs=2,
                n_predict=8,
                timeout=2,
                expected_model="qwen3.5-0.8b-q4_0",
            )
        self.assertEqual(result["$schema"], BENCH.SCHEMA)
        self.assertEqual(result["engineId"], "llama.cpp")
        self.assertEqual(result["modelId"], "qwen3.5-0.8b-q4_0")
        self.assertEqual(result["warmup_runs"], 1)
        self.assertEqual(result["measured_runs"], 2)
        self.assertEqual(FakeLlamaHandler.completion_calls, 3)
        self.assertEqual(len(result["samples"]), 2)
        self.assertGreater(result["summary"]["median_latency_ms"], 0)
        self.assertGreater(result["summary"]["median_wall_tokens_per_second"], 0)
        self.assertEqual(result["summary"]["median_server_tokens_per_second"], 20.0)
        self.assertFalse(result["release_gate"])
        self.assertFalse(result["tuning_applied"])

    def test_model_mismatch_fails_before_any_completion(self):
        with ServerFixture() as fixture:
            with self.assertRaisesRegex(BENCH.BenchmarkError, "active model mismatch"):
                BENCH.benchmark(
                    fixture.url,
                    runs=1,
                    n_predict=8,
                    timeout=2,
                    expected_model="wrong-model",
                )
        self.assertEqual(FakeLlamaHandler.completion_calls, 0)

    def test_run_and_timeout_bounds_are_explicit(self):
        with self.assertRaises(BENCH.BenchmarkError):
            BENCH.benchmark("http://127.0.0.1:17865", runs=0)
        with self.assertRaises(BENCH.BenchmarkError):
            BENCH.validate_timeout(0)
        with self.assertRaises(BENCH.BenchmarkError):
            BENCH.validate_timeout(BENCH.MAX_TIMEOUT_SECONDS + 1)


if __name__ == "__main__":
    unittest.main()
