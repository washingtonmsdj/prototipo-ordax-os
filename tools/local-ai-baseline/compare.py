#!/usr/bin/env python3
"""Compare two OrdaX Local AI baseline reports without selecting a tuning winner.

The comparison is intentionally descriptive. It rejects incompatible measurements
(model/API/token budget/hardware fingerprint drift) and reports objective percent
deltas for latency and throughput. It never promotes a candidate or changes
runtime/release state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BASELINE_SCHEMA = "prototype-ordax.local-ai-baseline/1"
HARDWARE_SCHEMA = "prototype-ordax.local-ai-hardware-probe/1"
BENCHMARK_SCHEMA = "prototype-ordax.local-ai-benchmark/1"
COMPARISON_SCHEMA = "prototype-ordax.local-ai-baseline-comparison/1"
PRODUCT_INFERENCE_API_PATH = "/v1/chat/completions"
MAX_BASELINE_BYTES = 2 * 1024 * 1024


class ComparisonError(RuntimeError):
    pass


def load_json(path: Path):
    path = Path(path)
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_BASELINE_BYTES + 1)
    except OSError as exc:
        raise ComparisonError(f"cannot read baseline: {path}") from exc
    if len(data) > MAX_BASELINE_BYTES:
        raise ComparisonError(f"baseline exceeds byte limit: {path}")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"baseline is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ComparisonError(f"baseline root must be an object: {path}")
    return value


def positive_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ComparisonError(f"{label} must be a positive number")
    return float(value)


def positive_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ComparisonError(f"{label} must be a positive integer")
    return value


def validate_baseline(value, label):
    if value.get("$schema") != BASELINE_SCHEMA:
        raise ComparisonError(f"{label} has incompatible baseline schema")

    policy = value.get("comparison_policy")
    if not isinstance(policy, dict):
        raise ComparisonError(f"{label} is missing comparison policy")
    if policy.get("release_gate") is not False or policy.get("runtime_bytes_modified") is not False:
        raise ComparisonError(f"{label} must remain non-promotional and observational")

    hardware = value.get("hardware")
    if not isinstance(hardware, dict) or hardware.get("$schema") != HARDWARE_SCHEMA:
        raise ComparisonError(f"{label} has incompatible hardware result")
    if hardware.get("runtime_compatible") is not True:
        raise ComparisonError(f"{label} hardware is not compatible with the pinned runtime")
    blockers = hardware.get("start_blockers")
    if not isinstance(blockers, list) or blockers:
        raise ComparisonError(f"{label} hardware contains start blockers")

    benchmark = value.get("benchmark")
    if not isinstance(benchmark, dict) or benchmark.get("$schema") != BENCHMARK_SCHEMA:
        raise ComparisonError(f"{label} has incompatible benchmark result")
    if benchmark.get("engineId") != "llama.cpp":
        raise ComparisonError(f"{label} has unexpected engine identity")
    model_id = benchmark.get("modelId")
    if not isinstance(model_id, str) or not model_id.strip() or len(model_id) > 160 or "\0" in model_id:
        raise ComparisonError(f"{label} has invalid model identity")
    if benchmark.get("api_path") != PRODUCT_INFERENCE_API_PATH:
        raise ComparisonError(f"{label} did not measure the product inference API path")
    if benchmark.get("release_gate") is not False or benchmark.get("tuning_applied") is not False:
        raise ComparisonError(f"{label} benchmark must remain non-promotional and untuned")

    measured_runs = positive_int(benchmark.get("measured_runs"), f"{label} measured_runs")
    n_predict = positive_int(benchmark.get("n_predict"), f"{label} n_predict")
    summary = benchmark.get("summary")
    if not isinstance(summary, dict):
        raise ComparisonError(f"{label} benchmark summary is missing")
    latency = positive_number(summary.get("median_latency_ms"), f"{label} median latency")
    wall_tps = positive_number(
        summary.get("median_wall_tokens_per_second"),
        f"{label} median wall throughput",
    )
    server_tps = summary.get("median_server_tokens_per_second")
    if server_tps is not None:
        server_tps = positive_number(server_tps, f"{label} median server throughput")

    memory = hardware.get("memory")
    if not isinstance(memory, dict):
        raise ComparisonError(f"{label} hardware memory result is missing")
    total_memory = memory.get("total_bytes")
    if total_memory is not None:
        total_memory = positive_int(total_memory, f"{label} total memory")

    cpu_features = hardware.get("cpu_features")
    if not isinstance(cpu_features, list) or any(not isinstance(item, str) or not item for item in cpu_features):
        raise ComparisonError(f"{label} CPU feature set is invalid")

    logical_cpus = hardware.get("logical_cpus")
    if logical_cpus is not None:
        logical_cpus = positive_int(logical_cpus, f"{label} logical CPU count")

    return {
        "model_id": model_id,
        "engine_id": benchmark["engineId"],
        "api_path": benchmark["api_path"],
        "measured_runs": measured_runs,
        "n_predict": n_predict,
        "latency_ms": latency,
        "wall_tps": wall_tps,
        "server_tps": server_tps,
        "hardware_fingerprint": {
            "runtime_artifact_platform": hardware.get("runtime_artifact_platform"),
            "architecture": hardware.get("architecture"),
            "logical_cpus": logical_cpus,
            "memory_total_bytes": total_memory,
            "cpu_features": tuple(cpu_features),
        },
    }


def percent_change(before, after):
    return round(((after - before) / before) * 100.0, 3)


def compare_baselines(baseline_value, candidate_value):
    baseline = validate_baseline(baseline_value, "baseline")
    candidate = validate_baseline(candidate_value, "candidate")

    for field in ("model_id", "engine_id", "api_path", "measured_runs", "n_predict"):
        if baseline[field] != candidate[field]:
            raise ComparisonError(f"baseline and candidate differ in required field: {field}")
    if baseline["hardware_fingerprint"] != candidate["hardware_fingerprint"]:
        raise ComparisonError("baseline and candidate hardware fingerprints differ")

    server_delta = None
    if baseline["server_tps"] is not None and candidate["server_tps"] is not None:
        server_delta = percent_change(baseline["server_tps"], candidate["server_tps"])

    return {
        "$schema": COMPARISON_SCHEMA,
        "comparable": True,
        "engineId": baseline["engine_id"],
        "modelId": baseline["model_id"],
        "api_path": baseline["api_path"],
        "measured_runs": baseline["measured_runs"],
        "n_predict": baseline["n_predict"],
        "baseline": {
            "median_latency_ms": baseline["latency_ms"],
            "median_wall_tokens_per_second": baseline["wall_tps"],
            "median_server_tokens_per_second": baseline["server_tps"],
        },
        "candidate": {
            "median_latency_ms": candidate["latency_ms"],
            "median_wall_tokens_per_second": candidate["wall_tps"],
            "median_server_tokens_per_second": candidate["server_tps"],
        },
        "delta_percent": {
            "latency": percent_change(baseline["latency_ms"], candidate["latency_ms"]),
            "wall_tokens_per_second": percent_change(baseline["wall_tps"], candidate["wall_tps"]),
            "server_tokens_per_second": server_delta,
        },
        "interpretation": {
            "latency_negative_is_lower": True,
            "throughput_positive_is_higher": True,
            "automatic_winner_selected": False,
            "release_gate": False,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        result = compare_baselines(load_json(args.baseline), load_json(args.candidate))
    except ComparisonError as exc:
        parser.error(str(exc))

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
