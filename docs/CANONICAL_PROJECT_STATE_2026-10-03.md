# Canonical Project State — 2026-10-03

## Root research goal
Localize which externally measurable LLM reasoning/control functions can be replaced or supplemented by deterministic EC or deterministic external control without material loss.

Do not equate these externally measurable functions with private Transformer attention/MLP internals.

## Frozen historical Phase1-v2 result

The coarse S1/S2/S3/S4 experiment is closed as a historical protocol.

Successor TCC: `PHASE1_MVP_TCC_V2`.
Actual terminal: `EC_NATIVE_SCOPE_INCOMPATIBLE`.

Why:
- S3 reframing is genuinely shared and reportable.
- frozen S3 all-admissible-set selection is not isomorphic to EC native singleton next-action authority.
- frozen S3 representation does not identify generic S4 closure.

Do not force incompatible functions into an A/B comparison and do not rewrite the frozen Phase1 result.

## Actual empirical results

### S1 discriminative successor
Qwen2.5-1.5B on `FUNCTION_BOUNDARY_S1_V1`:
- primary score `36/50 = 0.72`
- exact fixture match `4/10 = 0.40`
- primary evidence `0.50`
- semantic concept `0.70`
- key relation `0.50`
- ambiguity `0.90`
- protected goal `1.00`

S1 was subsequently split:
- S1A raw language -> structured claims/concepts/relations: unresolved.
- S1B structured evidence authority/freshness/conflict/abstention: EC `10/10 = 1.00`, fail-open `0`.

### S2 candidate construction
Frozen `FUNCTION_BOUNDARY_S2_V2` with correct S1:
- Qwen2.5-1.5B Candidate Recall `0.40`
- Candidate Precision `0.4210526316`

With actual measured S1:
- Candidate Recall `0.30`
- propagation delta `0.10`, below materiality `0.20`

Therefore the larger measured deficit was S2 itself rather than S1 propagation.

### S2A deterministic explicit-ontology retrieval
Issue #36 froze a gold-blind deterministic baseline before scoring:
- no category rules
- no domain-specific synonym table
- resolved S1 semantic strings + relation-linked dictionary expansion
- `0.70` token TF-IDF cosine + `0.30` char-trigram cosine
- top 3 candidate IDs, tie by ID

Actual ORACLE_S1 result:
- Candidate Recall `15/20 = 0.75`
- Candidate Precision `15/30 = 0.50`
- residual gold `5/20 = 0.25`
- deterministic minus Qwen1.5B recall `+0.35`, materially above `0.20`

Actual ACTUAL_S1 result:
- Candidate Recall `13/20 = 0.65`
- Candidate Precision `13/30 = 0.4333333333`

Interpretation:
- a large part of the current S2 assay is externalizable as deterministic retrieval when a candidate ontology is explicit;
- the remaining `25%` is unresolved, not proven LLM-dependent;
- do not call this native EC candidate generation.

Canonical evidence:
`results/function_boundary_s2a_deterministic_actual_2026-10-03.json`

### Reframing
Same frozen Phase1-v2 S3 semantic-state assay, 10 fixtures:
- ECv4.4: `9/10 = 0.90`.
- Qwen2.5-0.5B: `1/10 = 0.10`, YES-collapse.
- Qwen2.5-1.5B: `9/10 = 0.90`.

0.5B -> 1.5B improvement `+0.80`; capacity collapse resolved at 1.5B. No automatic 4B escalation.

### Single next-action authority
Frozen paired V2, 17 fixtures:
- EC decision accuracy `17/17 = 1.00`
- Qwen2.5-1.5B `1/17 = 0.0588235`, REFRAME-all collapse
- absolute gap `0.9411765`

Under this frozen authority-bound control contract, EC is a validated replacement for the single-next-action authority function.

### S4 identifiability
Frozen S3 structural state has CLOSE/CONTINUE label collisions.
Best structural-majority upper bound `8/10 = 0.80`.
This is an interface-identifiability bound, not EC accuracy.

## Current function boundary

Canonical machine-readable map:
`results/ec_llm_function_boundary_2026-10-03.json`

Current classification:
- S1A raw language -> structured semantic representation: unresolved/current LLM region.
- S1B evidence authority/freshness/conflict control: EC externalizable.
- S2A explicit-ontology candidate retrieval: partially deterministic externalizable; recall `0.75`.
- S2B residual after deterministic retrieval: `0.25`, unresolved.
- residual detection: EC + 1.5B LLM capable on current assay.
- bounded reframing: EC + 1.5B LLM capable on current assay.
- all-admissible-set selection: not isomorphic to EC next-action authority.
- single next-action authority: EC replaceable under frozen control contract.
- generic frozen-S3 -> S4 closure: not identifiable.
- authority-bound run/evidence closure: EC-native at richer control-plane abstraction.
- metacognitive runtime control: deterministic EC externalizable control.
- open-ended language realization / genuinely novel semantic synthesis: unresolved current LLM region.

## Active critical path

1. Freeze a fresh S2-residual holdout before adding residual-specific symbolic rules.
2. Test generic symbolic relation closure on unseen ambiguity, symmetric alternatives, blocking/negation and supersession cases.
3. Measure only any still-uncovered residual with Qwen2.5-1.5B.
4. Keep S1A separate; test parser/extractor replacements only in a dedicated successor assay.
5. Introduce closure-sufficient successor work only if closure remains material after the upstream boundary is localized.

## Constraints
- materiality threshold remains absolute `0.20` unless a successor rule is frozen before measurement.
- no hidden/oracle labels in model-visible inputs.
- no post-freeze prompt/fixture/threshold tuning.
- no automatic Qwen3-4B branch.
- Qwen3-4B ingress is optional reference work, not current critical path.
- GitHub Actions remain disabled.
- Google Drive model relay is prohibited.
