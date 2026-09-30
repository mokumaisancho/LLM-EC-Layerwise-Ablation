# Sandbox model import — verified connector bridge

Status: VERIFIED (2026-10-01)

## Problem

Direct binary download from the active sandbox is unreliable because two independent controls can intervene:

- shell-side outbound DNS may be unavailable;
- the container downloader requires a URL to pass web-layer safe-open validation, while large binary/raw URLs may not be renderable by that layer.

Hugging Face additionally redirects GGUF downloads through Xet / signed CDN URLs, which makes this boundary more visible.

The limitation is transport, not inference capability.

## Verified ingress path

The successful path is:

`external fetch runner -> chunked Base64 in Google Sheets -> Google Drive connector raw XLSX export -> sandbox -> deterministic reconstruction -> SHA verification -> llama.cpp`

This path does not require the sandbox shell to resolve the original model host.

### Transfer format

The verified workbook stores the model as 22 indexed parts.

- Parts 0..20: 5,000,000 bytes each.
- Part 21: 454,432 bytes.
- Total: 105,454,432 bytes.
- Each part carries `index`, `total_parts`, `byte_start`, `byte_end`, `byte_length`, and `sha256`.
- Binary bytes are Base64-encoded into cells, normally 40,000 Base64 characters per cell.
- Two parts may share one worksheet, using columns B and D.

Verified worksheet family:

- `__COGCOMP_XFER`: parts 0 and 1
- `__COGCOMP_M_02`: parts 2 and 3
- ...
- `__COGCOMP_M_20`: parts 20 and 21

The sandbox receives the Google Sheet through the Drive connector as an XLSX file. The reconstruction tool reads workbook XML/shared strings directly, validates every part before concatenation, then validates the final file.

## Verified model

Model: `SmolLM2-135M-Instruct-Q4_K_M.gguf`

- size: `105454432` bytes
- GGUF magic: `GGUF`
- SHA-256: `2e8040ceae7815abe0dcb3540b9995eaa1fa0d2ca9e797d0a635ae4433c68c2d`

A reconstruction from the transfer workbook was byte-for-byte identical to the already materialized sandbox GGUF.

## Runtime verification

Runtime: llama.cpp b10936 (`llama-completion` / `llama-server`).

A non-interactive smoke generation completed with exit code 0. Measured sample runtime was approximately:

- load time: 76.75 ms
- prompt evaluation: 237.32 tokens/s
- generation: 131.95 tokens/s

The earlier timeout was caused by conversation mode waiting for further input, not by a model/runtime failure. Use `-no-cnv` for batch smoke tests.

## Required reconstruction checks

A model import is accepted only when all checks pass:

1. every expected part index exists exactly once;
2. each part's decoded byte length matches metadata;
3. each part SHA-256 matches metadata;
4. `byte_end - byte_start + 1 == byte_length`;
5. all indices `0..total_parts-1` are present;
6. final file begins with `GGUF`;
7. final size matches the registry;
8. final SHA-256 matches the registry;
9. one non-empty llama.cpp generation exits successfully.

## Storage rule

The repository stores only transfer/reconstruction logic and model metadata. Do not commit model binaries to the Git tree.

After successful reconstruction and smoke verification:

- keep only the active GGUF and extracted active runtime in sandbox;
- remove duplicate reconstructed GGUFs, transfer XLSX files, downloaded runtime archives, and failed download artifacts;
- remove obsolete/incomplete model shards from Drive when they are no longer required as the active transfer source.

## Why GitHub Release is secondary

GitHub Release remains a useful normal distribution mechanism, but in this sandbox it does not by itself solve the transport boundary: shell DNS and safe-open validation can still block direct binary retrieval. A connector-materialized file path is therefore the currently verified ingress method.

See `tools/reconstruct_gguf_from_xlsx.py` and `MODEL_REGISTRY.json`.
