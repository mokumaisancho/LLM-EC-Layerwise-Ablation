# Phase1 MVP — AC Dependency DAG and One-Shot TCC

Protocol: `PHASE1_MVP_TCC_V1`
Date: 2026-10-03

## 1. MVP definition

The Phase1 MVP is the **minimum scientifically reportable coarse localization** of where a lightweight LLM remains necessary versus deterministic EC.

MVP output is one of:
- `MVP_COARSE_LOCALIZED:<S1|S2|S3|S4>`
- `MVP_NO_MATERIAL_LAYER`
- `MVP_AMBIGUOUS_DOMINANT_LAYER`

The MVP does **not** require fine decomposition of the selected layer. Fine decomposition begins only after the MVP exit gate.

### MVP architecture boundary
- S1: LLM + Oracle intervention.
- S2: LLM + Oracle intervention.
- S3: LLM vs actual ECv4.4 + Oracle intervention.
- S4: LLM vs actual ECv4.4 + Oracle intervention.
- A/B/C/D/E are all measured.
- New deterministic EC S1/S2 implementation is **out of MVP scope**. If coarse localization later shows S1/S2 to be the relevant boundary, deterministic alternatives may be added as a versioned post-MVP experiment.
- Qwen3-4B is **not an MVP dependency**. It is optional final-reference validation only.

## 2. Frozen materiality and capacity rules

These are operational MVP decision thresholds, not claims of statistical significance.

### Layer materiality
For each layer L:

`oracle_substitution_gain(L) = final_task_success(Oracle substituted only at L) - final_task_success(baseline)`

A layer is material when:
- `oracle_substitution_gain >= 0.20`, i.e. >=2 of the 10 frozen fixtures change from failure to success; or
- for S3/S4, the absolute LLM-vs-EC joint layer-success difference is `>= 0.20` while upstream hashes are identical.

A 0.10 one-fixture movement is non-material for dominant-layer selection.

### Dominant-layer selection
- No material layer -> `MVP_NO_MATERIAL_LAYER`.
- One unique maximum -> `MVP_COARSE_LOCALIZED:<layer>`.
- Two or more material layers whose gains differ by `<=0.10` -> `MVP_AMBIGUOUS_DOMINANT_LAYER`; do not manually break the tie.

### 0.5B capacity ambiguity
Automatic escalation to ~1.5B is authorized only when the schema-constrained ~0.5B arm is structurally valid but shows decision-family collapse:
- Oracle has >=2 classes for a decision family; and
- model modal-class share >=0.90; and
- accuracy for that family <=0.60.

If true for any core decision family, run exactly one predeclared ~1.5B capacity branch with unchanged fixtures/scoring. No automatic 4B escalation.

Output-contract failure is not capacity ambiguity. It is `INVALID_LLM_OUTPUT_CONTRACT` after the schema-constrained arm fails.

## 3. AC dependency DAG

### Foundation chain
`AC-19 protocol/schema version`
-> `AC-02 serialized replayable layer artifacts`
-> `AC-01 identical persisted upstream artifacts`
-> `AC-07 frozen upstream artifacts`
-> `AC-17 controlled one-layer intervention`
-> `AC-16 causal attribution may be claimed`

`AC-20` is a global invariant: GitHub Actions stay disabled.

### Coverage and measurement
- `AC-03` depends on AC-02/19 plus Issue #22 (S1/S2 + Oracle substitution runner).
- `AC-04` depends on AC-02/03 and the scoring harness.
- `AC-11` depends on actual ECv4.4 binding (Issue #20).
- `AC-12` depends on AC-04/11 plus reportable S3/S4 runs.
- `AC-13` depends on LLM provenance/caching runners and Issue #12 output-contract separation.
- `AC-14` depends on cached LLM outputs and stable upstream hashes.
- `AC-15` constrains MVP model selection: lightweight model is sufficient; large LLM cannot block Phase1.

### Localization
- `AC-05` depends on AC-01/03/04/07/17 plus Issue #22.
- `AC-06` depends on AC-04/05/11/12/16/17.
- `AC-08` depends on AC-05/06 plus the frozen materiality contract (Issue #21).
- `AC-09` depends on AC-05/08 plus the frozen threshold/tie rules.

### Post-MVP
- `AC-10` depends on AC-08/09/19 and applies to the selected fine decomposition.
- `AC-18` is the overall-study completion criterion. It may be satisfied by the coarse MVP only if the result already establishes a smallest necessary LLM layer or largest contiguous EC-replaceable downstream region; otherwise it depends on AC-10 refinement.

## 4. MVP AC set

Required at MVP exit:
`AC-01,02,03,04,05,06,07,08,09,11,12,13,14,15,16,17,19,20`.

Post-MVP by default:
`AC-10,18`.

No AC may be marked PASS when any upstream dependency in this DAG is FAIL/UNKNOWN.

## 5. Issue dependency map

### Critical path
- #20 Actual ECv4.4 binding, fail-closed provenance -> required before reportable EC S3/S4.
- #12 Separate format-contract compliance from semantic scoring -> required before reportable LLM semantic metrics.
- #21 Freeze materiality/capacity thresholds -> required before reading 0.5B measurement outcomes.
- #22 Implement LLM S1/S2 and per-layer Oracle substitution -> required before A/B/E and AC-03/05/08 closure.
- #14 Run frozen ~0.5B capacity sweep -> requires a valid 0.5B asset/runtime path and #12.
- #9 Fixed-candidate C/D comparison -> requires #12 + #14 + #20.
- #1 Phase1 coarse localization umbrella -> requires #9 + #22 + #21 and complete A/B/C/D/E scoring.

### Asset ingress is an OR dependency
The logical dependency is `0P5B_MODEL_READY`, not any single transport issue.

`0P5B_MODEL_READY = existing verified sandbox file OR connector-native materialization OR Generic Binary Ingress attachment OR GitHub text-shard fallback OR another verified non-Drive route`.

Issues #16/#17/#18/#19 are alternative transport implementations. They are not a sequential chain and none individually blocks the MVP if another verified route satisfies `0P5B_MODEL_READY`.

#11 is legacy ingress namespace hardening and is not on the Phase1 MVP critical path.

Qwen3-4B ingress is not on the Phase1 MVP critical path.

## 6. One-shot TCC state machine

`P0 PRECHECK`
-> `P1 FOUNDATION_GATE`
-> `P2 EC_BIND_GATE`
-> `P3 HARNESS_GATE`
-> `P4 LLM_ASSET_GATE`
-> `P5 LLM_CACHE_GATE`
-> `P6 A_B_C_D_E_RUN`
-> `P7 SCORE_AND_GAIN`
-> `P8 LOCALIZE`
-> `P9 EXIT_GATE`

### P0 PRECHECK
Verify:
- GitHub Actions disabled/not required.
- Phase1 v2 only; no v1/v2 pooling.
- frozen threshold contract exists.
- canonical model/EC provenance expected values are configured.
Failure -> `INVALID_TEST_CONTRACT`.

### P1 FOUNDATION_GATE
Verify/regenerate only from the frozen generator:
- Phase1 v2 fixtures.
- schema validation.
- leakage scan = 0.
- Oracle replay = 10/10.
- canonical dataset digest = `8bfce027bdc82a34b78e9b1a87f7812d907db34c164f50a9a996bd41b3b824d6`.
Mismatch -> `INVALID_TEST_CONTRACT`.

### P2 EC_BIND_GATE
Required actual EC:
- repo: `mokumaisancho/GPT-EC-Closure-Engine`
- pinned candidate commit: `d5ec423968f1c9242c590e5e77ccfd92d1f59eb2`
- protocol: `EC_V4_4_RESIDUAL_DETECTOR_V1`

Any fallback mode or provenance mismatch -> `BLOCKED_EC_BINDING`.
No fallback result is reportable.

### P3 HARNESS_GATE
Require:
- raw-output `format_contract_ok` recorded separately.
- schema-constrained arm available.
- semantic metrics scored only on contract-valid outputs.
- model/runtime/decoding/raw-output hash recorded.
Failure -> `INVALID_TEST_CONTRACT`.

### P4 LLM_ASSET_GATE
Target first capacity point:
- Qwen2.5-0.5B-Instruct Q4_K_M or the already-frozen equivalent 0.5B candidate.
- expected known artifact if Qwen2.5 is used: 397,808,192 bytes; SHA-256 `6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653`.

Route order:
1. already materialized sandbox artifact with exact size/SHA;
2. connector-native non-Drive file reference/materialization;
3. directly attachable Generic Binary Ingress;
4. GitHub text-shard fallback for the 0.5B artifact;
5. otherwise stop `BLOCKED_0P5B_INGRESS`.

Google Drive persistence/relay is prohibited for model ingress in this TCC.

### P5 LLM_CACHE_GATE
Run model inference once and cache outputs.
- Raw arm is a capability record only.
- Schema-constrained arm supplies semantic metrics.
- If schema-constrained contract fails -> `INVALID_LLM_OUTPUT_CONTRACT`.
- If valid and capacity-collapse rule fires -> run ~1.5B once with unchanged assay.
- If ~1.5B also collapses -> `CAPACITY_LIMIT_AFTER_1P5B`; no architecture-level conclusion.

### P6 A_B_C_D_E_RUN
A: LLM S1/S2 -> LLM S3/S4.
B: identical cached LLM S1/S2 -> actual ECv4.4 S3/S4.
C: frozen Oracle S2/S3 upstream -> LLM S3/S4.
D: identical frozen Oracle S2/S3 upstream -> actual ECv4.4 S3/S4.
E: substitute Oracle at exactly one of S1/S2/S3/S4 per run.

Any paired upstream hash mismatch -> `UPSTREAM_HASH_MISMATCH`.
No silent regeneration is allowed.

### P7 SCORE_AND_GAIN
Compute layer-native metrics plus final-task success and per-layer Oracle substitution gain.
All result records must include protocol/schema version and provenance hashes.
Incomplete results -> `INVALID_TEST_CONTRACT`.

### P8 LOCALIZE
Apply only the frozen thresholds in section 2.
No manual tie breaking or threshold changes.

### P9 EXIT_GATE
Allowed terminal states only:
- `MVP_COARSE_LOCALIZED:S1`
- `MVP_COARSE_LOCALIZED:S2`
- `MVP_COARSE_LOCALIZED:S3`
- `MVP_COARSE_LOCALIZED:S4`
- `MVP_NO_MATERIAL_LAYER`
- `MVP_AMBIGUOUS_DOMINANT_LAYER`
- `BLOCKED_EC_BINDING`
- `BLOCKED_0P5B_INGRESS`
- `INVALID_TEST_CONTRACT`
- `INVALID_LLM_OUTPUT_CONTRACT`
- `UPSTREAM_HASH_MISMATCH`
- `INTEGRITY_FAILED`
- `CAPACITY_LIMIT_AFTER_1P5B`

Any unexpected condition -> `FAIL_CLOSED_UNKNOWN`; no new branch may be invented during execution.

## 7. Execution discipline

- Independent PRECHECK evidence checks may run in parallel.
- Any branch that changes model, runtime, transport, intervention, or scoring is sequential and authority-bound.
- No manual mid-run prompt/fixture/threshold repair.
- Newly discovered blocking residual: register issue first, terminate `FAIL_CLOSED_UNKNOWN`, then version the next TCC contract rather than mutating this run.
- One final report only after a terminal state.