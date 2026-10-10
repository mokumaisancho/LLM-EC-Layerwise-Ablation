# Root issue #1 — original AC/MVP dependency-first execution contract (TCC v6)

**Authority and scope**: [root issue #1](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/1), `ACCEPTANCE_CRITERIA.md`, immutable `docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json`. No scientific exit definition is altered by later bounded experiments or administratively closed subissues. Existing scientific Phase1 V1/V2 data and materiality **0.20** remain unchanged.

## Definition of MVP and exit

The **original minimum reportable MVP** is the scientifically valid coarse four-layer S1 semantic extraction, S2 candidate generation, S3 selection/reframing, S4 execution/closure causal localization. The minimum requires **18 exact original ACs**: AC-01, 02, 03, 04, 05, 06, 07, 08, 09, 11, 12, 13, 14, 15, 16, 17, 19, 20. AC-10 fine decomposition and AC-18 final smallest-LLM/largest-EC replacement boundary are post-MVP in the frozen normative contract. The original end-to-end research additionally requires AC-18, and as applicable AC-10.

A PASS for the original MVP requires all 18 independent AC tests PASS with their dependencies PASS, genuine *semantically matched* original four-layer **A/B/C/D/E** and controlled single-layer Oracle substitutions, raw-source model/EC authority, same persisted upstream artifact across arms, materiality/scoring, and no evidence-overturning error. **Neither an isolated S3 Oracle success nor an all-correct EC fallback can count as original full A-E.**

## Pre-committed dependency graph and critical path

Versioned machine-readable authoritative contract: `docs/ISSUE1_ROOT_AC_MVP_DEPENDENCY_ORCHESTRATION_V6.json`. It **imports** the normative 20-AC dependency graph rather than reconstructing it from assistant guesses. The parser enforces exactly 20 original identifiers, 18 mandatory/2 post-MVP, known issue edges and explicit frozen conditional dependencies, topological order, no orphan edges/cycles, and a prohibition on a PASS when any prerequisite AC is not PASS.

| Order | Work ID | Required before | State after actual TCC v6 |
|---|---|---|---|
| P0 | W0_SOURCE_LOCK | None | DONE; original AC and normative Git blob pins |
| P0 | W1_DEPENDENCY_GRAPH | W0 | DONE; validated original AC20/MVP18 and issue dependencies |
| P0 | W2_NATIVE_CONTRACT_QUALIFICATION | W1 | DONE, negative source-capability witness |
| P0 | W3_LOCAL_ACTUAL_EXPERIMENTS | W1 | DONE **scoped only**; real EC/Qwen/Oracle/guard chain rerun |
| P0 | W4_VERSIONED_NATIVE_REPAIR_PLAN | W2+W3 | SPECIFIED, genuine native source extension NOT IMPLEMENTED |
| P0 | W5_FOUR_LAYER_ACTUAL_AE | W4 | BLOCKED: EC native S3+S4 source contract mismatch |
| P0 | W6_LOCALIZE_MVP | W5 | BLOCKED: absent whole-layer causal raw evidence |
| P1 | W7_INDEPENDENT_REVIEW | W6 | BLOCKED: independent unseen gold/original LLM0/authorized V4 |

Source-capability proof is precise: original generic S3 selects *all* admissible members for cases **M003, M009**, whereas pinned ECv4.4 is a **singleton next-action** selector. Generic S4 `selected/rejected/reframed` signature has CLOSE/CONTINUE collisions, a **best possible majority 8/10** bound in ten known cases, not EC closure accuracy. Cannot fix by silently renaming the EC singleton to full multiselection, adding private Oracle labels, changing the old frozen contract, or inventing S4 semantics. Real remediation needs an explicit versioned successor, **genuinely native EC implementation** and independent source-qualified reasons for all candidate selections and closure, then four-layer controlled same-function experiments.

## One-invocation machine TCC and failure branches

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_root_ac_orchestrator_v6.py \
 --tcc-root /private/tmp/llmec-tcc-generator-reference-20261009 \
 --ec-root /private/tmp/llmec-ecv44-source-20261010 \
 --out /private/tmp/issue1-root-ac-v6-last.json
```

TCC v6 generates a real compiler-pinned `tcc.spec.v3` graph **12 nodes/17 edges**. It performs G0 immutable original Git source check → G1 AC/work DAG → actual frozen V2 P0/P1/P2 replay → G4/G5/G6/G10 casewise real output precheck + input SHA seal → **self-directed actual stage1→5 nested TCC** → post-run raw output SHA and configuration seal → native S3/S4 functional incompatibility witnesses → AC20 topological scoring → true original MVP exit decision. No manual prompt is required between any executable nodes; previous real output is cached and source-pinned. Missing real model output can be re-inferred by an upstream compatible CLI branch if genuine pinned model+runtime are supplied; otherwise explicit blocker.

Branch rules: source/AC graph/raw/oracle/threshold mutation ⇒ **`INTEGRITY_FAIL_CLOSED`**; native actual source mismatch ⇒ **`NATIVE_SOURCE_CAPABILITY_GAP`**, after all compatible local experiments and repair spec have run; missing independent external study ⇒ `EXTERNAL_INDEPENDENCE_MISSING`; only genuine original 18/18 plus all-layer A-E ⇒ `ROOT_MVP_VERIFIED`. Exit code 0 is reserved for actually verified root; code 2 is an *honest scientific source blocker*, and code 3 indicates integrity failure.

### Result-overturning error gates

- **G0/G7**: original AC markdown, normative contract, EC adapter and S4 identifiability Git blobs match predeclared pins; the v6 plan itself has a predeclared Git blob; **13 Python scientific execution modules must match tracked HEAD Git blobs before execution, after experiments and before final AC scoring**. Uncommitted or runtime-modified scientific code invalidates the result. Original 0.20 threshold cannot silently change. No GitHub Actions.
- **G1/G2**: exact normative AC20/MVP18, issue and task dependency DAG acyclic and no unknown parent, every AC PASS requires prerequisite PASS.
- **G3**: actual native adapter authority and S3+S4 counterexamples; incompatible native APIs are recorded as factual capability gaps rather than hidden adapters.
- **G4/G5/G10**: 17 cases are unique and same-case aligned; real Qwen and EC raw source reports have fixed *historical external Git blob* pins; identical upstream SHA, raw response == scored prediction, immutable Oracle after inference, model/EC source identities, original item + aggregated scores recomputed. No duplicated or silent reclassification.
- **G6**: existing development fixtures and Qwen model are explicitly **not** independently unseen, are **not** the proven original LLM0, and cannot qualify independent performance.
- **G8/G9**: nested SUITE/ECv4 method audit and actual real inferences; hybrid gains are credited to 15 native EC fallback calls, **not** upgraded LLM competence. 
- **G11**: original root cannot be closed by bounded `machine_scoped_complete`, GitHub issue state, source hash alone, or a winning sublayer result.
- **Pre/post seal**: record SHA256 of seven frozen actual source artifacts **before and after all runs**, including recheck at AC assessment; changed artifact invalidates the whole result. Failed gate reaches TCC `blocked_integrity`; never report scientific success.

Actual v6 research result: original root has **2/18 strictly PASS** AC (AC-19, AC-20), **16/18 unmet**. It is a deliberately conservative original-AC score, not a denial of completed scoped model experiments. Machine TCC terminal `blocked_native_semantics`, not success. [Casewise sealed result](../results/issue1_root_ac_mvp_tcc_v6_actual_2026-10-10.json).

**Root task is NOT complete.** At present, only a genuine native-compatible EC source extension plus new versioned four-layer experimental contract can unlock W5. The externally independent #57/#58 model/holdout review is separately unqualified. Normal ChatGPT text conversations do not self-reopen after a final answer. The headless TCC implements one-call conditional execution of everything currently machine-feasible; it does not run a background scheduler, modify the human's desktop UI, self-certify external gold, or invent new EC authority.
