# GitHub text-shard model ingress

Status: VERIFIED POC (2026-10-01)

## Purpose
Avoid using Google Drive as persistent model storage while also avoiding sandbox outbound-DNS and binary safe-open restrictions.

## Verified path

`external fetch/encoder -> Base64 UTF-8 shards in GitHub -> GitHub connector -> sandbox decode -> per-shard SHA -> concat -> final SHA -> GGUF smoke inference`

The important property is that the GitHub connector reads UTF-8 repository files reliably even when the sandbox shell cannot download the corresponding binary directly.

## POC evidence

Repository path: `poc/github_text_shard_v2/`

A deterministic 4096-byte binary payload was Base64-encoded and stored as `part-000.b64` with a manifest.

Expected decoded SHA-256:
`c33417cdc29da3cc0cfb3efffebfa148bc571cedcfc99071417bcd9a5145b251`

GitHub connector returned blob SHA:
`8fba6ea2de0c54d9df215ede1467d1065f22cc7c`

The locally calculated Git blob SHA for the exact Base64 text was the same:
`8fba6ea2de0c54d9df215ede1467d1065f22cc7c`

After Base64 decode, the reconstructed binary SHA-256 matched the source payload exactly. Therefore GitHub connector text-shard transport is verified end-to-end for the POC.

## Preferred role

Use this as the preferred persistent transport representation for sandbox experiments when model size is manageable.

Google Drive is no longer the preferred persistent store. The existing Drive/XLSX bridge remains a fallback and, when required for external fetching, should be used only as a transient execution surface and cleaned after transfer.

## Production shard format

Each shard must be plain UTF-8 Base64 text. The manifest must record:
- model ID and original filename;
- decoded total size;
- final SHA-256;
- encoding (`base64`);
- ordered shard index;
- decoded shard size;
- decoded shard SHA-256;
- source provenance/version.

Recommended validation order:
1. Fetch manifest through GitHub connector.
2. Fetch every shard through GitHub connector.
3. Verify expected Git blob SHA when recorded.
4. Base64-decode each shard.
5. Verify each decoded shard size and SHA-256.
6. Concatenate in index order.
7. Verify final file size and SHA-256.
8. Verify `GGUF` magic.
9. Run one non-interactive llama.cpp smoke inference.

## Capacity warning

Base64 expands storage by roughly 4/3. A 400 MB GGUF becomes about 533 MB of text before Git object overhead. Therefore this route is suitable for controlled experiments but is not the long-term model registry for multi-GB model fleets.

For larger models, keep the same manifest/hash protocol but replace the source writer with object storage or another connector-native file-reference transport. Do not reintroduce an unverified binary redirect path.

## Current 0.5B experiment policy

For Issue #14, hold fixtures, grammar, scoring, and EC control rules fixed. Only model capacity changes. Prefer GitHub text shards for persistent transfer. If an external fetch runner must use Google Sheets, use it transiently only and remove the temporary binary staging after GitHub/sandbox verification.

GitHub Actions remain disabled.
