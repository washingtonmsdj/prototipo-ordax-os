# Release Manifest Contract

Status: CANONICAL TOOLING CONTRACT — RELEASE SIGNING/PUBLICATION NOT YET AUTHORIZED

`tools/release-manifest` produces the exact unsigned manifest consumed by the release-signing boundary and release-acquisition agent.

For schema `prototype-ordax.release-manifest/1`, the manifest contains exactly one artifact:

```text
name=system.tar
role=system
```

The generator pins:

- source repository;
- exact lowercase 40-hex source commit;
- `release_id` equal to the source commit;
- CI recipe identity;
- canonical HTTPS artifact URL;
- SHA-256 of the exact `system.tar` bytes;
- exact artifact size.

## Fail-closed input policy

- the artifact must be a regular non-symlink file named `system.tar`;
- artifact size must be greater than zero and no larger than the release-agent bound;
- the artifact URL must be absolute HTTPS without credentials or fragment;
- source commit must be lowercase 40-hex;
- output is create-only and never overwritten;
- output parent paths may not traverse symlinks.

The tool does not sign the manifest and does not publish any release.

## Versioning and evolution

`release-manifest/1` is intentionally small and its semantics are immutable. It means one complete `system.tar` addressed by the exact source commit. Existing v1 consumers must never discover that the same schema silently acquired a different meaning.

Future features extend the protocol through new schema versions rather than by weakening v1:

- delta updates require a new manifest schema;
- multiple release artifacts require a new manifest schema;
- new required fields require a new manifest schema;
- consumers explicitly opt into schemas they understand and fail closed on an unknown required schema;
- old and new schemas may coexist during an explicit migration window;
- while delta delivery is optional, a verified full-release fallback remains available;
- release trust rotation uses its own explicit versioned transition protocol rather than silently replacing the meaning of the current trust anchor.

The machine-readable authority for these compatibility rules is `docs/contracts/release-protocol.json`.

The generator, signer and acquisition agent remain independent fail-closed owners, while CI prevents their schema assumptions from drifting. V1, v2, v3 and v4 stay explicit compatibility boundaries; shared protocol code should only be extracted when it reduces real duplication without weakening those versioned contracts.

## Portable USB v2 manifest

Schema `prototype-ordax.release-manifest/2` is now generated explicitly with `--manifest-schema 2`. It is not a reinterpretation of v1.

The v2 shape is deliberately narrow:

```text
product_mode=usb
storage_profile=portable-usb-v2
runtime_format=erofs
artifact.name=system.erofs
artifact.role=system-image
```

The generator still defaults to schema v1. V1 continues to require exactly `system.tar` with role `system` and contains none of the portable-v2 identity fields.

The v2 generator, signer and non-activating acquisition/materialization path are implemented. Public publication and legacy `current` activation remain disabled; portable boot handoff is a separate proof boundary and does not turn v2 materialization into production authorization.

## Portable USB v3 manifest with offline Surface runtime

Schema `prototype-ordax.release-manifest/3` is the explicit multi-artifact successor to v2. It keeps the same USB/EROFS product identity and the same signed envelope/trust boundary, but pins two artifacts in canonical order:

```text
artifacts[0].name=system.erofs
artifacts[0].role=system-image
artifacts[1].name=native-surface-runtime.erofs
artifacts[1].role=surface-runtime
```

Generation uses `--manifest-schema 3` plus `--runtime-artifact` and `--runtime-artifact-url`. The signer accepts v3 only when both artifacts, roles and order match this contract exactly. V1 and v2 remain byte/semantic compatibility boundaries and are not reinterpreted.

The acquisition agent materializes the release system image under the source commit while storing the verified Surface runtime by SHA-256:

```text
/ordax-data/.ordax/releases/<source_commit>/
├─ system.erofs
├─ surface-runtime.sha256
├─ release-manifest.json
└─ release-envelope.json

/ordax-data/.ordax/runtimes/sha256/<runtime_sha256>/
└─ native-surface-runtime.erofs
```

A later system release that references the same already verified runtime hash reuses those exact bytes instead of downloading the runtime again. This is content-addressed reuse, not a mutable shared runtime. The v3 materializer still creates no `current` pointer, performs no boot handoff and does not authorize physical USB publication.


## Portable USB v4 manifest with native local AI runtime

Schema `prototype-ordax.release-manifest/4` extends v3 without changing its
existing meaning. It adds a third canonical artifact:

```text
artifacts[0] = system.erofs                  role=system-image
artifacts[1] = native-surface-runtime.erofs  role=surface-runtime
artifacts[2] = local-ai-runtime.erofs        role=local-ai-runtime
```

The manifest also requires a signed `local_ai` binding derived from
`system/services/local-ai/source-lock.json`. That binding pins the source-lock
SHA-256, llama.cpp source repository and commit, engine license, model identity,
upstream revision, exact model SHA-256/size and model license. The signer and
acquisition agent independently validate this v4 shape and fail closed on a
missing, malformed or reordered AI payload.

The local AI runtime is stored separately from the Surface runtime:

```text
/ordax-data/.ordax/releases/<source_commit>/
├─ system.erofs
├─ surface-runtime.sha256
├─ local-ai-runtime.sha256
├─ release-manifest.json
└─ release-envelope.json

/ordax-data/.ordax/ai-runtimes/sha256/<runtime_sha256>/
└─ local-ai-runtime.erofs
```

The v4 source protocol and verification path are implemented, but the real
llama.cpp + Qwen runtime EROFS is still a separate reproducible-build/promotion
gate. V4 support does not itself claim that those bytes have been built,
published or written to physical Stable/MVP media.

## Canonical pipeline

```text
system source
 -> deterministic system.tar
 -> release-manifest.json
 -> external Ed25519 signing boundary
 -> release-envelope.json
 -> canonical HTTPS release channel
 -> device verification
 -> transactional materialization
 -> atomic current activation
```

Each stage independently validates the input it owns. No stage may assume that success in a previous stage replaces its own checks.

## Current state

```text
RELEASE_MANIFEST_TOOLING_IMPLEMENTED=YES
SYSTEM_TAR_HASH_AND_SIZE_PINNED=YES
SOURCE_COMMIT_PINNED=YES
RELEASE_PROTOCOL_VERSIONING_CONTRACT=YES
RELEASE_MANIFEST_V1_SEMANTICS_IMMUTABLE=YES
RELEASE_MANIFEST_V2_SEMANTICS_IMMUTABLE=YES
RELEASE_MANIFEST_V3_MULTI_ARTIFACT_RUNTIME=YES
V3_RUNTIME_CONTENT_ADDRESSED_REUSE=YES
RELEASE_MANIFEST_V4_LOCAL_AI_RUNTIME=YES_SOURCE
V4_LOCAL_AI_SOURCE_LOCK_BINDING=YES
V4_LOCAL_AI_CONTENT_ADDRESSED_REUSE=YES_SOURCE
V4_REAL_LOCAL_AI_RUNTIME_BUILT=PASS_CI
V3_ACTIVATION_ENABLED=NO
V4_ACTIVATION_ENABLED=NO
DELTA_REQUIRES_NEW_MANIFEST_SCHEMA=YES
MULTI_ARTIFACT_REQUIRES_NEW_MANIFEST_SCHEMA=YES
CANONICAL_RELEASE_TRUST_RESOLVED=YES
CANONICAL_STABLE_V4_RELEASE_SIGNED=PENDING
PRODUCTION_RELEASE_PUBLISHED=NO
PHYSICAL_USB_WRITE_EXECUTED=NO
```
