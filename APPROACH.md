# Approach

## Phase 1: Coarse localization

Decompose the pipeline into four layers:

- S1 Language -> Domain Semantics
- S2 Domain Semantics -> Candidate Set
- S3 Candidate Set -> Selection / Reframing
- S4 Selected State -> Execution / Closure

For each task, persist the intermediate artifacts produced at every layer. Compare three implementations where applicable:

- LLM
- EC / deterministic
- Oracle

The Oracle supplies the correct output for that layer and is used only to estimate how much downstream performance is recoverable if that layer were perfect.

## Phase 2: Localize by intervention

For each layer, hold every upstream artifact constant and replace only that layer.

Measure:

- final task success delta,
- layer-local accuracy,
- downstream recovery,
- false closure,
- missed reframe,
- compute/token cost.

Rank layers by Oracle substitution gain. Only the layer with material gain is decomposed further.

## Phase 3: Fine decomposition

Example if S3 is the dominant layer:

- S3.1 candidate scoring
- S3.2 pruning
- S3.3 branch selection
- S3.4 contradiction detection
- S3.5 residual detection
- S3.6 reframing trigger
- S3.7 framing mutation
- S3.8 revised-framing selection

Repeat the same intervention protocol. If one sublayer still contains most of the gap, split that sublayer again.

## Phase 4: Convergence

Stop refining a layer when at least one condition holds:

- LLM vs EC difference is below the predefined materiality threshold;
- Oracle substitution yields negligible downstream improvement;
- further subdivision does not change causal attribution;
- remaining difference is dominated by stochastic variance or measurement noise.

## Core comparison matrix

A. LLM generation + LLM selection/control
B. LLM generation + EC selection/control
C. Fixed candidate set + LLM selection/control
D. Fixed candidate set + EC selection/control
E. Oracle layer substitution

This separates candidate coverage from candidate choice and control quality.

## Large-model policy

Large LLMs are not required for Phase 1 or Phase 2. The baseline should use:

- fixed fixtures,
- a lightweight local LLM where an LLM is required,
- deterministic EC,
- Oracle artifacts.

A larger LLM may be added later only as a comparison condition after the localization method is stable.

## Intermediate artifacts

Each task should be replayable from any layer using persisted JSON artifacts, for example:

- input.json
- semantic_ir.json
- candidates.json
- candidate_scores.json
- selected_branch.json
- reframed_state.json
- closure.json
- metrics.json

No downstream run may silently regenerate an upstream artifact when a fixed artifact is required by the experiment.