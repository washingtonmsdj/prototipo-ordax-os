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

## MCP boundary

The existing Control Plane MCP/OAuth tables belong to the development/operator authority. Product MCP for end users must use a separate client/token authority even if it reuses the same implementation patterns.
