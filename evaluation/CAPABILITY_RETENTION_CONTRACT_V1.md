# Capability-retention contract V1 — issue #57 / origin #1

This is a **measurement harness**, not a new semantic runtime version.

## Purpose and provenance

Borrow only conservation/evaluation logic from
[`self-consuming-llm-minimal-loop/research/registry.json`](https://github.com/mokumaisancho/self-consuming-llm-minimal-loop/blob/main/research/registry.json)
(current registry blob `ed9c1442249d657bc5a825ccfec7049c607a81c6`):
fixed reference, non-degradation, worst-case capability retention, rare/tail
conservation, and **evaluation-only external holdouts**. Do not import training
algorithms or confuse self-training collapse with deterministic replacement.

## Immutable baseline, comparable arms

Full qualification requires four genuine **matched** observations:
`LLM0` original LLM, `V1` initial deterministic runtime,
`V4` explicitly authorized runtime, and `V5` strict grammar gate.

- Same raw input and **case_id**, identical type/semantic inventory, same allowed
  information and action output mapping. Normalize outputs to
  `OPEN | CLOSE | ABSTAIN`; preserve full raw output separately.
- An arm lacking a genuine recorded response cannot be filled with simulated or
  model-imagined text. Full comparison fails closed.
- Original LLM0 model artifact, weights/hash, temperature, decoding, instruction
  contract, invocation and output cache must be pinned before an effectiveness
  claim. Benchmark labels must never appear in model-visible content.
- V4's legacy semantic grounding is shared with V1, but **V4 end-to-end execution
  cannot be imputed from V1**. Authorization and applicable-state context also
  matter. Any such shortcut must be labeled a narrower diagnostic.

## Loss decomposition

Per input, report correct→wrong, correct→abstain, wrong→correct, wrong-action
on otherwise legitimate input, false action on invalid input, and preserved
legitimate actionable rate. Report by individual capability and rare/tail
subset; always compare to original frozen LLM0 **and** each adjacent version.

A non-degradation certificate must **not** be granted if:
- any predeclared critical-capability or rare/tail correct case regresses;
- legitimate actionable-correct count decreases from original reference;
- invalid-input false actions increase versus original reference.

A higher aggregate accuracy is **not sufficient**, and lower unsafe execution
does not erase lost correct handling. Separate handling/safety dimensions.
Do not call any observational comparison causal without a single-component
intervention with identical upstream inputs.

## Exclusion and leakage

- No benchmark or gold labels may influence update, prompt selection, rollback
  tuning, active learning, early stopping, or within-run hyperparameters.
- `evaluation_locked` and `measurement_only` are **declarations**, not
  cryptographic proof of no external feedback; require independent provenance
  review before a publishable conclusion.
- The 16-case V5 set has been used in development. It is **retrospective**
  only. No independent heldout or replacement-quality conclusion may use it.
- `INDEPENDENT_UNSEEN` must mean independently sourced/annotated, genuinely
  not inspected during engineering of any compared method. A future dataset
  alone does not substitute for verified provenance.
- Existing published research and product files are immutable: 21 research
  pins + 11 product pins. No Oracle/scorer import into production.
- Frozen evaluator assumptions and thresholds may only be changed via a
  versioned successor with fresh evaluation data.

## Terminals

- `RETROSPECTIVE_DIAGNOSTIC_ONLY`: previous cases useful to check sensitivity.
- `BLOCKED_REFERENCE_LLM0_OUTPUT_MISSING`: no actual original model output.
- `FULL_COMPARISON_REQUIRES_INDEPENDENT_BENCHMARK`: reused historical data.
- `CAPABILITY_RETENTION_REGRESSION`: full paired benchmark with a regression.
- `CAPABILITY_RETENTION_PASS_FOR_THIS_FROZEN_BENCHMARK`: test-specific, never
  unlimited language generalization or universal replacement proof.
- Any invalid schema, hash, input set, or declared information-flow use:
  fail-closed.

Implementation: `tools/capability_retention_v1.py` (evaluator-only);
`tools/run_capability_retention_historical_v1.py` (diagnostic only).
