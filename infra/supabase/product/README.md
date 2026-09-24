# Supabase product foundation

This directory owns the source-controlled schema used by the OrdaX product domain when Supabase is the current backend adapter.

It is deliberately separate from development-device control tables already present in the `ordax-control-plane` project.

## Boundaries

Product tables own account bootstrap, Spaces, server-authoritative entitlement grants, profile-pack catalog metadata, memory metadata/semantic index and project-connection metadata.

They do not store:

- GitHub access tokens;
- OpenAI/xAI credentials;
- release signing keys;
- device private keys;
- recovery secrets;
- generic shell credentials.

External provider secrets require a dedicated server-side secret owner and are never exposed through public Data API tables.

## Migration 0001

`migrations/0001_product_foundation.sql`:

- bootstraps `ordax_accounts` from Supabase Auth;
- creates Spaces and membership;
- creates server-readable entitlement grants;
- creates versioned Profile Packs;
- creates provider-neutral Memory + derived pgvector embeddings;
- creates project-connection metadata suitable for future GitHub App installations;
- enables RLS on every public table;
- grants no anonymous access;
- seeds only **draft** Developer and Legal-BR pack descriptors, not legal knowledge.

The Legal-BR row is architecture metadata only. It does not claim current legal coverage.

## Mutation authority

Authenticated clients do not receive direct Data API authority to create or mutate Spaces, memberships, cloud Memory, project connections, Profile Pack assignments or entitlement grants.

`0004_server_authoritative_mutations.sql` revokes those client writes so future quotas, plan checks, approvals and audit receipts cannot be bypassed by calling Supabase directly. Product services/gateways own those mutations with server-side authority. The only direct authenticated account mutation retained is the user's own `display_name`.

## Catalog and semantic-index visibility

`0005_private_indexes_and_active_pack_catalog.sql` keeps Profile Pack drafts backend-only and exposes only `state=active` pack rows to authenticated clients. It also removes direct client SELECT access from `ordax_memory_embeddings`: semantic vectors are an internal derived search index, not user-facing Memory data.

## MCP boundary

The existing Control Plane MCP/OAuth tables belong to the development/operator authority. Product MCP for end users must use a separate client/token authority even if it reuses the same implementation patterns.
