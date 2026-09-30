import { createHash, randomUUID } from "node:crypto";
import { promises as dns } from "node:dns";
import { promises as fs } from "node:fs";
import path from "node:path";

export type ArtifactManifest = {
  id: string;
  source_url: string;
  final_url: string;
  filename: string;
  mime_type: string;
  size: number;
  sha256: string;
  created_at: string;
  expires_at: string;
  integrity: "verified" | "computed_only";
};

export type FetchArtifactInput = {
  url: string;
  expected_sha256?: string;
  expected_size?: number;
  ttl_seconds?: number;
  max_bytes?: number;
};

const ROOT = path.resolve(process.env.ARTIFACT_DIR ?? "/tmp/generic-binary-ingress");
const DEFAULT_MAX_BYTES = Number(process.env.ARTIFACT_MAX_BYTES ?? 2 * 1024 * 1024 * 1024);
const DEFAULT_CHUNK_BYTES = Number(process.env.ARTIFACT_CHUNK_BYTES ?? 4 * 1024 * 1024);
const MAX_TTL_SECONDS = Number(process.env.ARTIFACT_MAX_TTL_SECONDS ?? 86400);
const FETCH_TIMEOUT_MS = Number(process.env.ARTIFACT_FETCH_TIMEOUT_MS ?? 15 * 60 * 1000);
const MAX_REDIRECTS = 8;

const manifests = new Map<string, ArtifactManifest>();

const artifactPath = (id: string) => path.join(ROOT, `${id}.bin`);
const manifestPath = (id: string) => path.join(ROOT, `${id}.json`);
const assertId = (id: string) => {
  if (!/^[0-9a-f-]{36}$/i.test(id)) throw new Error("INVALID_ARTIFACT_ID");
};

const ipv4ToInt = (ip: string): number | null => {
  const parts = ip.split(".");
  if (parts.length !== 4) return null;
  const nums = parts.map(Number);
  if (nums.some((n) => !Number.isInteger(n) || n < 0 || n > 255)) return null;
  return (((nums[0] << 24) >>> 0) + (nums[1] << 16) + (nums[2] << 8) + nums[3]) >>> 0;
};

const inV4Range = (ip: string, base: string, bits: number) => {
  const n = ipv4ToInt(ip);
  const b = ipv4ToInt(base);
  if (n === null || b === null) return false;
  const mask = bits === 0 ? 0 : (0xffffffff << (32 - bits)) >>> 0;
  return (n & mask) === (b & mask);
};

const isPrivateAddress = (address: string): boolean => {
  const a = address.toLowerCase();
  const v4Ranges: Array<[string, number]> = [
    ["0.0.0.0", 8], ["10.0.0.0", 8], ["100.64.0.0", 10], ["127.0.0.0", 8],
    ["169.254.0.0", 16], ["172.16.0.0", 12], ["192.0.0.0", 24], ["192.0.2.0", 24],
    ["192.168.0.0", 16], ["198.18.0.0", 15], ["198.51.100.0", 24], ["203.0.113.0", 24],
    ["224.0.0.0", 4], ["240.0.0.0", 4]
  ];
  if (ipv4ToInt(a) !== null) return v4Ranges.some(([base, bits]) => inV4Range(a, base, bits));
  if (a === "::" || a === "::1") return true;
  if (a.startsWith("fc") || a.startsWith("fd")) return true;
  if (/^fe[89ab]/.test(a)) return true;
  if (a.startsWith("ff")) return true;
  const mapped = a.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/);
  if (mapped) return isPrivateAddress(mapped[1]);
  return false;
};

export const validatePublicUrl = async (raw: string): Promise<URL> => {
  const url = new URL(raw);
  if (url.protocol !== "https:" && url.protocol !== "http:") throw new Error("ONLY_HTTP_HTTPS_ALLOWED");
  if (url.username || url.password) throw new Error("URL_USERINFO_FORBIDDEN");
  const hostname = url.hostname.replace(/^\[|\]$/g, "");
  if (!hostname || hostname.toLowerCase() === "localhost" || hostname.toLowerCase().endsWith(".localhost")) {
    throw new Error("LOCALHOST_FORBIDDEN");
  }
  if (isPrivateAddress(hostname)) throw new Error(`NON_PUBLIC_ADDRESS_FORBIDDEN:${hostname}`);
  const answers = await dns.lookup(hostname, { all: true, verbatim: true });
  if (!answers.length) throw new Error("DNS_NO_ANSWER");
  for (const answer of answers) {
    if (isPrivateAddress(answer.address)) throw new Error(`NON_PUBLIC_ADDRESS_FORBIDDEN:${answer.address}`);
  }
  return url;
};

const safeFilename = (url: URL, contentDisposition: string | null) => {
  const fromHeader = contentDisposition?.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i)?.[1];
  const raw = fromHeader ? decodeURIComponent(fromHeader.replace(/^"|"$/g, "")) : path.basename(url.pathname) || "artifact.bin";
  return raw.replace(/[^A-Za-z0-9._-]+/g, "_").slice(0, 180) || "artifact.bin";
};

const saveManifest = async (manifest: ArtifactManifest) => {
  manifests.set(manifest.id, manifest);
  await fs.writeFile(manifestPath(manifest.id), JSON.stringify(manifest, null, 2) + "\n", "utf8");
};

export const getManifest = async (id: string): Promise<ArtifactManifest> => {
  assertId(id);
  let manifest = manifests.get(id);
  if (!manifest) {
    const raw = await fs.readFile(manifestPath(id), "utf8");
    manifest = JSON.parse(raw) as ArtifactManifest;
    manifests.set(id, manifest);
  }
  if (Date.now() >= Date.parse(manifest.expires_at)) {
    await deleteArtifact(id).catch(() => undefined);
    throw new Error("ARTIFACT_EXPIRED");
  }
  return manifest;
};

export const fetchArtifact = async (input: FetchArtifactInput): Promise<ArtifactManifest> => {
  await fs.mkdir(ROOT, { recursive: true, mode: 0o700 });
  const id = randomUUID();
  const out = artifactPath(id);
  const tmp = `${out}.part`;
  const maxBytes = Math.min(input.max_bytes ?? DEFAULT_MAX_BYTES, DEFAULT_MAX_BYTES);
  const ttl = Math.max(60, Math.min(input.ttl_seconds ?? 3600, MAX_TTL_SECONDS));
  const expectedHash = input.expected_sha256?.toLowerCase();
  if (!Number.isSafeInteger(maxBytes) || maxBytes <= 0) throw new Error("MAX_BYTES_INVALID");
  if (expectedHash && !/^[0-9a-f]{64}$/.test(expectedHash)) throw new Error("EXPECTED_SHA256_INVALID");
  if (input.expected_size !== undefined && (!Number.isSafeInteger(input.expected_size) || input.expected_size < 0)) {
    throw new Error("EXPECTED_SIZE_INVALID");
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new Error("FETCH_TIMEOUT")), FETCH_TIMEOUT_MS);
  let current = await validatePublicUrl(input.url);
  let res: Response | undefined;

  try {
    for (let i = 0; i <= MAX_REDIRECTS; i++) {
      await validatePublicUrl(current.href);
      res = await fetch(current, {
        method: "GET",
        redirect: "manual",
        signal: controller.signal,
        headers: { "User-Agent": "generic-binary-ingress-mcp/0.1.0", Accept: "*/*" }
      });
      if ([301, 302, 303, 307, 308].includes(res.status)) {
        const location = res.headers.get("location");
        if (!location) throw new Error("REDIRECT_WITHOUT_LOCATION");
        current = await validatePublicUrl(new URL(location, current).href);
        continue;
      }
      break;
    }
    if (!res) throw new Error("FETCH_NO_RESPONSE");
    if ([301, 302, 303, 307, 308].includes(res.status)) throw new Error("TOO_MANY_REDIRECTS");
    if (!res.ok) throw new Error(`UPSTREAM_HTTP_${res.status}`);
    if (!res.body) throw new Error("UPSTREAM_EMPTY_BODY");

    const contentLengthHeader = res.headers.get("content-length");
    const declared = contentLengthHeader === null ? undefined : Number(contentLengthHeader);
    if (declared !== undefined && (!Number.isSafeInteger(declared) || declared < 0)) throw new Error("CONTENT_LENGTH_INVALID");
    if (declared !== undefined && declared > maxBytes) throw new Error("ARTIFACT_TOO_LARGE_DECLARED");
    if (input.expected_size !== undefined && declared !== undefined && declared !== input.expected_size) {
      throw new Error(`EXPECTED_SIZE_MISMATCH_DECLARED:${declared}`);
    }

    const fh = await fs.open(tmp, "wx", 0o600);
    const hash = createHash("sha256");
    let size = 0;
    try {
      const reader = res.body.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = Buffer.from(value);
        size += chunk.length;
        if (size > maxBytes) throw new Error("ARTIFACT_TOO_LARGE_STREAM");
        hash.update(chunk);
        await fh.write(chunk);
      }
    } finally {
      await fh.close();
    }

    const sha256 = hash.digest("hex");
    if (input.expected_size !== undefined && size !== input.expected_size) {
      throw new Error(`EXPECTED_SIZE_MISMATCH:${size}`);
    }
    if (expectedHash && sha256 !== expectedHash) throw new Error(`EXPECTED_SHA256_MISMATCH:${sha256}`);

    await fs.rename(tmp, out);
    const now = new Date();
    const manifest: ArtifactManifest = {
      id,
      source_url: input.url,
      final_url: current.href,
      filename: safeFilename(current, res.headers.get("content-disposition")),
      mime_type: res.headers.get("content-type") ?? "application/octet-stream",
      size,
      sha256,
      created_at: now.toISOString(),
      expires_at: new Date(now.getTime() + ttl * 1000).toISOString(),
      integrity: expectedHash || input.expected_size !== undefined ? "verified" : "computed_only"
    };
    await saveManifest(manifest);
    return manifest;
  } catch (error) {
    await fs.rm(tmp, { force: true }).catch(() => undefined);
    await fs.rm(out, { force: true }).catch(() => undefined);
    throw error;
  } finally {
    clearTimeout(timer);
  }
};

export const readChunk = async (id: string, offset: number, length = DEFAULT_CHUNK_BYTES) => {
  const manifest = await getManifest(id);
  if (!Number.isSafeInteger(offset) || offset < 0 || offset >= manifest.size) throw new Error("OFFSET_INVALID");
  if (!Number.isSafeInteger(length) || length <= 0) throw new Error("CHUNK_LENGTH_INVALID");
  const bounded = Math.min(length, DEFAULT_CHUNK_BYTES, manifest.size - offset);
  const fh = await fs.open(artifactPath(id), "r");
  try {
    const buffer = Buffer.alloc(bounded);
    const { bytesRead } = await fh.read(buffer, 0, bounded, offset);
    const data = buffer.subarray(0, bytesRead);
    return {
      offset,
      length: bytesRead,
      sha256: createHash("sha256").update(data).digest("hex"),
      base64: data.toString("base64")
    };
  } finally {
    await fh.close();
  }
};

export const deleteArtifact = async (id: string) => {
  assertId(id);
  manifests.delete(id);
  await Promise.all([
    fs.rm(artifactPath(id), { force: true }),
    fs.rm(manifestPath(id), { force: true }),
    fs.rm(`${artifactPath(id)}.part`, { force: true })
  ]);
  return { id, deleted: true };
};

export const chunkBytes = DEFAULT_CHUNK_BYTES;
