# Issue #57 — Independent four-arm activation (TCC Generator V3)

This is the **one** research implementation repository: `mokumaisancho/LLM-EC-Layerwise-Ablation`. `mokumaisancho/tcc-compiler` is used **read-only**, pinned to `786d52c1efbc9271096f9311d768ef49bcd116e2`. Self-consuming LLM research is a methodological reference only. Parent/root issues: #1 / #57 / #58.

## What now runs

- `tools/run_issue57_tcc_generator_gate.py`: source-pinned typed-provenance recipe → generated `tcc.spec.v3` → compiled 17-node/16-edge execution graph → fail-closed TCC runtime → `tcc.ecv4-evidence.v0` handoff, without granting ECv4 issue closure.
- `tools/preflight_issue57_study_assets.py`: **gold-blind**, read-only study package inspection. It accepts optional `--study-dir`, `--ollama-root`, `--ollama-model`. It never reads private `gold.json` or nonce and never runs an LLM. Public+precommit+four-arm+seal matching means only **structural readiness**, not validity of private gold, data independence, genuine model inference or timestamp chronology.
- `tools/run_issue57_grammar_subtraction_diagnostic.py`: already-seen H01–H16 offline gate subtraction, **diagnostic only**. V1 assigned 14 cases and explicitly abstained H04/H15; V5 differs on seven upstream actions. H07 Japanese label agreement was accidental.

## Evidence collection contract (no shortcuts)

1. **Before any predictions** independent corpus author sources a new, non-overlapping corpus and publishes `public.json` with fixed task context, ontology and bilingual/rare/critical/counterfactual strata. Independently staffed adjudication produces private `gold.json`, with double-review/arbitration and a separate high-entropy secret nonce. Check exact/semantic overlap against historical H01–H16 and every development/tuning corpus.
2. Custodian executes `tools/blind_quality_protocol_v2.py prepare` with private `gold.json` and salt outside the prediction host, then independently time-stamps public corpus hash and salted `gold_precommit.json`. **Only** `public.json` and `gold_precommit.json` cross to predictors. Machine code cannot attest that authors or timestamps were genuinely independent.
3. Before accessing test labels, freeze a genuine **original** LLM0 choice (weights/blob SHA, tokenizer, prompt bytes, runtime build, decoding, seed, system prompt), the shared action ontology and adapter. A random available alternative is **not** automatically the original LLM or a valid LLM0.
4. Capture all arms under the **same public case IDs, visible task/training context and action contract**: LLM0 actual raw; V1 actual raw; V4 **owner-authorized** actual task/solver/policy-bound execution; V5 owner-authorized explicit finite grammar. Package default-deny V4/V5 policies are **not** approvals. Do not manufacture V4 by copying V1 and do not install policies without explicit operator authorization. Unexpressible arms or incompatible contexts must fail closed rather than be labeled compliant.
5. Freeze four raw-arm envelopes and `seal.json` before gold reveal. An independent reviewer verifies time ordering, author/adjudicator separation, lack of leakage, source pins, model execution provenance and authorized V4 policy. Hashes and self-reported `independent_review` fields are never sufficient.
6. Only after independent authorization may the isolated scorer open private gold, report original-LLM-conditional worst-capability and tail retention, true safety/false-refusal rates, paired uncertainty and all per-case transitions. A strict V5 grammar ablation must hold upstream classifications byte-identical and vary **only** the intended gate in a non-executable sandbox.
7. No code stage can issue a scientific `LLM_REPLACEMENT_NON_DEGRADING` certificate. #1/#57/#58 remain OPEN unless an external independent study establishes the actual claim and the correct scientific authority adjudicates it.

## Current real environment check (2026-10-09)

- Study public corpus and third-party gold commitment: **absent**.
- Candidate `qwen2.5:1.5b` Ollama registry manifest points to model layer `sha256:183715c435899236895da3869489cc30ac241476b4971a20285b1a462818a5b4` (986,048,512 bytes), but the referenced local blob is **missing**; Ollama server was unavailable. This is a diagnostic candidate, **not** selected as LLM0. Historical recorded Qwen inference on *other* cases is not substitutable.
- Versioned in-repository `approved_policy_v3.json` (V4) and `approved_policy_v5.json` (V5) each contain zero approvals; these are default deny; owner-installed authorization cannot be assumed.
- TCC generated 17 nodes; audit PASS; stopped at `blocked_gold` (rather than manufacturing data or reaching scientific SUCCESS). All previous 45 evaluator/CLI/legacy tests and eight new gold-blind preflight tests PASS. No GitHub Actions, autonomous model download, local server startup, or unauthorized policy installation occurred.

## Run commands (never pass private gold here)

```sh
python3 tools/preflight_issue57_study_assets.py --study-dir /path/to/public-only-study --ollama-root /path/to/ollama-models
python3 tools/run_issue57_tcc_generator_gate.py --tcc-root /path/to/read-only-tcc-compiler --source-commit EXACT_RESEARCH_HEAD --study-dir /path/to/public-only-study
```

`study-dir` should contain only `public.json`, `gold_precommit.json`, actual `LLM0.json`, `V1.json`, `V4.json`, `V5.json`, and `seal.json`. Keep **private** `gold.json` and the salt outside every such directory. These preflights never infer that on-disk artifacts are independent merely because signatures match.
