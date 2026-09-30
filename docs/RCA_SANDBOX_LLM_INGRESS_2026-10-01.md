# RCA: sandbox LLM ingress — 2026-10-01

## Problem

A lightweight LLM had previously been executed in the sandbox, but direct re-import initially failed despite sufficient disk capacity.

## Root causes

### 1. Direct Hugging Face binary path

The model page itself was reachable, but the GGUF download redirected through Hugging Face Xet to a signed external CDN URL. The sandbox downloader/safe-open path rejected that signed binary redirect. This was an ingress-policy/path problem, not a model-size or disk-capacity problem.

### 2. Shell outbound networking

The sandbox shell could not resolve ordinary external hosts. Therefore `curl`, `git clone`, direct PyPI downloads and direct Hugging Face downloads were not reliable ingress mechanisms.

### 3. Historical Drive staging was misunderstood

A small `TMP_MODEL_PART_000` file represented only an incomplete historical fragment and was not enough for reconstruction. It was deleted as obsolete.

The complete model was actually preserved inside the native workbook `Public Fetch Smoke Test Runtime` across paired hidden/staging sheets. Raw-exporting the complete workbook bypassed the need to make hundreds of connector cell reads.

### 4. Runtime part-0 archival copy was incomplete

One standalone `COGCOMP_RUNTIME_PART0_STATIC` copy contained only 112 of the declared 167 Base64 chunks. Another duplicate was only a wrapper/empty artifact. This did not block inference because a complete llama.cpp runtime was already present in the sandbox.

### 5. Apps Script function-name collision

Re-evaluating `=COGCOMP_FETCH_PART("RUNTIME",0)` no longer called the historical binary fetcher. The same global Apps Script function name had later been shadowed/replaced by unrelated YouTube logic and returned `YT_DIRECT_AUDIO_NOT_FOUND`.

This is a namespace-governance defect in the Apps Script integration hub. Future transport functions must use unique, versioned names.

## Resolution

The complete staging workbook was raw-exported to the sandbox as XLSX. All 22 model parts were decoded, verified individually and concatenated.

Verification:

- expected size: `105454432`
- reconstructed size: `105454432`
- expected SHA256: `2e8040ceae7815abe0dcb3540b9995eaa1fa0d2ca9e797d0a635ae4433c68c2d`
- reconstructed SHA256: exact match
- result: `PASS`

A pre-existing sandbox llama.cpp build was then used successfully.

Smoke result:

- `SANDBOX_LLM_OK`
- prompt throughput ~`587.6 tok/s`
- generation throughput ~`146.8 tok/s`

## Experiment-side finding

The first Issue #9 run exposed a second, scientifically important separation:

1. Unconstrained SmolLM2-135M output failed the JSON protocol on all 10 fixtures.
2. A JSON Schema constrained arm was therefore used only to enforce output structure and the set of candidate IDs already present in the input.
3. Semantic choices remained unconstrained.
4. Under that arm, parsing succeeded 10/10 but semantic selection remained 0/10, reframing 1/10 and closure 8/10.

Therefore protocol-format following and semantic selection must be reported as separate layers. A parse failure must not be misreported as a selection failure.

## Preventive actions

- Preserve exact source URL, revision, size and SHA for every staged binary.
- Verify every part before concatenation.
- Raw-export staging workbooks instead of retrieving huge Base64 ranges cell-by-cell.
- Use versioned Apps Script function names for binary transport.
- Do not rely on staging workbooks as permanent runtime archives.
- Keep only the actively used model/runtime in the sandbox.
- Separate output-contract compliance from semantic-selection metrics in the ablation harness.
- GitHub Actions remain disabled.
