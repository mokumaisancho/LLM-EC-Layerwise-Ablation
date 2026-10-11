# Issue #1 — Original Phase1 W4B/W4C policy TCC v12

Frozen original S1–S4, 18 MVP AC and materiality 0.20 remain unchanged. No optional 13 proof AC, 120 documents, C1–C6 expansion or GitHub Actions.

## TCC dependency DAG and branch rules

1. Seal new v12 source blobs before execution.
2. Execute original v11 TCC (includes v10, old native mismatch, 17 issue #61 adversarial controls) and require original **2/18**.
3. Pin new EC source-policy v2 commit `b5eb0c7d57ce819194e7ca840628007bd582274b`, native module and tests by Git blob digest.
4. Run new and old EC policy/native source tests, **46 tests PASS** with 24 distinct formal public-input cases.
5. Recheck all source blobs; never upgrade author-visible finite formal semantics to independently validated natural-language semantics or real-world obligation completeness.
6. If source, tests or executor integrity fails, return `blocked_integrity`; if checks pass but independent semantic custody is missing, return `blocked_external_semantics`. Original 18AC completion is forbidden until real A/B/C/D/E all-layer model/native/Oracle evidence.

Actual execution: **10 nodes, 13 edges, 46/46 EC tests PASS, source pins stable, 0 errors, terminal `blocked_external_semantics`, original 2/18 AC.** Evidence: `results/issue1_original_phase1_tcc_v12_source_policy_actual_2026-10-11.json`.

Dependencies: #59 independently correct S3 semantic meaning; #60 independently complete S4 task obligations; #61 trusted non-target LLM/EC execution and Oracle custody; then real matched A–E; finally 18/18 original AC. Formal policy source control and positive-negative diagnostic tests do not close those issues.
