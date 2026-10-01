import express from "express";
import { fetchArtifact, readChunk } from "./artifactStore.js";

const PORT = Number(process.env.PORT ?? 3000);
const TOKEN = String(process.env.TRANSFER_TOKEN ?? "");
const MODEL_URL = String(process.env.TRANSFER_MODEL_URL ?? "");
const EXPECTED_SHA256 = String(process.env.TRANSFER_MODEL_SHA256 ?? "");
const EXPECTED_SIZE = Number(process.env.TRANSFER_MODEL_SIZE ?? 0);
const PART_BYTES = Number(process.env.TRANSFER_PART_BYTES ?? 5000000);
const CSV_CHARS = 30000;

if (!TOKEN || !MODEL_URL || !EXPECTED_SHA256 || !EXPECTED_SIZE) {
  throw new Error("TRANSFER_ENV_INCOMPLETE");
}

const app = express();
app.disable("x-powered-by");
let artifactId = "";
let readyError = "";

app.get("/health", (_req, res) => {
  res.status(artifactId ? 200 : readyError ? 500 : 503).json({
    ok: Boolean(artifactId),
    state: artifactId ? "READY" : readyError ? "FAILED" : "LOADING",
    expected_size: EXPECTED_SIZE,
    part_bytes: PART_BYTES
  });
});

app.get("/part.csv", async (req, res) => {
  try {
    if (String(req.query.token ?? "") !== TOKEN) return res.status(401).send("UNAUTHORIZED\n");
    if (!artifactId) return res.status(503).send("NOT_READY\n");
    const index = Number(req.query.index);
    const total = Math.ceil(EXPECTED_SIZE / PART_BYTES);
    if (!Number.isSafeInteger(index) || index < 0 || index >= total) return res.status(400).send("INVALID_INDEX\n");
    const offset = index * PART_BYTES;
    const length = Math.min(PART_BYTES, EXPECTED_SIZE - offset);
    const chunk = await readChunk(artifactId, offset, length);
    const rows: string[] = [];
    rows.push(["META", index, total, offset, chunk.length, chunk.sha256].join(","));
    const n = Math.ceil(chunk.base64.length / CSV_CHARS);
    for (let i = 0; i < n; i++) {
      rows.push(["CHUNK", i + 1, n, chunk.base64.slice(i * CSV_CHARS, (i + 1) * CSV_CHARS)].join(","));
    }
    res.type("text/csv").set("Cache-Control", "no-store").send(rows.join("\n") + "\n");
  } catch (error) {
    res.status(500).type("text/plain").send(`ERROR:${error instanceof Error ? error.message : String(error)}\n`);
  }
});

app.listen(PORT, () => {
  console.log(`transfer-only listening on ${PORT}`);
  void fetchArtifact({
    url: MODEL_URL,
    expected_sha256: EXPECTED_SHA256,
    expected_size: EXPECTED_SIZE,
    ttl_seconds: 86400
  }).then((manifest) => {
    artifactId = manifest.id;
    console.log(`TRANSFER_ARTIFACT_READY ${JSON.stringify(manifest)}`);
  }).catch((error) => {
    readyError = error instanceof Error ? error.message : String(error);
    console.error(`TRANSFER_ARTIFACT_FAIL ${readyError}`);
  });
});
