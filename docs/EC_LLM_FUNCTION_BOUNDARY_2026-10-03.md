# EC / LLM Function Boundary — 2026-10-03

Protocol: `EC_LLM_FUNCTION_BOUNDARY_2026_10_03_V1`

## Scope

This study maps externally observable reasoning/runtime functions. It does not claim EC replaces private Transformer attention, MLP, KV-cache, or token-generation internals.

The frozen Phase1-v2 four-layer abstraction terminated correctly at `EC_NATIVE_SCOPE_INCOMPATIBLE`: S3/S4 were too coarse to compare EC-native semantics without changing what the functions mean.

## Empirical boundary

| Function | Current authority | Evidence | Current conclusion |
|---|---|---|---|
| S1 language -> domain semantic IR | unresolved | current S1 oracle audit | current fixture mostly copy-wraps facts/rules; replacement boundary not measurable yet |
| S2 semantic candidate generation | unresolved | runner absent | candidate recall remains unmeasured |
| residual detection | EC native + LLM | EC 0.90; Qwen1.5B reframe 0.90 | dual-capable on current assay |
| bounded reframing | EC native + LLM | EC 0.90; Qwen1.5B 0.90 | dual-capable, different error topology |
| all-admissible candidate-set selection | not EC-native-isomorphic | M003/M009 interface audit | separate from EC next-action authority |
| single next-action authority | EC native | `EC_NEXT_ACTION_V1` native contract/tests | deterministic EC replacement candidate |
| generic S4 outcome closure from frozen S3 | not identifiable | structural upper bound 0.80 | current interface invalid for EC closure comparison |
| authority-bound run/evidence closure | EC native | atomic closure implementation/regressions | deterministic EC replacement candidate at richer control-plane abstraction |
| intent/referent/contradiction/focus/exploration/action-permit/postflight/commit control | EC deterministic external control | metacognition-vNext POC suite | externalizable control-plane functions |
| open-ended language realization / novel semantic synthesis | no EC generator | not causally localized | likely LLM region, not yet proven necessary |

## Reframe capacity result

Frozen identical assay:

- Qwen2.5-0.5B Q4_K_M: `1/10 = 0.10`, YES on all fixtures.
- Qwen2.5-1.5B Q4_K_M: `9/10 = 0.90`, NO on all fixtures; M005 false-negative.
- ECv4.4: `9/10 = 0.90`; M004 false-positive.

Therefore the 0.5B result was a capacity collapse, not an architectural proof. The frozen escalation rule is resolved at 1.5B; automatic 4B escalation is forbidden.

Equal 0.90 aggregate accuracy does not mean equivalence: EC and 1.5B disagree on M004 and M005.

## S3 decomposition now supported by evidence

`semantic candidate set`
→ `residual detection`
→ `bounded reframing`
→ `admissibility-set handling`
→ `single next-action authority`
→ `closure/evidence authority`

This decomposition replaces the previous overloaded label `S3 selection/reframing` for successor experiments.

## Current smallest-LLM-region claim

Not yet identified.

The surviving test target is upstream/generative:

1. language -> domain semantic representation;
2. semantic candidate generation;
3. open-ended language realization / novel synthesis.

This is not evidence that an LLM is necessary for all three. It is the remaining untested region after downstream deterministic-control functions were separated and qualified.

## Measurement defect found in S1

`generate_phase1_measurement_v2.py` constructs S1 by copying every input fact into `FACT` entities and every domain rule into constraints, with a generic goal. This makes current S1 weakly discriminative for semantic extraction/relevance decisions.

Do not run an expensive S1 LLM benchmark and interpret copy accuracy as semantic understanding. Version a successor S1 assay with semantic distractor filtering, ambiguity resolution, relation extraction, and domain-term interpretation before the causal S1 comparison.

## Next empirical order

1. Freeze a discriminative successor S1 assay; keep Phase1-v2 history unchanged.
2. Run Qwen2.5-1.5B S1 on model-visible task only.
3. Freeze actual S1 outputs and run S2 candidate-generation recall separately from selection.
4. Benchmark LLM vs EC on the truly shared subfunction `single next-action authority` using identical structured plans.
5. Introduce a closure-sufficient successor interface only if closure remains necessary to localize the boundary.
6. Apply the existing 0.20 materiality rule and identify the smallest remaining LLM-dependent region.

## Evidence

- `results/ec_llm_function_boundary_2026-10-03.json`
- `results/phase1_ecv44_reframe_actual_2026-10-03.json`
- `results/phase1_qwen25_0p5b_reframe_actual_2026-10-03.json`
- `results/phase1_qwen25_1p5b_reframe_actual_2026-10-03.json`
- `results/phase1_ecv44_s3_native_interface_compatibility_2026-10-03.json`
- `results/phase1_s4_identifiability_audit_2026-10-03.json`
- `results/ec_native_adapter_qualification.json`
- EC repo `02_experiments/metacognition_vnext/FINAL_RESULT.md` at pin `d5ec423968f1c9242c590e5e77ccfd92d1f59eb2`.

GitHub Actions remain disabled. Google Drive model relay is not used.
