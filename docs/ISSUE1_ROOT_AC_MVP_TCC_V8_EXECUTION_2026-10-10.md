# Issue #1: AC/MVP-driven one-invocation TCC v8 — source-bound typed evidence and no false closure

**Date:** 2026-10-10. **Root:** [#1](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/1). **True root status: OPEN.** The original scientific contract, historical Phase1 V1/V2 cases, original frozen ECv4.4 commit, and previous causal score are unchanged.

## Original acceptance, MVP and dependency hierarchy

Normative sources are `ACCEPTANCE_CRITERIA.md` and `docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json`. Original AC are **AC-01..AC-20**. The scientific **MVP is all 18 mandatory original AC**, not the passing of an individual TCC workflow: AC-01..09, AC-11..17, AC-19..20. AC-10/AC-18 are post-MVP as explicitly distinguished in the original frozen contract. The primary MVP result is same-case source-pinned, four-layer S1→S4 LLM/EC comparison with A/B/C/D/E and individual Oracle interventions and materiality 0.20. A true final original project still requires subsequent scope/qualification.

The actual root AC v6 reevaluation is **2/18 qualified**, AC-19/AC-20 only. That count deliberately does not promote a narrow native next-action or a model's authored structured-test success into the original four-layer capability acceptance.

| Phase | AC / evidence dependency | Execution status |
|---|---|---|
| W0–W3 | Original AC-19/20, original source hashes, 20-AC/18-MVP DAG, frozen Phase1 replay, real historical model/EC measurements | Verified by actual v6/v7 nested TCC, root scientific status still open |
| W4A | W0–W3; native all-admissible candidate-set and explicit S4 closure mechanism | Genuine additive EC engine at pinned `24fe3a6`, 14 native source tests and 4 exposed development cases |
| W4B (bounded typed facts) | W4A; source-identified explicit Boolean facts and complete candidate requirements | **NEW: actually executed** at native commit `ae4b02b`, 24 native unit tests and 12 independent-of-old-Phase1 *synthetic typed* cases PASS |
| W4C (false closure) | W4B; no implicit completeness from self-declared source | **NEW: actually verified**, all 12 synthesized S4 attempted closures fail closed without external completeness proof |
| W4B natural language semantic validity | Typed source mechanics + genuinely independently validated original language interpretation / adjudications | **NOT QUALIFIED** (#59) |
| W4C complete S4 obligation source of truth | Typed scope + independently attested, complete inventory including absence of undeclared obligations | **NOT QUALIFIED** (#60) |
| W5 original S1/S2/S3/S4 A/B/C/D/E | Both independent W4B and W4C capabilities, genuinely equivalent native function contracts, same upstream and one-variable interventions | Not run/blocked on external semantic and S4 completeness proof |
| W6 original MVP/localization | W5 + original 18/18 accepted AC and blind assessment | Not complete |
| Separate original-LLM0 and V4 conservation | W5/W6 + genuine model identity, independently unseen judged gold, owner-approved V4 | Separate #57/#58 external qualification remains OPEN |

## Real runnable one-invocation TCC

Entry point: `tools/run_issue1_root_ac_w4b_tcc_v8.py`. It uses a **real compiler-pinned TCC graph** and simultaneously enforces nested original v6 → v7 semantic/source-gate → native typed W4B/W4C source verification. No user messages are required between executable steps:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_root_ac_w4b_tcc_v8.py \
  --tcc-root /private/tmp/llmec-tcc-generator-reference-20261009 \
  --ec-root /private/tmp/llmec-ecv44-source-20261010 \
  --v7-native-root /private/tmp/issue1-ec-w4a-frozen-20261010 \
  --new-native-root /private/tmp/issue1-ec-native-layerwise-20261010 \
  --out /private/tmp/issue1-ac-tcc8-last.json
```

The *old W4A source* is pinned separately at `24fe3a665b21ad90a79095eb8d5818dda5447d62`. The *new typed W4B/C source* is pinned at `ae4b02bca34147d549abda85fad9cdc793ca054f`, with exact Git module blobs `a3efa53f81004a17127c83e195f4281bd3fb645a` and `2f19334a01f4fb2cdeeac85c77c2188d65bc28ca`. Never repoint the old v7 regression tests to the new source: this would invalidate the original source qualification test, not change the scientific outcome.

Native formal W4B typed inputs contain only explicit Boolean facts, candidate prerequisites and source-bound SHA; **no Oracle/hidden/category/fixture ID** enters the isolated predictor subprocess. The parent compares source-independent finite Boolean semantics after inference; the test is formal/synthetic, **not independent natural-language semantic accuracy**. Missing or undefined prerequisites abort. Typed author-level statement `inventory_closed=true` is returned as **`condition_inventory_complete=false`** to S4, so a native CLOSE is explicitly rejected until independently certified; 12/12 false-closure gate trials rejected.

## Conditional execution and result-overturning gates

1. **Freeze before measurement:** immutable original AC20/MVP18, materiality 0.20, original frozen ECv4.4 data and pre-registered typed study contract; no retroactive changed gold.
2. **Separate old/new EC authority:** old v7 source and tests at commit `24fe3a6`, new W4B typed source and test modules at `ae4b02b`; exact module blobs. Any missing/version-changed source fails, never silently upgrades historical results.
3. **Source isolation:** frozen real model/raw case IDs/upstream hashes checked in nested original TCC. New typed candidate packet has only public fields; isolated child cannot see original label or Phase1 gold.
4. **Integrity pre/post:** source code must match tracked Git HEAD; source-identified upstream module/test hash and original frozen raw data stable before/after inference and just before acceptance scoring. Any mutation or mismatch invalidates the entire run.
5. **Logic:** all 24 native tests PASS and 12/12 generated typed formal evaluations PASS; unknown fact, missing candidate prerequisite or unsupported predicate yields fail-closed rather than a guessed answer.
6. **S4 fail-safe:** all 12 typed cases must reject S4 closure without independently complete obligations; authored completeness declarations never count as independent custody.
7. **Acceptance:** if genuinely independent natural-language interpretation and complete obligation proof remain absent, branch `blocked_external_semantics` with an exact W4B/W4C/W5 dependency DAG. W5 cannot be represented as a completed A-E comparison without the true source-implemented experiment and AC evidence. Only 18 original required AC PASS with complete source-verified A-E would qualify `verified_original_science`.
8. **No scheduler or UI interference:** all machine-available steps execute within this command; no task scheduling, Cloud Browser, ChatGPT self-message, daemon or background action.

Current real result: **24/24 native module tests and 12/12 typed samples**, S4 **12/12** rejected invalid self-signed closure. Original AC **2/18**. Terminal `VERIFIED_W4_TYPED_MECHANICS_EXTERNAL_NATURAL_SEMANTICS_AND_S4_COMPLETENESS_STILL_OPEN`. See [raw execution/evaluation record](../results/issue1_root_ac_tcc_v8_actual_2026-10-10.json). This result is a *verified bounded formal capability* and does not close #1, #59 or #60.

Normal ChatGPT cannot autonomously reopen a thread after its response is delivered. This TCC is a single-invocation headless workflow for currently machine-solvable steps, with explicit trustworthy external-science stop criteria. It does not self-certify unseen human judgements.
