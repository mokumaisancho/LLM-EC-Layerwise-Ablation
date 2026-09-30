# Generic Binary Ingress MCP

Generic binary ingress for ChatGPT/MCP clients, implemented as a minimal extension of the transport patterns used by `calibress/curl-mcp`.

## Purpose

Move a public HTTP(S) binary into an MCP-controlled temporary artifact store without requiring the ChatGPT sandbox itself to have outbound DNS/egress.

Flow:

`public URL -> hosted MCP -> streamed temp file -> SHA-256/size gate -> MCP ResourceLink -> bounded resource chunks`

This is generic: GGUF, ZIP, tarballs, firmware, datasets, wheels, and other binary artifacts are supported.

## Tools

- `artifact_fetch(url, expected_sha256?, expected_size?, ttl_seconds?, max_bytes?)`
- `artifact_info(id)`
- `artifact_chunk_link(id, offset, length?)`
- `artifact_delete(id)`

## Resources

- `artifact://{id}/manifest`
- `artifact://{id}/chunk/{offset}/{length}`

Binary chunks are returned as MCP resource `blob` values and are bounded by `ARTIFACT_CHUNK_BYTES`.

## Security defaults

- HTTP/HTTPS only.
- URL userinfo rejected.
- localhost, loopback, RFC1918/private, link-local, documentation, multicast and reserved address ranges rejected.
- DNS is checked before every request and every redirect target.
- redirects are handled manually and revalidated.
- server-side streamed download; binary is not embedded in the `artifact_fetch` result.
- hard maximum artifact size.
- optional expected SHA-256 and expected size gates.
- partial files removed on failure.
- signed URL query strings are not persisted in manifests.
- HTTP MCP defaults to API-key-required mode.
- artifacts expire by TTL and can be explicitly deleted.

## Important residual security limitation

The current Node `fetch()` implementation re-resolves the hostname after the explicit DNS validation step. Therefore this MVP reduces SSRF risk but does not fully eliminate DNS-rebinding/TOCTOU risk. Before exposing the service broadly, replace the resolver path with a pinned-address HTTP(S) transport (preserving TLS SNI/hostname validation) or enforce a strict source-host allowlist.

For the immediate single-user research PoC, keep API-key authentication enabled and do not expose the service publicly without access control.

## Environment

```text
PORT=3000
MCP_REQUIRE_KEY=true
MCP_API_KEYS=<long-random-secret>
MCP_ALLOWED_HOSTS=<public-host:port>
MCP_ALLOWED_ORIGINS=<optional-client-origin>
ARTIFACT_DIR=/tmp/generic-binary-ingress
ARTIFACT_MAX_BYTES=2147483648
ARTIFACT_CHUNK_BYTES=4194304
ARTIFACT_MAX_TTL_SECONDS=86400
ARTIFACT_FETCH_TIMEOUT_MS=900000
```

## Run

```bash
npm install
npm run build
MCP_API_KEYS='replace-me' npm start
```

Health endpoint:

```text
GET /health
```

MCP endpoint:

```text
POST/GET/DELETE /mcp
```

## Verification target for Issue #15

Use Qwen2.5-0.5B-Instruct Q4_K_M with its pinned SHA-256. Pass criteria:

1. `artifact_fetch` completes without Drive/Mac staging.
2. manifest reports expected final size and `sha256_verified`.
3. first, middle, and final chunk resources read successfully.
4. reconstructed artifact SHA-256 equals the expected model SHA.
5. llama.cpp smoke inference succeeds in sandbox.
6. `artifact_delete` removes staging.

GitHub Actions must remain disabled.
