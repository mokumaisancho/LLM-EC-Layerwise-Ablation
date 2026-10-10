# Root #1 — W4 actual EC-native implementation and AC-driven one-call TCC v7 (2026-10-10)

## Scientific authority, unchanged

Original [issue #1](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/1) and `ACCEPTANCE_CRITERIA.md`: 20 original AC, **18 required for MVP**, AC-10/AC-18 post-MVP under the frozen normative graph `docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json`. Original scientific MVP demands same-case frozen, authentic original S1/S2/S3/S4 A/B/C/D/E LLM/EC/Oracle intervention, source-pinned, 0.20 materiality, no end-to-end-only causal inference. Phase1 frozen V1/V2 scientific failure `EC_NATIVE_SCOPE_INCOMPATIBLE` is **preserved**. Its 2/18 strictly verified original MVP AC remain AC-19 and AC-20; bounded successors do not silently upgrade any parent AC.

Earlier v5 prematurely treated "machine-scoped complete" as terminal and did not execute next root work. v6 corrected original AC/work dependencies and protected all scientific source/data, but stopped at W4 source-design without writing native EC implementation. **v7 executes W4A** and recomputes the real next prerequisite.

## Actual W4A EC source implementation

In the **upstream EC engine**, not a Phase1 harness shim: [new additive native module](https://github.com/mokumaisancho/GPT-EC-Closure-Engine/blob/main/01_repo/src/v4/ec_layerwise_admissible_set_closure_v1.py), source Git commit `24fe3a665b21ad90a79095eb8d5818dda5447d62`, module blob `c12e4743c89221a9b81a2f2fa98c4df9d61d72b2`. Original pinned ECv4.4 at `d5ec423968f1c9242c590e5e77ccfd92d1f59eb2` remains **unchanged** and is still used to verify frozen original failure.

The additive `EC_LAYERWISE_EVIDENCE_BOUND_SET_AND_CLOSURE_V1` has actual source-level APIs:
- `select_admissible_set`: all selected/rejected IDs, including multi-admissible COMPETING and EQUIVALENT groups, a typed reason per candidate, SHA-bound complete upstream, and a mandatory per-candidate externally attested decision.
- `evaluate_closure`: conflicting selected alternatives, unresolved mandatory obligations, pending reframe, zero-admissible fail-closed, and an **explicit** `condition_inventory_complete=True` requirement. Unattested empty obligation list does **not** silently imply CLOSE.

The new module has **14 passing native positive/negative tests** including oracle-field rejection, source-hash mismatch, duplicate candidates, missing per-candidate adjudication, forged independent semantic status, and missing explicit obligation-inventory attestation. It does **not** provide an independently authenticated semantic inference source or prove that the external obligation inventory is exhaustive.

The research integration `tools/run_issue1_ec_native_layerwise_source_probe_v1.py` pins and executes that exact native engine in an isolated Python child, supplied solely with public S2 fields, explicit developer/source-evidence heuristic adjudications, and public task facts; labels and fixture IDs are held only in the separate parent scorer. On **four already exposed** development cases:
- M003 two admissible COMPETING candidates → CONTINUE;
- M009 two admissible EQUIVALENT candidates → CLOSE;
- M007 unresolved required evidence → CONTINUE;
- M008 settled evidence → CLOSE.

**4/4 observed casewise mechanics** do **not** establish independent semantic classification or generalization. In this experiment, candidate admissibility is an **authored evidence-reference heuristic** and obligation completeness is an **author assertion**. Both remain unverified independent authority. Never count them as native semantic competence or as original AC closure. [Raw versioned actual W4 test](../results/issue1_native_layerwise_W4_actual_2026-10-10.json).

## Dependency/MVP critical path

| Work | Depends on | Actual state |
|---|---|---|
| W0–W3 original source, AC DAG, native mismatch proof, scoped model experiments | Original 20 AC and 18 MVP graph | Verified by v6 |
| **W4A native set and S4 closure mechanism** | W0–W3 | **IMPLEMENTED** upstream new source; 14 tests, 4 public-input child process cases |
| **W4B genuine independently bound semantic admissibility** | W4A | **OPEN** [#59](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/59) |
| **W4C attested complete S4 obligation inventory** | W4A | **OPEN** [#60](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/60) |
| W5 all-four-layer real original-equivalent A/B/C/D/E | W4B AND W4C | Blocked; see [#9](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/9), [#1](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/1) |
| W6 MVP coarse causal localization + strict original AC 18/18 | W5 | Blocked |
| W7 separate LLM0/V4/independent unknown holdout review | W6 | Separate [#57](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/57) / [#58](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/58) |

Strict original MVP is **still only 2/18 scientifically PASS**. W4A compiled source means an important actual blocker subtask was addressed; W4B/W4C and W5 remain genuine required science. Do not invent authentication/gold and do not rewrite frozen original V1/V2 to declare full native equivalence.

## One-call generated TCC v7 — actual execution

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_root_ac_w4_tcc_v7.py \
  --tcc-root /private/tmp/llmec-tcc-generator-reference-20261009 \
  --ec-root /private/tmp/llmec-ecv44-source-20261010 \
  --new-native-root /private/tmp/issue1-ec-native-layerwise-20261010 \
  --out /private/tmp/issue1-root-tccv7-last.json
```

Pinned compiler builds real TCC **8 nodes/9 edges**: replay and audit entire original v6 (including actual Stage1–5, raw data and code SHA) → verify and execute new native EC W4A source tests and isolated four case predictions → independently recompute W4B/W4C/W5/W6 root AC prerequisite matrix → pre/post seal frozen raw artifacts and **both research scripts and upstream EC module/tests** → scientific exit. All code and original data must be tracked + hash-pinned. TCC branch choices are driven by result: authentic root 18/18+real all-layer A/E ⇒ only SUCCESS; absent independent semantic adjudication or S4 inventory ⇒ `blocked_W4_semantic_authority`; independent authorities present but genuine A/E missing ⇒ `blocked_W5_original_study`; any pin/raw/score/code/external-result forgery ⇒ `blocked_integrity`.

Actual terminal: **`W4_NATIVE_EXECUTED_INDEPENDENT_SEMANTIC_AUTHORITY_REQUIRED`**, with no integrity errors, and original #1 **OPEN**. v7 is a single bounded machine process: it cannot autonomously acquire an independent expert's commitment, certify an unseen dataset, or re-enter an ended ChatGPT thread. It does not schedule a background ChatGPT task or operate the desktop UI.

[Full actual v7 TCC evidence, all AC prerequisite states, source Git blobs and branch decisions](../results/issue1_root_ac_tcc_v7_actual_2026-10-10.json).

Verification: **14 native EC tests PASS**, **research regression suite PASS**, and new standalone research integration/TCC adversarial tests cover tampering of native code mid-run, spoofed original AC 18/18, fabricated independent semantic authority, Oracle contamination and unbound upstream. Frozen SUITE/ECv4 method gates remain PASS; original science remains unexecuted until dependencies genuinely satisfied.
