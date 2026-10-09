# Origin #1 — self-directed TCC workflow (not a scheduled ChatGPT task)

Protocol: `ISSUE1_SINGLE_TURN_AUTONOMOUS_TCC_EXECUTOR_V1`.
GitHub authority: [origin issue #1](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/1), `ACCEPTANCE_CRITERIA.md`, frozen `PHASE1_MVP_TCC_V1/V2`.
Capability-retention qualification issues #57/#58 are separate scientific requirements, not a substitute for the original S1–S4 A/B/C/D/E causal experiment.

## Operator intent

One invocation runs **every machine-executable step automatically**, including conditional branches and fail-closed status. **No intermediate chat prompt, interactive shell, extra scheduler, background daemon, GitHub Action, or ChatGPT automation is created.** A normal ChatGPT response cannot spontaneously send itself a follow-up once its turn has ended. Do not claim that this runner changes that ChatGPT product behavior.

Example in an authorized, clean research worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_autonomous_tcc_workflow.py \
  --tcc-root /private/tmp/llmec-tcc-generator-reference-20261009 \
  --source-commit "$(git rev-parse HEAD)" \
  --out /private/tmp/issue1-self-directed-last.json
```

TCC Compiler must be read-only and pinned to `786d52c1efbc9271096f9311d768ef49bcd116e2`. `--source-commit` prevents switching research source mid-run. Default external study source is **only** `evaluation/external_study_v1/`, or an explicitly supplied `--study-dir`, never a broad scan of personal files. The runner reads **public corpus, precommit, four arm envelopes and frozen seal only** and never accesses private gold.

## State machine / conditional paths

1. `verify_frozen_origin`: verify immutable source hashes, 8/10 S4 structural identifiability upper bound and audit the scoped successor's actual raw-model hash; **re-execute frozen Phase1 TCC V2**. Missing, changed, failed, or unrecognized evidence → `blocked_integrity`.
2. `audit_suite_ecv4`: run actual suite/ECv4 method audit and require both PASS; any failure → `blocked_integrity`.
3. `route_original_scope`: `EC_NATIVE_SCOPE_INCOMPATIBLE` → `verify_scoped_successor`. Any undocumented change/claim of original end-to-end A–E completion → `blocked_integrity`, never a fabricated pass.
4. `verify_scoped_successor`: require the audited, pinned, **restricted** S1C finite-typed-space evidence and preserved limitations. A successful scoped result is **not** original #1 closure.
5. `check_blind_study`: validate any new external **public** files / commitments / arm envelopes / seal. Lack of them → `scoped_verified_external_missing` (blocked). Even structural completeness → `scoped_verified_external_review` (success **only of this subworkflow**, not independent scientific certification).
6. `route_external_evidence`: always label unverified independent label custody and original scientific four-arm completion separately. The TCC output contains ECv4 evidence for the actual branch path.

**Genuine user-independent original completion is not currently possible:** frozen S3 multi-selection semantics diverge from EC native singleton next action; frozen S3 is insufficient to determine S4 closure. Repair-in-place invalidates original experiment, and falsely labeling harness code as EC-native is forbidden. The separately frozen replacement boundary already has a narrower audited terminal.

The remaining scientific work requires a newly authorized, semantically matched **versioned** EC-native/LLM experimental contract, a genuinely unseen independently adjudicated corpus, properly frozen real model outputs, and external provenance review. Self-authored labels or self-asserted independent custody are not substitutes. Until those exist, the only truthful workflow result is a documented **BLOCKED** original issue and **COMPLETE_FOR_CURRENT_MVP_BOUNDARY** scoped successor.

## Verification and resumption

- Actual first-run generated an 8-node TCC DAG, then the method audit step was integrated to produce 9 nodes / 12 edges. TCC generated from pinned source/semantic facts, no undisclosed node insertion.
- The 10 dedicated automation-regression tests cover source pins, branch policy, refusal of fake science, forged scope, no task creation, and missing vs structurally ready external files. Along with 82 other applicable tests, **92 total passed** locally on 2026-10-10.
- `results/issue1_autonomous_tcc_verified_2026-10-10.json` is the immutable verified current-run snapshot. Subsequent runs may supply legitimate new evidence, but the runner does **not** change the original acceptance criteria. A truly new experiment needs its own versioned protocol.
- Every invocation terminates; there is no idle polling, retry storm, background timer or attempt to manipulate this ChatGPT thread's UI. Output is atomically written (`.tmp` then replace) so partial JSON is not treated as accepted evidence.
