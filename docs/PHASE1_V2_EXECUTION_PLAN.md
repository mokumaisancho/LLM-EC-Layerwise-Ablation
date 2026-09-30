# Phase 1 v2 Coarse Ablation Execution Plan

Protocol: `PHASE1_COARSE_ABLATION_V2`

## Purpose

Localize where LLM and deterministic EC behavior diverges while preventing oracle/category leakage from the measurement input.

## Layer decomposition

- S1: natural language -> domain semantic IR
- S2: domain semantic IR -> semantic candidate set
- S3: candidate set + semantic state -> selection / reframing
- S4: selected state -> execution / closure

## Measurement principle

Start coarse. Only subdivide the layer that shows material causal divergence under controlled intervention.

## Fixture generations

- `phase1_v1`: qualification/regression only. Never use for reported measurement because model-visible scenario labels exist.
- `phase1_v2`: measurement generation. No oracle-revealing category labels in model-visible artifacts.

## Visible vs hidden separation

Model-visible:
- task prompt
- facts / evidence
- domain rules
- stated goal / protected intent
- persisted upstream artifact for the target layer

Hidden evaluation metadata:
- fixture taxonomy/category
- oracle acceptable candidate IDs
- expected reframe requirement
- expected closure class
- scoring annotations

## TCC gates before measurement

1. schema gate
2. content-hash / upstream-chain gate
3. leakage gate
4. oracle consistency gate
5. controlled-intervention gate
6. result completeness gate

Any blocking residual stops measurement.

## Comparison conditions

A. lightweight LLM generation + LLM selection/control
B. lightweight LLM generation + EC selection/control
C. fixed candidate set + LLM selection/control
D. fixed candidate set + EC selection/control
E. Oracle substitution at S1, S2, S3, and S4 independently

Large LLM is optional and reserved for a final reference comparison only.

## Execution order

1. Generate v2 fixtures.
2. Run TCC qualification and leakage gate.
3. Freeze v2 generator + schema + scorer commit.
4. Run Oracle replay to prove harness correctness.
5. Run deterministic EC path first, especially S3/S4.
6. Import/cache lightweight LLM outputs once.
7. Run A-E using identical persisted upstream hashes.
8. Compute layer metrics and Oracle substitution gain.
9. Select the highest-materiality layer only.
10. Split that layer and repeat.

## Core metrics

S1: semantic recall, constraint recall, forbidden-semantic rate.

S2: valid candidate recall, invalid candidate admission rate, oracle-candidate coverage.

S3: selection accuracy, correct candidate rank, residual recall, reframe precision/recall, intent-violation rate.

S4: false-closure rate, missed-closure rate, residual carry-through accuracy, final task success.

Cross-layer: token/compute/latency where measurable, upstream hash equality, Oracle substitution gain.

## Causal attribution rule

A layer is causal only if changing that layer while holding its upstream artifact hash fixed materially changes downstream success. End-to-end correlation alone is insufficient.

## Refinement rule

For layer L:

- If LLM-vs-EC difference < materiality threshold AND Oracle substitution gain < threshold: stop subdividing L.
- Otherwise subdivide only L.

This implements `coarse -> localize -> split -> retest -> converge`.

## Recording newly discovered problems

Every blocking methodological or implementation residual discovered during TCC execution must be recorded as a GitHub issue before repair. The repair commit and rerun result must be linked before closure.

## Constraints

- GitHub Actions remain disabled.
- v1 and v2 results must never be pooled.
- A model-visible field may not contain hidden taxonomy, expected selection, reframe, or closure labels.
