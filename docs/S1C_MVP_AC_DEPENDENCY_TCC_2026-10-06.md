# S1C MVP — AC Dependency DAG and One-Shot TCC

Protocol: `S1C_SEMANTIC_SPACE_TCC_V1`
Owner: issue #48
Prerequisite: #43 `S2B2_MVP_COMPLETE`, boundary commit `348ef61bd517b855db97b723a3ee70a0c1be6bcf`.

## Research boundary

Current evidence places the unresolved boundary upstream of finite typed symbolic search. S1C asks which part of semantic-space creation from raw language still requires model capacity.

Do not pool:
- `R`: raw-language grounding into an already finite but opaque typed semantic inventory;
- `V`: discovery of reusable semantic slots when the canonical inventory is not supplied;
- `W`: genuinely out-of-vocabulary/world-knowledge invention. `W` is excluded from this MVP.

## MVP-R

Question: with identical raw-language evidence, frozen demonstrations, opaque semantic symbols and type/arity declarations, can deterministic external control produce the same typed IR as Qwen2.5-1.5B without material loss?

### R acceptance criteria

`R01_SCOPE`: model-visible data contains raw language, neutral entity identifiers, opaque semantic symbol IDs, type/arity declarations, and frozen demonstrations only.

`R02_OUTPUT_IDENTITY`: deterministic and Qwen emit the identical versioned typed-IR schema and have identical semantic authority.

`R03_SCORER_INDEPENDENCE`: scorer is frozen before predictor/generator measurement and does not import/call either predictor.

`R04_DETERMINISTIC_FREEZE`: deterministic grounder/inducer is frozen before held-out generator/corpus freeze.

`R05_HOLDOUT_INDEPENDENCE`: 16 fixtures / 8 structural families are structurally disjoint from prior S1A/S2A/S2B/B1/B2 and from frozen demonstrations; surface relexicalization alone is insufficient.

`R06_LEAKAGE_ZERO`: no hidden gloss, semantic category, family, Oracle IR, expected downstream state, or answer-bearing symbol name appears recursively in model-visible artifacts or constrained grammar.

`R07_IDENTIFIABLE`: hidden IR is uniquely determined by the frozen demonstrations + raw fixture evidence under the declared semantic contract. Ambiguous fixtures fail before inference.

`R08_VISIBLE_IDENTITY`: byte-canonical visible artifact hashes are equal across paired arms.

`R09_RAW_RECOMPUTABLE`: every Qwen response is cached per fixture with raw hash, parsed hash, visible hash, model/runtime pin and decoding settings.

`R10_METRIC_RECOMPUTABLE`: independent postrun replay exactly reproduces aggregate, per-family and downstream metrics from raw evidence.

`R11_DOWNSTREAM_CAUSAL`: fixed downstream B2 adapter/solver is byte-pinned. Only typed IR varies among Oracle, deterministic and Qwen substitutions.

`R12_NO_POST_RESULT_REPAIR`: no prompt/predictor/scorer/generator/threshold/grammar/fixture repair after inference. Unexpected failure requires Registry issue + successor protocol version.

### R MVP metrics

Primary:
- semantic atom/slot accuracy;
- exact typed-IR rate.

Secondary:
- entity/argument binding accuracy;
- type/arity accuracy;
- relation direction accuracy;
- negation/modality accuracy;
- ambiguity/abstention accuracy;
- fixed-downstream B2 success under Oracle/deterministic/Qwen IR.

Materiality threshold: absolute `0.20` on predeclared primary score and downstream substitution success. No post hoc metric selection.

### R branch

After independent audit:
- `Qwen - deterministic >= 0.20` on primary OR downstream fixed-solver success: terminal `R_LLM_MATERIAL_ADVANTAGE`; localize here and STOP. MVP-V is forbidden.
- `deterministic - Qwen >= 0.20`: terminal `R_DETERMINISTIC_MATERIAL_ADVANTAGE`; proceed to V.
- otherwise: terminal `R_NO_MATERIAL_SEPARATION`; proceed to V.

## MVP-V

Question: if R does not show material LLM advantage, can a reusable typed semantic partition be discovered without canonical semantic slot names?

V is conditional and MUST NOT execute before a valid R terminal authorizes it.

### V acceptance criteria

`V01_DENOTATIONAL_CONTRACT`: discovered symbol surface names are never scored. Meaning is defined only by extension, argument typing and observable transition behavior on independent probes.

`V02_EQUIVALENCE_SCORER`: semantic-equivalence matcher is frozen before V predictor/generator and cannot access predictor internals.

`V03_DETERMINISTIC_DISCOVERY_FREEZE`: deterministic discovery algorithm freezes before V heldout generation.

`V04_HOLDOUT_INDEPENDENCE`: V uses new structural families disjoint from R/prior assays.

`V05_LEAKAGE_ZERO`: no canonical hidden semantic names/IDs or answer-bearing glosses visible.

`V06_IDENTIFIABLE_DENOTATION`: hidden semantic partition has a unique denotational matching under the frozen equivalence scorer; non-unique cases fail before inference.

`V07_PAIRED_AUTHORITY`: both arms may create the same number/range of discovered slots under the same output contract and information budget.

`V08_RAW_RECOMPUTABLE`: per-fixture raw cache + hashes required.

`V09_METRIC_RECOMPUTABLE`: independent replay required before any boundary claim.

`V10_SINGLE_BOUNDARY_UPDATE`: human + machine boundary update in one commit only after audited V terminal.

## Dependency DAG / one-shot TCC

`P0_AUTHORITY`
-> `P1_R_CONTRACT_SCORER_FREEZE`
-> `P2_R_DETERMINISTIC_FREEZE`
-> `P3_R_GENERATOR_CORPUS_FREEZE`
-> `P4_R_PREINFERENCE_GATES`
-> `P5_R_PAIRED_EXECUTE_ONCE`
-> `P6_R_INDEPENDENT_AUDIT`
-> `P7_R_TERMINAL`
-> branch:
  - `R_LLM_MATERIAL_ADVANTAGE` -> `P12_SINGLE_BOUNDARY_UPDATE` -> `S1C_MVP_COMPLETE_R_BOUNDARY`
  - `R_DETERMINISTIC_MATERIAL_ADVANTAGE` or `R_NO_MATERIAL_SEPARATION` -> `P8_V_CONTRACT_SCORER_ALGO_FREEZE`
-> `P9_V_GENERATOR_AND_GATES`
-> `P10_V_PAIRED_EXECUTE_ONCE`
-> `P11_V_INDEPENDENT_AUDIT`
-> `P12_SINGLE_BOUNDARY_UPDATE`
-> `S1C_MVP_COMPLETE`.

## Result-overturning fail-closed gates

Immediate terminal protocol failure on:
- `INVALID_PREDECESSOR_STATE`
- `FREEZE_ORDER_VIOLATION`
- `STRUCTURAL_HOLDOUT_REUSE`
- `ANSWER_BEARING_SYMBOL_LEAKAGE`
- `ORACLE_FAMILY_CATEGORY_LEAKAGE`
- `CIRCULAR_ORACLE_OR_SCORER`
- `ASYMMETRIC_VISIBLE_INPUT`
- `ASYMMETRIC_OUTPUT_AUTHORITY`
- `GRAMMAR_ENCODES_SEMANTIC_ANSWER`
- `NON_IDENTIFIABLE_FIXTURE`
- `RAW_EVIDENCE_MISSING`
- `METRIC_RECOMPUTATION_MISMATCH`
- `DOWNSTREAM_SOLVER_DRIFT`
- `POST_RESULT_REPAIR_ATTEMPT`
- `FAIL_CLOSED_UNKNOWN`.

Any such failure: register issue first -> terminate V1 -> create versioned successor -> refreeze from the earliest affected dependency. No in-place causal continuation.

## Constraints

Pinned reference unless successor version explicitly changes it:
- Qwen2.5-1.5B-Instruct Q4_K_M
- SHA-256 `1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370`
- llama.cpp `b11146`
- temperature `0`.

No automatic 4B branch. No Google Drive relay. No GitHub Actions. Natural-corpus broad-generalization and open-ended world-knowledge invention remain post-MVP.