# Issue #1 — Raw-file-free reconstruction V2 (17 Oct 2026)

## Status and scientifically valid interpretation

**Operational reproducibility PASS**: 48 model-visible formal inputs and 48 mechanical reference results regenerate deterministically from **only source code + hash-pinned manifest**. In a clean temporary checkout containing no `public.json`, `private_gold.json`, or `native_score.json`, 21/21 Python regression tests passed. Normal Python and `python -O` produce identical root digests. The frozen old V1 artifacts/results have **not** been overwritten.

**Scientific evaluation NOT QUALIFIED**: gold is defined by the SAME authored formal policy/algorithm as the benchmark. It is not an independent natural-language semantic label. This does not validate S1/S2 semantics, original target-only A–E, or LLM generalization nondegradation. Original AC remains **2/18**.

## Exact repository sources

- `tools/issue1_formal_holdout48_v1.py` (Git blob `2eb9b49bdfd8d0e42d497218ee4c9d66cd46e4a7`).
- `fixtures/issue1_formal_holdout48_v1/manifest.json` (Git blob `74ee6317c96835a2abd9cb5e33bc968b3fa496fa`).
- `tools/issue1_rehydrate_audit_v2.py` (Git blob `a1a5513215e951f93ac204f03e0b3c12b48753bb`).
- `tests/test_issue1_rehydrate_audit_v2.py` (Git blob `1f94b9e40ad5c6fd3a50f21665cc30d8621dbcd4`).
- `results/issue1_github_only_rehydration_audit_v2_2026-10-17.json` is the execution receipt **without any raw inputs or labels**.

Run in a checkout of **this branch at a pinned commit**, with Python 3.10+ and `sympy==1.14.0`:

```bash
python3 -m unittest discover -s tests -p 'test_issue1_rehydrate_audit_v2.py' -v
python3 tools/issue1_rehydrate_audit_v2.py \
  --generator tools/issue1_formal_holdout48_v1.py \
  --manifest fixtures/issue1_formal_holdout48_v1/manifest.json
```

The second command generates all 48 tasks and all reference objects in **memory** and prints only a hash-bound summary; it does not require source dataset files. To export **only** model-visible data, additionally use `--emit-public /temporary/only_public.json`; the tool refuses to overwrite the target. **Never supply generator source, score files, or private gold to the predictor.** Physical model/scorer isolation is an external deployment duty; a source audit alone cannot guarantee it.

To replay the **real** native EC on regenerated, temporary-only inputs, provide `--native-source` pointing to `GPT-EC-Closure-Engine@3f435ad4365d846d96264458540efb4848ce3541:01_repo/src/v4/ec_layerwise_source_policy_authority_v2.py`. Its required Git blob is `7da0cd8d876505cafdd5a9811132427e2f441a14`. The V2 verifier fail-closes on a mismatched EC blob, executes the source-pinned EC against 48 regenerated cases in a self-deleting directory, and validates every result against the frozen formal reference. The native source can be fetched using existing authenticated GitHub access; it is not bundled and no new local background service, COMMAND file, or LLM inference is required. **This turn verified exact reconstruction and recorded old native score, not a fresh native execution**, because the private native source was not mounted in the sandbox.

## Integrity / falsification evidence

| Test | Actual result | Limit |
|---|---|---|
| Regenerate public and mechanical gold from two pinned files | Both SHA-256 match frozen original | Same-authored formal labels, not independent NL truth |
| Run the same regeneration with `python -O` | PASS / hashes unchanged | The old V1 code had an `assert` bypass; new V2 `require()` is unconditional |
| Change generator code | REJECT | Trusted Git pin required |
| Modify or jointly replace manifest and its embedded hashes | REJECT | Replacing V2 verifier source+Git trust root itself remains out of scope |
| Inject `oracle_constraints` into model-visible input | REJECT | Lexical/semantic cues from policy meaning are not independently eliminated |
| Use an unpinned fake EC file under `python -O` | REJECT before import | Real native EC replay not newly measured here |
| Modify historical native score bytes | REJECT | Original score raw file is optional and **not** required for GitHub-only regeneration |
| Replay the historical local score when present | 48/48 same cases, inputs, labels and outputs | Rechecks recorded bytes, not fresh actual native execution |
| Actual fresh LLM inferences on the same 48 cases | NONE | No claim of nondegradation |

## Answer contamination findings

The predictor-exported `public.json` has **no** literal gold, oracle, label, reference, prediction, or closure-class strings. The original author source nevertheless defines the synthetic rule/solution correspondence and can regenerate the 48 reference values; therefore the full repository/source **must not** be included in a model prompt or accessible to a test agent. All claimed correctness here is derived by **code**, not any LLM judgment. The old ten-task source had trivial answer-proxy naming (`v*` correct, `x1` incorrect), and the newer projector only removes direct proxies; broad absence of semantic answer proxies has not been certified. The historical 17-case 1.5B result had no literal oracle fields in the observed prompt construction, but lacks a fresh independent NL holdout.

## Remaining blockers to scientific conclusions

Provide independently adjudicated natural-language source tasks from outside the author-written benchmark generator, frozen before any prediction; separate evaluator/model read permissions; execute identical-function EC and real LLM arms on identical public inputs; freeze raw model outputs prior to scoring; execute target-only original A–E interventions and apply the untouched original 0.20 threshold. Do not promote any old 48/48 code pass to an original AC.
