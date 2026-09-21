# Release Trust Bootstrap

Status: CANONICAL PUBLIC TRUST PINNED — PHYSICAL WRITE NOT AUTHORIZED

This owner contains only the canonical public trust material required to authenticate signed OrdaX release envelopes. The exact anchor is pinned by `docs/contracts/minimal-bootstrap.json`; no private signing material belongs here.

Canonical runtime path:

```text
/ordax/bootstrap/trust/release-ed25519.json
```

The release acquisition agent expects schema `prototype-ordax.release-trust/1`, a stable `key_id` and a 32-byte Ed25519 public key encoded as base64.

## Security boundary

- private release-signing keys are never stored in this repository;
- private signing keys are never shipped in the Creator payload or device bootstrap;
- the pinned public trust anchor is versioned only because its corresponding private signing key has an explicit owner outside the repository and recovery was cryptographically proven;
- a random, disposable or CI-ephemeral key must not be promoted as the physical trust anchor;
- public trust promotion does not authorize physical media mutation; Creator physical authorization remains blocked until fresh explicit Stable/MVP owner authorization and the remaining physical gates pass.

`tools/release-signing/` provides standard-library tooling to generate an external PKCS#8 Ed25519 key during an explicit operator ceremony, derive the public trust JSON from an existing external private key, and sign exact release-manifest bytes. The tool does not make a key canonical merely by generating it.

The signer is fail-closed against trust drift: `sign` requires the public trust JSON and refuses to create an envelope unless the supplied external private key derives exactly the same Ed25519 public key and the requested `key_id` equals the trust anchor `key_id`.

## Canonicalization result

The canonicalization gate has passed for the first controlled prototype. The public anchor is present at `bootstrap/trust/release-ed25519.json`, and the minimal bootstrap binds its exact SHA-256. The non-secret ceremony evidence records:

```text
PRIVATE_KEY_CUSTODY_OWNER=<explicit owner/system outside Git>
PRIVATE_KEY_RECOVERY_POLICY=DEFINED
PRIVATE_KEY_ROTATION_POLICY=DEFINED
KEY_ID=<stable id>
PUBLIC_KEY_DERIVED_FROM_CUSTODIED_PRIVATE_KEY=YES
PUBLIC_KEY_FINGERPRINT_REVIEWED=YES
SIGNER_PRIVATE_TRUST_MATCH=PASS
PRIVATE_KEY_IN_GIT=NO
```

The public file was derived from the actual external private key, independently recovered from an encrypted backup, and the recovered key produced a signing proof verified against this public anchor. The exact public bytes are now bound in `docs/contracts/minimal-bootstrap.json`.

A CI-only test key may still be used by isolated protocol tests, but it remains test-scoped and can never replace or satisfy the canonical physical bootstrap identity.

See `docs/RELEASE-SIGNING.md`.

## Rotation protocol candidate

The immutable bootstrap anchor remains the initial root of release trust. A separate signed transition protocol now exists in source so the currently trusted release key can authorize a successor without changing release-envelope semantics.

The protocol binds an exact current-trust SHA-256, monotonic sequence, successor key id/public key and canonical successor-trust SHA-256, then requires an Ed25519 signature by the current trusted key. Signer and release-agent verification exist and fail closed.

This is **not yet device activation**. No installed OrdaX may silently replace its effective trust anchor from this protocol until persistent monotonic trust state, atomic activation and bootstrap effective-trust selection are implemented and proven. The first controlled physical MVP proof does not depend on production rotation.
