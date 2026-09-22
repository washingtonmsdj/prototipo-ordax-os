# Ordax Intelligence

Ordax Intelligence is a **system capability**, not an application.

The visual assistant, search, Notes, Files, System and future workflows may all
consume the same provider-neutral `ordax.intelligence/1` contract. A chat UI is
only one surface for the capability and must never become the intelligence
authority.

## Layering

```text
Surface / apps / search
        |
        v
ordax.intelligence/1
        |
        v
Ordax Intelligence
  - authorized context
  - policy
  - provenance
  - future typed tools
  - model routing
        |
        v
ordax.local-ai/1
        |
        v
local inference backend
```

The current MVP route is local-only. The existing `ordax.local-ai/1` boundary is
the AI Runtime / inference backend and currently targets llama.cpp with a pinned
small GGUF model.

## MVP authority

The first Intelligence slice is **read/answer only**. It does not obtain file,
shell, network mutation, power or update authority merely because it is part of
the operating system. Context is supplied explicitly by the caller and is
treated as data, never as a permission grant.

Typed tools can be added later only through existing OrdaX contracts with their
normal authorization and validation. Intelligence must never bypass the Runtime
or call privileged internals directly.

## Distribution

The public Stable/MVP product is intended to include a local inference runtime
and default model. This is separate from boot criticality: failure of the model
or inference process must not prevent OrdaX from booting or the Surface from
working.

Engine and model identities remain replaceable. Future releases may switch the
engine, model or add an explicitly allowed remote provider without changing the
`ordax.intelligence/1` system contract.
