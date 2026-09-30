import cors from "cors";
import express from "express";
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import { createIngressMcpServer } from "./serverFactory.js";

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
app.use(cors({
  origin: ALLOWED_ORIGINS.length ? ALLOWED_ORIGINS : false,
  exposedHeaders: ["mcp-session-id", "Mcp-Session-Id"]
}));

const reject = (res: express.Response, status: number, message: string) => {
  res.status(status).json({ jsonrpc: "2.0", error: { code: -32000, message }, id: null });
};

const authMiddleware: express.RequestHandler = (req, res, next) => {
  if (!REQUIRE_KEY) return next();
  if (!API_KEYS.length) return reject(res, 503, "MCP_REQUIRE_KEY=true but MCP_API_KEYS is empty.");
  const auth = Array.isArray(req.headers.authorization) ? req.headers.authorization[0] : req.headers.authorization;
  const bearer = auth?.startsWith("Bearer ") ? auth.slice(7) : undefined;
  const rawX = req.headers["x-api-key"];
  const xKey = Array.isArray(rawX) ? rawX[0] : rawX;
  const candidate = bearer ?? xKey;
  if (candidate && API_KEYS.includes(candidate)) return next();
  return reject(res, 401, "Unauthorized");
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

app.get("/health", (_req, res) => res.json({ ok: true, service: "generic-binary-ingress", version: "0.1.0" }));

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

const httpServer = app.listen(PORT, () => console.log(`generic-binary-ingress listening on ${PORT}`));

const shutdown = async () => {
  httpServer.close();
  await Promise.all(Array.from(transports.values()).map((t) => t.close().catch(() => undefined)));
  transports.clear();
  servers.clear();
  process.exit(0);
};

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
