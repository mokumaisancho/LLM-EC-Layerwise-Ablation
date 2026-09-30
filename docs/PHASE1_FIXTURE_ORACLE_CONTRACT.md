# Phase 1 Fixture / Oracle / Artifact Contract

Protocol: `PHASE1_ARTIFACT_CONTRACT_V1`

## Purpose

Freeze the comparison boundary before any LLM-vs-EC measurement. The study must compare implementations at one layer while holding the upstream artifact identical.

## Coarse layer boundaries

- `S1`: natural-language task input -> `domain_semantic_ir`
- `S2`: `domain_semantic_ir` -> `candidate_set`
- `S3`: `candidate_set` + semantic state -> `selected_reframed_state`
- `S4`: `selected_reframed_state` -> `closure_execution_result`

## Required persisted artifacts

Every fixture must contain or reference:

1. `input/task.json`
2. `oracle/s1_domain_semantic_ir.json`
3. `oracle/s2_candidate_set.json`
4. `oracle/s3_selected_reframed_state.json`
5. `oracle/s4_closure_execution_result.json`
6. `fixture_manifest.json`

Generated LLM/EC outputs must use the same layer schema as the corresponding oracle artifact.

## Deterministic materialization

The canonical Phase 1 fixture set may be stored as a deterministic generator rather than committing every generated artifact by hand.

- Canonical generator: `tools/generate_phase1_fixtures.py`
- Canonical generated path: `fixtures/phase1_v1/generated/`
- Validator: `tools/validate_phase1_tcc.py`
- Freeze authority: `fixtures/phase1_v1/FREEZE_MANIFEST.json`

The generator must materialize all required artifacts above, compute canonical content hashes, and produce the same fixture generation from the frozen source commit. Manually expanded fixture directories outside `generated/` are non-authoritative examples and must not be mixed into experimental runs.

## Oracle independence rule

Oracle artifacts are normative test references, not model outputs. They must be created or reviewed independently of the implementation currently under test. If an oracle is changed after comparison begins, the fixture generation must change and prior results must not be mixed with the new generation.

## Ambiguity rule

A fixture must not force a single answer when multiple outputs are semantically valid. Oracle artifacts may therefore encode:

- `required_elements`
- `allowed_elements`
- `forbidden_elements`
- `equivalence_constraints`
- `acceptable_candidate_ids`
- `acceptable_closure_classes`

Scoring evaluates satisfaction of constraints rather than exact surface text.

## Artifact identity

Every persisted artifact must record:

- `schema_version`
- `fixture_id`
- `fixture_generation`
- `layer_id`
- `artifact_id`
- `content_hash`
- `source_refs`

The canonical content hash is SHA-256 over canonical JSON with the `content_hash` field omitted.

## Freeze rule

Phase 1 comparison begins only after:

1. all four layer schemas are versioned;
2. the canonical generator materializes at least 10 fixtures with complete S1-S4 oracle artifacts;
3. fixture manifests are complete;
4. hashes are recorded;
5. TCC qualification reports zero blocking residuals;
6. `FREEZE_MANIFEST.json` pins the source commit and marks the generation `FROZEN`.

After freeze, any semantic change to a fixture, generator, schema, oracle, or scoring rule requires a new `fixture_generation` and a separate result set.

## Controlled intervention rule

For a layer comparison, the upstream artifact hash must be identical across LLM, EC, and Oracle-substitution runs. A run that regenerates an upstream artifact is a different experiment and cannot be used for causal attribution at the target layer.

## Minimum Phase 1 fixture composition

The first frozen set should contain at least 10 fixtures and should include:

- direct domain-semantic extraction cases;
- distractor/near-miss domain concepts;
- multiple plausible candidate branches;
- cases requiring rejection of a superficially plausible branch;
- cases requiring reframing;
- cases where no reframing is needed;
- false-closure traps;
- valid closure cases;
- at least one case with multiple semantically valid outputs;
- domain-language ambiguity.

## Exit condition for Issue #2

Issue #2 is complete when schemas and contracts exist, the canonical generator can instantiate all 10 fixtures without schema changes, TCC qualification has zero blocking residuals, and the generator/schema source commit is pinned by the freeze manifest before any measurement begins.
