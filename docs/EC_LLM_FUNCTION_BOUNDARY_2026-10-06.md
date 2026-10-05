# EC / LLM Function Boundary — 2026-10-06

Protocol authority: `S2B2_MVP_TCC_V3`
Supersedes the 2026-10-03 boundary for current conclusions; earlier evidence remains historical.

## Scope

This map concerns externally measurable reasoning/control functions. It does not claim that EC replaces private Transformer attention, MLP, KV-cache, or token-generation internals.

Materiality threshold: absolute `0.20`.

## Audited S2B2 result

### A — known-primitive composition
Inherited independent audit PASS. The previously measured known-primitive composition result remains valid under its own claim boundary.

### B1 — explicit structured requirements -> new action schema
Question: when no supplied primitive satisfies an already explicit structured schema requirement, can a deterministic synthesizer construct the new schema?

Audited paired result:
- deterministic: `16/16 = 1.00`
- Qwen2.5-1.5B: `1/16 = 0.0625`
- deterministic advantage: `+0.9375`
- representation-relaxed sensitivity still leaves a material deterministic advantage (`+0.75`).

Conclusion: when parameters, required preconditions/effects and forbidden effects are already explicitly structured, NEW_CLASS construction is deterministic-externalizable on this assay.

Evidence: `results/function_boundary_s2b2_b1_audited_actual_2026-10-05.json`.

### B2 — structured transitions -> reusable operator induction
Question: when the operator schema is hidden but uniquely identifiable from structured positive/negative transitions inside a frozen typed hypothesis space, can deterministic search induce it?

Pre-inference gates:
- 16 fixtures / 8 structural families
- unique identifiable hypothesis `16/16`
- deterministic vs independent Oracle `16/16`
- B1 structural overlap `0`
- leakage `0`
- grammar concrete-entity leakage `0`

Audited paired result:
- deterministic: `16/16 = 1.00`, search-bound `0`
- Qwen2.5-1.5B: `2/16 = 0.125`
- Qwen failure topology: semantic-signature mismatch `12`, unused parameter `2`, valid `2`
- deterministic advantage: `+0.875`

Post-run audit:
- visible hash match `16/16`
- raw JSON reparse match `16/16`
- deterministic / independent Oracle match `16/16`
- Qwen valid held-out transition match `2/2`
- result-overturning gate failures `0`
- model re-inference `0`

Conclusion: reusable operator induction is deterministic-externalizable when the predicate vocabulary and finite typed hypothesis grammar are supplied and the operator is uniquely identifiable from structured examples.

Evidence: `results/function_boundary_s2b2_b2_audited_actual_2026-10-06.json`.

## Updated functional boundary

Deterministic/externalizable evidence now covers:
- supplied-dictionary concept/relation/goal grounding on the tested S1A assays;
- structured evidence authority/freshness/conflict control;
- explicit-ontology fixed-budget retrieval;
- relation-conditioned candidate-text interpretation and structured closure;
- known-primitive composition;
- new-schema construction from complete structured requirements (B1);
- uniquely identifiable operator induction inside a frozen typed symbolic hypothesis space (B2);
- residual detection / bounded reframing;
- single next-action authority;
- authority-bound run/evidence closure and metacognitive runtime control.

LLM-assisted but not proven LLM-necessary:
- primary-evidence fact selection inside supplied-dictionary S1A synthetic assays.

Still unresolved generative boundary:
1. raw natural language -> semantic vocabulary / ontology / typed relation representation when the dictionary is not already supplied;
2. genuinely new predicate/operator/world-model semantics outside the supplied vocabulary and frozen hypothesis grammar;
3. open-ended language realization and unconstrained semantic synthesis.

`unresolved` is not evidence that an LLM is necessary.

## Architectural interpretation

The surviving LLM boundary has moved upstream from symbolic search/control. On current evidence, once a task is represented as a finite, typed, auditable symbolic space, both schema construction and operator induction can be externalized to deterministic machinery without material degradation on the tested assays.

The remaining question is therefore not “can EC search or compose?” but “who creates the semantic space to search?” The next causal target is the interface that maps unstructured language/world knowledge into the typed predicates, entities, relations and hypothesis grammar consumed by deterministic EC.

## Next empirical order

1. Freeze a successor assay for `raw language -> typed semantic/operator IR` with unseen structural families and no supplied answer-bearing ontology labels.
2. Separate vocabulary discovery from relation/operator grounding; do not pool them.
3. Hold the downstream B2 solver fixed and substitute only the upstream semantic representation to measure causal loss.
4. Test genuinely out-of-vocabulary semantic invention only after the representation interface is qualified.
5. Replicate the boundary on a less synthetic/natural corpus before broad generalization.

No automatic Qwen3-4B branch. GitHub Actions disabled. Google Drive model relay prohibited.
