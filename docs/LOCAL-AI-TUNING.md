# Local AI performance qualification

Status: **ENGINEERING FOUNDATION — NOT A RELEASE GATE**

This document defines how OrdaX measures and later tunes the local inference
backend without weakening the Stable/MVP portability, privacy or signed-runtime
boundaries.

## Current baseline

The Stable/MVP local AI artifact is byte-pinned and uses the generic reproducible
`llama.cpp` build/launcher defined by the release lane. Performance flags must
not be changed opportunistically in the product runtime because changing the
engine or launcher changes the signed v4 payload identity.

Three engineering tools are available on the source tree and do **not** modify
the runtime artifact:

```text
tools/local-ai-hardware-probe/probe.py
tools/local-ai-benchmark/benchmark.py
tools/local-ai-baseline/report.py
```

All three are covered by the `Intelligence Foundation` source gate.

## 1. Hardware capability probe

Run:

```bash
python tools/local-ai-hardware-probe/probe.py
```

The probe reads bounded `/proc/cpuinfo` and `/proc/meminfo` inputs without shelling
out. It reports:

- normalized architecture;
- logical CPU count;
- total and available memory when exposed by the kernel;
- a bounded allow-list of CPU SIMD/features common to every parsed processor;
- objective compatibility with the currently pinned `linux-x86_64` engine
  artifact.

The probe deliberately does **not** invent RAM/CPU performance minimums and does
not output tuning flags. Today the only start blocker it may derive is an
architecture mismatch with the pinned engine artifact. Any future memory or
feature threshold must be justified by measured product behavior and then added
to an explicit contract.

The MVP contract requires a hardware probe before backend start. The probe
implementation is now source-complete, but wiring it into Stable Base startup is
still a separate integration step. Until that wiring lands, do not claim the
`hardware_probe_before_start` requirement as runtime-complete. When wired, probe
failure or incompatibility must degrade Local AI and must not block Surface,
recovery, files or update.

## 2. Steady-state benchmark

With the pinned Local AI backend already running on its loopback endpoint, run:

```bash
python tools/local-ai-benchmark/benchmark.py \
  --expected-model qwen3.5-0.8b-q4_0 \
  --runs 5 \
  --n-predict 32 \
  --output local-ai-benchmark.json
```

The benchmark accepts only literal IPv4 loopback HTTP with an explicit port. It
first discovers exactly one active model through `/v1/models`, fails closed on
an unexpected model identity, performs one unreported warmup, and then records
bounded deterministic `/completion` samples.

The JSON result records:

- engine/model identity;
- measured run count and token budget;
- per-run wall latency;
- predicted token count;
- wall-clock tokens/second;
- llama.cpp-reported predicted tokens/second when supplied by the backend;
- medians across measured samples.

The warmup is excluded from the reported summary so model-load/cache effects are
not confused with steady-state generation throughput.

This benchmark is intentionally **not** a performance release gate. CI tests the
benchmark's policy, parsing and bounds with a local fake server; CI runner speed
must not become a product acceptance threshold.

## 3. Composed target baseline

For a real notebook or USB target, the preferred capture is a single baseline
report that preserves the complete hardware-probe and benchmark payloads:

```bash
python tools/local-ai-baseline/report.py \
  --expected-model qwen3.5-0.8b-q4_0 \
  --runs 5 \
  --n-predict 32 \
  --output local-ai-baseline.json
```

The reporter does not duplicate the measurement logic. It loads the canonical
hardware probe and benchmark, requires the hardware probe to be compatible with
the pinned runtime before attempting inference, and emits both original schema
payloads under `hardware` and `benchmark`.

A baseline is invalid if either component fails. The reporter never converts an
incompatible architecture or an unavailable/mismatched model into a partial
performance result. Its comparison policy explicitly records that it is not a
release gate, that runtime bytes were not modified, and that later tuning should
change one variable at a time.

This report intentionally contains host capability classes (architecture, CPU
count, bounded common SIMD flags and memory totals) but no hostname, account,
prompt history, model responses, user files, tokens or remote telemetry identity.

## 4. Tuning workflow

For a real notebook/hardware target:

1. capture `local-ai-baseline.json` from the untouched currently signed/pinned
   runtime;
2. keep engine commit, model SHA, quantization, prompt, token budget and benchmark
   run count fixed while testing one engine/launcher change at a time;
3. capture a new baseline for each candidate on the same target when practical;
4. compare medians rather than a single run;
5. reject a candidate that changes model/engine identity unexpectedly, breaks
   loopback-only operation, increases failure rate, or violates the bounded
   runtime contracts;
6. only after a measured candidate is selected, update the engine/launcher in the
   release lane and regenerate the exact engine/runtime hashes and signed v4
   evidence.

Do not silently activate CPU-specific flags based only on feature presence. A CPU
feature is an input to experimentation, not proof that a particular build or
threading policy is faster or sufficiently portable.

## 5. What remains

The following work is intentionally still open:

- wire the source-complete hardware probe into Stable Base **before** launching
  the local backend, with fail-soft behavior;
- collect a baseline on the actual target notebook/USB environment;
- decide whether the portable generic engine already meets the UX target;
- if not, evaluate measured alternatives without changing the stable
  `ordax.local-ai/1` / `ordax.intelligence/1` APIs;
- if a tuned engine/launcher is adopted, re-pin and re-prove the entire local AI
  runtime through the canonical release lane.

No cloud provider, tool execution, agent authority or prompt telemetry is enabled
by this performance workflow.
