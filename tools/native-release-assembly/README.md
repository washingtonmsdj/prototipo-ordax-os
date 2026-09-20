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
      └─ .ordax/native-release-tools.json
 -> tools/release-bundle
 -> system.tar
 -> existing release manifest/signing/acquisition pipeline
```

## Security boundary

The injected helper is the **read-only target discovery and exact target-plan helper** required by the OrdaX USB installer. It has no Native physical APPLY implementation and no authorization to mutate a block device.

The assembly recipe:

- cross-compiles the helper as `linux/amd64` with `CGO_ENABLED=0`;
- uses the repository Go module under `tools/creator`;
- emits the helper at `system/bin/ordax-native-install-targets`;
- binds its SHA-256, size, mode, role, source package and source commit into release-local provenance;
- refuses an output tree inside repository source;
- leaves final archive determinism to `tools/release-bundle`;
- leaves release identity and signature authority to the existing release manifest/signing pipeline.

No compiler or source checkout is required on the end-user OrdaX USB.
