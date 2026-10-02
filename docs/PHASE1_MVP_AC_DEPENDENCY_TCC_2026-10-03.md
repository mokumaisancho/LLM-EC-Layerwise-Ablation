# Phase1 MVP — AC Dependency DAG and One-Shot TCC

Protocol: `PHASE1_MVP_TCC_V1`
Date: 2026-10-03

## 1. MVP

Phase1 MVP = minimum scientifically reportable **coarse localization** of where a lightweight LLM remains necessary versus deterministic EC.

Allowed localization outputs:
- `MVP_COARSE_LOCALIZED:<S1|S2|S3|S4>`
- `MVP_NO_MATERIAL_LAYER`
- `MVP_AMBIGUOUS_DOMINANT_LAYER`

Fine decomposition is post-MVP.

MVP boundary:
- S1: LLM + Oracle intervention.
- S2: LLM + Oracle intervention.
- S3: LLM vs ECv4.4-native behavior through a qualified oracle-blind adapter + Oracle intervention.
- S4: LLM vs ECv4.4-native behavior through a qualified oracle-blind adapter + Oracle intervention.
- New deterministic EC S1/S2 is post-MVP only if coarse localization makes it relevant.
- Qwen3-4B is optional final reference only.

## 2. Frozen decision rules

Operational MVP thresholds only; not statistical-significance claims.

`oracle_substitution_gain(L) = final_success(do(L=Oracle)) - final_success(baseline)`

Material when:
- Oracle substitution gain >= 0.20; or
- for S3/S4, absolute LLM-vs-EC joint-layer difference >= 0.20 with identical upstream hashes.

Rules:
- 0.10 one-fixture movement is non-material.
- no material layer -> `MVP_NO_MATERIAL_LAYER`.
- unique material maximum -> `MVP_COARSE_LOCALIZED:<layer>`.
- material maxima within 0.10 -> `MVP_AMBIGUOUS_DOMINANT_LAYER`; no manual tie break.

~1.5B is run exactly once only when a valid schema-constrained ~0.5B run has decision-family collapse:
- Oracle classes >=2;
- model modal-class share >=0.90;
- family accuracy <=0.60.

Output-contract failure -> `INVALID_LLM_OUTPUT_CONTRACT`, not capacity escalation.
No automatic 4B branch.

## 3. AC dependency DAG

Foundation:
`AC-19 -> AC-02 -> AC-01 -> AC-07 -> AC-17 -> AC-16`

Global invariant: `AC-20` (GitHub Actions disabled/not required).

Coverage:
- AC-03 <- AC-02/19 + #22.
- AC-04 <- AC-02/03.
- AC-11 <- #23 + #20.
- AC-12 <- AC-04/11.
- AC-13 <- #12 + #22.
- AC-14 <- AC-01/13.
- AC-15 constrains Phase1 to lightweight models.

Localization:
- AC-05 <- AC-01/03/04/07/17 + #22 + #24.
- AC-06 <- AC-04/05/11/12/16/17.
- AC-08 <- AC-05/06 + #21.
- AC-09 <- AC-05/08 + #21.

Post-MVP:
- AC-10 <- AC-08/09/19.
- AC-18 requires AC-10 refinement only if coarse MVP does not already establish the final boundary.

Required at MVP exit:
`AC-01,02,03,04,05,06,07,08,09,11,12,13,14,15,16,17,19,20`.

No AC may PASS if an upstream dependency is FAIL/UNKNOWN.

## 4. Critical issue DAG

Completed:
- #12 format-contract vs semantic-scoring separation.
- #21 materiality/capacity thresholds.

Open critical path:
- #23 oracle-blind EC-native S3/S4 adapter.
- #20 reportable actual ECv4.4 binding; depends on #23.
- #24 hash-preserving Oracle intervention semantics; required by E arm/AC-17.
- #22 LLM S1/S2 + A/B/E + intervention/gain runner; depends on #12/#24.
- #14 frozen ~0.5B capacity run; depends on #12 + `0P5B_MODEL_READY`.
- #9 C/D fixed-candidate comparison; depends on #14/#20/#23.
- #1 Phase1 MVP umbrella; depends on #9/#21/#22 + complete A-E/gain.

#11 is not on the MVP critical path.

### 0.5B ingress is OR, not sequential

`0P5B_MODEL_READY` is satisfied by any one verified non-Drive path:
1. already verified sandbox artifact;
2. connector-native non-Drive materialization;
3. directly attachable Generic Binary Ingress;
4. GitHub text-shard fallback for 0.5B;
5. another exact size/SHA verified non-Drive route.

#16/#17/#18/#19 are alternative implementations of that OR dependency.
Google Drive model relay is prohibited.

## 5. EC-native authority gate

Pinned EC source:
- repo `mokumaisancho/GPT-EC-Closure-Engine`
- commit `d5ec423968f1c9242c590e5e77ccfd92d1f59eb2`

Verified native components include:
- `EC_V4_4_RESIDUAL_DETECTOR_V1`
- `EC_V4_4_FRAMING_SEARCH_V1`
- `EC_V4_4_CONTROL_PLANE_V1`
- EC atomic closure runtime.

The generic Phase1 candidate-set contract is not identical to the EC remediation-plan contract.
Therefore a residual-detector-only binding is not sufficient to call the whole S3/S4 result actual ECv4.4.

`PHASE1_EC_NATIVE_ADAPTER_V1` must:
- be deterministic and oracle-blind;
- consume only model-visible/frozen upstream artifacts;
- expose per-subfunction authority (`EC_NATIVE`, `ADAPTER`, `EC_NATIVE_NOT_APPLICABLE`);
- never label harness-local candidate selection/closure as ECv4.4;
- record semantic incompatibility as an experimental result instead of hiding it.

Failure -> `BLOCKED_EC_NATIVE_ADAPTER` or `EC_NATIVE_SCOPE_INCOMPATIBLE`.

## 6. Oracle intervention gate

E arm is `do(layer=Oracle)`, not replacement with a canonical Oracle file whose upstream hash differs.

`PHASE1_ORACLE_INTERVENTION_V1` rules:
- S1: task fixed; Oracle S1; rerun S2-S4 unchanged.
- S2: actual S1 hash fixed; intervention S2 references that exact S1 hash; rerun S3-S4 unchanged.
- S3: actual S2/state fixed; Oracle may select only candidate IDs present upstream. If correct candidate is absent -> `INTERVENTION_NOT_IDENTIFIABLE_UPSTREAM_DEFICIT`; do not invent it. Rerun S4 unchanged.
- S4: actual S3 fixed; only execution/closure changes. Upstream selection errors remain errors.

Every intervention records target layer, baseline run, upstream hashes, oracle authority, and intervention provenance.
Hash mismatch -> `UPSTREAM_HASH_MISMATCH`.

## 7. One-shot TCC

`P0 PRECHECK`
-> `P1 FOUNDATION_GATE`
-> `P2 EC_ADAPTER_GATE`
-> `P3 EC_BIND_GATE`
-> `P4 HARNESS_GATE`
-> `P5 LLM_ASSET_GATE`
-> `P6 LLM_CACHE_GATE`
-> `P7 A_B_C_D_E_RUN`
-> `P8 SCORE_AND_GAIN`
-> `P9 LOCALIZE`
-> `P10 EXIT_GATE`

### P0 PRECHECK
Check all static dependencies together: Actions, protocol, threshold contract, implementation files, canonical expected provenance.
Any unresolved static contract -> `INVALID_TEST_CONTRACT`.

### P1 FOUNDATION_GATE
Require:
- Phase1 v2 only;
- leakage 0;
- Oracle replay 10/10;
- schema/hash-chain PASS;
- dataset digest `8bfce027bdc82a34b78e9b1a87f7812d907db34c164f50a9a996bd41b3b824d6`.
Mismatch -> `INVALID_TEST_CONTRACT`.

### P2 EC_ADAPTER_GATE
Require qualified `PHASE1_EC_NATIVE_ADAPTER_V1`.
Missing/unqualified -> `BLOCKED_EC_NATIVE_ADAPTER`.
Proven semantic incompatibility -> `EC_NATIVE_SCOPE_INCOMPATIBLE`.

### P3 EC_BIND_GATE
Require exact EC repo/commit/protocol/module provenance through the qualified adapter.
Fallback/mismatch -> `BLOCKED_EC_BINDING`.

### P4 HARNESS_GATE
Require raw vs schema-constrained separation, semantic scoring only for contract-valid schema-constrained output, cache/provenance, and `PHASE1_ORACLE_INTERVENTION_V1`.
Failure -> `INVALID_TEST_CONTRACT`.

### P5 LLM_ASSET_GATE
First capacity point: Qwen2.5-0.5B Q4_K_M or frozen equivalent.
Known Qwen2.5 artifact: 397,808,192 bytes; SHA-256 `6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653`.
Use the predeclared non-Drive OR routes only.
No route -> `BLOCKED_0P5B_INGRESS`.
Mismatch -> `INTEGRITY_FAILED`.

### P6 LLM_CACHE_GATE
Run inference once and cache.
Raw arm = capability evidence only.
Schema-constrained arm = semantic measurement.
Valid collapse -> ~1.5B exactly once.
Invalid schema arm -> `INVALID_LLM_OUTPUT_CONTRACT`.
1.5B still collapsed -> `CAPACITY_LIMIT_AFTER_1P5B`.

### P7 A_B_C_D_E_RUN
- A: LLM S1/S2 -> LLM S3/S4.
- B: identical cached LLM S1/S2 -> EC-native qualified S3/S4.
- C: fixed controlled upstream -> LLM S3/S4.
- D: identical fixed controlled upstream -> EC-native qualified S3/S4.
- E: `do(S1=Oracle)`, `do(S2=Oracle)`, `do(S3=Oracle)`, `do(S4=Oracle)` independently under the intervention contract.

No silent upstream regeneration.
Any controlled-pair hash mismatch -> `UPSTREAM_HASH_MISMATCH`.

### P8 SCORE_AND_GAIN
Compute layer-native metrics, final success, and per-layer intervention gain.
Incomplete/non-provenanced result -> `INVALID_TEST_CONTRACT`.

### P9 LOCALIZE
Apply only frozen section-2 thresholds.
No manual threshold/tie changes.

### P10 EXIT_GATE
Allowed terminals:
- `MVP_COARSE_LOCALIZED:S1|S2|S3|S4`
- `MVP_NO_MATERIAL_LAYER`
- `MVP_AMBIGUOUS_DOMINANT_LAYER`
- `BLOCKED_EC_NATIVE_ADAPTER`
- `EC_NATIVE_SCOPE_INCOMPATIBLE`
- `BLOCKED_EC_BINDING`
- `BLOCKED_0P5B_INGRESS`
- `INVALID_TEST_CONTRACT`
- `INVALID_LLM_OUTPUT_CONTRACT`
- `UPSTREAM_HASH_MISMATCH`
- `INTEGRITY_FAILED`
- `CAPACITY_LIMIT_AFTER_1P5B`
- `FAIL_CLOSED_UNKNOWN`

Unexpected condition -> `FAIL_CLOSED_UNKNOWN`; no branch may be invented during the run.

## 8. Execution discipline

- Independent prechecks may run in parallel.
- Model/runtime/transport/intervention/scoring changes are sequential authority-bound transitions.
- No mid-run prompt, fixture, threshold, or schema repair.
- Newly discovered blocking residual -> Registry first -> fail closed -> new versioned contract if methodology changes.
- One final report only after a terminal state.
