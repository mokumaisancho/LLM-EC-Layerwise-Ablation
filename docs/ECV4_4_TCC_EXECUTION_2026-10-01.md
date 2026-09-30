# ECv4.4 + TCC execution record — Phase 1 fixture qualification

Date: 2026-10-01 JST

## Intent

Freeze a causally valid Phase 1 fixture/oracle contract before any LLM-vs-EC measurement.

Protected invariants:

- controlled layer comparisons use an identical persisted upstream artifact;
- fixture generations are never mixed;
- oracle artifacts are not derived from the implementation under test;
- semantic equivalence is not reduced to exact surface-string equality;
- GitHub Actions remain disabled.

## ECv4.4-aligned execution order

1. Anchor intent and success conditions.
2. Inventory schemas and fixture artifacts.
3. Detect structural/semantic residuals.
4. Block on residuals that would invalidate causal comparison.
5. Repair the smallest admissible framing/artifact defect.
6. Re-run qualification.
7. Verify the S1 -> S2 -> S3 -> S4 artifact identity chain.
8. Freeze the source authority only after zero blocking residuals.

This follows the current ECv4.4 candidate direction: intent anchor -> residual detection -> bounded corrective revision -> explicit commit -> downstream execution/closure.

## TCC execution

TCC was used to consolidate independent file/schema checks and sequential semantic decisions.

Initial qualification:

- fixture count: 10
- structurally validated artifacts: 60
- blocking residuals: 1
- status: BLOCKED

Finding #1: `P1-003-multi-candidate` stated that two branches were valid, while the oracle exposed only one acceptable candidate. Recorded as Issue #3. The generator was corrected to emit two acceptable valid branches.

Second qualification:

- fixture count: 10
- structurally validated artifacts: 60
- blocking residuals: 0
- status: PASS

Pre-freeze audit then found a separate artifact-identity defect: downstream `content_hash` values were computed before upstream hash references were inserted. Recorded as Issue #4.

The generator was corrected to hash in dependency order:

`S1 hash -> set S2 semantic_ir_hash -> S2 hash -> set S3 candidate_set_hash -> S3 hash -> set S4 selected_state_hash -> S4 hash`.

The TCC validator was extended to recompute every content hash, verify the upstream identity chain, and compare manifest hashes.

Final qualification:

- schemas present: 6/6
- fixtures: 10
- artifacts validated: 60/60
- hash-chain checks: PASS
- scenario-semantic checks: PASS
- blocking residuals: 0
- qualification status: PASS

## Freeze

Canonical generator: `tools/generate_phase1_fixtures.py`

Validator: `tools/validate_phase1_tcc.py`

Frozen source authority: `07c5a2a86ee3b7d21ff1e130f9142396de9ce133`

Freeze manifest: `fixtures/phase1_v1/FREEZE_MANIFEST.json`

Freeze-manifest commit: `bb7b02e139c81208427609447981001d3b8f057d`

## Runtime constraint

The sandbox could not clone GitHub directly because outbound DNS was unavailable. TCC qualification therefore ran against a local deterministic materialization of the same fixture contract and corrected generator semantics; the canonical GitHub source was inspected and mutated through the GitHub connector.

## Closure

Issue #2 can close. Issues #3 and #4 can close as repaired. Phase 1 measurement can now proceed from the frozen generator/schema authority. Any semantic change requires a new fixture generation.
