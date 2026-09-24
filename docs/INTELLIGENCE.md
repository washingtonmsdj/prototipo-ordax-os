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
backend startup. A dedicated non-promotional CI gate now signs a v4 envelope with
an ephemeral CI-only key, materializes the three artifacts over loopback HTTPS using
the real built AI EROFS, revalidates the release offline and byte-compares the
content-addressed stored AI runtime. This still does not claim a promoted Stable/MVP
artifact: canonical-key Stable v4 signing/materialization plus disposable v4 boot and
physical proof remain release gates.

## Memory and model routing

The pre-MVP foundation now separates persistent product memory from inference providers:

```text
ordax.intelligence/1
  +-- ordax.memory/1
  +-- ordax.model-router/1
        +-- ordax.local-ai/1
        +-- OpenAI adapter (future)
        +-- xAI adapter (future)
        +-- future providers
```

Memory belongs to OrdaX. llama.cpp, GPT, Grok or another model may receive authorized context, but none of them becomes the owner of persistent memory.

Memory scopes are device, account, Space, project and session. Persistent items carry provenance and sensitivity. The user-facing memory owner must support review, edit and delete. Secret material is not memory.

Semantic embeddings are derived indexes: replacing an embedding model does not change the identity of the underlying memory item.

External routes require an explicit egress decision. Local AI remains the offline baseline when an external provider is unavailable or not authorized.

Professional Profile Packs may influence retrieval sources and preferred model purpose, but they cannot bypass Space membership, memory authorization or tool permissions.

## Authority boundary

The MVP Intelligence runtime is consultative:

- no implicit file writes;
- no implicit command or shell execution;
- no implicit external network access;
- no package installation;
- no system or disk mutation;
- no silent cloud fallback;
- no privilege gained from prompt text.

Context supplied to Intelligence is bounded and carries provenance. Tool execution, agents and broader capability bridges still require their own explicit contracts and permissions before activation. Persistent memory now has the source-level `ordax.memory/1` contract, but runtime persistence/retrieval remains a separate implementation step and does not grant tool authority.

## Nova OrdaX reference

The legacy `novo-ordax-os` architecture correctly separated **Ordax
Intelligence** from the **AI Runtime / Inference Broker** and treated Surface
apps as clients. This prototype reimplements those architecture invariants
clean-room; it does not copy the legacy runtime, agents or permission system.
The exact reuse decision is recorded in `docs/SOURCE-MIGRATION.md`.
