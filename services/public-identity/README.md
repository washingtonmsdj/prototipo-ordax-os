# OrdaX Public Identity Gateway

Status: GATEWAY CORE IMPLEMENTED / DEDICATED SUPABASE TARGET PREPARED / PUBLIC PROVIDER NOT ENABLED

This directory defines the backend responsibility that will sit behind the public site's login and registration entry points.

It is intentionally separate from:

- `sites/public/`, which is static presentation;
- `system/services/account/`, which owns product-side account semantics;
- any specific identity vendor.

## Intended flow

```text
sites/public/login or cadastro
 -> same-origin /auth/* entry
 -> OrdaX public identity gateway
 -> provider adapter
 -> canonical OrdaX account/session
```

The public page must not become the identity authority. The gateway owns provider handoff, callback validation, session establishment, logout and account bootstrap.

## Required routes

The gateway core in `gateway.py` now exposes this contract:

```text
GET  /auth/login
POST /auth/login
GET  /auth/register
POST /auth/register
POST /auth/logout
GET  /auth/session
GET  /sync/objects
POST /sync/mutate
```

GET login/register routes lead only to the canonical same-origin pages. Credential POST, account sync and authenticated session behavior fail closed when runtime provider configuration is absent. `/auth/session` remains anonymous/unconfigured in that state. The gateway owns no public listener; deployment stays external and same-origin.

The public site configuration therefore keeps login/register disabled until these routes are deployed behind the same origin. The runtime shape is pinned in `docs/contracts/public-identity-gateway.json`.

## Session policy

Production sessions must:

- use secure transport;
- prefer HttpOnly cookies so browser JavaScript does not own bearer tokens;
- use Secure cookies in production;
- use SameSite=Lax by default unless a reviewed flow requires otherwise;
- validate callback state/PKCE data;
- support revocation;
- avoid placing tokens in URLs, logs or analytics.

## Provider independence

A provider adapter may initially use Supabase Auth, but public routes and account semantics must remain OrdaX-owned.

The provider may not redefine:

- one-account-across-product-modes;
- entitlements;
- sync data classification;
- device/session revocation semantics;
- account deletion/export rules.

## Current provider decision

The dedicated Supabase project `ordax-control-plane` is now the selected pre-MVP provider target. The product-domain foundation from `infra/supabase/product/migrations/0001_product_foundation.sql` has been applied there and owns the single `ordax_accounts` bootstrap.

The previously suggested shared `Ordax-2026-1` project remains rejected for OrdaX identity because it already has another product's `public.profiles` lifecycle and an unrelated signup trigger.

The provider-specific email/password adapter in `supabase_password.py` and account-sync adapter in `supabase_sync.py` use only the Supabase publishable key plus the authenticated user's bearer token. Passwords are transient request inputs; provider tokens stay in HttpOnly cookies owned by the gateway and are never returned to Surface JavaScript.

**Target prepared does not mean public identity enabled.** The gateway still fails closed until all of the following are true:

- a same-origin production deployment owns the session cookie;
- the Supabase runtime configuration is supplied outside source;
- Auth redirect/email settings are reviewed;
- leaked-password protection and the chosen password/passkey policy are hardened;
- public privacy/terms readiness is complete;
- login/register routes pass end-to-end tests.

The product domain remains provider-neutral, so the Supabase project can later be migrated without changing Surface account semantics.

## Non-goals of this foundation

- no production identity provider is enabled;
- no password form is added to the static site;
- no publishable/service key is committed;
- no migration is applied to an existing Supabase project;
- no account is claimed to exist until the provider and gateway are live.
