# Sandbox LLM ingress

Status: VERIFIED on 2026-10-01.

## Working route

The reliable route is:

`external model -> Apps Script bound fetcher -> Google Sheets literal Base64 staging -> Drive XLSX raw export -> sandbox -> Base64 decode -> per-part SHA check -> concatenate -> whole-file SHA check -> llama.cpp`

This avoids direct sandbox outbound HTTP/DNS and Hugging Face Xet signed-CDN restrictions.

## Verified model

- Model: `SmolLM2-135M-Instruct-Q4_K_M.gguf`
- Source revision URL used by the historical staging fetcher: `https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF/resolve/f0a2b81d63eb57be0e90e82e327e03a7fc66a7dc/SmolLM2-135M-Instruct-Q4_K_M.gguf?download=true`
- Exact size: `105454432` bytes
- Expected SHA256: `2e8040ceae7815abe0dcb3540b9995eaa1fa0d2ca9e797d0a635ae4433c68c2d`
- Reconstructed SHA256: exact match
- Parts: `22/22` verified individually before concatenation
- Chunk size in the preserved staging workbook: `5,000,000` bytes per part except final part

## Preserved Drive staging source

- Workbook: `Public Fetch Smoke Test Runtime`
- Drive file ID: `1HjjjD1YAfkhKfkVBp4i1vQ4Ayl80Dpb3CzlSbmfIiPY`
- Model sheets:
  - `__COGCOMP_XFER` -> parts 0 and 1
  - `__COGCOMP_M_02` -> parts 2 and 3
  - ...
  - `__COGCOMP_M_20` -> parts 20 and 21

The critical property is that the sheets contain literal Base64 data, byte ranges, byte lengths and SHA256 values. They can therefore be exported as a single XLSX and reconstructed offline in the sandbox.

## Sandbox reconstruction procedure

1. Raw-export the complete staging workbook to XLSX through the Drive connector.
2. Open the XLSX locally in the sandbox.
3. For each model part, read metadata rows (`index`, `byte_start`, `byte_end`, `byte_length`, `sha256`, `data_chunks`).
4. Concatenate its `DATA` Base64 chunks.
5. Base64-decode and verify `byte_length` and per-part SHA256.
6. Concatenate parts in index order.
7. Verify exact whole-file size and SHA256 before loading it.
8. Run with the sandbox llama.cpp runtime.

## Verified runtime

A pre-existing sandbox runtime was found at:

- `/mnt/data/llama-b10936/llama-b10936/llama-cli`
- `/mnt/data/llama-b10936/llama-b10936/llama-server`
- build: `b10936-790cf51aa`

Inference smoke test:

- prompt: `Return exactly: SANDBOX_LLM_OK`
- output: `SANDBOX_LLM_OK`
- exit: `0`
- observed prompt throughput: about `587.6 tok/s`
- observed generation throughput: about `146.8 tok/s`

## Operational rules

- Never trust reconstructed bytes until per-part and whole-file hashes pass.
- Prefer one active model only; delete obsolete model copies/staging after a successful run.
- Treat Drive staging as transport, not as model authority. The source URL + exact size + expected SHA are the authority.
- Keep GitHub Actions disabled; this path does not require Actions.
- If the bound Apps Script fetch function is reused, give the fetcher a unique namespace; historical generic function names were later shadowed by unrelated code.
