# Canonical Project State — 2026-10-03

## Root research goal
Localize which externally measurable LLM reasoning/control functions can be replaced or supplemented by deterministic EC without material loss.

Do not equate these externally measurable functions with private Transformer attention/MLP internals.

## Frozen Phase1-v2 result

The coarse S1/S2/S3/S4 experiment is closed as a historical protocol.

Successor TCC: `PHASE1_MVP_TCC_V2`.
Actual terminal: `EC_NATIVE_SCOPE_INCOMPATIBLE`.

Why:
- S3 reframing is genuinely shared and reportable.
- frozen S3 all-admissible-set selection is not isomorphic to EC native singleton next-action authority.
- frozen S3 representation does not identify generic S4 closure.

Do not force incompatible functions into an A/B comparison and do not rewrite the frozen Phase1 result.

## Actual empirical results

### Reframing
Same frozen Phase1-v2 S3 semantic-state assay, 10 fixtures:
- ECv4.4: `9/10 = 0.90`.
  - error: M004 false-positive reframe.
- Qwen2.5-0.5B Q4_K_M: `1/10 = 0.10`.
  - collapsed to YES on all 10.
- Qwen2.5-1.5B Q4_K_M: `9/10 = 0.90`.
  - error: M005 false-negative reframe.

0.5B -> 1.5B absolute improvement: `+0.80`.
The frozen capacity-collapse condition is resolved at 1.5B. No automatic 4B escalation is permitted.

Equal EC/1.5B aggregate accuracy does not imply equivalence: paired disagreement is M004/M005.

### S3 native interface
EC `EC_NEXT_ACTION_V1` returns exactly one authority-bound next action.
Frozen Phase1 S3 permits one-or-more selected candidates; M003/M009 require two.
Result: `EC_NATIVE_NOT_APPLICABLE` for full admissible-set selection, while native next-action authority remains directly testable as a separate subfunction.

### S4 identifiability
Frozen S3 structural state has CLOSE/CONTINUE label collisions.
Best structural-majority upper bound: `8/10 = 0.80`.
This is an interface-identifiability bound, not EC accuracy.
Native EC run/evidence closure is a richer control-plane function and requires a separate compatible assay.

## Current function boundary

Canonical files:
- `docs/EC_LLM_FUNCTION_BOUNDARY_2026-10-03.md`
- `results/ec_llm_function_boundary_2026-10-03.json`

Current classification:
- S1 language -> semantic IR: unresolved; current S1 oracle is weakly discriminative.
- S2 semantic candidate generation: unresolved; Candidate Recall not yet measured in the successor protocol.
- residual detection: EC_NATIVE + 1.5B LLM capable on current assay.
- bounded reframing: EC_NATIVE + 1.5B LLM capable on current assay.
- all-admissible-set selection: not isomorphic to EC next-action authority.
- single next-action authority: EC_NATIVE; paired LLM-vs-EC assay pending.
- generic frozen-S3 -> S4 closure: not identifiable.
- authority-bound run/evidence closure: EC_NATIVE at a richer control-plane abstraction.
- intent continuity, referent binding, contradiction/focus/exploration control, action permit, postflight and COMMIT authority: deterministic EC external control with existing metacognition-vNext POC evidence.
- open-ended language realization / novel semantic synthesis: likely LLM region but not yet causally localized.

## S1 measurement defect

`tools/generate_phase1_measurement_v2.py` copy-wraps every input fact and every domain rule into S1, with a generic goal and little fixture-specific semantic transformation. Therefore a high score on the old S1 representation would not establish semantic-extraction competence.

Do not use the old S1 oracle to conclude that an LLM is or is not necessary. A versioned discriminative successor assay is required.

## Active critical path

Issue #33 — discriminative S1 + 1.5B S1->S2 measurement:
1. freeze a successor S1 benchmark testing distractor filtering, domain-term disambiguation, relation extraction, protected-intent retention and ambiguity/residual representation;
2. run Qwen2.5-1.5B on model-visible task only;
3. persist S1;
4. run S2 from that exact S1;
5. measure Candidate Recall separately from selection.

Issue #34 — shared next-action authority comparison:
1. freeze structured plan/current-state fixtures;
2. provide identical inputs to EC and Qwen2.5-1.5B;
3. measure exact next-action accuracy and fail-closed correctness separately.

Closure-sufficient successor work is conditional: only introduce it if #33/#34 leave closure as a material unresolved boundary.

## Retired old critical-path items
- Issue #20: closed; actual EC binding resolved, full generic S1-S4 EC baseline invalid under frozen semantics.
- Issue #22: closed/not-planned; old full A/B/E runner superseded.
- Issue #23: closed; adapter qualification complete.
- Issue #24: closed/not-planned for frozen protocol; Oracle intervention design retained for compatible successor subfunctions.
- Issue #25: closed; S1->S3 oracle-blind adapter implemented.
- Issue #26: closed; M004 divergence preserved as research result.
- Issues #27/#28: closed as architecture/interface findings.
- Issues #29/#30/#31: capacity execution investigations resolved; valid 1.5B result exists.
- Issue #32: closed; TCC dependency scheduling corrected in V2.

## Constraints
- materiality threshold remains absolute `0.20` unless a successor rule is frozen before measurement.
- no hidden/oracle labels in model-visible inputs.
- no post-freeze prompt/fixture/threshold tuning.
- no automatic Qwen3-4B branch.
- Qwen3-4B ingress is optional reference work, not current critical path.
- GitHub Actions remain disabled.
- Google Drive model relay is prohibited.
