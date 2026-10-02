import express from "express";
import { createHash } from "node:crypto";
import { performance } from "node:perf_hooks";

const PORT = Number(process.env.PORT ?? 3000);
const MODEL_URL = "https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf";
const EXPECTED_SHA256 = "7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5";
const EXPECTED_SIZE = 2497280256;

const MIB = 1024 * 1024;
const LEGACY_CSV_PART_BYTES = 1_000_000;
const CSV_CHARS = 30000;
const RAW_PART_BYTES_CANDIDATES = [64, 32, 16, 8, 4].map((mib) => mib * MIB);
const RAW_DEFAULT_PART_BYTES = Number(process.env.RAW_PART_BYTES ?? 16 * MIB);

function parseRawPartBytes(value: unknown): number {
  const candidate = value === undefined ? RAW_DEFAULT_PART_BYTES : Number(value);
  if (!Number.isSafeInteger(candidate) || !RAW_PART_BYTES_CANDIDATES.includes(candidate)) {
    throw new Error(`INVALID_PART_BYTES:${candidate};allowed=${RAW_PART_BYTES_CANDIDATES.join("|")}`);
  }
  return candidate;
}

async function fetchPart(index: number, partBytes: number) {
  const total = Math.ceil(EXPECTED_SIZE / partBytes);
  if (!Number.isSafeInteger(index) || index < 0 || index >= total) {
    throw new Error(`INVALID_INDEX:${index};total=${total}`);
  }

  const offset = index * partBytes;
  const length = Math.min(partBytes, EXPECTED_SIZE - offset);
  const end = offset + length - 1;
  const started = performance.now();
  const upstream = await fetch(MODEL_URL, {
    redirect: "follow",
    headers: {
      "User-Agent": "qwen-sandbox-transfer/2.0",
      Range: `bytes=${offset}-${end}`,
      Accept: "application/octet-stream",
    },
  });
  if (upstream.status !== 206) throw new Error(`UPSTREAM_STATUS_${upstream.status}`);
  const contentRange = upstream.headers.get("content-range") ?? "";
  if (contentRange !== `bytes ${offset}-${end}/${EXPECTED_SIZE}`) {
    throw new Error(`CONTENT_RANGE_MISMATCH:${contentRange}`);
  }
  const data = Buffer.from(await upstream.arrayBuffer());
  if (data.length !== length) throw new Error(`LENGTH_MISMATCH:${data.length};expected=${length}`);
  const sha256 = createHash("sha256").update(data).digest("hex");
  const elapsedMs = Math.round((performance.now() - started) * 100) / 100;
  return { index, total, offset, end, length, partBytes, sha256, elapsedMs, data };
}

const app = express();
app.disable("x-powered-by");

app.get("/health", (_req, res) => res.json({
  ok: true,
  state: "READY",
  model: "Qwen3-4B-Q4_K_M.gguf",
  expected_size: EXPECTED_SIZE,
  expected_sha256: EXPECTED_SHA256,
  transport: {
    preferred: "RAW_BINARY",
    raw_default_part_bytes: RAW_DEFAULT_PART_BYTES,
    raw_candidate_part_bytes_desc: RAW_PART_BYTES_CANDIDATES,
    selection_policy: "probe descending and freeze the largest end-to-end successful size for the run",
    legacy_csv_part_bytes: LEGACY_CSV_PART_BYTES,
  },
}));

app.get("/manifest", (_req, res) => res.json({
  model_url: MODEL_URL,
  expected_size: EXPECTED_SIZE,
  expected_sha256: EXPECTED_SHA256,
  raw_candidate_part_bytes_desc: RAW_PART_BYTES_CANDIDATES,
  raw_part_counts: Object.fromEntries(
    RAW_PART_BYTES_CANDIDATES.map((partBytes) => [String(partBytes), Math.ceil(EXPECTED_SIZE / partBytes)]),
  ),
  legacy_csv_part_bytes: LEGACY_CSV_PART_BYTES,
  drive_required: false,
}));

app.get("/probe", async (req, res) => {
  try {
    const partBytes = parseRawPartBytes(req.query.part_bytes);
    const index = req.query.index === undefined ? 0 : Number(req.query.index);
    const part = await fetchPart(index, partBytes);
    res.json({
      ok: true,
      index: part.index,
      total_parts: part.total,
      byte_start: part.offset,
      byte_end: part.end,
      byte_length: part.length,
      part_bytes: part.partBytes,
      sha256: part.sha256,
      upstream_fetch_ms: part.elapsedMs,
    });
  } catch (error) {
    res.status(500).json({ ok: false, error: error instanceof Error ? error.message : String(error) });
  }
});

app.get("/part.bin", async (req, res) => {
  try {
    const partBytes = parseRawPartBytes(req.query.part_bytes);
    const index = Number(req.query.index);
    const part = await fetchPart(index, partBytes);
    res
      .status(200)
      .type("application/octet-stream")
      .set({
        "Cache-Control": "public, max-age=86400, immutable",
        "X-Content-Type-Options": "nosniff",
        "X-Part-Index": String(part.index),
        "X-Total-Parts": String(part.total),
        "X-Byte-Start": String(part.offset),
        "X-Byte-End": String(part.end),
        "X-Byte-Length": String(part.length),
        "X-Part-Bytes": String(part.partBytes),
        "X-Part-SHA256": part.sha256,
        "X-Model-Size": String(EXPECTED_SIZE),
        "X-Model-SHA256": EXPECTED_SHA256,
        "X-Upstream-Fetch-Ms": String(part.elapsedMs),
        "Content-Length": String(part.data.length),
      })
      .send(part.data);
  } catch (error) {
    res.status(500).type("text/plain").send(`ERROR:${error instanceof Error ? error.message : String(error)}\n`);
  }
});

// Compatibility only. This remains at 1,000,000 bytes because that value was
// introduced specifically for the historical Sheets/IMPORTDATA envelope.
app.get("/part.csv", async (req, res) => {
  try {
    const index = Number(req.query.index);
    const part = await fetchPart(index, LEGACY_CSV_PART_BYTES);
    const b64 = part.data.toString("base64");
    const rows: string[] = [];
    rows.push(["META", part.index, part.total, part.offset, part.data.length, part.sha256].join(","));
    const n = Math.ceil(b64.length / CSV_CHARS);
    for (let i = 0; i < n; i++) {
      rows.push(["CHUNK", i + 1, n, b64.slice(i * CSV_CHARS, (i + 1) * CSV_CHARS)].join(","));
    }
    res.type("text/csv").set("Cache-Control", "public, max-age=86400, immutable").send(rows.join("\n") + "\n");
  } catch (error) {
    res.status(500).type("text/plain").send(`ERROR:${error instanceof Error ? error.message : String(error)}\n`);
  }
});

app.listen(PORT, () => console.log(`transfer-only ready on ${PORT}`));
