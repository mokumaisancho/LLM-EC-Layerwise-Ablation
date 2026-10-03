# Canonical Project State — 2026-10-03

## Root research goal
Localize which externally measurable LLM reasoning/control functions can be replaced or supplemented by deterministic EC or deterministic external control without material loss.

Do not equate these externally measurable functions with private Transformer attention/MLP internals.

## Validation-audit correction
Issues #39/#40 repaired three material defects:
1. the first S1A 20-fixture successor reused historical structural families and is relexicalization/domain-transfer evidence only;
2. the old S2A `+0.35` claim used unequal output budgets and is superseded;
3. the first S2B `1.00` assay exposed structured action metadata and proves only fully structured closure.

Regression gates passed `4/4` at commit `12f6c7baa3311395448002284d940fd164f26e11`.

## Actual empirical boundary

### S1A — supplied-dictionary language grounding
Repaired structurally-disjoint 16-fixture holdout:
- deterministic predictor core `84c8585e7362976069d2a385b370a20084534b79`
- generator `8d8a333ebc17e73ee04a43baf3a3976c865d621f`
- digest `3192d093d3f2162f94e22e8a2e30ea5dbb691cfc42a7913492435d511d506b9a`

Exact paired measurement on that same holdout (#38):

| Arm | Five-field accuracy | Exact |
|---|---:|---:|
| deterministic | `0.7375` | `0.3125` |
| Qwen2.5-1.5B | `0.6875` | `0.3125` |

Per-field Qwen minus deterministic:
- primary fact `+0.25`
- concept `-0.1875`
- relation `-0.0625`
- ambiguity `-0.0625`
- goal `-0.1875`

There is no material overall separation under the frozen `0.20` threshold, but the error topology is complementary: Qwen is materially better at primary-evidence fact selection on this assay while deterministic grounding is numerically stronger on the remaining semantic fields.

### S1A prospective hybrid successor
To prevent post-hoc routing, #42 froze the field router before creating a fresh generator:
- route freeze `b9fc26809da58ed25572454f3de5a09e99930b6a`
- generator freeze `d38cda27c906fa8c92b070c97821da3f0143e6ed`
- digest `8cf95fa3e9fc44c5ad155ac38b551aaa497f8fa82133cb5ef0f39e9d97a55404`
- wrapper `b160fc16136f14fd5d05d0aa135a87cc41c2d316`
- 16 fixtures / 8 new structural families, no prior S1A family reuse

Frozen route:
- `primary_fact_id` -> Qwen2.5-1.5B
- concept / relation / ambiguity / goal -> deterministic predictor

Prospective result:

| Arm | Five-field accuracy | Exact |
|---|---:|---:|
| deterministic | `65/80 = 0.8125` | `8/16 = 0.500` |
| Qwen2.5-1.5B | `59/80 = 0.7375` | `4/16 = 0.250` |
| frozen hybrid | `70/80 = 0.8750` | `10/16 = 0.625` |

Hybrid vs best single arm:
- primary `+0.0625`
- exact `+0.125`
- primary improvement is descriptive, not material (`<0.20`).

Architecture implication: under a supplied semantic dictionary, S1A is not monolithic. Primary evidence selection and downstream semantic grounding behave as separable functions. A fixed LLM-assisted fact selector plus deterministic concept/relation/goal grounding reproduced the complementary topology on a fresh synthetic successor.

This does not establish deterministic ontology induction, unrestricted natural-language parsing, or novel semantic invention.

Evidence: `results/function_boundary_s1a_hybrid_successor_actual_2026-10-03.json`.

### S1B — structured evidence authority/control
EC structured evidence authority/freshness/conflict/abstention:
- accuracy `1.00`
- fail-open `0`

Evidence: `results/function_boundary_s1b_ec_actual_2026-10-03.json`.

### S2A — explicit-ontology fixed-budget retrieval
The old unequal-budget comparison is invalid and superseded.

Same-budget ORACLE_S1 paired assay:

| k | Deterministic R/P/F1 | Qwen1.5B R/P/F1 | Recall delta |
|---|---|---|---|
| 1 | `0.35 / 0.70 / 0.4667` | `0.25 / 0.50 / 0.3333` | `+0.10` |
| 2 | `0.50 / 0.50 / 0.50` | `0.25 / 0.25 / 0.25` | `+0.25` |
| 3 | `0.75 / 0.50 / 0.60` | `0.45 / 0.30 / 0.36` | `+0.30` |

Conclusion: deterministic retrieval is competitive/stronger on this frozen explicit-ontology assay; this does not test missing-candidate invention.

Evidence: `results/function_boundary_s2a_equal_budget_actual_2026-10-03.json`.

### S2B — relation-conditioned candidate interpretation/closure
Fully structured metadata boundary:
- recall/precision/exact `1.00/1.00/1.00`
- retained only as `structured operator + structured action metadata -> deterministic closure`.

Metadata-blind successor, predictor sees structured relation/operator + candidate natural-language text only:
- recall `0.875`
- precision `0.875`
- exact set `0.75`

Conclusion: once relation/operator is structured, substantial candidate-text interpretation and closure can be externalized deterministically; missing-candidate invention remains untested.

Evidence: `results/function_boundary_s2b_metadata_blind_actual_2026-10-03.json`.

### S3 / control plane
Bounded reframing:
- ECv4.4 `0.90`
- Qwen2.5-1.5B `0.90`

Single next-action authority:
- EC `17/17 = 1.00`
- Qwen2.5-1.5B `1/17 = 0.0588235`
- gap `0.9411765`; Qwen collapsed to REFRAME-all.

Generic old S4 remains non-identifiable from its frozen interface; authority-bound run/evidence closure is EC-native at the richer control-plane abstraction.

## Current functional partition
Substantially externalizable / deterministic-capable region:
- supplied-dictionary concept/relation/goal grounding;
- structured evidence authority/freshness/conflict control;
- explicit-ontology fixed-budget retrieval;
- relation-conditioned candidate-text interpretation;
- fully structured relation/action closure;
- residual detection and bounded reframing;
- single next-action authority;
- authority-bound run/evidence closure;
- metacognitive runtime control.

LLM-assisted region observed in current assays:
- primary-evidence fact selection inside supplied-dictionary S1A.

Still unresolved generative region:
1. unconstrained raw language -> new ontology / relation-operator induction;
2. candidate/action construction when the correct candidate is absent;
3. genuinely novel semantic/action synthesis and open-ended language realization.

`unresolved` means no deterministic substitute has yet been validated, not proof that an LLM is necessary.

## Active critical path
1. Test candidate/action ontology construction with the correct candidate intentionally absent.
2. Test raw-language relation/operator induction separately from downstream deterministic closure.
3. Replicate the supplied-dictionary partition on a less synthetic/natural corpus before broad generalization.
4. Use larger models only for a specifically localized capacity residual; no automatic 4B branch.

## Constraints
- materiality threshold `0.20` unless frozen before a successor measurement;
- no hidden/oracle labels in model-visible inputs;
- no post-freeze tuning;
- no automatic Qwen3-4B branch;
- GitHub Actions disabled;
- Google Drive model relay prohibited.
