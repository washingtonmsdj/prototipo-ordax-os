# OrdaX Local AI

Local AI is the **default local inference backend for the Stable/MVP system**.
It is not an application and it is not the product intelligence policy layer.

The system-facing intelligence contract is `ordax.intelligence/1`, owned by
`system/services/intelligence/`. That layer may be consumed by Search, Files,
Notes, System, an Assistant surface and future workflows. This service owns only
local model execution behind the provider-neutral `ordax.local-ai/1` port.

## MVP distribution

The public Stable/MVP target includes the local inference runtime and default
small model. The user does not need to opt into AI during USB creation.

This does **not** make inference a boot dependency. If the engine or model cannot
start, OrdaX must still boot, render the Surface and keep non-AI functionality
available. The failure is a degraded capability, not a failed operating system.

The current physical writer candidate predates the signed AI bundle. It must not
silently claim that the model is already on the first physical media. Before the
public MVP media is promoted, the media contract must bind the exact signed AI
bundle and the physical authorization context must be recalculated.

## Initial backend

The first runtime target is `llama.cpp` with a small GGUF model. The current
candidate is Qwen3.5-0.8B-class so the MVP does not assume a discrete GPU.

The model bytes are pinned by exact SHA-256 and size in
`source-lock.json`. The engine source is pinned by exact upstream commit.
No compiled engine is accepted into a Stable/MVP bundle until the build output
has exact provenance, SHA-256 and size.

The service listens on loopback only. Prompt content stays local by default.
There is no implicit cloud fallback, filesystem access, tool execution or prompt
telemetry.

## Evolution and migration

Engine and model identities are separate. A future release may replace
`llama.cpp`, replace the model, or add another explicitly allowed provider
without changing `ordax.intelligence/1`.

For the first MVP the backend is distributed with the product. Independent
signed component-slot activation remains a later promotion step until its
current/previous health and rollback path is fully proven. Migration must reuse
that official component mechanism rather than invent another updater.
