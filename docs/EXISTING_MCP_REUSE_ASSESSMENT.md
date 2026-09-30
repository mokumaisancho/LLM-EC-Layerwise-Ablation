# Existing MCP Reuse Assessment

## Conclusion
Do not build a generic HTTP/binary fetch MCP from scratch.

Use an existing curl-oriented MCP as the transport base and add only the missing artifact-ingress controls required by this project.

## Existing candidates

### calibress/curl-mcp
Useful existing capabilities:
- hosted HTTP MCP transport;
- GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS;
- custom headers, so HTTP Range can be requested;
- redirect/session handling;
- binary responses represented as Base64 with content type and size metadata.

Main gap for this project:
- binary responses are still returned in MCP response bodies, which is unsuitable for hundreds-of-MB artifacts;
- no project-specific artifact registry;
- no required SHA-256 gate;
- no bounded chunk/resource delivery contract.

### 247arjun/mcp-curl
Useful existing capabilities:
- `curl_download` to a local file;
- resume support;
- redirects, headers and advanced curl arguments;
- safe subprocess invocation.

Main gap for this project:
- designed primarily around local/stdin use rather than a hosted ChatGPT ingress service;
- downloaded files are server-local and are not automatically exposed as MCP ResourceLinks/files to the client;
- no SHA-256 acceptance gate or artifact lifecycle contract.

### Generic fetch MCP servers
Examples include modelcontextprotocol/servers fetch and zcaceres/fetch-mcp.
They are primarily page/text extraction tools and intentionally truncate/limit returned content. They are not suitable as large binary artifact ingress without substantial changes.

## MCP protocol feature to reuse
MCP already supports `ResourceLink` and binary resource contents. For large artifacts, the service should return a ResourceLink/custom resource URI instead of embedding hundreds of MB of Base64 in a tool result.

The server may back a custom resource URI with a downloaded server-side artifact. The client can resolve the resource through MCP `resources/read`; for very large artifacts, bounded chunk/resource endpoints should be used to avoid one huge JSON/Base64 message.

## Minimal extension only
Required additions on top of an existing curl MCP:
1. `register_artifact(url, expected_sha256, expected_size?)`
2. server-side streamed download to temporary artifact storage;
3. redirect-following and optional HTTP Range/resume;
4. SHA-256 computed while streaming;
5. fail closed when expected hash/size does not match;
6. return an MCP ResourceLink such as `artifact://<id>` rather than embedding the binary;
7. `get_artifact_manifest(id)`;
8. bounded `read_artifact_chunk(id, offset, length)` or equivalent resource template;
9. explicit artifact deletion and TTL/size limits;
10. SSRF protection: public HTTP(S) only, reject loopback/private/link-local/metadata addresses and revalidate after redirects/DNS resolution.

## Decision
Preferred base: `calibress/curl-mcp` for its hosted HTTP MCP transport and mature structured HTTP handling, borrowing the file-download/resume behavior already present in `247arjun/mcp-curl`.

This is an extension/integration task, not a greenfield MCP implementation.

## Non-goals
- Hugging Face-specific logic;
- Google Drive persistence;
- Mac/Remote Desktop dependency;
- unrestricted generic proxy endpoint;
- storing model binaries in the research repository.
