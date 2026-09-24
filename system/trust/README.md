# Runtime component public trust

This directory intentionally contains no canonical component trust anchor until
the operator ceremony and encrypted-recovery proof have completed.

The future canonical public anchor path is:

```text
system/trust/runtime-components-ed25519.json
```

Only public material may exist here. The matching Ed25519 private key is owned
outside Git and outside the device.

Promotion is performed only from the public handoff created by the component
trust recovery ceremony. Source support for the promoter does not mean that the
anchor is pinned, publication is enabled or component-slot activation is enabled.
