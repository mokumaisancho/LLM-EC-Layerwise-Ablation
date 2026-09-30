# LLM-EC Layerwise Ablation

Purpose: localize where performance differences arise between LLM-driven reasoning/control and deterministic EC-style control by progressively refining the architecture from coarse layers to fine-grained sublayers.

## Core research question

If a lightweight LLM already contains broad domain-semantic coverage, are major failures caused primarily by candidate generation, or by downstream scoring, branch selection, reframing, contradiction handling, and closure control?

## Strategy

1. Start with a coarse four-layer decomposition.
2. Hold intermediate artifacts fixed so downstream comparisons receive identical inputs.
3. Compare LLM, deterministic/EC, and Oracle behavior layer by layer.
4. Identify the layer where replacing the implementation with an Oracle produces the largest final-performance gain.
5. Split only that layer into finer sublayers.
6. Repeat until the divergence point is localized or further subdivision no longer changes the result materially.

Initial layers:
- S1: Language -> Domain Semantics
- S2: Domain Semantics -> Candidate Set
- S3: Candidate Set -> Selection / Reframing
- S4: Selected State -> Execution / Closure

## Design principles

- Coarse-to-fine localization, not premature fine decomposition.
- Candidate-generation quality and candidate-selection quality are measured separately.
- Large LLMs are optional and reserved for later comparison, not required for the initial study.
- Lightweight LLM, fixed fixtures, deterministic EC, and Oracle substitutions are the baseline experimental setup.
- Every intermediate artifact is persisted in a machine-readable format so each layer can be replayed independently.
- No GitHub Actions are required for the study.

See `ISSUE_STATEMENT.md`, `APPROACH.md`, and `ACCEPTANCE_CRITERIA.md`.