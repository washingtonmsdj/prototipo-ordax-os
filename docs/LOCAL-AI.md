# OrdaX Local AI

Status: MVP PROVIDER FOUNDATION / SIGNED RUNTIME PACKAGE PENDING

Local AI is the first **provider** for the OrdaX AI Native foundation. It is not
the foundation itself.

```text
ordax.ai-runtime/1
 -> local provider adapter
 -> ordax.local-ai/1
 -> loopback llama.cpp
 -> verified GGUF model
```

The current source lock pins a Qwen3.5 0.8B Q4_0 GGUF profile and a llama.cpp
source revision. Engine and model are independently replaceable.

Local inference is designed to work without an account or internet once the
signed component has been installed. Prompt content is local by default; there
is no implicit cloud fallback, direct filesystem access, tool execution or
prompt-content telemetry.

The model lives outside `system.erofs` under the local-AI component root so it
can be added, removed or upgraded independently. Removing it must not remove
user files or prevent OrdaX from booting.

The public Creator should eventually offer **Incluir IA local**, selected by
default but optional. The actual physical-writer binding remains deferred until
the already-authorized first Stable/MVP USB proof has completed and a new
authorization context covers the changed Creator.
