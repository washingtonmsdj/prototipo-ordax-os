#!/usr/bin/env python3
"""Report bounded host capabilities relevant to the pinned OrdaX local AI runtime.

The probe intentionally does not invent performance thresholds or tuning flags. It
only records observable host capabilities and whether the pinned linux-x86_64
engine artifact can execute on the current architecture. Performance choices are
left to benchmark-backed policy.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform

SCHEMA = "prototype-ordax.local-ai-hardware-probe/1"
RUNTIME_ARTIFACT_PLATFORM = "linux-x86_64"
MAX_CPUINFO_BYTES = 4 * 1024 * 1024
MAX_MEMINFO_BYTES = 256 * 1024
TRACKED_CPU_FEATURES = frozenset({
    "avx",
    "avx2",
    "bmi1",
    "bmi2",
    "fma",
    "popcnt",
    "sse4_1",
    "sse4_2",
})


class HardwareProbeError(RuntimeError):
    pass


def read_bounded_text(path: Path, max_bytes: int) -> str:
    try:
        with Path(path).open("rb") as handle:
            data = handle.read(max_bytes + 1)
    except OSError as exc:
        raise HardwareProbeError(f"cannot read hardware probe source: {path}") from exc
    if len(data) > max_bytes:
        raise HardwareProbeError(f"hardware probe source exceeds byte limit: {path}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HardwareProbeError(f"hardware probe source is not UTF-8: {path}") from exc


def normalize_machine(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"x86_64", "amd64"}:
        return "x86_64"
    if normalized in {"aarch64", "arm64"}:
        return "aarch64"
    return normalized or "unknown"


def parse_cpu_features(cpuinfo_text: str):
    feature_sets = []
    for raw_line in cpuinfo_text.splitlines():
        key, separator, raw_value = raw_line.partition(":")
        if separator and key.strip().lower() in {"flags", "features"}:
            values = {value.strip().lower() for value in raw_value.split() if value.strip()}
            if values:
                feature_sets.append(values)
    if not feature_sets:
        return []
    # Intersection is deliberate: a feature is reported only when every parsed
    # processor entry exposes it, avoiding unsafe tuning on heterogeneous CPUs.
    common = set.intersection(*feature_sets)
    return sorted(common & TRACKED_CPU_FEATURES)


def parse_meminfo(meminfo_text: str):
    values = {}
    for raw_line in meminfo_text.splitlines():
        key, separator, raw_value = raw_line.partition(":")
        if not separator:
            continue
        parts = raw_value.strip().split()
        if not parts:
            continue
        try:
            numeric = int(parts[0])
        except ValueError:
            continue
        if numeric < 0:
            continue
        multiplier = 1024 if len(parts) >= 2 and parts[1].lower() == "kb" else 1
        values[key.strip()] = numeric * multiplier
    return {
        "total_bytes": values.get("MemTotal"),
        "available_bytes": values.get("MemAvailable"),
    }


def probe_system(
    *,
    machine=None,
    logical_cpus=None,
    cpuinfo_path=Path("/proc/cpuinfo"),
    meminfo_path=Path("/proc/meminfo"),
):
    architecture = normalize_machine(platform.machine() if machine is None else machine)
    cpu_count = os.cpu_count() if logical_cpus is None else logical_cpus
    if cpu_count is not None and (not isinstance(cpu_count, int) or cpu_count <= 0):
        raise HardwareProbeError("logical CPU count is invalid")

    cpuinfo = read_bounded_text(Path(cpuinfo_path), MAX_CPUINFO_BYTES)
    meminfo = read_bounded_text(Path(meminfo_path), MAX_MEMINFO_BYTES)
    features = parse_cpu_features(cpuinfo)
    memory = parse_meminfo(meminfo)

    blockers = []
    if architecture != "x86_64":
        blockers.append("runtime-artifact-architecture-mismatch")

    return {
        "$schema": SCHEMA,
        "runtime_artifact_platform": RUNTIME_ARTIFACT_PLATFORM,
        "architecture": architecture,
        "logical_cpus": cpu_count,
        "memory": memory,
        "cpu_features": features,
        "runtime_compatible": not blockers,
        "start_blockers": blockers,
        "benchmark_required_before_tuning": True,
        "tuning_recommendation": None,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        result = probe_system()
    except HardwareProbeError as exc:
        parser.error(str(exc))

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
