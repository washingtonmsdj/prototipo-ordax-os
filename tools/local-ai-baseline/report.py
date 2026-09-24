#!/usr/bin/env python3
"""Compose an OrdaX Local AI hardware probe and benchmark into one baseline report.

This tool does not start the backend, tune it, or alter release/runtime bytes. It
runs the existing bounded engineering probe + benchmark and emits a single JSON
record suitable for before/after tuning comparisons on the same target machine.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARDWARE_PROBE = ROOT / "tools/local-ai-hardware-probe/probe.py"
BENCHMARK = ROOT / "tools/local-ai-benchmark/benchmark.py"
SCHEMA = "prototype-ordax.local-ai-baseline/1"


class BaselineError(RuntimeError):
    pass


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BaselineError(f"cannot load baseline component: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_baseline(
    *,
    base_url="http://127.0.0.1:17865",
    runs=3,
    n_predict=32,
    timeout=120.0,
    expected_model=None,
):
    hardware_module = load_module(HARDWARE_PROBE, "ordax_local_ai_hardware_probe")
    benchmark_module = load_module(BENCHMARK, "ordax_local_ai_benchmark")

    try:
        hardware = hardware_module.probe_system()
    except Exception as exc:
        raise BaselineError(f"hardware probe failed: {exc}") from exc

    if hardware.get("runtime_compatible") is not True:
        blockers = hardware.get("start_blockers") or ["unknown-hardware-blocker"]
        raise BaselineError("hardware is incompatible with the pinned runtime: " + ",".join(blockers))

    try:
        benchmark = benchmark_module.benchmark(
            base_url,
            runs=runs,
            n_predict=n_predict,
            timeout=timeout,
            expected_model=expected_model,
        )
    except Exception as exc:
        raise BaselineError(f"benchmark failed: {exc}") from exc

    return {
        "$schema": SCHEMA,
        "hardware": hardware,
        "benchmark": benchmark,
        "comparison_policy": {
            "same_target_recommended": True,
            "single_variable_tuning_required": True,
            "release_gate": False,
            "runtime_bytes_modified": False,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:17865")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--n-predict", type=int, default=32)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--expected-model")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        result = build_baseline(
            base_url=args.base_url,
            runs=args.runs,
            n_predict=args.n_predict,
            timeout=args.timeout,
            expected_model=args.expected_model,
        )
    except BaselineError as exc:
        parser.error(str(exc))

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
