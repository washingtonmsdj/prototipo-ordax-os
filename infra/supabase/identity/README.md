# Supabase identity adapter preparation

This folder owns provider-specific preparation for the Supabase-backed OrdaX identity adapter.

The **account schema no longer lives here**. Account bootstrap, Spaces, entitlements, Profile Packs and Memory are owned by the product-domain migrations in `infra/supabase/product/`. This avoids two competing profile tables or two signup triggers.

## Current target

The dedicated `ordax-control-plane` Supabase project is the selected pre-MVP backend target. Its product foundation migration has been applied, but the public identity gateway remains fail-closed until deployment, Auth hardening and legal-readiness gates are complete.

The previously considered shared `Ordax-2026-1` project is not an identity target because it already has another product's `public.profiles` lifecycle and a signup trigger on `auth.users`.

## Safety boundary

Before changing an identity target:

1. run `preflight.sql` read-only;
2. reject unrelated signup triggers on `auth.users`;
3. ensure `public.ordax_accounts` belongs to the canonical product migration;
4. keep account/domain semantics provider-neutral;
5. review redirect URLs, email delivery, passkeys/password policy and leaked-password protection separately;
6. do not expose login/registration until same-origin session ownership and legal readiness are complete.

## Canonical product migration

The current account bootstrap is:

`infra/supabase/product/migrations/0001_product_foundation.sql`

It creates `public.ordax_accounts` and the single OrdaX product signup trigger together with the other pre-MVP product-domain tables.

Do not recreate `ordax_profiles`.

## Secrets

Do not commit service-role keys, JWT signing secrets, SMTP credentials, OAuth client secrets, provider access tokens or private redirect-state keys.

Browser-facing publishable configuration, when activated, must enter through runtime/deployment configuration rather than becoming a product secret.
