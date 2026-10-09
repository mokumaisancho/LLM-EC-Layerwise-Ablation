# Issue #1 — autonomous machine-resolvable continuation (2026-10-10)

Authority remains [origin issue #1](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/1), `ACCEPTANCE_CRITERIA.md`, frozen Phase1 TCC V1/V2 and the scoped successor evidence. This document **does not authorize changing original exit criteria**.

## Why the first self-directed workflow stopped too early

`tools/run_issue1_autonomous_tcc_workflow.py` truthfully found original P2 `EC_NATIVE_SCOPE_INCOMPATIBLE`, but had no branch to execute further machine-resolvable science. The original incompatibility is structural: generic Phase1 S3 accepts multiple simultaneous candidates (M003/M009), actual EC-native next-action authority selects one action; generic S3 does not expose enough structural information for S4 closure (bound 8/10). No result from a shorter protocol may be mislabeled as original A/B/C/D/E completion.

## Executed *new* branches

1. Restore exact source Git blobs of the original 17-case next-action experimental fixture and policy: `fixtures/function_boundary_next_action_v1.json` (Git SHA `12faa9a4cacf0c91694d25f1ccce45e093d95e44`) and `docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json` (Git SHA `af2b29c3fbd6318fc8083bfd8035eb053d3d8304`). Both were recoverable from historical reachable Git objects even though absent from current tree. They are author-visible historical fixtures, NOT independent blind gold.
2. Reconstruct exact six native ECv4.4 implementation blobs at commit `d5ec423968f1c9242c590e5e77ccfd92d1f59eb2`. **Critical**: two actual blobs are the `01_repo/src/v4/` versions of `ec_next_action_authority.py` and `ec_dynamic_frontier.py`, not the different root `01_repo/src/` files. Use pinned source import verification. `tools/replay_issue1_ecv44_native_next_action_v2.py` actually reruns all 17 and reproduces 17/17 status+work ID and 17/17 reason, including dynamic-state authority checks and expected fail-closed outcomes. Evidence: `results/issue1_ecv44_native_next_action_v2_local_replay_2026-10-10.json`.
3. Restore byte-exact original prompt+GBNF logic under `verification/issue1_next_action_v2/archived_original_runner_2026_10_03.py`, Git SHA `486863d076f49a9378a538e97739464849a044b1`. Do NOT run its network-heavy Ubuntu downloader; `tools/run_issue1_llm_next_action_v2_local_mac.py` replaces the completion transport with verified native Mac `llama-cli`. With pinned `Qwen2.5-1.5B-Instruct-Q4_K_M.gguf`, 17 genuinely executed inferences: **all 17 chose REFRAME** and **1/17 status+work correct** (N217), matching the historical aggregate **1/17**. Model weight matches historical SHA, but llama.cpp runtime/server/platform does not; this is a **new versioned Mac replication**, not bit-identical historical inference. Evidence: `results/issue1_qwen_next_action_v2_mac_actual_2026-10-10.json`.
4. Original S4 under-identified representation has structural-majority bound 8/10. The versioned `tools/run_issue1_s4_interface_information_diagnostic_v1.py` uses only publicly visible domain facts, S2 relation types and S3 selection, passes sanitized features into an isolated subprocess, scores only after prediction: 10/10 on the **known** 10 fixtures. Removing COMPETING and unresolved-required-condition input bits causes two predeclared negative controls to fail. This isolates *missing information*, **not EC runtime performance or generalization**. Evidence: `results/issue1_s4_interface_information_diagnostic_actual_2026-10-10.json`.
5. `tools/run_issue1_autonomous_tcc_workflow_v2.py` creates an actual new TCC DAG of **8 nodes/10 edges**, calls the original TCC and SUITE/ECv4 audit, then branches automatically through S4 diagnostic, real pinned native EC17 and pinned actual Qwen17. It uses existing sealed inference output if available, avoiding unnecessary repeat cost; if no output and model/binary/pinned EC are supplied, it runs the actual Qwen invocation. It fails closed on source/provenance tampering and never claims original full A–E qualification. Current second-stage terminal: `MACHINE_SCOPED_EVIDENCE_COMPLETE_ORIGINAL_SCIENCE_STILL_BLOCKED`. Evidence: `results/issue1_autonomous_stage2_machine_scoped_2026-10-10.json`.

## Invoke without intermediary chat prompts

Use a clean isolated worktree, with a separately fetched read-only pinned ECv4.4 checkout and pinned TCC compiler.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_autonomous_tcc_workflow_v2.py \
  --tcc-root /private/tmp/llmec-tcc-generator-reference-20261009 \
  --ec-root /private/tmp/llmec-ecv44-source-20261010
```

The runner executes all available branches in one call. It never registers an automation, sends itself ChatGPT conversation messages, runs a watcher, changes the user's UI, starts GitHub Actions, or silently closes the issue.

Verification: **134 relevant regression/unit tests PASS**; SUITE PASS; ECv4 methodology gate PASS. The 17 native and Qwen runs and the 10-case S4 intervention actually executed; no simulated model output.

## Genuine remaining completion prerequisites

- Original #1 **S1–S4 A/B/C/D/E same-function comparison with actual single-layer Oracle interventions** is not defined by semantically compatible interfaces under original Phase1. The original frozen protocol must not be silently repaired or closed.
- For #57/#58 conservation qualification, genuinely unseen independently adjudicated gold, independently verified custody/chronology, genuine original LLM0 designation with real same-case predictions and owner-authorized V4 policy remain unavailable. Known historical fixtures and this retrospective report **are not eligible**.
- An independent valid experimental contract for general raw-language semantic invention and a heldout dataset is needed before full language-model replacement claims. Finite typed symbolic space and bounded policy enforcement cannot certify unrestricted world knowledge or ontology invention.

**Stop rule:** Finish all local machine-resolvable stages in one invocation, return scientific status `BLOCKED_EXTERNAL_EVIDENCE` instead of spinning or inventing results where an independent owner/human adjudication or incompatible source interface is required. This is a real execution limit, not permission to stop after an easy subtask. A normal ChatGPT text reply itself cannot spontaneously launch further model turns after its reply; no scheduled ChatGPT task was created.
