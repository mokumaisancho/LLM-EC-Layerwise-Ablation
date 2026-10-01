# TCC One-Shot Sandbox LLM Execution Plan

Date: 2026-10-02 JST
Status: EXECUTION CONTRACT

## Goal
Run large-LLM and audio-file validation in the GPT sandbox with no iterative human correction loop. Predefine all decision branches, stop conditions, fallbacks, evidence capture, and closure criteria before execution.

## Hard invariants
1. GPT sandbox is the default execution environment.
2. Mac is forbidden except tests that intrinsically require physical hardware / OS-specific device I/O.
3. Audio-file tests run in the GPT sandbox. Mac-generated ASR results are not admissible as benchmark evidence.
4. GitHub Actions remain disabled.
5. Frozen fixtures/oracles/prompts/scoring stay unchanged within a comparison run.
6. Every branch records exact model/runtime SHA or version, source size, final file hash, wall-clock, peak RSS when observable, and outcome.
7. No manual mid-run prompt tuning, shard-size tuning, or model substitution. Branches below decide automatically.

## Optimization objective
Primary: minimum one-shot end-to-end wall-clock that passes correctness and sandbox resource gates.
Secondary: minimum external->sandbox transfer calls and bytes.
Tertiary: minimum peak RSS.

End-to-end time = ingress + materialization/reconstruction + runtime/model-open + task execution + scoring.

## Phase 0 — Preflight
Collect once:
- sandbox CPU count, RAM, free disk, architecture;
- available llama.cpp/compatible runtime and version;
- available file-reference/materialization route;
- candidate model manifest(s): total params, active params, file size, format, SHA;
- audio fixtures and expected transcript/labels;
- frozen assay version/hash.

Gate P0:
- free disk >= candidate artifact size * 1.25 AND >= 2 GiB reserve;
- available RAM >= 4 GiB;
- fixture/oracle hash chain PASS.

Branches:
- If disk gate fails -> select next smaller-on-disk candidate from predeclared candidate list; do not requantize ad hoc.
- If RAM gate fails -> switch runtime mode to lazy/expert-paging candidate; if unavailable, mark candidate NOT_EXECUTABLE and continue to next candidate.
- If fixture/oracle gate fails -> STOP INVALID_TEST_CONTRACT. Do not run models.

## Phase 1 — Ingress route selection
Test routes in this order without changing the model bytes:

R1. Connector-native raw file reference -> sandbox materialize.
R2. Existing Generic Binary Ingress MCP/file-reference path, only if directly attachable in the current product context.
R3. GitHub Base64 text shards as fallback.

Route decision:
- R1 available and materialization succeeds -> use R1.
- Else R2 available end-to-end -> use R2.
- Else -> use R3.

For R3:
- use the already-qualified shard protocol and manifest/hash checks;
- do not increase shard size beyond the last known-safe connector response envelope without a bounded preflight probe;
- streaming decode directly to destination file; never hold whole artifact Base64 or decoded bytes in memory;
- verify per-shard size/hash only when manifest provides them; always verify final size/SHA and GGUF magic.

Ingress failure handling:
- integrity mismatch -> retry failed unit once from source; second mismatch = SOURCE_OR_TRANSPORT_CORRUPTION and stop that route;
- timeout/transient connector error -> retry failed unit once; then fall through to next route;
- size/response-limit error -> reduce only the transport unit according to manifest policy; do not alter model bytes;
- out-of-disk -> delete partial artifact, select next candidate or stop if none fit.

Ingress success evidence:
route, calls, source bytes, destination bytes, wall-clock, final SHA, final size.

## Phase 2 — Model/runtime strategy
Candidate order is capability-preserving, not size-first:

M1. Large MoE model supported by current llama.cpp, preferred when total capacity is large but active params are low (e.g. Qwen3-30B-A3B class).
M2. Large dense model required by the assay, if MoE is not semantically acceptable for the test.
M3. Smaller control model only for smoke/control comparison; never substitute it for the required large-model result.

Runtime mode order per candidate:
A. lazy/expert on-demand paging if supported and model > practical RAM;
B. mmap;
C. normal load only if estimated resident set fits RAM gate.

Automatic branch:
- model file > 0.75 * available RAM -> A if available, else B;
- model file <= 0.75 * available RAM -> B first;
- model-open OOM/kill -> retry once with A; if A already used or unavailable -> candidate NOT_EXECUTABLE;
- model-open > ingress wall-clock * 2 and no progress signal -> abort mode and try next runtime mode;
- runtime incompatibility -> next compatible runtime/candidate, no source/model mutation.

## Phase 3 — Smoke gate
Before full assay, execute exactly one deterministic minimal prompt/input.

Pass:
- process exits normally;
- parseable output;
- no NaN/corruption/runtime fatal;
- peak RSS stays within sandbox limit.

Fail branches:
- OOM/kill -> runtime-mode fallback from Phase 2;
- parser/template failure -> apply only predeclared chat-template adapter for that model, then rerun smoke once;
- second functional failure -> reject candidate and continue.

No full benchmark runs before smoke PASS.

## Phase 4 — Full LLM assay
Use the frozen fixtures, prompt contract, grammar, scoring, and EC control rules.

Run all fixtures in one model session where feasible, but no result depends on cache persistence.
Record per fixture:
- prompt/input id;
- output;
- parse status;
- correctness metrics;
- latency;
- token counts where available;
- runtime errors.

Correctness gate:
- 100% required parseability for grammar-constrained categorical outputs;
- any oracle/fixture hash mismatch invalidates the run;
- architecture/model comparisons use identical frozen inputs.

Branch:
- parseability < 100% due runtime/template defect -> one predeclared adapter retry only;
- correctness below required assay threshold -> record FAIL_QUALITY; do not tune prompt during run; continue to next predeclared candidate if capacity comparison requires it;
- resource failure mid-run -> mark PARTIAL_RESOURCE_FAIL and try next runtime mode once; restart full assay from fixture 1 to preserve comparability.

## Phase 5 — Audio-file validation
Environment: GPT sandbox only.

Input classes:
- English clean speech;
- Japanese clean speech;
- mixed/realistic noise fixtures if available.

For each ASR candidate, execute from files stored/materialized in sandbox.
Measure:
- CER for Japanese;
- WER for English;
- release/end-of-speech -> final transcript latency when the test harness provides timestamps;
- real-time factor / wall-clock;
- peak RSS;
- load time.

Branches:
- decoder/runtime unavailable -> next declared ASR backend;
- audio decode format unsupported -> convert once inside sandbox to canonical PCM/WAV, preserving source reference and conversion command/version;
- OOM -> lower runtime memory mode/batch according to predeclared backend policy; do not move execution to Mac;
- accuracy failure -> record FAIL_QUALITY and continue candidate comparison; no iterative prompt/decoder tuning unless explicitly part of the frozen matrix.

Mac branch:
Only enter MAC_REQUIRED when the test target itself is physical microphone/device/OS I/O behavior. Audio-file accuracy/performance never enters this branch.

## Phase 6 — Selection rule
A candidate is admissible only if:
1. ingress integrity PASS;
2. smoke PASS;
3. frozen-assay integrity PASS;
4. required correctness threshold PASS;
5. sandbox resource gate PASS.

Among admissible candidates choose minimum:
TOTAL_WALL_CLOCK = ingress + materialize/reconstruct + model-open + full-assay execution + scoring.

Tie-breakers in order:
1. fewer external->sandbox calls;
2. lower peak RSS;
3. lower transferred bytes;
4. simpler/standard mainline runtime.

Do not select a faster candidate that fails correctness.

## Phase 7 — TCC closure
One final report only. No iterative progress/approval loop.

Required output:
- selected route/model/runtime;
- complete branch path taken;
- measured timings and resource metrics;
- correctness/audio metrics;
- rejected candidates + exact rejection reason;
- blockers that could not be crossed automatically;
- evidence hashes/versions;
- next action only if no admissible configuration exists.

Terminal states:
PASS_SELECTED
NO_ADMISSIBLE_MODEL
INVALID_TEST_CONTRACT
TRANSPORT_BLOCKED
SANDBOX_RESOURCE_LIMIT
MAC_REQUIRED_FOR_PHYSICAL_TEST_ONLY

## TCC execution policy
TCC may run independent preflight, source metadata, runtime capability, fixture-integrity, and transport-probe checks concurrently. Decisions that alter the active route/model/runtime are sequential and authority-bound. No branch may self-authorize a semantic change to fixtures, oracle, prompt, scoring, or acceptance thresholds.
