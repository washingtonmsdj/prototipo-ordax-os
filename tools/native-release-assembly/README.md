# Native Release Assembly

Status: CANONICAL BUILD RECIPE FOR THE NATIVE SYSTEM RELEASE — PUBLIC RELEASE STILL GATED

`tools/native-release-assembly/build.py` prepares the source tree consumed by the existing deterministic `tools/release-bundle` tool.

It does not replace the shared `system/` source and does not introduce a second release format.

```text
repository system/
 + repository Creator Core / Linux Native target helper source
 -> Native release assembly
 -> staged system/
      ├─ shared product source
      ├─ bin/ordax-native-install-targets
      ├─ bin/ordax-runtime-component-channel
      └─ .ordax/native-release-tools.json
 -> tools/release-bundle
 -> system.tar
 -> existing release manifest/signing/acquisition pipeline
```

## Security boundary

The injected helpers have separate responsibilities:

- `ordax-native-install-targets` is the **read-only target discovery and exact target-plan helper** required by the OrdaX USB installer. It has no Native physical APPLY implementation and no authorization to mutate a block device.
- `ordax-runtime-component-channel` verifies signed component releases/slots and owns the fail-closed component activation-state machine. It has no private signing key, no component publishing authority, and source presence alone does not enable slot serving.

The assembly recipe:

- cross-compiles the helper as `linux/amd64` with `CGO_ENABLED=0`;
- uses the repository Go modules under `tools/creator` and `tools/runtime-component-channel`;
- emits the helpers at `system/bin/ordax-native-install-targets` and `system/bin/ordax-runtime-component-channel`;
- binds each helper's SHA-256, size, mode, role, source package and source commit into release-local provenance;
- refuses an output tree inside repository source;
- leaves final archive determinism to `tools/release-bundle`;
- leaves release identity and signature authority to the existing release manifest/signing pipeline.

No compiler or source checkout is required on the end-user OrdaX USB.
