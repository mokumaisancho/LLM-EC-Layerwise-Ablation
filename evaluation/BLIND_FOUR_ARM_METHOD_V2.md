# Corrected blind evaluation method — #58 / parent #57 / origin #1

## Diagnosis being corrected

**Previous quantitative result is NOT evidence of semantic capacity retention.**
Historical runner `tools/run_capability_retention_historical_v1.py` imported
`tests.test_semantic_runtime_v5_grammar` and its known phrases, mapped
`T01/T02 -> OPEN` and `T03/T04 -> CLOSE` by hand, then read retrospective labels.
V1 assigned Japanese `start review`, `end review`, and unrelated text all
to the same slot because its ASCII tokenizer discarded the Japanese content.
The H07 historical "correct" result was a coincidental label match, not
a verified ability. Historical H01-H16 are excluded from fresh qualification.

## Separation of responsibilities

| Phase | Human/process role | Reads public text | Reads private gold | Writes |
| --- | --- | --- | --- | --- |
| Author | Independent corpus author | yes | no | public corpus, immutable spec |
| Adjudication | Independent labeler | yes | yes | separately encrypted/private gold |
| Prepare | Independent custodian | yes | yes, nonce | public SHA and salted gold *commitment only* |
| Predict | Isolated pre-frozen inference runners | yes | **NO** | raw results with input/output SHA for each arm |
| Freeze | Prediction operator | yes | **NO** | output commitments for all four arms |
| Score | Independent adjudicator | yes | **only after freeze** | per-capability, contrast, safety, retention report |
| Review | Separate provenance reviewer | yes | after freeze | evidence of independence and timeline |

The code implements `prepare`, `freeze`, and `score` separately in
`tools/blind_quality_protocol_v2.py`, using
`evaluation/quality_blind_v2.py` (stdlib-only). Never expose the scorer
to an LLM/model inference process or call it with any gold/secret in the
same OS account/container/working directory used to produce predictions.
The CLI stages provide *logical process* separation; actual security
requires distinct access rights or isolated containers/accounts.

**Important**: SHA256 integrity and salted precommit prove that artifacts
presented during audit agree with their commitments; they do **not** prove
when those commitments were created, whether a different model actually
ran, whether the curator saw the candidate outputs, or that dataset examples
were unseen. Before any scientific claim, an independent reviewer must
verify independently time-stamped, immutable commits for the two-stage
sequence (public + salted gold commitment before inference, frozen all-arm
raw outputs before private gold release) and independently sourced labels.

## Four genuinely comparable arms

- `LLM0`: record an actual original reference model's weights/revision SHA,
  tokenizer, library/runtime revision, prompt bytes, decoding parameters,
  run seed and actual raw output, rather than post-hoc reconstructed responses.
- `V1`: actual frozen V1 predictor output under identical task demonstrations.
- `V4`: actual authorized V4 execution with *the same* input, applicable
  state and pre-installed independent policy; **do not infer V4 from V1**.
- `V5`: actual finite grammar-approved V5 execution, respecting its default
  deny and policy constraints. A V5 abstention is a measurable coverage loss,
  not evidence of understanding ambiguity.

Freeze the **same** public case IDs, raw text, entity registries, training
demonstrations, action ontology, allowed context and generation outputs
before comparing. If an arm cannot comply with an identical task contract,
record that as an unsupported capability instead of adjusting the task
after seeing results.

Use a single **precommitted** universal output adapter producing strictly:
`{"action":"OPEN"}`, `{"action":"CLOSE"}`, or `{"action":"ABSTAIN"}`.
V1/V4 semantic slot IDs must be mapped to action labels *only* through a
pre-registered **public behavioral ontology** (e.g., action effect probes);
no `H07`/case-ID mapping, no access to gold and no mapping derived after
outputs are seen. Raw non-JSON outputs are **format failures** counted in
the denominator, not silently discarded. Freeze adapter source SHA with each arm.

## Required blind case composition

- Independent ordinary positive and negative commands (both actions).
- Safe non-action/uncertain/negated instructions and adversarial prompts.
- Previously unseen natural paraphrases (do not rely on literal phrase
  memorization), Japanese and English, and different entity placements.
- Genuine rare/tail conditions and separate capability strata.
- At least one *contrast pair* of otherwise matched context with opposite
  meaning: start vs end, valid vs "unclear", etc. A predictor assigning
  the **same** action to a gold-contrasting pair fails the contrast test
  even if it accidentally gets one answer right.
- Label every item with correct action, critical and tail flags and
  capability metadata in a **private** file. Adjudicate by two people
  independently with arbitration of disagreement before precommit;
  document that procedure in `gold_provenance`.
- Exclude exact and semantic near-duplicates of the known fixtures from
  independence claims; algorithmic exact-match checks are insufficient.
- Ensure a sufficient sample size for the intended effect threshold,
  then report paired uncertainty (e.g. matched bootstrap/McNemar), with
  family-wise treatment of multiple subscales where appropriate. Six
  test cases in code are *synthetic test machinery only*.

## Gate semantics

The v2 scorer refuses incomplete four-arm caches, missing/altered cases,
mismatched public and gold commitments, modified raw results, duplicate
IDs, answer-bearing keys in public inputs, missing counterfactual pairs,
identical gold labels in an allegedly contrastive pair, and missing
independent-adjudicator identity.

Always report simultaneously: overall correct, legitimate correct,
legitimate false-refusal, wrong action, invalid-input false action,
format errors, per-capability retention, rare/tail retention,
every adjacent-generation correct→incorrect transition, losses versus LLM0,
and failures to distinguish contrast pairs.

**No automatic certificate**: even if all input files and hashes pass,
the scorer returns `REVIEW_REQUIRED_SCORES_ARE_NOT_SCIENTIFIC_CERTIFICATION`
and `quality_preservation_certified=false`. This is deliberate: the current
software cannot attest real independence or proof of a real LLM0 inference
by itself. A separate independent scientific review, data freeze and
admissible raw-output chain of custody are mandatory for a final conclusion.

## Commands (roles MUST run in separate authorized environments)

1. Custodian, with private gold and a long unpredictable private nonce:

```sh
CAPABILITY_GOLD_SECRET_SALT="$(cat /secure/gold_nonce)" \
python3 tools/blind_quality_protocol_v2.py prepare \
  --public public.json --gold /secure/gold.json > gold_precommit.json
```

Publish the precommit and public file in a tamper-evident,
independently verifiable history **before** prediction. Do not publish
nonce/private gold.

2. Predictor-only environment: process `public.json` through genuine
source-pinned `LLM0`, `V1`, `V4`, `V5`; each returns an immutable
`{ARM}.json` containing committed raw stdout. This stage must have no
filesystem, API, environment-variable, or repository-history access
to private gold. Document network, process and credential isolation.

3. Freeze process **without gold**:

```sh
python3 tools/blind_quality_protocol_v2.py freeze \
  --public public.json --precommit gold_precommit.json \
  --llm0 LLM0.json --v1 V1.json --v4 V4.json --v5 V5.json > sealed.json
```

Publish/anchor `sealed.json` with trusted timestamp before releasing gold.

4. Independent scorer after external proof of stages 1–3:

```sh
CAPABILITY_GOLD_SECRET_SALT="$(cat /secure/gold_nonce)" \
python3 tools/blind_quality_protocol_v2.py score \
  --public public.json --gold /secure/gold.json --seal sealed.json \
  --llm0 LLM0.json --v1 V1.json --v4 V4.json --v5 V5.json > report.json
```

Do **not** feed `report.json` back into any within-run prompt tuning,
sample selection, model training, retry decisions, or stopping rule.
To change the model after viewing these results requires a *different*
freshly frozen evaluation corpus and versioned protocol.

## Migration: legacy full-quality path retired

`tools/capability_retention_v1.py` remains readable for reproducible
V1→V5 retrospective *diagnostics only*. Its non-diagnostic mode now fails
with `LEGACY_FULL_QUALITY_UNVERIFIABLE_USE_BLIND_V2`, even when all four
arms are self-attested and benchmark origin says `INDEPENDENT_UNSEEN`.
The old CLI `tools/run_capability_retention_gate_v1.py` therefore also
rejects unsafe full-certification requests. This prevents old scripted
claim paths from bypassing the blinded protocol.

## Current status

- 20 evaluator/negative tests + 4 process-level CLI tests; old 16
  retrospective comparator tests retained (not reused as independent data).
- 21 research and 11 product pinned artifacts preserved.
- Gold/salt not provided to freeze process in direct subprocess test.
- No real four-arm scientific scores claimed or generated by these unit tests.
- #58 method implementation can be verified separately; #57 and #1 remain
  OPEN until actual independent inputs, output cache and review exist.


## Reused conservation principles (evaluation design only)

External reference, **read-only**: `mokumaisancho/self-consuming-llm-minimal-loop`, README blob `4a3163836c1d8aa6a1b1ff7d57ee100fe9164669`, registry blob `ed9c1442249d657bc5a825ccfec7049c607a81c6`. The self-consuming repo, its experiments (including EXP-000), its scientific conclusions, and its data are NOT part of this project. This is a **single-repository** implementation: source of truth is `LLM-EC-Layerwise-Ablation`.

The transferable principles are a frozen original-generation anchor, stage-by-stage paired measurement, predeclared worst-capability preservation, rare/tail preservation, evaluation-only external benchmarks, and one-component-at-a-time ablation. Model self-training, synthetic recursive sampling, and updates are intentionally not imported.

### Additional diagnostic output from blind v2

`retention_vs_llm0` now reports, for each of `V1`, `V4`, `V5`, the **same** `LLM0` baseline-correct denominator:

- Overall, every independently labeled capability, all critical cases, and tail cases: `anchor_correct`, `retained`, `lost`, `lost_case_ids`, and `retention_rate`.
- `correct_to_abstain`, `correct_to_wrong_action`, `correct_to_format_error` are separate; a safe abstention is **not** retained positive-command capability.
- `worst_capability_retention_rate` and `worst_capability_ids` expose the most degraded estimable capability regardless of aggregate-score improvement.
- `unestimable_capabilities` identifies strata on which LLM0 itself had no correct cases; **zero denominator is null**, never perfect preservation.
- `non_degradation_diagnostic_only` and `monotonic_correctness_diagnostic_only` are conservative flags for supplied labels; neither is a scientific certificate.
- `quality_preservation_certified=false` is unconditional until provenance review outside the scorer; no synthetic unit-test output, self-declared timestamp, or published hash may silently promote it.

`retention_rate = (# original-LLM-correct cases still correct in candidate)/(# original-LLM-correct cases)`; this assesses preservation of correct behavior, not standalone absolute accuracy. Continue reporting absolute accuracy, correct legitimate-command handling, false refusal, unsafe false action, and matched per-case transitions independently. Anchor failures must not be treated as evidence of candidate preservation. Every capability stratum and rare/critical flag must be independently assigned **before** prediction and the results must not be recycled into model selection within the same study.

### Causal attribution is a separate experiment

A raw `LLM0 → V1 → V4 → V5` score trajectory is **observational**, not proof that a particular EC substitution caused loss. For a controlled grammar-gate subtraction, run two V5 branches on identical frozen `case_id` and **byte-identical upstream V1/V4 classification outputs**, same demonstrator examples, entity registry, prior task/state, ontology, policy and adapter. Freeze/verify the upstream artifact and its SHA *before* either branch. In one branch alone, bypass the specific strict V5 grammar decision while retaining all other security and authorization rules; keep the treatment isolated to a sandbox, never expose this branch for unapproved live actions. Capture and independently seal both outcomes. Pair and score only after gold release.

If upstream hashes, authorized policy, or task contracts differ, mark `ABLATION_CONFOUNDED`. If differences follow only the one frozen gate intervention, report `GATE_LOCALIZED_DIFFERENCE`, **not** generalized LLM necessity or general-domain causal replacement. Always preserve original raw outputs and no-retrofit change logs.

### Outstanding scientific gate

No independent unseen corpus, independently adjudicated precommitted gold, genuine pinned LLM0 outputs for matching cases, genuine V4 authorized matching execution, or external custody review has yet been supplied. The original #1 and #57/#58 remain open, scientific four-arm comparison `NOT_RUN`, and non-degradation `NOT_ESTABLISHED`. Historical H01-H16 stay diagnostic-only.
