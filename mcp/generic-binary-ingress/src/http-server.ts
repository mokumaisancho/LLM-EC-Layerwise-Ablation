import cors from "cors";
import express from "express";
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import { createIngressMcpServer } from "./serverFactory.js";
import { fetchArtifact } from "./artifactStore.js";
import { runOAuthSelfTest } from "./oauthSelfTest.js";
import {
  protectedResourceMetadata,
  authorizationServerMetadata,
  registerClient,
  authorizeGet,
  authorizePost,
  tokenPost,
  validateAccessToken,
  authChallenge
} from "./oauth.js";

const PORT = Number(process.env.MCP_PORT ?? process.env.PORT ?? 3000);
const REQUIRE_KEY = (process.env.MCP_REQUIRE_KEY ?? "true").toLowerCase() === "true";
const API_KEYS = (process.env.MCP_API_KEYS ?? "").split(",").map((v) => v.trim()).filter(Boolean);
const ALLOWED_HOSTS = (process.env.MCP_ALLOWED_HOSTS ?? "").split(",").map((v) => v.trim()).filter(Boolean);
const ALLOWED_ORIGINS = (process.env.MCP_ALLOWED_ORIGINS ?? "").split(",").map((v) => v.trim()).filter(Boolean);

const transports = new Map<string, StreamableHTTPServerTransport>();
const servers = new Map<string, McpServer>();
const app = express();
app.disable("x-powered-by");
app.use(express.json({ limit: "1mb" }));
app.use(express.urlencoded({ extended: false, limit: "64kb" }));
app.use(cors({
  origin: ALLOWED_ORIGINS.length ? ALLOWED_ORIGINS : false,
  exposedHeaders: ["mcp-session-id", "Mcp-Session-Id", "WWW-Authenticate"]
}));

const reject = (res: express.Response, status: number, message: string, challenge = false) => {
  if (challenge) res.setHeader("WWW-Authenticate", authChallenge());
  res.status(status).json({ jsonrpc: "2.0", error: { code: -32000, message }, id: null });
};

const authMiddleware: express.RequestHandler = (req, res, next) => {
  if (!REQUIRE_KEY) return next();
  const auth = Array.isArray(req.headers.authorization) ? req.headers.authorization[0] : req.headers.authorization;
  const bearer = auth?.startsWith("Bearer ") ? auth.slice(7) : undefined;
  const rawX = req.headers["x-api-key"];
  const xKey = Array.isArray(rawX) ? rawX[0] : rawX;
  if (bearer && validateAccessToken(bearer)) return next();
  if ((bearer && API_KEYS.includes(bearer)) || (xKey && API_KEYS.includes(xKey))) return next();
  return reject(res, 401, "Unauthorized", true);
};

const boundaryMiddleware: express.RequestHandler = (req, res, next) => {
  if (ALLOWED_HOSTS.length) {
    const host = Array.isArray(req.headers.host) ? req.headers.host[0] : req.headers.host;
    if (!host || !ALLOWED_HOSTS.includes(host)) return reject(res, 403, "Host not allowed");
  }
  if (ALLOWED_ORIGINS.length) {
    const origin = Array.isArray(req.headers.origin) ? req.headers.origin[0] : req.headers.origin;
    if (!origin || !ALLOWED_ORIGINS.includes(origin)) return reject(res, 403, "Origin not allowed");
  }
  return next();
};

const createSession = () => {
  const server = createIngressMcpServer("http");
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: () => randomUUID(),
    onsessioninitialized: (sessionId: string) => {
      transports.set(sessionId, transport);
      servers.set(sessionId, server);
    },
    allowedHosts: ALLOWED_HOSTS.length ? ALLOWED_HOSTS : undefined,
    allowedOrigins: ALLOWED_ORIGINS.length ? ALLOWED_ORIGINS : undefined,
    enableDnsRebindingProtection: ALLOWED_HOSTS.length > 0 || ALLOWED_ORIGINS.length > 0
  });
  transport.onclose = () => {
    const id = transport.sessionId;
    if (id) {
      transports.delete(id);
      servers.delete(id);
    }
  };
  return { server, transport };
};

const sessionId = (req: express.Request) => {
  const h = req.headers["mcp-session-id"];
  return Array.isArray(h) ? h[0] : h;
};

app.get("/health", (_req, res) => res.json({ ok: true, service: "generic-binary-ingress", version: "0.2.0" }));
app.get("/.well-known/oauth-protected-resource", protectedResourceMetadata);
app.get("/.well-known/oauth-authorization-server", authorizationServerMetadata);
app.post("/oauth/register", registerClient);
app.get("/oauth/authorize", authorizeGet);
app.post("/oauth/authorize", authorizePost);
app.post("/oauth/token", tokenPost);

app.post("/mcp", authMiddleware, boundaryMiddleware, async (req, res) => {
  try {
    const id = sessionId(req);
    if (id && transports.has(id)) {
      await transports.get(id)!.handleRequest(req, res, req.body);
      return;
    }
    if (!isInitializeRequest(req.body)) {
      return reject(res, 400, "Initialize request required for a new MCP session.");
    }
    const { server, transport } = createSession();
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error(error);
    if (!res.headersSent) reject(res, 500, "Internal MCP error");
  }
});

app.get("/mcp", authMiddleware, boundaryMiddleware, async (req, res) => {
  const id = sessionId(req);
  if (!id || !transports.has(id)) return reject(res, 400, "Invalid or missing MCP session ID");
  try {
    await transports.get(id)!.handleRequest(req, res);
  } catch (error) {
    console.error(error);
    if (!res.headersSent) reject(res, 500, "MCP GET failed");
  }
});

app.delete("/mcp", authMiddleware, boundaryMiddleware, async (req, res) => {
  const id = sessionId(req);
  if (!id || !transports.has(id)) return reject(res, 400, "Invalid or missing MCP session ID");
  try {
    await transports.get(id)!.handleRequest(req, res);
  } catch (error) {
    console.error(error);
    if (!res.headersSent) reject(res, 500, "MCP DELETE failed");
  }
});

const httpServer = app.listen(PORT, () => {
  console.log(`generic-binary-ingress listening on ${PORT}`);
  const smokeUrl = process.env.ARTIFACT_SMOKE_URL;
  if (smokeUrl) {
    void fetchArtifact({
      url: smokeUrl,
      expected_sha256: process.env.ARTIFACT_SMOKE_SHA256 || undefined,
      ttl_seconds: Number(process.env.ARTIFACT_SMOKE_TTL_SECONDS ?? 3600)
    })
      .then((manifest) => console.log(`ARTIFACT_SMOKE_PASS ${JSON.stringify(manifest)}`))
      .catch((error) => console.error(`ARTIFACT_SMOKE_FAIL ${error instanceof Error ? error.message : String(error)}`));
  }
  const gasProbeUrl = process.env.GAS_PROBE_URL;
  if (gasProbeUrl) {
    void fetch(gasProbeUrl, { redirect: "follow" })
      .then(async (response) => {
        const text = await response.text();
        if (!response.ok) throw new Error(`HTTP_${response.status}:${text.slice(0, 1000)}`);
        console.log(`GAS_PROBE_PASS ${text.slice(0, 4000)}`);
      })
      .catch((error) => console.error(`GAS_PROBE_FAIL ${error instanceof Error ? error.message : String(error)}`));
  }
  if ((process.env.OAUTH_SELFTEST ?? "").toLowerCase() === "true") {
    setTimeout(() => {
      void runOAuthSelfTest()
        .then((result) => console.log(`OAUTH_MCP_SELFTEST_PASS ${JSON.stringify(result)}`))
        .catch((error) => console.error(`OAUTH_MCP_SELFTEST_FAIL ${error instanceof Error ? error.message : String(error)}`));
    }, 1500);
  }
});

const shutdown = async () => {
  httpServer.close();
  await Promise.all(Array.from(transports.values()).map((t) => t.close().catch(() => undefined)));
  transports.clear();
  servers.clear();
  process.exit(0);
};

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
