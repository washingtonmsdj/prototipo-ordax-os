# OrdaX Local AI

Status: MVP FOUNDATION / RUNTIME PACKAGE PENDING

The MVP local-assistant design has one stable product identity and a replaceable
inference implementation.

```text
Assistente app
 -> ordax.ai-runtime/1
 -> provider adapter
 -> local inference engine
 -> selected verified model
```

The first profile targets `llama.cpp` and a lightweight Qwen3 0.6B Q4_K_M
model. That choice is a profile, not a permanent product dependency. Engine and
model identities are configuration, while the app remains `assistant`.

## MVP boundary

The assistant may:

- answer text prompts locally;
- summarize text explicitly selected by the user;
- explain sanitized diagnostics supplied through a bounded product contract.

It may not:

- execute an arbitrary shell;
- gain raw-disk authority;
- change release trust;
- bypass Creator/physical-write authorization;
- silently send prompts to a cloud provider;
- index arbitrary user files without an explicit product flow.

The system remains fully usable when local AI is omitted.

## Creator

`docs/contracts/creator-feature-selection.json` defines **IA local** as selected
by default and user-toggleable. A selected feature must resolve to a signed,
verified local package before public Stable/MVP exposure.

The first real Stable/MVP USB proof has already been authorized against the
current Creator/writer source context. This change therefore does not modify the
physical writer. Binding the checkbox to physical media contents is a subsequent
revision and requires a new authorization context.

## Migration

Provider migration is intentionally independent from UI identity. A future local
engine, a larger/smaller GGUF model, or a reviewed cloud provider can implement
the same product contract. Cloud use, if ever added, must be explicit and must
not become a fallback for a user who selected local-only operation.

Independent production delivery through `component-slot` is also a separate
future promotion. The MVP keeps Assistente bundled until signed component trust,
pending-health activation, promotion and rollback are fully promoted.
