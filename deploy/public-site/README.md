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
- upstream cookies and HTTP status codes are preserved;
- every proxied account/sync request is marked with `X-OrdaX-Public-Site: 1`.

The loopback listener is deliberate. A production TLS terminator on the same
host should be the only public listener and should forward the public origin to
this adapter. Do not expose port 8080 directly.

The adapter applies the security and cache policy from
`docs/contracts/public-site-deployment.json`. The marker is part of the
server-side activation boundary: the deployed OrdaX gateway rejects public-site
login, registration and synchronization while its public account gate is
disabled. This means hiding the HTML forms is not the security boundary.

Login remains disabled in the public-site runtime configuration and in the
gateway's public-site gate until legal readiness, Auth hardening and actual
same-origin HTTPS deployment are complete. Native/USB account traffic does not
carry the public-site marker and remains a separate real account path.

No service-role key, password, bearer token or user secret belongs in this
directory.
