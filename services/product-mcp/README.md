# OrdaX Product MCP Gateway

Status: ARCHITECTURE FOUNDATION / NOT DEPLOYED

This service boundary is for **end-user** AI clients such as ChatGPT, Grok and future MCP-compatible assistants.

It is not the existing owner/development Control Plane authority.

## Connection model

```text
ChatGPT / Grok / other MCP client
        |
        | OAuth 2.1 + user authorization
        v
OrdaX Product MCP Gateway
        |
        +-- OrdaX account/session
        +-- entitlement resolution
        +-- Space membership
        +-- project capability grants
        +-- audit receipt
        |
        +-- OrdaX-local project adapter
        +-- GitHub App adapter
```

The external AI client authenticates to **OrdaX**. The user's ChatGPT/xAI identity is not the canonical OrdaX user ID.

## GitHub is a separate connection

A user does not need to hand a GitHub token to ChatGPT/Grok through OrdaX.

The intended flow is:

1. user signs in to OrdaX;
2. user installs/authorizes the OrdaX GitHub App;
3. user selects the repositories the App may access;
4. OrdaX stores only the connection metadata in the public product schema;
5. the GitHub credential/installation token is held by a server-side secret owner;
6. a Space links only to selected repository IDs;
7. an external AI client authenticates to OrdaX MCP;
8. MCP tools resolve the caller -> account -> Space -> project -> permitted operation.

Direct GitHub connectors inside ChatGPT/Grok remain independent integrations and are not required for the OrdaX connector.

## Initial read-only MCP tools

The first public tool set should be intentionally small:

- `spaces.list`;
- `projects.list`;
- `project.read_context`;
- `memory.search_authorized`;
- `artifacts.list`.

Do not expose a generic filesystem, shell, SQL or GitHub token tool.

## Mutating tools

Future write actions must have a separate capability from read actions. A proposed change flow may later expose operations such as create branch, write selected file or open a pull request, but only with:

- explicit Space/project scope;
- current user authorization;
- entitlement where applicable;
- approval policy;
- idempotency;
- audit receipt;
- revocation.

## OAuth

Remote MCP clients use an OrdaX-owned OAuth 2.1 authorization boundary with PKCE for public clients. Client registration/metadata must follow the requirements of the consuming MCP platform.

The existing Control Plane `ordax_mcp_*` tables demonstrate useful patterns for codes, token hashes, expiration and revocation, but their credentials/authority must **not** be reused for product users.

## Secret boundary

Never return or place in Memory:

- GitHub installation tokens;
- OpenAI/xAI API keys;
- Supabase service-role keys;
- release keys;
- device private credentials.

The MCP gateway receives a scoped OrdaX authorization decision, not raw upstream credentials.
