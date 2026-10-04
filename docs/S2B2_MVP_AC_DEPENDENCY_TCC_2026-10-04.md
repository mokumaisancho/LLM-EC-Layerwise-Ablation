# S2B2 MVP — AC Dependency DAG and One-Shot TCC

Protocol: `S2B2_MVP_TCC_V1`
Date: 2026-10-04
Owner issue: #43
Parent evidence state: validation repair #39/#40 complete; boundary map V8.

## 1. Research split

S2B2 is split before execution and the two claims MUST NOT be pooled.

- Stage A / `S2B2A_COMPOSITION`: the correct candidate instance is absent from the candidate list, but its action primitive and semantic vocabulary already exist. Question: can an engine construct the missing candidate from known primitives?
- Stage B / `S2B2B_NEW_CLASS`: the required action-class semantic signature is absent from the supplied primitive ontology. Question: can an engine propose a new structured action class that satisfies hidden semantic requirements?

Stage B is not evidence for unconstrained raw-language ontology induction. That remains a separate unresolved S1A/generative question.

## 2. MVP

### MVP-A
Minimum scientifically reportable Stage-A result:
1. 16 frozen fixtures from 8 structural families not reused from the previous metadata-blind S2B assay.
2. correct candidate instances absent from `existing_candidates`.
3. frozen deterministic composition core and Qwen2.5-1.5B consume the same visible semantic contract.
4. hidden Oracle is produced by an independent declarative transition evaluator, never by the deterministic predictor.
5. paired metrics: semantic candidate recall/precision/F1, exact set, invalid output, fail-open, per-family metrics.
6. all contamination/provenance gates PASS.

### MVP-B
Minimum scientifically reportable Stage-B result, executed only after a valid MVP-A terminal:
1. 16 frozen fixtures from 8 new structural families.
2. required action-class semantic signature is absent from supplied primitive ontology, not merely renamed.
3. deterministic arm is immutable and must fail closed when no authorized known-class composition exists.
4. Qwen2.5-1.5B emits a fixed structured class schema; class name wording is not scored.
5. hidden Oracle scores preconditions/effects/constraints/parameter semantics through an independent evaluator.
6. all contamination/provenance gates PASS.

### Full #43 MVP exit
Both MVP-A and MVP-B have valid terminal measurements and the machine boundary map is version-advanced once. Raw-language relation/operator induction, natural-corpus replication, open-ended realization, 4B, and model-capacity sweeps are outside this MVP.

## 3. Global AC dependencies

The repository AC remains normative. Local gates refine it, not replace it.

Foundation DAG:
`AC-19 -> AC-02 -> AC-01 -> AC-07 -> AC-17 -> AC-16`

S2B2 requires:
- `AC-01`: paired engines receive identical persisted visible inputs.
- `AC-02`: fixture, visible contract, output, Oracle, and result are fixed machine-readable artifacts.
- `AC-04`: candidate generation metrics remain separate from downstream selection metrics.
- `AC-06`: failures remain attributable to composition vs new-class synthesis; no layer pooling.
- `AC-07`: no upstream/fixture regeneration during a comparison.
- `AC-10`: methodology changes require a new version; failed run is never repaired in place.
- `AC-13`: Qwen model/runtime/decoding/raw-output provenance is recorded.
- `AC-14`: Qwen output is cached once and replayed for scoring.
- `AC-16`: no end-to-end score is used as layer-causal evidence.
- `AC-17`: only the engine changes inside each paired Stage-A comparison.
- `AC-19`: protocol/schema/fixture/generator/scorer versions and hashes are recorded.
- `AC-20`: GitHub Actions remain disabled/not required.

Local AC DAG:
- `S2B2-AC01_SCOPE_SPLIT` <- AC-04, AC-06, AC-16
- `S2B2-AC02_FREEZE_ORDER` <- AC-07, AC-10, AC-19
- `S2B2-AC03_VISIBLE_IDENTITY` <- AC-01, AC-02, AC-07, AC-17
- `S2B2-AC04_ORACLE_INDEPENDENCE` <- AC-02, AC-16, AC-17, AC-19
- `S2B2-AC05_NO_LEAKAGE` <- S2B2-AC03, S2B2-AC04
- `S2B2-AC06_STRUCTURAL_DISJOINTNESS` <- AC-10, AC-19
- `S2B2-AC07_STAGE_A_MISSING_CANDIDATE` <- S2B2-AC05, S2B2-AC06
- `S2B2-AC08_STAGE_A_KNOWN_PRIMITIVE` <- S2B2-AC07
- `S2B2-AC09_PAIRED_OUTPUT_CONTRACT` <- AC-01, AC-13, AC-14, AC-17
- `S2B2-AC10_METRIC_COMPLETENESS` <- AC-04, AC-06, S2B2-AC09
- `S2B2-AC11_STAGE_B_SEMANTIC_ABSENCE` <- S2B2-AC02, S2B2-AC04, S2B2-AC06
- `S2B2-AC12_STAGE_B_FAIL_CLOSED` <- S2B2-AC11
- `S2B2-AC13_PROVENANCE_CHAIN` <- AC-13, AC-14, AC-19
- `S2B2-AC14_REGRESSION_GATES` <- all above

No local AC may PASS if any upstream dependency is FAIL or UNKNOWN.

## 4. Issue dependency DAG

Completed prerequisites:
- #39 validation repair: corrected S1A independence, S2A budget mismatch, S2B metadata leakage.
- #40 regression gates for repaired validation.
- #42 prospective S1A partition; contextual evidence only, not a hard Stage-A execution dependency.

Current #43 dependency chain:
`#39 COMPLETE + #40 COMPLETE`
-> `S2B2A core freeze c83632855cc775b8502e6a1ded18a3f3b022f19a`
-> `this TCC contract freeze`
-> `Stage-A generator freeze`
-> `Stage-A fixture manifest/digest freeze`
-> `Stage-A independent Oracle/scorer freeze`
-> `Stage-A Qwen wrapper/output-contract freeze`
-> `Stage-A pre-inference gate`
-> `Stage-A deterministic + Qwen paired execution`
-> `Stage-A scoring + terminal`
-> `Stage-B generator/schema/scorer freeze`
-> `Stage-B pre-inference semantic-absence gate`
-> `Stage-B deterministic fail-closed + Qwen execution`
-> `Stage-B scoring + terminal`
-> `boundary map version advance`
-> `#43 close`.

## 5. Frozen assets and model

Stage-A deterministic core is already frozen before fixture generation:
`tools/s2b2a_composition_core.py`
commit `c83632855cc775b8502e6a1ded18a3f3b022f19a`.

Qwen reference is pinned to the already-qualified artifact:
- `bartowski/Qwen2.5-1.5B-Instruct-GGUF`
- `Qwen2.5-1.5B-Instruct-Q4_K_M.gguf`
- size `986048768`
- SHA-256 `1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370`
- temperature `0`
- llama.cpp `b11146`

No model substitution is allowed mid-run. Missing pinned execution path -> `BLOCKED_QWEN1P5B_EXECUTION`.

## 6. Error-exclusion gates

These gates exist specifically to prevent a later audit from overturning the measurement.

### G0 AUTHORITY/PREDECESSOR
Require #39/#40 complete, V8 or later canonical boundary state, Actions disabled, no Drive model relay.
Fail -> `INVALID_PREDECESSOR_STATE`.

### G1 FREEZE ORDER
Require commit order:
`composition core < TCC contract < generator < manifest/digest < Oracle/scorer < Qwen wrapper < inference/result`.
No file affecting visible data, prediction, Oracle, scoring, thresholds, or output grammar may change after its freeze point.
Fail -> `FREEZE_ORDER_VIOLATION`.

### G2 STRUCTURAL DISJOINTNESS
Stage-A and Stage-B family fingerprints must be disjoint from the eight metadata-blind S2B fixtures and from each other. Renaming entities/IDs alone does not count as disjointness.
Fail -> `HOLDOUT_NOT_INDEPENDENT`.

### G3 LEAKAGE / VISIBLE ALLOWLIST
Recursive visible-input scan. Forbidden unless explicitly allowed by the stage schema: `gold`, `oracle`, `expected`, `label`, `family`, `category`, `forbidden`, hidden outcome classes, scorer annotations.
Stage A may expose primitive `action_class` because known primitives are the tested premise; candidate-level hidden action metadata is prohibited.
Fail -> `ORACLE_OR_LABEL_LEAKAGE`.

### G4 ORACLE INDEPENDENCE / CIRCULARITY
Generator/scorer MUST NOT import or invoke `s2b2a_composition_core` to construct gold. Oracle gold is derived by an independent declarative transition evaluator: instantiate semantic action, verify all preconditions, apply effects, then check ALL required effects and NO forbidden resulting effects/constraints.
Static import/reference scan plus independent recomputation required.
Fail -> `CIRCULAR_ORACLE`.

### G5 STAGE-A MISSING-CANDIDATE
No Oracle-gold semantic candidate may already occur in `existing_candidates` after canonical semantic normalization.
Fail -> `GOLD_ALREADY_PRESENT`.

### G6 STAGE-A KNOWN-PRIMITIVE PREMISE
Every hidden gold Stage-A candidate must use an action class already present in the frozen primitive ontology and parameter values allowed by the visible domains. This gate checks the premise only; it MUST NOT call the deterministic predictor to decide gold.
Fail -> `INVALID_STAGE_A_FIXTURE`.

### G7 SAME VISIBLE INPUT / SAME OUTPUT CONTRACT
For each Stage-A fixture, deterministic and Qwen arms use byte-identical canonical visible input hash and the same semantic candidate-object schema. No per-arm prompt facts, ontology, targets, constraints, or candidate budget changes.
Fail -> `PAIRED_CONTRACT_MISMATCH`.

### G8 QWEN PROVENANCE/CACHE
Require exact model size/SHA, runtime tag, decoding parameters, raw output hash, schema-valid cached output. Inference occurs once per frozen fixture set; rescoring uses cache.
Fail -> `MODEL_OR_CACHE_PROVENANCE_INVALID`.

### G9 METRIC RECOMPUTATION
Recompute TP/emitted/gold totals from per-fixture records. Aggregate recall/precision/F1/exact/fail-open must exactly match recomputation. Per-family totals must sum to global totals.
Fail -> `METRIC_INCONSISTENCY`.

### G10 STAGE-B SEMANTIC ABSENCE
Before Stage-B inference, prove no supplied primitive has an equivalent semantic signature to the required hidden class (parameter roles + preconditions + effects + constraints), regardless of class name. Name-only absence is insufficient.
Fail -> `ONTOLOGY_CLASS_NOT_ACTUALLY_NOVEL`.

### G11 STAGE-B FAIL-CLOSED AUTHORITY
Deterministic Stage-B arm may not mutate the ontology or synthesize an unauthorized class. No authorized known composition -> exactly `FAIL_CLOSED_NO_AUTHORIZED_CLASS`.
Unexpected deterministic class creation -> `UNAUTHORIZED_ONTOLOGY_MUTATION`.

### G12 NO POST-RESULT REPAIR
Any gate failure or unexpected condition is terminal for this protocol version. Do not modify prompt, fixture, primitive set, scorer, threshold, grammar, or predictor and resume under V1. Register residual, create V2, refreeze from the appropriate upstream point.
Unexpected -> `FAIL_CLOSED_UNKNOWN`.

## 7. Scoring and decision rules

Stage A metrics, separately for deterministic and Qwen:
- semantic candidate recall
- semantic candidate precision
- semantic candidate F1
- exact structured candidate-set rate
- invalid output count
- fail-open/forbidden generation count
- per-family values

Paired primary comparison = semantic candidate F1. Existing materiality threshold remains absolute `0.20`; no new threshold is introduced.

Stage-A terminals after all gates pass:
- delta `deterministic - Qwen >= 0.20` -> `STAGE_A_DETERMINISTIC_MATERIAL_ADVANTAGE`
- delta `Qwen - deterministic >= 0.20` -> `STAGE_A_LLM_MATERIAL_ADVANTAGE`
- otherwise -> `STAGE_A_NO_MATERIAL_SEPARATION`

Absolute scores are always reported. These terminals describe comparative separation, not universal capability.

Stage B is not scored as a symmetric race. Deterministic fail-closed is the required baseline when the ontology lacks an authorized class. Qwen outcome per fixture is one of:
- `NOVEL_CLASS_PROPOSED_AND_ORACLE_VALID`
- `NOVEL_CLASS_INVALID`
- `INVALID_OUTPUT`

The study reports proposal-validity rate, invalid rate, fail-open violations, and per-family results. A valid Qwen proposal proves only new-class synthesis under supplied structured semantic requirements, not unconstrained ontology induction.

## 8. One-shot TCC state machine

`P0_PRECHECK`
-> `P1_CONTRACT_GATE`
-> `P2_STAGE_A_FREEZE_GATE`
-> `P3_STAGE_A_CONTAMINATION_GATE`
-> `P4_STAGE_A_EXECUTE`
-> `P5_STAGE_A_SCORE_AUDIT`
-> `P6_STAGE_A_TERMINAL`
-> `P7_STAGE_B_FREEZE_GATE`
-> `P8_STAGE_B_CONTAMINATION_GATE`
-> `P9_STAGE_B_EXECUTE`
-> `P10_STAGE_B_SCORE_AUDIT`
-> `P11_BOUNDARY_UPDATE`
-> `P12_MVP_EXIT`.

P0: prerequisites/actions/model policy/static files. Failure is terminal.
P1: validate this TCC schema, dependency closure, pinned commits/model, frozen threshold.
P2: require core/generator/manifest/oracle/scorer/Qwen-wrapper freeze order and hashes.
P3: run G2-G9 before any reportable inference. Any failure terminates V1.
P4: run deterministic once; run Qwen once; cache both outputs. No repairs.
P5: recompute metrics independently and verify hashes/totals.
P6: assign exactly one Stage-A terminal from the frozen 0.20 comparison rule. Stage B proceeds for all three valid Stage-A terminals.
P7: freeze Stage-B ontology-absence generator, output schema, independent Oracle/scorer before inference.
P8: run G2-G4 and G10-G11; failure terminates V1.
P9: deterministic fail-closed baseline then one Qwen run; cache raw/schema output.
P10: independent recomputation/audit.
P11: update human and machine boundary state once, based only on audited Stage-A/B results.
P12: close #43 only if all required local AC are PASS.

## 9. Allowed terminal states

Scientific terminals:
- `S2B2_MVP_COMPLETE`
- `STAGE_A_DETERMINISTIC_MATERIAL_ADVANTAGE`
- `STAGE_A_LLM_MATERIAL_ADVANTAGE`
- `STAGE_A_NO_MATERIAL_SEPARATION`

Fail-closed terminals:
- `INVALID_PREDECESSOR_STATE`
- `INVALID_TEST_CONTRACT`
- `FREEZE_ORDER_VIOLATION`
- `HOLDOUT_NOT_INDEPENDENT`
- `ORACLE_OR_LABEL_LEAKAGE`
- `CIRCULAR_ORACLE`
- `GOLD_ALREADY_PRESENT`
- `INVALID_STAGE_A_FIXTURE`
- `PAIRED_CONTRACT_MISMATCH`
- `MODEL_OR_CACHE_PROVENANCE_INVALID`
- `METRIC_INCONSISTENCY`
- `BLOCKED_QWEN1P5B_EXECUTION`
- `ONTOLOGY_CLASS_NOT_ACTUALLY_NOVEL`
- `UNAUTHORIZED_ONTOLOGY_MUTATION`
- `FAIL_CLOSED_UNKNOWN`

A Stage-A scientific terminal is intermediate, not #43 completion. Only `S2B2_MVP_COMPLETE` closes the full MVP.

## 10. Execution invariants

- No GitHub Actions.
- No Google Drive model relay.
- No Qwen3-4B automatic branch.
- No post-result prompt/fixture/scorer/threshold/grammar/predictor change.
- No same-family relexicalization presented as independent holdout.
- No deterministic predictor used to author/compute its own Oracle.
- No candidate metadata hidden from one arm but exposed to the other.
- No name-only ontology novelty claim.
- No Stage-A composition claim reused as Stage-B invention evidence.
- New blocking residual -> Registry first -> fail closed -> versioned successor contract.
