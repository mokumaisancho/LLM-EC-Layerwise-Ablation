# ChatGPT Plus Attachment Path for Generic Binary Ingress MCP

Date: 2026-10-01

## Current server state

The server-side problem is resolved.

Render endpoint:

`https://generic-binary-ingress-mcp.onrender.com/mcp`

Verified hosted qualification:

- full 397,808,192-byte Qwen2.5-0.5B-Instruct Q4_K_M GGUF fetch;
- exact SHA-256 match: `6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653`;
- Protected Resource Metadata;
- Authorization Server Metadata;
- OAuth 2.1 authorization code + PKCE S256;
- Dynamic Client Registration;
- RFC 9207 issuer identification;
- `offline_access` and refresh token issuance;
- Bearer-authenticated MCP initialize;
- `tools/list`;
- `artifact_fetch`;
- `artifact_delete`.

The hosted E2E self-test passed before being disabled for normal operation.

## Direct custom MCP attachment

Current OpenAI documentation checked on 2026-10-01 describes direct custom MCP developer mode as available to Business and Enterprise/Edu. Pro can connect read/fetch MCPs in developer mode. Plus is not listed for direct custom MCP developer mode.

Therefore direct attachment of the Render MCP from the current Plus account should be treated as a product-plan boundary unless the UI exposes Developer mode for this account.

If Developer mode is present despite the documented plan boundary, use:

- MCP URL: `https://generic-binary-ingress-mcp.onrender.com/mcp`
- Authentication: OAuth
- OAuth discovery is automatic from:
  - `/.well-known/oauth-protected-resource`
  - `/.well-known/oauth-authorization-server`
- Authorization password: stored only as a Render secret; do not commit it.

## Plus-compatible route to test: ChatGPT Sites

Current OpenAI documentation states:

- ChatGPT Sites is available in public beta for Plus and Pro accounts;
- a Site can host an MCP server used through a plugin;
- hosting a plugin with ChatGPT Sites is available to all plans;
- a Site may connect to an external MCP server where the required permissions/features are available.

Target architecture:

`ChatGPT plugin -> ChatGPT Site -> external Render MCP -> arbitrary public binary -> artifact resource`

This should be tested before considering a plan upgrade.

## Required Site configuration

Ask ChatGPT Sites to create a private Site/plugin bridge whose only external service is:

`https://generic-binary-ingress-mcp.onrender.com/mcp`

The Site/plugin must expose the existing MCP tools without reimplementing transport logic:

- `artifact_fetch`
- `artifact_info`
- `artifact_chunk_link`
- `artifact_delete`

Do not proxy arbitrary URLs in the Site itself. The Render MCP remains responsible for SSRF checks, redirects, size gates, hashing, TTL and artifact storage.

## Acceptance criteria for Plus attachment

1. The Site connects to the external Render MCP using OAuth.
2. Plugin installation succeeds on the Plus account.
3. `tools/list` exposes the artifact tools.
4. A small artifact fetch succeeds from a normal ChatGPT conversation.
5. Qwen2.5-0.5B GGUF fetch succeeds through the plugin path.
6. Chunks can be read/materialized by the ChatGPT execution environment.
7. Reconstructed GGUF SHA equals `6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653`.
8. llama.cpp smoke inference succeeds.
9. Phase 1 135M vs 0.5B comparison resumes without changing fixture, grammar, scoring or EC control rules.

## Fallback order

1. ChatGPT Sites plugin bridge on Plus.
2. Direct custom MCP only if Developer mode appears for the account or plan changes.
3. GitHub text-shard ingress fallback.
4. Drive connector bridge only as last-resort transient staging.
5. Remote Desktop / Mac is not a normal path.
