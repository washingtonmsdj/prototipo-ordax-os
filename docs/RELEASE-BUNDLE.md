# Release Bundle Contract

Status: CANONICAL TOOLING CONTRACT — RELEASE PUBLICATION NOT YET AUTHORIZED

OrdaX release acquisition v1 consumes exactly one signed artifact:

```text
system.tar
```

The archive materializes the normal post-bootstrap system under:

```text
/ordax/releases/<commit>/system/
```

The bootstrap activates that immutable release through `/ordax/current` only after the signed manifest, artifact hash, archive structure and materialized tree pass verification.

## Bundle source contract

The bundler receives a source root containing `system/` and emits a new `system.tar`. For the Native product release, that source root is prepared by `tools/native-release-assembly/build.py`: it starts from the canonical shared `system/` source and injects only explicitly contracted, prebuilt Native release tools plus their provenance. The bundler itself remains platform-neutral and does not compile or invent Native content.

Required:

- `system/` is a real directory with mode `0755`;
- `system/entrypoint` exists, is a non-empty regular file and has mode `0755`;
- directories are `0755`;
- regular files are `0644` or `0755`;
- symlinks, hardlinks, devices and other special file types are forbidden;
- the output archive cannot be created inside the source `system/` tree;
- existing output is never overwritten.

The release acquisition agent independently enforces the same runtime safety boundary when extracting the archive. The bundler does not replace device-side verification.

## Determinism

`tools/release-bundle` normalizes archive metadata so identical input bytes, paths and modes produce byte-identical output:

- lexical path order;
- uid/gid `0`;
- empty user/group names;
- timestamp fixed to Unix epoch;
- no host-specific ownership metadata;
- canonical modes preserved;
- USTAR archive format.

CI builds the tool for Linux and Windows and proves two independent bundle invocations are byte-identical.

## Portable USB v2 EROFS candidate

The durable USB architecture needs a compressed read-only filesystem image, but the signed release protocol v1 must remain immutable. Therefore the repository now uses a compatibility bridge:

```text
canonical system/
 -> tools/release-bundle policy
 -> deterministic system.tar
 -> portable-release-image builder
 -> deterministic system.erofs candidate
```

`system.tar` remains the only artifact accepted by `release-manifest/1`, the v1 signer and the current acquisition agent. The EROFS candidate does **not** silently become a v1 release artifact.

`tools/portable-release-image/build.py` first revalidates the normalized tar metadata boundary, then creates `system.erofs` with fixed timestamp, fixed filesystem UUID, root ownership and LZ4 compression. CI must build the image twice and require byte-identical output, then run EROFS integrity verification.

This candidate does not publish, sign, activate or authorize physical media. A future portable release protocol must use a new manifest schema and explicit consumer support before the boot path may rely on `system.erofs`.

## Release boundary

This tooling does not publish a GitHub Release and does not sign a release envelope by itself.

The intended pipeline is:

```text
canonical system source
 -> deterministic system.tar
 -> SHA-256 + size
 -> release-manifest.json tied to exact source commit
 -> external Ed25519 signing boundary
 -> release-envelope.json
 -> publication to canonical HTTPS release channel
 -> bootstrap verification and transactional activation
```

A production release must not be published until the canonical public Ed25519 trust anchor has an explicitly owned private key outside Git and the release-signing gate validates that the external private key matches that trust anchor.

## Current state

```text
RELEASE_BUNDLE_TOOLING_IMPLEMENTED=YES
DETERMINISTIC_SYSTEM_TAR_CONTRACT=YES
DEVICE_SIDE_SAFE_EXTRACTION_IMPLEMENTED=YES
CANONICAL_SYSTEM_RUNTIME_COMPLETE=NO
CANONICAL_RELEASE_TRUST_RESOLVED=NO
PRODUCTION_RELEASE_PUBLISHED=NO
PHYSICAL_WRITE_AUTHORIZED=NO
```

`system/` remains the single source for the shared OrdaX product, but its native runtime entrypoint is not yet production-complete. The presence of bundle tooling must not be interpreted as a completed OrdaX release.
