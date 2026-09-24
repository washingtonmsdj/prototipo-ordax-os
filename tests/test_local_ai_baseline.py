from __future__ import annotations

import importlib.util
from pathlib import Path
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/local-ai-baseline/report.py"
SPEC = importlib.util.spec_from_file_location("ordax_local_ai_baseline", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load local AI baseline reporter")
BASELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASELINE)


class LocalAiBaselineTests(unittest.TestCase):
    def modules(self, *, compatible=True, benchmark_error=None):
        hardware = types.SimpleNamespace(
            probe_system=lambda: {
                "$schema": "prototype-ordax.local-ai-hardware-probe/1",
                "runtime_compatible": compatible,
                "start_blockers": [] if compatible else ["runtime-artifact-architecture-mismatch"],
                "architecture": "x86_64" if compatible else "aarch64",
            }
        )

        def benchmark(*args, **kwargs):
            if benchmark_error is not None:
                raise benchmark_error
            return {
                "$schema": "prototype-ordax.local-ai-benchmark/1",
                "engineId": "llama.cpp",
                "modelId": "qwen-test",
                "summary": {"median_wall_tokens_per_second": 12.5},
                "release_gate": False,
                "tuning_applied": False,
            }

        benchmark_module = types.SimpleNamespace(benchmark=benchmark)
        return hardware, benchmark_module

    def test_composes_probe_and_benchmark_without_claiming_release_or_tuning(self):
        hardware, benchmark = self.modules()
        with patch.object(BASELINE, "load_module", side_effect=[hardware, benchmark]):
            result = BASELINE.build_baseline(
                base_url="http://127.0.0.1:17865",
                runs=4,
                n_predict=64,
                timeout=30.0,
                expected_model="qwen-test",
            )

        self.assertEqual(result["$schema"], "prototype-ordax.local-ai-baseline/1")
        self.assertTrue(result["hardware"]["runtime_compatible"])
        self.assertEqual(result["benchmark"]["modelId"], "qwen-test")
        self.assertFalse(result["comparison_policy"]["release_gate"])
        self.assertFalse(result["comparison_policy"]["runtime_bytes_modified"])
        self.assertTrue(result["comparison_policy"]["single_variable_tuning_required"])

    def test_incompatible_hardware_fails_before_benchmark(self):
        hardware, benchmark = self.modules(compatible=False)
        benchmark_calls = []
        benchmark.benchmark = lambda *args, **kwargs: benchmark_calls.append((args, kwargs))
        with patch.object(BASELINE, "load_module", side_effect=[hardware, benchmark]):
            with self.assertRaisesRegex(
                BASELINE.BaselineError,
                "runtime-artifact-architecture-mismatch",
            ):
                BASELINE.build_baseline()
        self.assertEqual(benchmark_calls, [])

    def test_benchmark_failure_invalidates_the_baseline(self):
        hardware, benchmark = self.modules(benchmark_error=RuntimeError("backend unavailable"))
        with patch.object(BASELINE, "load_module", side_effect=[hardware, benchmark]):
            with self.assertRaisesRegex(BASELINE.BaselineError, "benchmark failed: backend unavailable"):
                BASELINE.build_baseline()


if __name__ == "__main__":
    unittest.main()
