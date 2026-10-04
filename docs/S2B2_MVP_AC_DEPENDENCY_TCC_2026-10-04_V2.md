# S2B2 MVP — AC Dependency DAG and One-Shot TCC V2

Protocol: `S2B2_MVP_TCC_V2`
Date: 2026-10-04
Owner: issue #43
Supersedes: `S2B2_MVP_TCC_V1` and `FUNCTION_BOUNDARY_S2B2B_ONTOLOGY_INVENTION_TCC_V1` for all future causal claims.

## 1. Why V2 exists

Stage A is already measured. The first Stage-B design was stopped before fixture generation because it allowed only Qwen to synthesize a new class while deterministic EC was forced closed-world. Since the target effects/constraints were explicitly visible, that asymmetry would pre-bake a generative advantage.

V2 removes that bias before any Stage-B fixture exists.

The study is now three distinct units:
- `A_AUDIT`: audit the already completed known-primitive candidate composition measurement; no model rerun.
- `B1_EXPLICIT_SCHEMA_SYNTHESIS`: explicit structured requirements are visible; BOTH deterministic synthesis and Qwen may create a new schema.
- `B2_OPERATOR_INDUCTION`: required operator schema is absent and is NOT explicitly copyable from target fields; BOTH engines infer a schema from structured transition examples under the same hypothesis/output contract.

No result may be pooled across A/B1/B2.

## 2. MVP

### A-AUDIT MVP
Accept existing Stage-A evidence only if all pass:
1. frozen dataset digest remains `a58e978a26f86f41ce9b08e36003e08c4682cd144a3d70a5aa945bd539f0f845`;
2. 16 Render raw fixture records reconstruct to TP=9, emitted=16, gold=16, invalid=0, fail-open=7;
3. independent semantic evaluator, which does not import/call `s2b2a_composition_core`, recomputes each gold candidate from visible preconditions/effects and matches the 16 stored Oracles;
4. deterministic frozen core result is recomputed separately and matches 16/16;
5. same fixture/input/candidate budget for both arms is verified;
6. import-path-only repair occurred before any successful inference and changed no methodology.

A-AUDIT terminal: `STAGE_A_AUDIT_PASS` or fail closed. No Stage-A model rerun is required.

### B1 MVP — explicit-requirement schema synthesis
Question: when no supplied primitive satisfies an explicit structured requirement, can a generic deterministic schema synthesizer construct a valid new schema as well as Qwen?

Required:
- deterministic B1 synthesizer frozen BEFORE B1 generator;
- both arms may emit `NEW_CLASS` under the SAME structured output schema;
- same visible target effects/forbidden effects/state/parameter domains/predicate vocabulary;
- no gold schema template/model-visible family label;
- hidden scorer validates semantics, not class name;
- exact same fixture set and inference budget;
- 16 fixtures / 8 structurally new families;
- independent evaluator proves supplied known primitives cannot already satisfy the target.

Primary metric: valid schema proposal rate. Secondary: invalid, forbidden/fail-open, exact semantic signature where identifiable, per-family.
Existing materiality threshold: absolute `0.20` on paired valid-proposal rate difference.

### B2 MVP — operator induction from structured examples
Question: when the required operator is absent from the ontology and is not explicitly spelled out as target effects, can an engine infer a reusable new operator schema from structured transition examples?

B2 avoids an impossible or subjective “world-knowledge invention” test. It uses formal positive/negative transition examples so the hidden operator is objectively identifiable.

Required:
- deterministic B2 hypothesis grammar + bounded enumerative/program-synthesis algorithm frozen BEFORE B2 generator;
- Qwen receives the identical examples, predicate vocabulary, domains, and output schema;
- visible target does NOT contain the complete hidden operator effects/preconditions;
- required semantic operator signature absent from supplied ontology;
- at least 2 positive and 1 negative transition examples per fixture;
- target uses new entities/bindings not occurring as the exact training transition;
- `IDENTIFIABILITY_GATE`: exactly one schema in the frozen hypothesis space is consistent with all visible positive/negative examples; 0 or >1 -> fixture invalid before inference;
- hidden Oracle is that unique semantic signature; name/order not scored;
- 16 fixtures / 8 new structural families disjoint from A and B1.

Primary metric: valid induced-schema rate on the held-out target. Secondary: exact semantic signature, invalid, fail-open, search exhaustion, per-family.

A deterministic miss caused only by the frozen search bound is classified `DETERMINISTIC_SEARCH_BOUND`, not “LLM necessary”.

### Full #43 MVP exit
`A_AUDIT_PASS + valid B1 terminal + valid B2 terminal + one audited boundary-map update`.

Excluded: raw-language relation extraction, natural-corpus replication, unconstrained world-knowledge invention, language realization, Qwen3-4B, capacity sweep.

## 3. Global AC dependency DAG

Normative base:
`AC-19 -> AC-02 -> AC-01 -> AC-07 -> AC-17 -> AC-16`

Required global AC:
`AC-01, AC-02, AC-04, AC-06, AC-07, AC-10, AC-13, AC-14, AC-16, AC-17, AC-19, AC-20`.

Meaning for #43:
- AC-01/17: paired arms receive byte-identical canonical visible artifacts; only engine changes.
- AC-02/19: every contract/generator/fixture/oracle/output/result is versioned and hashed.
- AC-04/06: A composition, B1 schema synthesis, B2 operator induction are scored separately.
- AC-07: no fixture/upstream regeneration within a paired comparison.
- AC-10: methodology repair requires a versioned successor; never resume a failed protocol in place.
- AC-13/14: exact Qwen model/runtime/decoding/raw-output hash; inference cached once.
- AC-16: no end-to-end difference is a layer-causal claim.
- AC-20: no GitHub Actions dependency.

Local AC dependency chain:
`L01_SCOPE`
-> `L02_FREEZE_ORDER`
-> `L03_VISIBLE_IDENTITY`
-> `L04_ORACLE_INDEPENDENCE`
-> `L05_LEAKAGE_ZERO`
-> `L06_STRUCTURAL_DISJOINTNESS`
-> `L07_A_AUDIT_RAW_RECOMPUTABLE`
-> `L08_A_ORACLE_RECOMPUTABLE`
-> `L09_B1_SYMMETRIC_GENERATION_AUTHORITY`
-> `L10_B1_KNOWN_ONTOLOGY_INSUFFICIENT`
-> `L11_B1_PAIRED_OUTPUT_CONTRACT`
-> `L12_B1_METRIC_RECOMPUTATION`
-> `L13_B2_NO_MECHANICAL_TARGET_COPY`
-> `L14_B2_SEMANTIC_NOVELTY`
-> `L15_B2_IDENTIFIABLE_UNIQUE_HYPOTHESIS`
-> `L16_B2_PAIRED_OUTPUT_CONTRACT`
-> `L17_B2_METRIC_RECOMPUTATION`
-> `L18_PROVENANCE_COMPLETE`
-> `L19_BOUNDARY_UPDATE_SINGLE_COMMIT`.

Any upstream FAIL/UNKNOWN prevents downstream PASS.

## 4. Issue dependency graph

Completed prerequisite repairs:
- #39: validation repair.
- #40: regression gates.
- #42: S1A prospective partition; contextual only.

#43 current state:
- Stage-A core freeze `c83632855cc775b8502e6a1ded18a3f3b022f19a`.
- Stage-A generator freeze `f88e37abf64c10e7e56ce61b5b5c9d6fbb09a075`.
- Stage-A paired result `2a93bc38d263850963536bc092f03377cc787b48`.
- Initial Stage-B contract `260eb9aad1d4616fe92566fb697c047b1dc0bb96` is superseded before fixture generation.

Critical path:
`#39/#40 complete`
-> `A independent audit`
-> `B1 deterministic synthesizer freeze`
-> `B1 scorer/output contract freeze`
-> `B1 generator freeze`
-> `B1 contamination/identifiability preflight`
-> `B1 paired execution/cache`
-> `B1 independent score audit`
-> `B2 hypothesis grammar + deterministic synthesizer freeze`
-> `B2 scorer/output contract freeze`
-> `B2 generator freeze`
-> `B2 novelty + identifiability preflight`
-> `B2 paired execution/cache`
-> `B2 independent score audit`
-> `boundary update`
-> `#43 close`.

## 5. Gates that prevent result-overturning errors

### G0 PREDECESSOR/AUTHORITY
Require #39/#40 complete, Actions disabled, no Drive relay, no 4B branch, canonical V8+.
Fail: `INVALID_PREDECESSOR_STATE`.

### G1 SUPERSESSION
V1 and `260eb9...` may be read as historical evidence only. Any executable reference to them as current Stage-B authority fails.
Fail: `SUPERSEDED_CONTRACT_IN_USE`.

### G2 FREEZE ORDER
For each new stage:
`algorithm/grammar -> scorer/output schema -> generator -> manifest/digest -> inference -> result -> boundary update`.
No predictor/prompt/schema/threshold/fixture/scorer changes after its freeze point.
Fail: `FREEZE_ORDER_VIOLATION`.

### G3 LEAKAGE
Predictor-visible artifact recursively forbids oracle/gold/expected/family/category/hidden score annotations. Explicitly authorized semantic requirement fields are allowed only where the stage premise requires them.
Fail: `ORACLE_OR_LABEL_LEAKAGE`.

### G4 ORACLE INDEPENDENCE
Oracle/scorer must not call the tested predictor/synthesizer. Gold/validity is recomputed by an independently implemented transition/schema evaluator.
Fail: `CIRCULAR_ORACLE`.

### G5 STRUCTURAL DISJOINTNESS
Structural fingerprints, not names/IDs, must be disjoint across previous S2B, A, B1, B2. Relexicalization does not count.
Fail: `HOLDOUT_NOT_INDEPENDENT`.

### G6 RAW-CACHE RECOMPUTABILITY
Every Qwen result requires persisted or recoverable per-fixture raw output sufficient to recompute aggregates. Aggregate-only evidence cannot advance the boundary.
Fail: `RAW_EVIDENCE_MISSING`.

### G7 SAME-INPUT/SAME-AUTHORITY
Within B1 and B2, deterministic and Qwen arms receive the same canonical visible hash and are BOTH authorized to emit the same semantic output type. No arm may be artificially closed-world while the other is generative.
Fail: `ASYMMETRIC_CAPABILITY_CONTRACT`.

### G8 B1 KNOWN-ONTOLOGY INSUFFICIENCY
Independent exhaustive check over supplied primitives/bindings must show no known primitive can satisfy all required effects/constraints. Otherwise B1 fixture is invalid.
Fail: `KNOWN_PRIMITIVE_ALREADY_SUFFICIENT`.

### G9 B1 NO NAME SCORING
New-class name and ordering are ignored. Validity = formal preconditions/effects/constraints under visible state/domain/predicate vocabulary.
Fail: `SURFACE_LABEL_SCORING_CONTAMINATION`.

### G10 B2 NO MECHANICAL COPY
B2 visible target must not expose a complete precondition/effect schema or a one-field projection that directly reconstructs hidden Oracle. Static dependency analysis must confirm hidden signature requires induction from examples.
Fail: `B2_TARGET_LEAKS_SCHEMA`.

### G11 B2 SEMANTIC NOVELTY
No supplied primitive has an equivalent semantic signature to hidden operator, regardless of name.
Fail: `ONTOLOGY_CLASS_NOT_ACTUALLY_NOVEL`.

### G12 B2 IDENTIFIABILITY
Enumerate the frozen hypothesis space before model inference. Exactly one semantic schema must fit all visible positive/negative transitions. Zero -> `B2_NO_VALID_HYPOTHESIS`; >1 -> `B2_AMBIGUOUS_HYPOTHESIS`. Both are terminal fixture-contract failures, not model errors.

### G13 METRIC RECOMPUTATION
Aggregate TP/emitted/gold/valid/invalid/fail-open/search-bound values are independently recomputed from per-fixture cache and must exactly match reported totals and family sums.
Fail: `METRIC_INCONSISTENCY`.

### G14 NO POST-RESULT REPAIR
Any unexpected condition or gate failure terminates V2. Register residual, create V3, refreeze from the appropriate upstream point. No “small fix and continue”.
Fail: `FAIL_CLOSED_UNKNOWN`.

## 6. Frozen paired decision rules

Qwen reference remains:
- `bartowski/Qwen2.5-1.5B-Instruct-GGUF`
- `Qwen2.5-1.5B-Instruct-Q4_K_M.gguf`
- size `986048768`
- SHA-256 `1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370`
- temperature `0`
- llama.cpp `b11146`.

No mid-run model substitution. Missing pinned execution -> `BLOCKED_QWEN1P5B_EXECUTION`.

Existing operational materiality threshold only: absolute `0.20`.

B1 primary = valid schema proposal rate.
- deterministic - Qwen >= 0.20 -> `B1_DETERMINISTIC_MATERIAL_ADVANTAGE`
- Qwen - deterministic >= 0.20 -> `B1_LLM_MATERIAL_ADVANTAGE`
- else -> `B1_NO_MATERIAL_SEPARATION`.

B2 primary = valid induced-schema rate on held-out target.
Same 0.20 paired rule, except deterministic `SEARCH_BOUND` fixtures are reported separately and cannot support an “LLM necessary” claim.

## 7. One-shot TCC

`P0_PRECHECK`
-> `P1_STAGE_A_AUDIT`
-> `P2_B1_FREEZE_GATE`
-> `P3_B1_CONTAMINATION_GATE`
-> `P4_B1_EXECUTE_CACHE`
-> `P5_B1_SCORE_AUDIT`
-> `P6_B1_TERMINAL`
-> `P7_B2_FREEZE_GATE`
-> `P8_B2_CONTAMINATION_IDENTIFIABILITY_GATE`
-> `P9_B2_EXECUTE_CACHE`
-> `P10_B2_SCORE_AUDIT`
-> `P11_BOUNDARY_UPDATE`
-> `P12_MVP_EXIT`.

P0 runs G0-G2 and supersession checks.
P1 runs Stage-A raw reconstruction + independent Oracle/deterministic semantic recomputation; no model inference.
P2 freezes B1 deterministic synthesizer first, then scorer/output contract, then generator/manifest.
P3 runs G3-G9 before inference.
P4 runs each arm once and persists raw cache.
P5 runs G13; failure terminates.
P6 assigns one B1 terminal; all valid B1 terminals proceed to B2.
P7 freezes B2 hypothesis grammar + deterministic synthesis algorithm first, then scorer/output contract, then generator/manifest.
P8 runs G3-G7 and G10-G12 before inference.
P9 runs both arms once and persists raw cache.
P10 runs G13 and separates search-bound from semantic failures.
P11 updates human/machine boundary once; no intermediate boundary claim between B1 and B2.
P12 closes #43 only if L01-L19 all PASS.

## 8. Terminal states

Success/intermediate:
- `STAGE_A_AUDIT_PASS`
- `B1_DETERMINISTIC_MATERIAL_ADVANTAGE`
- `B1_LLM_MATERIAL_ADVANTAGE`
- `B1_NO_MATERIAL_SEPARATION`
- `B2_DETERMINISTIC_MATERIAL_ADVANTAGE`
- `B2_LLM_MATERIAL_ADVANTAGE`
- `B2_NO_MATERIAL_SEPARATION`
- `S2B2_MVP_COMPLETE`.

Fail closed:
- `INVALID_PREDECESSOR_STATE`
- `SUPERSEDED_CONTRACT_IN_USE`
- `FREEZE_ORDER_VIOLATION`
- `ORACLE_OR_LABEL_LEAKAGE`
- `CIRCULAR_ORACLE`
- `HOLDOUT_NOT_INDEPENDENT`
- `RAW_EVIDENCE_MISSING`
- `ASYMMETRIC_CAPABILITY_CONTRACT`
- `KNOWN_PRIMITIVE_ALREADY_SUFFICIENT`
- `SURFACE_LABEL_SCORING_CONTAMINATION`
- `B2_TARGET_LEAKS_SCHEMA`
- `ONTOLOGY_CLASS_NOT_ACTUALLY_NOVEL`
- `B2_NO_VALID_HYPOTHESIS`
- `B2_AMBIGUOUS_HYPOTHESIS`
- `METRIC_INCONSISTENCY`
- `BLOCKED_QWEN1P5B_EXECUTION`
- `FAIL_CLOSED_UNKNOWN`.

## 9. Invariants

No GitHub Actions. No Google Drive model relay. No Qwen3-4B auto branch. No predictor-authored Oracle. No aggregate-only Qwen evidence. No asymmetric generation authority. No relexicalization presented as independent. No class-name scoring. No B1 evidence relabeled as B2 induction. No B2 fixture with non-unique hidden hypothesis. New blocker -> Registry first -> fail closed -> versioned successor.
