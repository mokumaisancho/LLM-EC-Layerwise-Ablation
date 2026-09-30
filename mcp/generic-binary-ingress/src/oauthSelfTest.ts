import { createHash, randomBytes } from "node:crypto";

const b64url = (buf: Buffer) => buf.toString("base64url");

const parseMcpPayload = async (res: Response) => {
  const text = await res.text();
  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) return JSON.parse(text);
  const dataLine = text.split(/\r?\n/).find((line) => line.startsWith("data:"));
  if (!dataLine) throw new Error("MCP_RESPONSE_UNPARSEABLE");
  return JSON.parse(dataLine.slice(5).trim());
};

const mcpPost = async (root: string, token: string, sessionId: string | undefined, body: unknown) => {
  const headers: Record<string, string> = {
    authorization: `Bearer ${token}`,
    "content-type": "application/json",
    accept: "application/json, text/event-stream"
  };
  if (sessionId) headers["mcp-session-id"] = sessionId;
  return fetch(`${root}/mcp`, { method: "POST", headers, body: JSON.stringify(body) });
};

export const runOAuthSelfTest = async () => {
  const root = (process.env.MCP_PUBLIC_BASE_URL ?? "").replace(/\/$/, "");
  const password = process.env.MCP_OAUTH_PASSWORD ?? "";
  if (!root || !password) throw new Error("SELFTEST_CONFIG_MISSING");

  const prmRes = await fetch(`${root}/.well-known/oauth-protected-resource`);
  if (!prmRes.ok) throw new Error(`PRM_HTTP_${prmRes.status}`);
  const prm = await prmRes.json() as any;
  if (prm.resource !== root || !Array.isArray(prm.authorization_servers) || !prm.authorization_servers.includes(root)) {
    throw new Error("PRM_INVALID");
  }

  const asmRes = await fetch(`${root}/.well-known/oauth-authorization-server`);
  if (!asmRes.ok) throw new Error(`ASM_HTTP_${asmRes.status}`);
  const asm = await asmRes.json() as any;
  if (asm.issuer !== root || !asm.registration_endpoint || !asm.token_endpoint || !asm.authorization_endpoint) {
    throw new Error("ASM_INVALID");
  }
  if (!Array.isArray(asm.code_challenge_methods_supported) || !asm.code_challenge_methods_supported.includes("S256")) {
    throw new Error("ASM_PKCE_MISSING");
  }
  if (!Array.isArray(asm.scopes_supported) || !asm.scopes_supported.includes("offline_access")) {
    throw new Error("ASM_OFFLINE_ACCESS_MISSING");
  }
  if (asm.authorization_response_iss_parameter_supported !== true) throw new Error("ASM_ISS_SUPPORT_MISSING");

  const redirectUri = "https://example.invalid/oauth/callback";
  const regRes = await fetch(asm.registration_endpoint, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ redirect_uris: [redirectUri], client_name: "GBI hosted self-test" })
  });
  if (regRes.status !== 201) throw new Error(`DCR_HTTP_${regRes.status}`);
  const reg = await regRes.json() as any;
  const clientId = String(reg.client_id ?? "");
  if (!clientId) throw new Error("DCR_CLIENT_ID_MISSING");

  const verifier = b64url(randomBytes(48));
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  const state = b64url(randomBytes(16));
  const scope = "artifacts:fetch offline_access";

  const authorize = new URL(asm.authorization_endpoint);
  authorize.searchParams.set("client_id", clientId);
  authorize.searchParams.set("redirect_uri", redirectUri);
  authorize.searchParams.set("response_type", "code");
  authorize.searchParams.set("code_challenge", challenge);
  authorize.searchParams.set("code_challenge_method", "S256");
  authorize.searchParams.set("scope", scope);
  authorize.searchParams.set("state", state);
  authorize.searchParams.set("resource", root);

  const authGet = await fetch(authorize, { redirect: "manual" });
  if (!authGet.ok) throw new Error(`AUTHORIZE_GET_HTTP_${authGet.status}`);

  const form = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    code_challenge: challenge,
    code_challenge_method: "S256",
    scope,
    state,
    resource: root,
    password
  });
  const authPost = await fetch(asm.authorization_endpoint, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: form,
    redirect: "manual"
  });
  if (authPost.status !== 302) throw new Error(`AUTHORIZE_POST_HTTP_${authPost.status}`);
  const location = authPost.headers.get("location");
  if (!location) throw new Error("AUTHORIZE_LOCATION_MISSING");
  const callback = new URL(location);
  const code = callback.searchParams.get("code") ?? "";
  if (!code || callback.searchParams.get("state") !== state || callback.searchParams.get("iss") !== root) {
    throw new Error("AUTHORIZE_CALLBACK_INVALID");
  }

  const tokenBody = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    client_id: clientId,
    redirect_uri: redirectUri,
    code_verifier: verifier,
    resource: root
  });
  const tokenRes = await fetch(asm.token_endpoint, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: tokenBody
  });
  if (!tokenRes.ok) throw new Error(`TOKEN_HTTP_${tokenRes.status}`);
  const token = await tokenRes.json() as any;
  if (!token.access_token || !token.refresh_token || !String(token.scope ?? "").includes("artifacts:fetch")) {
    throw new Error("TOKEN_RESPONSE_INVALID");
  }

  const initRes = await mcpPost(root, token.access_token, undefined, {
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2025-06-18",
      capabilities: {},
      clientInfo: { name: "gbi-selftest", version: "1.0.0" }
    }
  });
  if (!initRes.ok) throw new Error(`MCP_INIT_HTTP_${initRes.status}`);
  const sessionId = initRes.headers.get("mcp-session-id");
  if (!sessionId) throw new Error("MCP_SESSION_ID_MISSING");
  const initPayload = await parseMcpPayload(initRes);
  if (!initPayload?.result?.serverInfo) throw new Error("MCP_INIT_PAYLOAD_INVALID");

  const initializedRes = await mcpPost(root, token.access_token, sessionId, {
    jsonrpc: "2.0",
    method: "notifications/initialized",
    params: {}
  });
  if (!initializedRes.ok && initializedRes.status !== 202) throw new Error(`MCP_INITIALIZED_HTTP_${initializedRes.status}`);

  const listRes = await mcpPost(root, token.access_token, sessionId, {
    jsonrpc: "2.0", id: 2, method: "tools/list", params: {}
  });
  if (!listRes.ok) throw new Error(`TOOLS_LIST_HTTP_${listRes.status}`);
  const listPayload = await parseMcpPayload(listRes);
  const names = (listPayload?.result?.tools ?? []).map((tool: any) => tool.name);
  for (const required of ["artifact_fetch", "artifact_info", "artifact_chunk_link", "artifact_delete"]) {
    if (!names.includes(required)) throw new Error(`TOOL_MISSING:${required}`);
  }

  const smallUrl = "https://raw.githubusercontent.com/calibress/curl-mcp/main/LICENSE";
  const fetchRes = await mcpPost(root, token.access_token, sessionId, {
    jsonrpc: "2.0",
    id: 3,
    method: "tools/call",
    params: {
      name: "artifact_fetch",
      arguments: { url: smallUrl, ttl_seconds: 60, max_bytes: 65536 }
    }
  });
  if (!fetchRes.ok) throw new Error(`ARTIFACT_FETCH_TOOL_HTTP_${fetchRes.status}`);
  const fetchPayload = await parseMcpPayload(fetchRes);
  if (fetchPayload?.result?.isError) throw new Error(`ARTIFACT_FETCH_TOOL_ERROR:${JSON.stringify(fetchPayload.result)}`);
  const artifactId = String(fetchPayload?.result?.structuredContent?.id ?? "");
  const artifactSha = String(fetchPayload?.result?.structuredContent?.sha256 ?? "");
  const artifactSize = Number(fetchPayload?.result?.structuredContent?.size ?? 0);
  if (!artifactId || !/^[0-9a-f]{64}$/.test(artifactSha) || artifactSize <= 0) {
    throw new Error("ARTIFACT_FETCH_TOOL_PAYLOAD_INVALID");
  }

  const deleteRes = await mcpPost(root, token.access_token, sessionId, {
    jsonrpc: "2.0",
    id: 4,
    method: "tools/call",
    params: { name: "artifact_delete", arguments: { id: artifactId } }
  });
  if (!deleteRes.ok) throw new Error(`ARTIFACT_DELETE_TOOL_HTTP_${deleteRes.status}`);
  const deletePayload = await parseMcpPayload(deleteRes);
  if (deletePayload?.result?.isError || deletePayload?.result?.structuredContent?.deleted !== true) {
    throw new Error("ARTIFACT_DELETE_TOOL_INVALID");
  }

  return {
    protected_resource_metadata: "PASS",
    authorization_server_metadata: "PASS",
    dynamic_client_registration: "PASS",
    pkce_authorization_code: "PASS",
    issuer_identification: "PASS",
    refresh_token_issued: "PASS",
    mcp_initialize: "PASS",
    tools_list: "PASS",
    artifact_fetch_tool: "PASS",
    artifact_delete_tool: "PASS",
    session_id_present: true,
    sample_artifact_size: artifactSize,
    sample_artifact_sha256: artifactSha
  };
};
