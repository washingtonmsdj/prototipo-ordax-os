# Ordax Intelligence

Status: **MVP SYSTEM FOUNDATION**

Ordax Intelligence is a system capability, not an application.

The first-party Assistant may later provide a conversational Surface, but it is
only a client. Files, Notes, Search, Settings, diagnostics and future automation
may consume the same system intelligence contract without opening an Assistant
window.

## Layering

```text
Surface / applications
 -> shared OrdaX services and Workspace context
 -> Ordax Intelligence
 -> AI Runtime / local inference backend
 -> llama.cpp + verified local model (initial implementation)
```

`ordax.intelligence/1` owns product intelligence semantics. The inference
backend remains behind `ordax.local-ai/1`. Engine and model may therefore be
replaced without redefining the OrdaX Intelligence contract.

## MVP policy

The Stable/MVP distribution is expected to include local inference by default
as part of the product. It is **not** a Creator opt-out feature.

This does not make AI boot-critical. A missing, incompatible or failed model
must degrade Intelligence while the operating system, recovery, files and
updates remain usable. The signed engine/model payload and its actual Stable USB
materialization are separate release gates and must not be claimed merely
because the source contract exists.

The initial source lock targets a small Qwen3.5 GGUF profile served by
`llama.cpp`, so the first MVP does not assume a discrete GPU. A later signed
update may replace the model, quantization or inference engine without changing
the stable Intelligence API.


The release layer has a dedicated v4 source contract for this payload.
`prototype-ordax.release-manifest/4` keeps the system image and Surface runtime
semantics from v3, adds `local-ai-runtime.erofs`, and signs a binding to the
canonical engine/model source lock. Surface and AI runtimes are independently
content-addressed and verified. The real engine/model EROFS is reproducibly proven
in CI, and the Portable v2/Stable Base handoff now supports exact v4 verification,
read-only mounting at `/run/ordax/runtime/local-ai`, and non-boot-critical loopback
backend startup. This still does not claim a promoted Stable/MVP artifact: signed
Stable v4 materialization/activation plus disposable and physical boot proof remain
release gates.

## Authority boundary

The MVP Intelligence runtime is consultative:

- no implicit file writes;
- no implicit command or shell execution;
- no implicit external network access;
- no package installation;
- no system or disk mutation;
- no silent cloud fallback;
- no privilege gained from prompt text.

Context supplied to Intelligence is bounded and carries provenance. Tool
execution, agents, persistent memory and broader capability bridges require
their own explicit contracts and permissions before activation.

## Nova OrdaX reference

The legacy `novo-ordax-os` architecture correctly separated **Ordax
Intelligence** from the **AI Runtime / Inference Broker** and treated Surface
apps as clients. This prototype reimplements those architecture invariants
clean-room; it does not copy the legacy runtime, agents or permission system.
The exact reuse decision is recorded in `docs/SOURCE-MIGRATION.md`.
