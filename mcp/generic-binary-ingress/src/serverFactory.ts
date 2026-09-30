import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { chunkBytes, deleteArtifact, fetchArtifact, getManifest, readChunk } from "./artifactStore.js";

const FetchSchema = z.object({
  url: z.string().url(),
  expected_sha256: z.string().regex(/^[0-9a-fA-F]{64}$/).optional(),
  expected_size: z.number().int().nonnegative().optional(),
  ttl_seconds: z.number().int().min(60).max(86400).optional(),
  max_bytes: z.number().int().positive().optional()
});

const IdSchema = z.object({ id: z.string().uuid() });
const ChunkSchema = z.object({
  id: z.string().uuid(),
  offset: z.number().int().nonnegative(),
  length: z.number().int().positive().max(chunkBytes).optional()
});

export const createIngressMcpServer = (source: string) => {
  const server = new McpServer({ name: "generic-binary-ingress", version: "0.1.0" });

  server.registerTool(
    "artifact_fetch",
    {
      description: "Fetch a public HTTP(S) binary artifact into temporary server-side storage, compute SHA-256 while streaming, and return an MCP ResourceLink instead of embedding the binary.",
      inputSchema: FetchSchema
    },
    async (args): Promise<any> => {
      try {
        const manifest = await fetchArtifact(args);
        return {
          content: [
            {
              type: "resource_link",
              uri: `artifact://${manifest.id}/manifest`,
              name: manifest.filename,
              title: manifest.filename,
              description: `Temporary verified artifact manifest; binary is available in ${chunkBytes}-byte bounded chunks.`,
              mimeType: "application/json",
              size: manifest.size
            },
            { type: "text", text: JSON.stringify(manifest, null, 2) }
          ],
          structuredContent: manifest
        };
      } catch (error) {
        return {
          isError: true,
          content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }]
        };
      }
    }
  );

  server.registerTool(
    "artifact_info",
    { description: "Return the manifest for a temporary artifact.", inputSchema: IdSchema },
    async ({ id }): Promise<any> => {
      try {
        const manifest = await getManifest(id);
        return { content: [{ type: "text", text: JSON.stringify(manifest, null, 2) }], structuredContent: manifest };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }] };
      }
    }
  );

  server.registerTool(
    "artifact_chunk_link",
    {
      description: `Return a ResourceLink for one bounded artifact chunk. Maximum chunk size is ${chunkBytes} bytes.`,
      inputSchema: ChunkSchema
    },
    async ({ id, offset, length }): Promise<any> => {
      try {
        const manifest = await getManifest(id);
        const bounded = Math.min(length ?? chunkBytes, chunkBytes, Math.max(0, manifest.size - offset));
        if (bounded <= 0) throw new Error("CHUNK_OUT_OF_RANGE");
        return {
          content: [{
            type: "resource_link",
            uri: `artifact://${id}/chunk/${offset}/${bounded}`,
            name: `${manifest.filename}.part.${offset}`,
            description: `Binary chunk at offset ${offset}, length ${bounded}.`,
            mimeType: manifest.mime_type,
            size: bounded
          }]
        };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }] };
      }
    }
  );

  server.registerTool(
    "artifact_delete",
    { description: "Delete a temporary artifact and its manifest immediately.", inputSchema: IdSchema },
    async ({ id }): Promise<any> => {
      try {
        const result = await deleteArtifact(id);
        return { content: [{ type: "text", text: JSON.stringify(result) }], structuredContent: result };
      } catch (error) {
        return { isError: true, content: [{ type: "text", text: error instanceof Error ? error.message : String(error) }] };
      }
    }
  );

  server.registerResource(
    "artifact-manifest",
    new ResourceTemplate("artifact://{id}/manifest", { list: undefined }),
    { title: "Artifact manifest", description: "Temporary artifact metadata and integrity digest.", mimeType: "application/json" },
    async (uri, variables): Promise<any> => {
      const manifest = await getManifest(String(variables.id));
      return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(manifest, null, 2) }] };
    }
  );

  server.registerResource(
    "artifact-chunk",
    new ResourceTemplate("artifact://{id}/chunk/{offset}/{length}", { list: undefined }),
    { title: "Artifact binary chunk", description: "Bounded Base64 binary chunk from a temporary artifact.", mimeType: "application/octet-stream" },
    async (uri, variables): Promise<any> => {
      const id = String(variables.id);
      const offset = Number(variables.offset);
      const requestedLength = Number(variables.length);
      if (!Number.isSafeInteger(requestedLength) || requestedLength <= 0 || requestedLength > chunkBytes) {
        throw new Error("CHUNK_LENGTH_INVALID");
      }
      const manifest = await getManifest(id);
      const chunk = await readChunk(id, offset, requestedLength);
      return {
        contents: [{
          uri: uri.href,
          mimeType: manifest.mime_type,
          blob: chunk.base64,
          _meta: { offset: chunk.offset, length: chunk.length, sha256: chunk.sha256, artifact_sha256: manifest.sha256 }
        }]
      };
    }
  );

  server.registerTool(
    "mcp_version",
    { description: "Return Generic Binary Ingress MCP version information." },
    async (): Promise<any> => ({ content: [{ type: "text", text: `generic-binary-ingress 0.1.0 (${source})` }] })
  );

  return server;
};
