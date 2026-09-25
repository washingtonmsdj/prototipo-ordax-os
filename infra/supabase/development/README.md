# Supabase development authority

This directory owns source-controlled extensions to the **engineering/development**
authority hosted in the same Supabase project currently named
`ordax-control-plane`.

It is deliberately separate from `infra/supabase/product/`.

## Authority boundary

Sharing one backend project does **not** merge privileges:

- development device credentials authenticate only engineering/device jobs;
- product account/device credentials do not authenticate engineering jobs;
- development credentials do not authenticate product users;
- Product MCP/Web/Mobile never receive development operator credentials;
- product tables such as `ordax_product_devices` are not aliases for
  engineering `ordax_devices`.

## Device Agent adapters

The first extension owned here is
`20260925193000_device_agent_blender_adapter_v1.sql`.

It adds `ordax.dev.adapter.invoke` to the existing DEVELOPMENT queue as a
closed-world envelope. Version 1 accepts only:

- `adapter = "blender"`;
- an `action` beginning with `blender.`;
- an opaque registered project slug;
- a bounded JSON object payload.

The Windows OrdaX Device Agent remains the final action allow-list. The database
does not grant generic shell, arbitrary scripts, raw disk, release signing or
SYSTEM authority through this adapter capability.

The extension is not a bootstrap dependency and does not change Stable/MVP USB
promotion gates.

## Runnerless Windows recovery

`ordax-development-device-identify` is the narrow recovery endpoint for an
already-enrolled engineering machine whose local Device Agent still has its
device token but no longer has a current v2 device id/settings file.

The endpoint:

- accepts only the existing `X-Ordax-Device-Token`;
- stores/logs no raw token;
- resolves exactly one active credential;
- requires the referenced device to remain in `developer` mode;
- returns only the canonical `device_id` and protocol identity;
- grants no new scope and creates no credential.

This lets the Windows external bootstrap recover `development-v2` and register
approved local project slugs without requiring a GitHub self-hosted runner.
GitHub OIDC remains the preferred path for issuing a brand-new credential.
