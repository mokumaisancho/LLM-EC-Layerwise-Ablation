# Canonical Project State — 2026-10-03

## Root research goal
Localize which externally measurable LLM reasoning/control functions can be replaced or supplemented by deterministic EC or deterministic external control without material loss.

Do not equate these externally measurable functions with private Transformer attention/MLP internals.

## Validation-audit correction
Issues #39/#40 repaired three material validation defects discovered after the first S1A/S2A/S2B split:

1. the first S1A 20-fixture surface holdout reused the same structural families after Stage-1 results were known; its `0.72` is relexicalization/domain-transfer evidence only, not independent generalization;
2. the old S2A `+0.35` deterministic-vs-Qwen recall claim compared 30 deterministic emissions with 19 Qwen emissions and is superseded;
3. the first S2B `1.00` assay supplied structured candidate/action metadata and therefore proves closure only after that metadata already exists.

Repairs were frozen before successor scoring, and regression gates now enforce disjoint S1A families, reproducible digests, and metadata-blind S2B inputs.

## Frozen historical Phase1-v2 result
The coarse S1/S2/S3/S4 protocol is closed at `EC_NATIVE_SCOPE_INCOMPATIBLE` because the old S3/S4 abstractions mixed functions that are not isomorphic to EC-native authority contracts.

## Actual empirical boundary

### S1A — language grounding with a supplied semantic dictionary
Historical Qwen2.5-1.5B mixed S1 assay:
- primary `36/50 = 0.72`
- exact fixture `4/10 = 0.40`
- fact `0.50`; concept `0.70`; relation `0.50`; ambiguity `0.90`; goal `1.00`

Retrospective deterministic Stage-1 diagnostic:
- primary `0.62`
- exact `0.20`

The first 20-fixture surface successor scored `0.72`, but it reused the same structural family set and is not independent generalization evidence.

Repaired prospective structurally-disjoint successor:
- predictor-core freeze `84c8585e7362976069d2a385b370a20084534b79`
- generator freeze `8d8a333ebc17e73ee04a43baf3a3976c865d621f`
- 16 fixtures / 8 new structural families
- holdout digest `3192d093d3f2162f94e22e8a2e30ea5dbb691cfc42a7913492435d511d506b9a`
- primary `59/80 = 0.7375`
- exact `5/16 = 0.3125`
- fact `0.5625`; concept `0.6875`; relation `0.6875`; ambiguity `0.9375`; goal `0.8125`

Conclusion: when a semantic dictionary already exists, a material part of S1 grounding is deterministically externalizable. This does not establish deterministic ontology induction, unconstrained raw-language semantic interpretation, or novel semantic invention.

Evidence: `results/function_boundary_s1a_disjoint_holdout_actual_2026-10-03.json`.

### S1B — structured evidence authority/control
Structured evidence authority/freshness/conflict/abstention:
- EC `10/10 = 1.00`
- fail-open `0`

Evidence: `results/function_boundary_s1b_ec_actual_2026-10-03.json`.

### S2 initial LLM result
Frozen `FUNCTION_BOUNDARY_S2_V2`, correct S1, original variable-cardinality contract:
- Qwen2.5-1.5B recall `0.40`
- precision `0.4210526316`
- emitted candidates `19`

Actual-S1 arm recall `0.30`; propagation delta `0.10 < 0.20`.

### S2A — explicit-ontology retrieval
Standalone frozen deterministic top-3 result remains valid:
- ORACLE_S1 recall `15/20 = 0.75`
- precision `15/30 = 0.50`
- residual `5/20 = 0.25`
- ACTUAL_S1 recall `13/20 = 0.65`

The historical `+0.35` comparison against Qwen is invalid because output budgets differed.

Repaired same-budget ORACLE_S1 paired assay:

| k | Deterministic R/P/F1 | Qwen1.5B R/P/F1 | Recall delta |
|---|---|---|---|
| 1 | `0.35 / 0.70 / 0.4667` | `0.25 / 0.50 / 0.3333` | `+0.10` |
| 2 | `0.50 / 0.50 / 0.50` | `0.25 / 0.25 / 0.25` | `+0.25` |
| 3 | `0.75 / 0.50 / 0.60` | `0.45 / 0.30 / 0.36` | `+0.30` |

Both engines emitted exactly k candidates per fixture; invalid outputs `0` for all k.

Conclusion: on this frozen explicit-ontology fixed-budget retrieval assay, deterministic retrieval has higher same-k recall/precision/F1 at k=1/2/3. This is task-local evidence, not a claim about open-ended candidate generation or general model superiority.

Evidence: `results/function_boundary_s2a_equal_budget_actual_2026-10-03.json`.

### S2B — relation-conditioned candidate interpretation and closure
Original structured-metadata closure assay:
- recall `1.00`
- precision `1.00`
- exact `1.00`
- fail-open `0`

This result is retained only for the boundary:
`structured relation/operator + structured action metadata -> deterministic closure`.

Repaired metadata-blind successor removes `action_class`, `target`, `constraint_preserved`, `forbidden`, and gold from predictor input. Predictor sees only structured relation/operator + candidate natural-language text.

Actual repaired result:
- recall `14/16 = 0.875`
- precision `14/16 = 0.875`
- exact set `6/8 = 0.75`
- `INSUFFICIENT_TO_RESOLVE`: `1.00`
- `SUPERSEDES`: `1.00`
- `ADMISSIBLE_UNDER_CONSTRAINT`: recall/precision `0.75`
- `BLOCKS_INFERENCE`: recall/precision `0.75`

Conclusion: once the relation/operator is already structured, a substantial part of candidate-text interpretation plus closure is deterministic-externalizable, but it is not perfect.

Evidence: `results/function_boundary_s2b_metadata_blind_actual_2026-10-03.json`.

### Downstream control
Reframing, same frozen 10-fixture assay:
- ECv4.4 `0.90`
- Qwen2.5-0.5B `0.10` YES-collapse
- Qwen2.5-1.5B `0.90`

Single next-action authority, 17 frozen fixtures:
- EC `17/17 = 1.00`
- Qwen2.5-1.5B `1/17 = 0.0588235`, REFRAME-all collapse
- gap `0.9411765`

Frozen generic S4 remains non-identifiable from its old interface; authority-bound run/evidence closure is EC-native at a richer control-plane abstraction.

## Current smallest unresolved region
Measured deterministic/externalizable region now includes:
- supplied-dictionary semantic grounding to substantial coverage (`0.7375` field accuracy on structurally-disjoint synthetic holdout);
- structured evidence authority/freshness/conflict control;
- explicit-ontology fixed-budget retrieval;
- relation-conditioned candidate-text interpretation to substantial coverage (`0.875` recall/precision);
- fully structured relation closure;
- residual detection;
- bounded reframing;
- single next-action authority;
- authority-bound run/evidence closure;
- metacognitive runtime control.

Remaining unvalidated LLM/generative region is concentrated in:
1. unconstrained raw language -> new ontology / structured relation-operator induction;
2. candidate ontology/action-class construction when the correct candidate is absent;
3. genuinely novel semantic/action synthesis and open-ended language realization.

`unvalidated LLM region` means no deterministic substitute has yet been validated, not that an LLM is proven necessary.

## Validation gates
- `tests/test_validation_repair.py`: `4/4 PASS` on Render service `srv-db0efc2d0e5s73b93tcg`, commit `12f6c7baa3311395448002284d940fd164f26e11`.
- S1A disjoint holdout digest is regenerated and checked.
- S1A successor family set must remain disjoint from the old ten families.
- S1A predictor must run without oracle/family fields.
- S2B candidates visible to the predictor must remain text-only; structured action metadata is forbidden.

## Active critical path
1. Paired Qwen2.5-1.5B measurement on the exact repaired 16-fixture S1A disjoint holdout, if direct S1A engine comparison is needed.
2. Test candidate-ontology construction with the correct action/candidate class intentionally absent.
3. Test raw-language relation/operator induction separately from downstream deterministic closure.
4. Use larger models only if a specifically localized residual requires capacity escalation; no automatic 4B branch.

## Constraints
- materiality threshold `0.20` unless frozen before a successor measurement;
- no hidden/oracle labels in model-visible inputs;
- no post-freeze tuning;
- no automatic Qwen3-4B branch;
- GitHub Actions disabled;
- Google Drive model relay prohibited.
