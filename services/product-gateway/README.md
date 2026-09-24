# OrdaX Product Project Gateway

Status: **SOURCE FOUNDATION / FAIL-CLOSED / NOT DEPLOYED**

This gateway owns future server-authoritative product mutations shared by OrdaX
Web, Mobile and Product MCP. It is deliberately separate from the owner/development
Control Plane and from the public identity provider adapter.

The core currently exposes:

- `GET /product/status`;
- `POST /product/projects`;
- `POST /product/project-bindings`;
- `POST /product/remote-grants`.

Mutation routes require an authenticated OrdaX session, same-origin/CSRF
protection, JSON, a bounded payload and an idempotency key. The server-side
authority must return a receipt proving entitlement, approval and audit checks.

The default session resolver is anonymous and the default authority is disabled,
so source presence **does not enable public mutations**.

## Boundaries

The browser never receives a Supabase service-role key. Device bindings use an
opaque local project reference rather than a filesystem path. The gateway rejects
generic shell, raw disk, release-signing-key, implicit admin, cross-user/cross-Space
memory and unscoped GitHub authority before an adapter is called.

A later Supabase adapter may implement this interface using the already-applied
product schema, but the HTTP/product contract remains OrdaX-owned so the backend
provider can be migrated without changing Web/Mobile/MCP semantics.
