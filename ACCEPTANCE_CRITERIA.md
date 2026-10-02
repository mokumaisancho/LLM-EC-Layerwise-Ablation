# Acceptance Criteria

AC-01. LLM, EC, and Oracle variants can consume exactly the same persisted upstream artifact for a given layer.

AC-02. Every layer output is serialized in a fixed machine-readable format and can be replayed independently.

AC-03. Phase 1 supports all four coarse layers: S1 semantic extraction, S2 candidate generation, S3 selection/reframing, S4 execution/closure.

AC-04. Candidate Recall and Selection Accuracy are measured separately.

AC-05. Oracle substitution gain is measurable independently for every coarse layer.

AC-06. Final error can be attributed at minimum to semantic error, candidate-generation error, selection/reframing error, or closure/execution error.

AC-07. Upstream artifacts are frozen when a downstream layer is being compared; downstream runs may not regenerate them silently.

AC-08. The layer with the largest material Oracle substitution gain is selected for the next fine-grained decomposition.

AC-09. A layer whose LLM-vs-EC difference and Oracle gain are both below the predefined materiality threshold is not subdivided further.

AC-10. Fine decomposition reuses the same fixtures and scoring rules used before subdivision unless a versioned methodology change is explicitly declared.

AC-11. EC decisions expose machine-readable reasons for candidate acceptance/rejection, reframing, and closure.

AC-12. False Closure Rate and Missed Reframe Rate are measured independently.

AC-13. Repeated stochastic LLM runs record model identifier, decoding parameters, seed where supported, and raw output hash.

AC-14. Cached LLM outputs can be reused so EC experiments do not require repeated model inference.

AC-15. Phase 1 and Phase 2 can be executed without a large LLM; fixed fixtures plus a lightweight model, EC, and Oracle are sufficient.

AC-16. End-to-end performance differences alone are never treated as evidence that a specific layer caused the difference.

AC-17. Each causal attribution is backed by a controlled intervention in which only the target layer implementation changes.

AC-18. At completion, the study identifies at least one of:
- the smallest layer where an LLM remains materially necessary;
- the largest contiguous downstream region replaceable by deterministic EC without material degradation.

AC-19. Experimental artifacts record protocol/schema version so results remain comparable after the architecture is subdivided.

AC-20. GitHub Actions are not required or automatically enabled by this repository.

## Dependency and MVP enforcement

The normative AC dependency graph, Phase1 MVP scope, frozen materiality/capacity rules, issue dependencies, allowed branches, and terminal states are defined in:

- `docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.md`
- `docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json`

An AC MUST NOT be marked PASS when any upstream dependency declared by that contract is FAIL or UNKNOWN.

Phase1 MVP requires AC-01,02,03,04,05,06,07,08,09,11,12,13,14,15,16,17,19,20. AC-10 and AC-18 are post-MVP by default unless the coarse result already establishes the final replacement boundary.

The frozen Phase1 MVP materiality threshold is an absolute 0.20 on the defined primary comparison/gain; a one-fixture 0.10 movement is non-material. Ties within 0.10 are reported as `MVP_AMBIGUOUS_DOMINANT_LAYER`; they may not be manually broken.

New deterministic EC implementations for S1/S2 and Qwen3-4B ingress are not Phase1 MVP dependencies. Large-model reference work cannot block the Phase1 coarse-localization path.