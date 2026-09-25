from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/local-ai-baseline/compare.py"
SPEC = importlib.util.spec_from_file_location("ordax_local_ai_baseline_compare", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load local AI baseline comparator")
COMPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPARE)


def baseline(*, latency=200.0, wall_tps=10.0, server_tps=12.0):
    return {
        "$schema": "prototype-ordax.local-ai-baseline/1",
        "hardware": {
            "$schema": "prototype-ordax.local-ai-hardware-probe/1",
            "runtime_artifact_platform": "linux-x86_64",
            "architecture": "x86_64",
            "logical_cpus": 8,
            "memory": {
                "total_bytes": 16 * 1024 * 1024 * 1024,
                "available_bytes": 8 * 1024 * 1024 * 1024,
            },
            "cpu_features": ["avx", "avx2", "fma", "sse4_2"],
            "runtime_compatible": True,
            "start_blockers": [],
        },
        "benchmark": {
            "$schema": "prototype-ordax.local-ai-benchmark/1",
            "engineId": "llama.cpp",
            "modelId": "qwen3.5-0.8b-q4_0",
            "api_path": "/v1/chat/completions",
            "warmup_runs": 1,
            "measured_runs": 5,
            "n_predict": 32,
            "summary": {
                "median_latency_ms": latency,
                "median_wall_tokens_per_second": wall_tps,
                "median_server_tokens_per_second": server_tps,
            },
            "release_gate": False,
            "tuning_applied": False,
        },
        "comparison_policy": {
            "same_target_recommended": True,
            "single_variable_tuning_required": True,
            "release_gate": False,
            "runtime_bytes_modified": False,
        },
    }


class LocalAiBaselineCompareTests(unittest.TestCase):
    def test_reports_objective_deltas_without_selecting_a_winner(self):
        before = baseline()
        after = baseline(latency=180.0, wall_tps=11.0, server_tps=13.2)
        result = COMPARE.compare_baselines(before, after)

        self.assertEqual(result["$schema"], "prototype-ordax.local-ai-baseline-comparison/1")
        self.assertTrue(result["comparable"])
        self.assertEqual(result["api_path"], "/v1/chat/completions")
        self.assertEqual(result["delta_percent"]["latency"], -10.0)
        self.assertEqual(result["delta_percent"]["wall_tokens_per_second"], 10.0)
        self.assertEqual(result["delta_percent"]["server_tokens_per_second"], 10.0)
        self.assertFalse(result["interpretation"]["automatic_winner_selected"])
        self.assertFalse(result["interpretation"]["release_gate"])

    def test_rejects_model_or_api_drift(self):
        before = baseline()
        after = baseline()
        after["benchmark"]["modelId"] = "different-model"
        with self.assertRaisesRegex(COMPARE.ComparisonError, "model_id"):
            COMPARE.compare_baselines(before, after)

        after = baseline()
        after["benchmark"]["api_path"] = "/completion"
        with self.assertRaisesRegex(COMPARE.ComparisonError, "product inference API path"):
            COMPARE.compare_baselines(before, after)

    def test_rejects_hardware_fingerprint_drift(self):
        before = baseline()
        after = copy.deepcopy(before)
        after["hardware"]["logical_cpus"] = 4
        with self.assertRaisesRegex(COMPARE.ComparisonError, "hardware fingerprints differ"):
            COMPARE.compare_baselines(before, after)

        after = copy.deepcopy(before)
        after["hardware"]["cpu_features"] = ["avx", "sse4_2"]
        with self.assertRaisesRegex(COMPARE.ComparisonError, "hardware fingerprints differ"):
            COMPARE.compare_baselines(before, after)

    def test_rejects_measurement_shape_drift(self):
        before = baseline()
        after = baseline()
        after["benchmark"]["n_predict"] = 64
        with self.assertRaisesRegex(COMPARE.ComparisonError, "n_predict"):
            COMPARE.compare_baselines(before, after)

        after = baseline()
        after["benchmark"]["measured_runs"] = 3
        with self.assertRaisesRegex(COMPARE.ComparisonError, "measured_runs"):
            COMPARE.compare_baselines(before, after)

    def test_server_rate_delta_is_optional_only_when_not_available(self):
        before = baseline(server_tps=None)
        after = baseline(server_tps=None)
        result = COMPARE.compare_baselines(before, after)
        self.assertIsNone(result["delta_percent"]["server_tokens_per_second"])

    def test_rejects_promotional_or_incompatible_baselines(self):
        before = baseline()
        after = baseline()
        after["comparison_policy"]["release_gate"] = True
        with self.assertRaisesRegex(COMPARE.ComparisonError, "non-promotional"):
            COMPARE.compare_baselines(before, after)

        after = baseline()
        after["hardware"]["runtime_compatible"] = False
        after["hardware"]["start_blockers"] = ["runtime-artifact-architecture-mismatch"]
        with self.assertRaisesRegex(COMPARE.ComparisonError, "not compatible"):
            COMPARE.compare_baselines(before, after)


if __name__ == "__main__":
    unittest.main()
