# Issue #1: TCC v9 AC dependency continuation — candidate, runtime verification pending

The scientific source of truth remains `ACCEPTANCE_CRITERIA.md` plus `docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json`. Original Phase1 requires AC-01..20, with **18 mandatory MVP AC** and post-MVP AC-10/AC-18, four original matched S1–S4 A/B/C/D/E and one-layer Oracle attribution. The original materiality threshold is 0.20; earlier ECv4.4 singleton limitations, S4 identifiability issues, and original source hash witnesses remain in force.

## One-command candidate

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_root_ac_continuation_tcc_v9.py \
  --tcc-root /private/tmp/llmec-tcc-generator-reference-20261009 \
  --ec-root /private/tmp/llmec-ecv44-source-20261010 \
  --v7-native-root /private/tmp/issue1-ec-w4a-frozen-20261010 \
  --new-native-root /private/tmp/issue1-ec-native-layerwise-20261010 \
  --out /private/tmp/issue1-root-tcc9-result.json
```

An optional `--external-study-dir <path>` adds gold-blind structural preflight of genuine external readiness, **never** self-certifies independent custody/LLM0/V4 or upgrades original scientific AC.

### Dependency order and branches

- W0–W3: original AC source lock, 20-AC/18-MVP dependency DAG, frozen v6 and scoped actual v8 source checks.
- W4A: original pinned EC 24fe3a6 native multi-selection and S4 obligation mechanism.
- W4B typed formal sublayer: native ae4b02b, 24 source tests and original 12 public typed cases, followed by **48 additional generated structured cases** if the new code actually executes.
- W4C fail-closed: underived complete S4 obligation inventory cannot authorize CLOSE; **48 additional S4 refusal checks** and source hash/unknown-fact negative controls if executed.
- W4B independent natural-language semantic authority (#59) and W4C independently exhaustive S4 obligations (#60) remain separate unresolved prerequisites for W5.
- W5: true source-equivalent original A/B/C/D/E across S1–S4; no run/claim until both provenance prerequisites and proper independent same-function source are demonstrated.
- W6: root 18/18 mandatory original AC and layerwise causal attribution.
- W7: distinct LLM0/V4/gold blind independent ability-retention follow-up.

The v9 planner parses the **existing original normative** AC DAG, checks exact 18/20 membership, dependencies and cycles, allows only registered original source-qualified local AC-19/AC-20 PASS, and forbids promoting scoped typed behavior or even an internally well-formed external study into independent scientific correctness. Any altered frozen threshold, false PASS, source hash drift, unauthorized oracle/gold exposure, duplicate case or unexpected runtime exit fails closed. It also checks pre/post original actual raw hashes, native/source Python Git blobs and frozen contract tracked HEAD hashes.

### Verification state

**Do not treat v9 as validated.** At the time of this commit the authorized Mac checkout update and test creation were blocked by the execution safety check. The two v9 Python modules were saved to the research repo but **have not been executed**. The 48 additional cases and the v9 completion branch are expected test scopes, **not completed experiment results**. Previously sealed v8 remains the latest verified machine result: 273 research regressions PASS, 24 native unit tests PASS, 12 formal typed tests PASS, true root scientific AC **2/18** and original issue OPEN.

The code is not a background task, scheduler, or self-reinvocation system. It is a bounded one-invocation TCC continuation path that can only execute if run on an authorized machine, cannot create independent expert judgments from hidden development labels, and must preserve the original scientific exit.
