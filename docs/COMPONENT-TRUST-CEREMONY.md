# Canonical Runtime Component Trust Ceremony

Status: **SOURCE FOUNDATION READY — OPERATOR CEREMONY PENDING — NO CANONICAL COMPONENT KEY PINNED**

This ceremony creates the trust identity used to authenticate independently
updated OrdaX runtime components such as Internet. It is intentionally separate
from whole-OS release trust.

Machine-readable authority:

`docs/contracts/runtime-component-trust-policy.json`

## Boundary

```text
external operator/signing host
  -> ordax-runtime-component-channel generate-key
  -> external PKCS#8 Ed25519 private key
  -> reviewed public runtime-component trust JSON
  -> encrypted recovery copy
  -> independent public derivation
  -> recovered-key signing proof
  -> public-only handoff
  -> repository pin of public trust only
```

The fixed first component key id is:

```text
ordax-runtime-components-v1
```

The future public anchor target is:

```text
repository: system/trust/runtime-components-ed25519.json
runtime:    /srv/ordax-system/trust/runtime-components-ed25519.json
```

No private component-signing key belongs in Git, the OrdaX USB, a public build
artifact, CI logs or chat.

## Trust separation

The component key must **not** reuse, copy or alias the whole-OS release key.

This separation allows the OS release authority and component publication
authority to evolve independently. Compromise or rotation of one trust domain
must not silently grant authority in the other.

CI may create disposable component keys only for protocol tests. A disposable
CI key can never satisfy the canonical component-trust gate.

## Required ceremony

The ceremony is an explicit operator action. Source support does not make a key
canonical.

Using a reviewed `ordax-runtime-component-channel` binary bound to an exact
reviewed source commit, generate the private key outside the repository:

```text
ordax-runtime-component-channel generate-key \
  --private-key <external-private-path>/runtime-component-private.pem \
  --trust <review-path>/runtime-components-ed25519.json \
  --key-id ordax-runtime-components-v1
```

Then derive the public trust independently into a second empty review path:

```text
ordax-runtime-component-channel derive-trust \
  --private-key <external-private-path>/runtime-component-private.pem \
  --out <second-review-path>/runtime-components-ed25519.json \
  --key-id ordax-runtime-components-v1
```

Require byte-identical public files and a 32-byte Ed25519 public key.

## Signing proof

Before pinning the public anchor, create a real-shaped test component package and
release descriptor using `release_mode=component-slot`. Sign it with the
candidate private key while supplying the candidate public trust explicitly:

```text
ordax-runtime-component-channel sign \
  --release runtime-component-release.json \
  --private-key <external-private-path>/runtime-component-private.pem \
  --trust <review-path>/runtime-components-ed25519.json \
  --key-id ordax-runtime-components-v1 \
  --out runtime-component-envelope.json

ordax-runtime-component-channel verify-envelope \
  --envelope runtime-component-envelope.json \
  --trust <review-path>/runtime-components-ed25519.json
```

A private/public mismatch must fail closed.

## Recovery proof

Before the public anchor becomes eligible for Git:

1. create at least one encrypted recovery copy outside the repository;
2. restore a copy to a distinct temporary private path;
3. derive public trust from the restored copy;
4. require byte identity with both earlier public derivations;
5. sign a second protocol-shaped component release with the recovered key;
6. verify that envelope using only the candidate public trust;
7. remove the temporary restored private key according to the operator custody procedure.

The repository records only non-secret evidence. Never record private key bytes,
a private-key hash, seed, recovery password or encrypted backup contents.

## Public anchor pin

Only after generation, independent derivation, custody and recovery proof pass
may the reviewed public JSON be committed at:

`system/trust/runtime-components-ed25519.json`

Pinning the public anchor means only:

```text
CANONICAL_COMPONENT_TRUST_ANCHOR_PINNED=YES
```

It does **not** mean:

```text
COMPONENT_PUBLISH_ALLOWED=YES
COMPONENT_SLOT_ACTIVATION_ALLOWED=YES
PHYSICAL_WRITE_ALLOWED=YES
```

Publication still requires a reviewed signing workflow. Production activation
still requires pending probation execution, runtime health, atomic promote and
rollback proof. Physical USB authorization remains a completely separate gate.

## Current state

Today:

```text
CANONICAL_COMPONENT_TRUST_ANCHOR_PINNED=NO
COMPONENT_PUBLISH_ALLOWED=NO
PRODUCTION_COMPONENT_SLOT_ACTIVATION_ALLOWED=NO
```

The signed component protocol, immutable slots, activation state machine and
verified runtime-file reader exist in source. The operator trust ceremony is the
next identity gate; it must not be silently replaced by a random CI key.
