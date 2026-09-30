import { createHash, randomBytes } from "node:crypto";

const b64url = (buf: Buffer) => buf.toString("base64url");

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

  const initRes = await fetch(`${root}/mcp`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token.access_token}`,
      "content-type": "application/json",
      accept: "application/json, text/event-stream"
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2025-06-18",
        capabilities: {},
        clientInfo: { name: "gbi-selftest", version: "1.0.0" }
      }
    })
  });
  if (!initRes.ok) throw new Error(`MCP_INIT_HTTP_${initRes.status}`);
  const sessionId = initRes.headers.get("mcp-session-id");
  if (!sessionId) throw new Error("MCP_SESSION_ID_MISSING");

  return {
    protected_resource_metadata: "PASS",
    authorization_server_metadata: "PASS",
    dynamic_client_registration: "PASS",
    pkce_authorization_code: "PASS",
    refresh_token_issued: "PASS",
    mcp_initialize: "PASS",
    session_id_present: true
  };
};
