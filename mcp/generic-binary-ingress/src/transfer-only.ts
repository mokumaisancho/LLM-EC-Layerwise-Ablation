import express from "express";
import { createHash } from "node:crypto";

const PORT = Number(process.env.PORT ?? 3000);
const MODEL_URL = "https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf";
const EXPECTED_SHA256 = "7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5";
const EXPECTED_SIZE = 2497280256;
const PART_BYTES = 5000000;
const CSV_CHARS = 30000;

const app = express();
app.disable("x-powered-by");

app.get("/health", (_req, res) => res.json({
  ok: true,
  state: "READY",
  model: "Qwen3-4B-Q4_K_M.gguf",
  expected_size: EXPECTED_SIZE,
  expected_sha256: EXPECTED_SHA256,
  part_bytes: PART_BYTES
}));

app.get("/part.csv", async (req, res) => {
  try {
    const index = Number(req.query.index);
    const total = Math.ceil(EXPECTED_SIZE / PART_BYTES);
    if (!Number.isSafeInteger(index) || index < 0 || index >= total) return res.status(400).send("INVALID_INDEX\n");
    const offset = index * PART_BYTES;
    const length = Math.min(PART_BYTES, EXPECTED_SIZE - offset);
    const end = offset + length - 1;
    const upstream = await fetch(MODEL_URL, {
      redirect: "follow",
      headers: { "User-Agent": "qwen-sandbox-transfer/1.0", "Range": `bytes=${offset}-${end}`, Accept: "application/octet-stream" }
    });
    if (upstream.status !== 206) throw new Error(`UPSTREAM_STATUS_${upstream.status}`);
    const contentRange = upstream.headers.get("content-range") ?? "";
    if (contentRange !== `bytes ${offset}-${end}/${EXPECTED_SIZE}`) throw new Error(`CONTENT_RANGE_MISMATCH:${contentRange}`);
    const data = Buffer.from(await upstream.arrayBuffer());
    if (data.length !== length) throw new Error(`LENGTH_MISMATCH:${data.length}`);
    const sha256 = createHash("sha256").update(data).digest("hex");
    const b64 = data.toString("base64");
    const rows: string[] = [];
    rows.push(["META", index, total, offset, data.length, sha256].join(","));
    const n = Math.ceil(b64.length / CSV_CHARS);
    for (let i = 0; i < n; i++) rows.push(["CHUNK", i + 1, n, b64.slice(i * CSV_CHARS, (i + 1) * CSV_CHARS)].join(","));
    res.type("text/csv").set("Cache-Control", "public, max-age=86400, immutable").send(rows.join("\n") + "\n");
  } catch (error) {
    res.status(500).type("text/plain").send(`ERROR:${error instanceof Error ? error.message : String(error)}\n`);
  }
});

app.listen(PORT, () => console.log(`transfer-only ready on ${PORT}`));
