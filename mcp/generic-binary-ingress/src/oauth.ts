import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import type { Request, Response } from "express";

const ACCESS_TTL_SECONDS = 3600;
const CODE_TTL_SECONDS = 300;
const REFRESH_TTL_SECONDS = 30 * 24 * 3600;
const RESOURCE_SCOPE = "artifacts:fetch";
const OFFLINE_SCOPE = "offline_access";
const SCOPES = [RESOURCE_SCOPE, OFFLINE_SCOPE];

type Client = {
  client_id: string;
  redirect_uris: string[];
  client_name?: string;
};
type AuthCode = {
  client_id: string;
  redirect_uri: string;
  code_challenge: string;
  scope: string;
  resource: string;
  expires_at: number;
};
type AccessToken = { scope: string; resource: string; expires_at: number };
type RefreshToken = { client_id: string; scope: string; resource: string; expires_at: number };

const clients = new Map<string, Client>();
const codes = new Map<string, AuthCode>();
const accessTokens = new Map<string, AccessToken>();
const refreshTokens = new Map<string, RefreshToken>();

const token = (bytes = 32) => randomBytes(bytes).toString("base64url");
const baseUrl = () => (process.env.MCP_PUBLIC_BASE_URL ?? "").replace(/\/$/, "");
const issuer = () => baseUrl();

const cleanExpired = () => {
  const now = Date.now();
  for (const [k, v] of codes) if (v.expires_at <= now) codes.delete(k);
  for (const [k, v] of accessTokens) if (v.expires_at <= now) accessTokens.delete(k);
  for (const [k, v] of refreshTokens) if (v.expires_at <= now) refreshTokens.delete(k);
};

const safeEq = (a: string, b: string) => {
  const aa = Buffer.from(a);
  const bb = Buffer.from(b);
  if (aa.length !== bb.length) return false;
  return timingSafeEqual(aa, bb);
};

const escapeHtml = (s: string) => s.replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[c]!));

const normalizeScope = (raw: string) => {
  const requested = raw.split(/\s+/).filter(Boolean);
  for (const scope of requested) if (!SCOPES.includes(scope)) throw new Error("invalid_scope");
  if (!requested.includes(RESOURCE_SCOPE)) requested.unshift(RESOURCE_SCOPE);
  return Array.from(new Set(requested)).join(" ");
};

export const protectedResourceMetadata = (_req: Request, res: Response) => {
  const root = baseUrl();
  res.json({
    resource: root,
    authorization_servers: [root],
    scopes_supported: [RESOURCE_SCOPE],
    resource_documentation: `${root}/health`
  });
};

export const authorizationServerMetadata = (_req: Request, res: Response) => {
  const root = issuer();
  res.json({
    issuer: root,
    authorization_endpoint: `${root}/oauth/authorize`,
    token_endpoint: `${root}/oauth/token`,
    registration_endpoint: `${root}/oauth/register`,
    response_types_supported: ["code"],
    grant_types_supported: ["authorization_code", "refresh_token"],
    token_endpoint_auth_methods_supported: ["none"],
    code_challenge_methods_supported: ["S256"],
    scopes_supported: SCOPES,
    authorization_response_iss_parameter_supported: true
  });
};

export const registerClient = (req: Request, res: Response) => {
  const redirectUris = Array.isArray(req.body?.redirect_uris) ? req.body.redirect_uris.map(String) : [];
  if (!redirectUris.length || redirectUris.some((u: string) => !/^https:\/\//i.test(u))) {
    return res.status(400).json({ error: "invalid_redirect_uris" });
  }
  const client_id = token(24);
  clients.set(client_id, {
    client_id,
    redirect_uris: redirectUris,
    client_name: req.body?.client_name ? String(req.body.client_name) : undefined
  });
  return res.status(201).json({
    client_id,
    client_id_issued_at: Math.floor(Date.now() / 1000),
    redirect_uris: redirectUris,
    token_endpoint_auth_method: "none",
    grant_types: ["authorization_code", "refresh_token"],
    response_types: ["code"]
  });
};

const validateAuthorize = (q: Record<string, unknown>) => {
  const client_id = String(q.client_id ?? "");
  const redirect_uri = String(q.redirect_uri ?? "");
  const response_type = String(q.response_type ?? "");
  const code_challenge = String(q.code_challenge ?? "");
  const method = String(q.code_challenge_method ?? "");
  const scope = normalizeScope(String(q.scope ?? `${RESOURCE_SCOPE} ${OFFLINE_SCOPE}`));
  const state = String(q.state ?? "");
  const resource = String(q.resource ?? baseUrl());
  const client = clients.get(client_id);
  if (!client || !client.redirect_uris.includes(redirect_uri)) throw new Error("invalid_client_or_redirect");
  if (response_type !== "code") throw new Error("unsupported_response_type");
  if (!code_challenge || method !== "S256") throw new Error("pkce_s256_required");
  if (resource !== baseUrl()) throw new Error("invalid_resource");
  return { client_id, redirect_uri, code_challenge, scope, state, resource };
};

export const authorizeGet = (req: Request, res: Response) => {
  try {
    const v = validateAuthorize(req.query as Record<string, unknown>);
    const hidden = Object.entries({ ...v, response_type: "code", code_challenge_method: "S256" })
      .filter(([, value]) => value !== undefined)
      .map(([k, value]) => `<input type="hidden" name="${escapeHtml(k)}" value="${escapeHtml(String(value))}">`)
      .join("\n");
    res.type("html").send(`<!doctype html><html><head><meta charset="utf-8"><title>Authorize Generic Binary Ingress</title></head><body><main><h1>Authorize Generic Binary Ingress</h1><p>Scope: ${escapeHtml(v.scope)}</p><form method="post" action="/oauth/authorize">${hidden}<label>Access password <input type="password" name="password" autocomplete="current-password" required></label><button type="submit">Authorize</button></form></main></body></html>`);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : "invalid_request" });
  }
};

export const authorizePost = (req: Request, res: Response) => {
  try {
    const v = validateAuthorize(req.body ?? {});
    const configured = process.env.MCP_OAUTH_PASSWORD ?? "";
    const supplied = String(req.body?.password ?? "");
    if (!configured || !safeEq(configured, supplied)) return res.status(403).type("text").send("Authorization denied");
    const code = token(32);
    codes.set(code, { ...v, expires_at: Date.now() + CODE_TTL_SECONDS * 1000 });
    const target = new URL(v.redirect_uri);
    target.searchParams.set("code", code);
    if (v.state) target.searchParams.set("state", v.state);
    target.searchParams.set("iss", issuer());
    return res.redirect(302, target.href);
  } catch (error) {
    return res.status(400).json({ error: error instanceof Error ? error.message : "invalid_request" });
  }
};

const pkceMatches = (verifier: string, challenge: string) =>
  createHash("sha256").update(verifier).digest("base64url") === challenge;

const issueTokens = (client_id: string, scope: string, resource: string) => {
  const access_token = token(32);
  const refresh_token = token(40);
  accessTokens.set(access_token, { scope, resource, expires_at: Date.now() + ACCESS_TTL_SECONDS * 1000 });
  refreshTokens.set(refresh_token, { client_id, scope, resource, expires_at: Date.now() + REFRESH_TTL_SECONDS * 1000 });
  return { access_token, token_type: "Bearer", expires_in: ACCESS_TTL_SECONDS, refresh_token, scope };
};

export const tokenPost = (req: Request, res: Response) => {
  cleanExpired();
  const grant = String(req.body?.grant_type ?? "");
  if (grant === "authorization_code") {
    const codeValue = String(req.body?.code ?? "");
    const client_id = String(req.body?.client_id ?? "");
    const redirect_uri = String(req.body?.redirect_uri ?? "");
    const verifier = String(req.body?.code_verifier ?? "");
    const resource = String(req.body?.resource ?? baseUrl());
    const record = codes.get(codeValue);
    if (!record || record.expires_at <= Date.now()) return res.status(400).json({ error: "invalid_grant" });
    if (
      record.client_id !== client_id ||
      record.redirect_uri !== redirect_uri ||
      record.resource !== resource ||
      !pkceMatches(verifier, record.code_challenge)
    ) {
      return res.status(400).json({ error: "invalid_grant" });
    }
    codes.delete(codeValue);
    return res.json(issueTokens(client_id, record.scope, record.resource));
  }
  if (grant === "refresh_token") {
    const refresh = String(req.body?.refresh_token ?? "");
    const client_id = String(req.body?.client_id ?? "");
    const resource = String(req.body?.resource ?? baseUrl());
    const record = refreshTokens.get(refresh);
    if (
      !record ||
      record.expires_at <= Date.now() ||
      record.client_id !== client_id ||
      record.resource !== resource
    ) return res.status(400).json({ error: "invalid_grant" });
    refreshTokens.delete(refresh);
    return res.json(issueTokens(client_id, record.scope, record.resource));
  }
  return res.status(400).json({ error: "unsupported_grant_type" });
};

export const validateAccessToken = (value: string | undefined, requiredScope = RESOURCE_SCOPE) => {
  cleanExpired();
  if (!value) return false;
  const record = accessTokens.get(value);
  if (!record || record.expires_at <= Date.now() || record.resource !== baseUrl()) return false;
  return record.scope.split(/\s+/).includes(requiredScope);
};

export const authChallenge = () => `Bearer resource_metadata="${baseUrl()}/.well-known/oauth-protected-resource", scope="${RESOURCE_SCOPE}"`;
