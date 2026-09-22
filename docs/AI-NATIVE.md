# OrdaX AI Native

Status: MVP FOUNDATION IMPLEMENTED / LOCAL RUNTIME PACKAGE PENDING

AI is a **platform foundation** in OrdaX. It is not defined by the Assistente app,
by llama.cpp, or by one model vendor.

```text
OrdaX apps / experiences
  -> ordax.ai-runtime/1
     -> context + policy boundary
     -> provider adapter
        -> ordax.local-ai/1 -> local engine/model
        -> future explicit remote provider
```

The **Assistente** is one first-party client of this runtime. Files, Notes,
System diagnostics and future workflows may use the same runtime through
bounded product contracts. They must not import a model provider directly.

## Authority

A model is never authority. AI may propose or request work, but filesystem,
network, package, update, boot, release trust and destructive operations remain
owned by their existing typed capabilities and authorization flows.

The MVP foundation explicitly forbids:

- implicit shell or root authority;
- raw-disk access;
- release-trust changes;
- bypass of Creator or physical-write confirmation;
- silent cloud fallback;
- arbitrary background indexing of user files;
- treating text from files or websites as system instructions.

Future tools must preserve the sequence:

```text
intent -> typed operation -> policy/consent -> execution owner -> receipt/evidence
```

## Context, memory and tools

The legacy Novo OrdaX architecture described Agent Manager, Context Manager,
Knowledge, Model Router, Tool Manager, AI Permissions, Capability Bridge,
receipts and audit. Those documents were planning, not a production runtime.
The current OrdaX adopts the useful invariants incrementally:

1. provider-neutral runtime and local provider boundary;
2. explicit user-selected context;
3. typed tools with least privilege;
4. provenance and receipts for tool-backed answers/actions;
5. scoped memory/knowledge with deletion and invalidation;
6. optional multi-provider/model routing.

Only item 1 is a complete MVP source foundation today. Items 2–5 are product
work to add through explicit contracts; they must not be simulated by the UI.

## Local AI profile

The first local provider targets pinned `llama.cpp` plus
`Qwen3.5-0.8B-Q4_0`. This is a replaceable profile, not an OrdaX dependency.
Engine and model identities are stored separately and may migrate without
changing `ordax.ai-runtime/1` or the Assistant identity.

The model and engine binaries are not committed to Git. Stable/MVP packaging
requires exact source, license, size and SHA-256, a signed component manifest
and normal component health/promotion.

## Creator and USB

The desired Creator experience is **Incluir IA local**, selected by default and
user-toggleable. Omitting the local provider must still produce a fully usable
OrdaX; the AI runtime reports the provider as unavailable.

The first real Stable/MVP USB proof is already authorized against an exact
Creator/writer source context. Therefore the current proof writer is deliberately
unchanged. The checkbox can be physically bound only in a later authorized
revision after the first proof; changing the writer now would invalidate the
authorization being proven.

## Migration

Provider migration is a normal component evolution:

```text
same OrdaX AI Runtime
 -> llama.cpp + Qwen3.5 today
 -> another local engine/model later
 -> optional reviewed cloud provider in the future
```

Remote providers, if introduced, must be explicit, disclose data transfer, use
separate credentials and never become a fallback for a local-only choice.
