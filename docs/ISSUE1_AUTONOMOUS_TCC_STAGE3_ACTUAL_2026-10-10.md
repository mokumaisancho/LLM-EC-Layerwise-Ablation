# Origin #1: self-directed scientific continuation through TCC stage 3 (2026-10-10)

## Canonical root and closure rule

[Original root issue #1](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/1), `ACCEPTANCE_CRITERIA.md` AC-01–20 and the frozen `PHASE1_MVP_TCC_V1/V2` define the required **four-layer S1/S2/S3/S4 A–E controlled single-layer Oracle substitution**. An EC native next-action policy selecting **one action** cannot be falsely relabeled as the original generic S3 **all-admissible multiselection**, nor can generic S4 closure be measured when its public structural S3 signature aliases CLOSE and CONTINUE (bound 8/10). We do not modify frozen original source/fixtures/gold/thresholds or close #1 by inheriting acceptance from narrower child issues.

The second-stage TCC already replayed frozen Phase1 P2, verified scoped S1C finite typed space, reran real native ECv4.4 next-action on 17 same frozen cases (17/17), and actually ran 17 model-pinned Qwen predictions (1/17); methodology SUITE/ECv4 PASS. Evidence:
- `results/issue1_autonomous_stage2_machine_scoped_2026-10-10.json`
- `results/issue1_ecv44_native_next_action_v2_local_replay_2026-10-10.json`
- `results/issue1_qwen_next_action_v2_mac_actual_2026-10-10.json`

## New stage 3, driven by a preregistered causal input intervention

**Pre-registration happened before inference** at `docs/ISSUE1_S4_PUBLIC_INFORMATION_CONTROLLED_MODEL_ABLATION_V1.json`, Git blob `74e04a3b7598a0327bf45aea8ed2bfd6be5d0fa5`. It freezes 10 known historical Phase1 cases, Qwen2.5-1.5B model weight SHA and Mac llama-cli executable SHA, seed 0, temperature 0, GBNF, 0.20 materiality and paired STRUCTURAL vs ENRICHED *input information*. Only S2 publicly visible COMPETING/EQUIVALENT relation and required-condition-state fields are added to enriched; model, prompt instructions, decoding and each case's common baseline structural data remain fixed.

The predictor is a separate isolated Python subprocess given only allowlisted public fields; no fixture ID, category, oracle, hidden gold, source/private label, or selected-operation feature. The parent scores after model predictions are recorded. This isolates the **effect of public upstream information on this fixed Qwen prompt and exposed set only**. It is **not** original five-arm Oracle substitution, an independent heldout, a true ECv4 native generic S4 closure run, or evidence that native or replacement LLM generalizes.

### Actual result, never substitute a mock

`tools/run_issue1_s4_public_info_paired_llm_v1.py` performed **20 real Qwen inferences**, two per frozen known case. Raw hashes and paired predictions are sealed at `results/issue1_s4_qwen20_paired_info_ablation_actual_2026-10-10.json`.

- STRUCTURAL: 7/10 correct.
- ENRICHED: 7/10 correct.
- Paired effect: **0.00**, under precommitted 0.20 threshold. Exactly **0/10 model labels** changed under information addition.
- Separate author-visible deterministic typed-rule comparator, not real EC-native S4: 10/10 correct.
- Errors in both model arms: M003 competing alternatives incorrectly CLOSE; M007 unresolved mandatory condition incorrectly CLOSE; M005 reframing scenario incorrectly CONTINUE.

Therefore, the earlier statement that S4 differences are *solely* absent information would be too strong: information insufficiency of the **structural interface** is real (8/10 bound), but **information addition alone did not change the fixed model's output**. Semantic interpretation or policy application remains unqualified. This is not proof of universal LLM incapacity or evidence of a statistically significant effect.

## Actual no-follow-up-prompt workflow

`tools/run_issue1_autonomous_tcc_workflow_v3.py` is a generated pinned TCC DAG, **9 nodes / 13 edges**, executed successfully end-to-end without intermediary prompts:

1. Frozen original TCC truth and SUITE/ECv4 gate; native EC17 and actual Qwen17 source pins and raw evidence.
2. Verify preregistered S4 raw model20, each paired case, public upstream hashes, source blob, model raw response, and score, not trusting previously printed aggregates.
3. Branch under the **pre-frozen** 0.20 threshold: `no_material_effect` routes to `diagnose_model_information_use`; `material_effect` routes to separate review. Never silently retune prompt on same measured fixtures.
4. Inspect external independent-study public corpus/commitments and independent provenance; do not read private gold and do not certify ownership/unseenness from locally signed JSON.
5. Emit explicit ECv4 evidence, next scientific target and a truthful *scoped* terminal: `ALL_AVAILABLE_SCOPED_EXPERIMENTS_AUDITED_ORIGINAL_FULL_STUDY_STILL_OPEN`.

The workflow **automatically generates missing real 20-call model evidence** if a model and binary are supplied and the desired report file does not exist, writing it via atomic create-only hard link. Re-running against existing evidence **never unnecessarily re-infers**. It neither starts a daemon nor sends recursive prompts into the ChatGPT UI; no GitHub Actions, ChatGPT scheduled tasks, headless browser, cron, launchctl or background watcher are introduced.

On an authorized machine with these separately pinned read-only inputs:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_autonomous_tcc_workflow_v3.py \
 --tcc-root /private/tmp/llmec-tcc-generator-reference-20261009 \
 --ec-root /private/tmp/llmec-ecv44-source-20261010
```

For a **new** record when the model report is genuinely absent, supply `--report /private/tmp/issue1-fresh-model.json --model /private/tmp/llmec-qwen-comparison-20261009/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf --llama-cli /opt/homebrew/bin/llama-cli`. No overwriting prior raw evidence.

Regression coverage: **158 relevant unit/regression tests PASS**, including 12 real-model-public-input tests, 12 TCC v3 tamper/automatic-missing-evidence tests, prior stage suites, and SUITE+ECv4 methodology PASS. Current sealed workflow trace is `results/issue1_autonomous_stage3_controlled_s4_qwen_actual_2026-10-10.json`. Distinguish methodology code PASS from scientific outcome completeness.

## Next actual prerequisites, with state-machine stops

**Original issue #1 P0:** a new *explicitly authorized and versioned* four-layer contract for the **same** capability in EC and LLM, with fixed upstream artifacts, actual comparable S1–S4 implementations, A–E controlled single-layer Oracle substitutions, independent output provenance and material layer localization. Frozen Phase1 may not be relabeled to declare EC's singleton function equal to generic multiselection. Until such a same-function design is legitimately verified and executed, original A–E remains **UNREPORTABLE**.

**Separate conservation #57/#58 P1:** true independently judged previously unseen source and adjudicated gold with independent custody, *genuine original LLM0* source and matched same-case outputs, owner-approved V4, separately frozen raw outputs/seal and human-independent provenance review. Existing author-visible synthetic fixtures and output labels cannot be recycled as an unseen test set.

**Observed model-specific next science:** test fresh unseen semantic grounding and task representation under a genuinely matched input contract; do not retune this particular 10-case prompt and then claim independent confirmation. If model still fails, separate representational vs decoding vs intrinsic capability hypotheses by precommitted single-factor ablation. If improvement is found, localize it without claiming universal sufficiency.

A ChatGPT reply cannot, by itself, re-enter the same conversation after the response is sent. The local one-invocation TCC runner executes all currently machine-resolvable steps and returns a reproducible honest terminal. It intentionally **does not** spin indefinitely, self-certify external human provenance, create a schedule, or assert the original #1 is done.
