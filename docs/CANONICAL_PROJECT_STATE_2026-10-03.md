# Canonical Project State — 2026-10-03

## Root research goal
Localize which externally measurable LLM reasoning/control functions can be replaced or supplemented by deterministic EC or deterministic external control without material loss.

Do not equate these externally measurable functions with private Transformer attention/MLP internals.

## Frozen historical Phase1-v2 result
The coarse S1/S2/S3/S4 protocol is closed at `EC_NATIVE_SCOPE_INCOMPATIBLE` because the old S3/S4 abstractions mixed functions that are not isomorphic to EC-native authority contracts.

## Actual empirical boundary

### S1
Qwen2.5-1.5B discriminative S1:
- primary `36/50 = 0.72`
- exact fixture `4/10 = 0.40`
- fact `0.50`; concept `0.70`; relation `0.50`; ambiguity `0.90`; goal `1.00`

S1 split:
- S1A raw language -> structured claims/concepts/relation operators: unresolved.
- S1B structured evidence authority/freshness/conflict/abstention: EC `10/10 = 1.00`, fail-open `0`.

### S2 initial LLM result
Frozen `FUNCTION_BOUNDARY_S2_V2`, correct S1:
- Qwen2.5-1.5B recall `0.40`
- precision `0.4210526316`

Actual S1 arm recall `0.30`; propagation delta `0.10 < 0.20`, so measured S2 deficit was mostly local to S2.

### S2A — explicit ontology retrieval
Issue #36 froze a gold-blind deterministic baseline before scoring.

ORACLE_S1:
- recall `15/20 = 0.75`
- precision `15/30 = 0.50`
- residual `5/20 = 0.25`
- recall advantage over Qwen1.5B `+0.35 > 0.20`

ACTUAL_S1:
- recall `13/20 = 0.65`
- precision `13/30 = 0.4333333333`

Conclusion: when a candidate ontology is explicit, a large part of S2 is deterministic retrieval rather than an LLM-only function. This is not native EC candidate generation.

Evidence: `results/function_boundary_s2a_deterministic_actual_2026-10-03.json`.

### S2B — structured relation closure
Issue #37 avoided retesting C203/C208/C209/C210 after adding rules. It froze both a symbolic engine and holdout generator in commit `0911957782c05ab65a15e303f25d987ac675061c`, then used that commit SHA as the holdout seed.

Fresh synthetic structural holdout:
- 16 fixtures; 4 each for `INSUFFICIENT_TO_RESOLVE`, `ADMISSIBLE_UNDER_CONSTRAINT`, `BLOCKS_INFERENCE`, `SUPERSEDES`
- holdout digest `b9f3db5ea4b3476863049d488f2295b09fb7660f7ba9f19ecf9bf71f744f305c`
- candidate IDs/order generated from the freeze commit seed
- predictor sees structured relation operator + candidate metadata, not gold or candidate surface text

Actual result:
- recall `32/32 = 1.00`
- precision `32/32 = 1.00`
- exact set `16/16 = 1.00`
- forbidden fail-open `0`
- every relation family recall/precision/exact `1.00`

Conclusion: the four tested residual relation-closure functions are deterministic-externalizable once relation operators and candidate/action metadata are structured.

This does NOT show that raw-language relation extraction or missing-candidate invention is deterministic.

Evidence: `results/function_boundary_s2b_symbolic_actual_2026-10-03.json`.
Authoritative reproducibility: frozen runner + seed/digest manifest; no hand-expanded holdout copy is authoritative.

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
Canonical machine map: `results/ec_llm_function_boundary_2026-10-03.json`.

Measured deterministic/externalizable region now includes:
- structured evidence authority/freshness/conflict control;
- explicit-ontology retrieval to substantial coverage (`0.75` recall);
- structured relation closure for the four tested operators;
- residual detection;
- bounded reframing;
- single next-action authority;
- authority-bound run/evidence closure;
- metacognitive runtime control.

Remaining unvalidated LLM/generative region is concentrated in:
1. raw language -> structured claims/concepts/relation operators (S1A);
2. candidate ontology/action-class construction when the correct candidate is absent;
3. genuinely novel semantic/action synthesis and language realization.

`unvalidated LLM region` means no deterministic substitute has yet been validated, not that an LLM is proven necessary.

## Active critical path
1. Split S1A on a fresh holdout: deterministic parser/extractor vs residual semantic interpretation.
2. Separately test candidate-ontology construction with intentionally absent candidate/action classes.
3. Only then use Qwen2.5-1.5B on the genuinely uncovered residual.
4. No automatic 4B escalation.

## Constraints
- materiality threshold `0.20` unless frozen before a successor measurement;
- no hidden/oracle labels in model-visible inputs;
- no post-freeze tuning;
- no automatic Qwen3-4B branch;
- GitHub Actions disabled;
- Google Drive model relay prohibited.
