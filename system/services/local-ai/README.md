# OrdaX Local AI

Local AI is an **optional Stable/MVP component**, never a boot dependency.

The stable Surface boundary is `ordax.local-ai/1`. The UI talks only to this
provider-neutral port. It must not import llama.cpp, OpenVINO, a specific model
vendor, or a cloud API directly.

## Initial implementation direction

The first runtime target is `llama.cpp` with a small GGUF model. The current
candidate is Qwen3.5-0.8B-class so the first MVP does not assume a discrete GPU.
No engine/model bytes are accepted into a release until their exact SHA-256,
size, upstream source and license are pinned in a signed component manifest.

The service listens on loopback only. Prompt content stays local by default.
There is no implicit cloud fallback, filesystem access, tool execution or
prompt telemetry.

## Migration

Engine and model identities are separate. A future release may replace
llama.cpp with OpenVINO or another local provider, and may replace the model,
without changing the Surface contract or user-facing assistant identity.

The model is stored outside `system.erofs` under the Local AI component root,
so it can be added, removed or upgraded independently.

## Creator

The intended public Creator option is **Incluir IA local / Include local AI /
Incluir IA local**, selected by default once the signed bundle is available.
The user can turn it off.

The first real Stable/MVP USB authorization is already bound to a frozen Creator
source context. Therefore the Creator UI itself is not changed until that first
physical proof is completed; changing the writer before that proof would
invalidate the authorization binding. This is deliberate, not a temporary
bypass.
