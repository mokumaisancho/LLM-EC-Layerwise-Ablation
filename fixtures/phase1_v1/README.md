# Phase 1 v1 Fixture Set

Status: `DRAFT`
Protocol: `PHASE1_ARTIFACT_CONTRACT_V1`

Each fixture directory must contain:

```text
<fixture_id>/
  input/task.json
  oracle/s1_domain_semantic_ir.json
  oracle/s2_candidate_set.json
  oracle/s3_selected_reframed_state.json
  oracle/s4_closure_execution_result.json
  fixture_manifest.json
```

## Planned first 10 fixtures

1. `P1-001-direct-semantic` — direct domain-semantic extraction; minimal distractors.
2. `P1-002-near-miss-concept` — correct domain concept vs linguistically plausible near miss.
3. `P1-003-multi-candidate` — several plausible semantic branches; only a subset valid.
4. `P1-004-superficial-winner` — high linguistic plausibility but evidence/constraint failure.
5. `P1-005-reframe-required` — initial framing cannot satisfy success conditions without revision.
6. `P1-006-reframe-not-required` — unnecessary reframing must be rejected.
7. `P1-007-false-closure-trap` — locally coherent state with unresolved required residual.
8. `P1-008-valid-closure` — all closure preconditions satisfied.
9. `P1-009-multiple-valid-outputs` — multiple semantically equivalent outputs allowed.
10. `P1-010-domain-language-ambiguity` — same surface language has domain-specific constrained meaning.

## Freeze criteria

This generation may be marked `FROZEN` only when all 10 fixtures have complete S1-S4 oracle artifacts, schema validation succeeds, hashes are recorded, oracle independence is documented, and the scoring version is fixed.

No experimental result from `DRAFT` fixtures is valid evidence for the main comparison.
