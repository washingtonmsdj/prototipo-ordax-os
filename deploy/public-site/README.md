# Public site same-origin adapter

This directory contains the first production-shaped hosting adapter for the
OrdaX public portal.

It is intentionally host-neutral: Nginx serves the deterministic
`public-site` artifact and forwards only `/auth/*` and `/sync/*` to the
deployed OrdaX account gateway. Browser code therefore talks only to its own
origin and never learns Supabase credentials or provider-specific APIs.

## Boundary

- static artifact root: `/srv/ordax-public-site`;
- local listener: `127.0.0.1:8080`;
- public HTTPS/TLS termination: external to this adapter;
- account upstream: OrdaX `ordax-account-gateway`;
- identity routes: `/auth/*`;
- synchronization routes: `/sync/*`;
- upstream cookies and HTTP status codes are preserved.

The loopback listener is deliberate. A production TLS terminator on the same
host should be the only public listener and should forward the public origin to
this adapter. Do not expose port 8080 directly.

The adapter applies the security and cache policy from
`docs/contracts/public-site-deployment.json`. Login remains disabled in the
public-site runtime configuration until legal readiness and Auth hardening are
complete; having the route available does not activate account UX.

No service-role key, password, bearer token or user secret belongs in this
directory.
