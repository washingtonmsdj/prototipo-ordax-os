# Release Pipeline Contract

Status: CI PROOF ONLY — NOT A PRODUCTION RELEASE OR PHYSICAL AUTHORIZATION

The release pipeline is intentionally split into small owners with independent validation. The Native assembly step is a build-time composition owner, not a new runtime channel:

```text
shared system source + Native release helper source
 -> tools/native-release-assembly
 -> staged Native system/
 -> tools/release-bundle
 -> system.tar
 -> tools/release-manifest
 -> release-manifest.json
 -> tools/release-signing + explicit trust input
 -> release-envelope.json
 -> bootstrap/release-acquisition
 -> verified transactional materialization
 -> atomic current activation
```

## Native release assembly

The shared product source remains `system/`. Native-only prebuilt executables that are required by the USB/Native capability boundary are injected into a temporary staged `system/` tree by `tools/native-release-assembly/build.py` before bundling.

For the MVP installer this currently adds exactly one binary:

```text
system/bin/ordax-native-install-targets
```

Its source remains under the shared Creator Core/Linux adapter. CI cross-compiles it as a static `linux/amd64` binary, records SHA-256/size/mode/source package/source commit in `system/.ordax/native-release-tools.json`, and then the ordinary deterministic bundler includes those bytes in `system.tar`.

There is no separate helper download channel and no compilation on the user's device. Because the helper is inside `system.tar`, it is covered by the same release manifest hash and Ed25519 envelope as the rest of the Native system release. Its current role is read-only discovery/target-plan binding; physical APPLY remains unauthorized.

## CI integration proof

`.github/workflows/release-pipeline.yml` composes the real tools against an isolated temporary system fixture. It proves:

```text
SOURCE_TO_BUNDLE=PASS
BUNDLE_TO_MANIFEST=PASS
MANIFEST_TO_SIGNED_ENVELOPE=PASS
SIGNED_ENVELOPE_TO_AGENT=PASS
```

The workflow uses a CI-only ephemeral Ed25519 key. The private key exists only under the runner temporary directory, is removed before completion and is never uploaded.

The proof deliberately does **not**:

- create or rotate the canonical release key;
- satisfy `bootstrap-release-trust`;
- publish a GitHub Release;
- move the canonical `latest` release pointer;
- authorize Creator APPLY;
- write or repartition physical media.

## Production boundary

Production release publication remains blocked until all of these are true:

```text
CANONICAL_SYSTEM_RUNTIME_COMPLETE=YES
CANONICAL_RELEASE_TRUST_RESOLVED=YES
SIGNER_PRIVATE_TRUST_MATCH=PASS
RELEASE_ARTIFACT_IDENTITY=PASS
RELEASE_ENVELOPE_VERIFY=PASS
PUBLICATION_POLICY=PASS
```

The temporary CI system fixture is only a protocol fixture. It is not the OrdaX product runtime and must never be promoted as a user release.
