# Phase1 MVP TCC V2 — dependency-order successor

Protocol: `PHASE1_MVP_TCC_V2`
Parent: `PHASE1_MVP_TCC_V1`
Authority: Issue #32

## Reason for V2

The actual V1 run stopped at `INVALID_TEST_CONTRACT` in P0 because Issue #22 downstream assets were required before P2. That ordering prevented P2 from emitting the already-defined terminal `EC_NATIVE_SCOPE_INCOMPATIBLE` after the EC-native scope was qualified as incompatible.

V2 changes dependency scheduling only. It does not alter fixtures, dataset identity, thresholds, prompts, decoding, model results, EC source/protocols, or scoring semantics.

## Gate order

1. `P0_EARLY_PRECHECK`
   - no GitHub Actions
   - frozen foundation evidence exists
   - EC-native adapter contract exists
   - thresholds remain frozen
2. `P1_FOUNDATION_GATE`
   - dataset digest / leakage / Oracle replay unchanged from V1
3. `P2_EC_ADAPTER_GATE`
   - missing/unqualified -> `BLOCKED_EC_NATIVE_ADAPTER`
   - `INCOMPATIBLE` -> `EC_NATIVE_SCOPE_INCOMPATIBLE`
   - `PASS` -> downstream precheck
4. `P2B_DOWNSTREAM_PRECHECK_IF_COMPATIBLE`
   - only here require Issue #20, Issue #12 and full Issue #22 assets
5. If compatible and downstream-complete, delegate to the unchanged V1 continuation logic and wrap its terminal under V2 provenance.

## Preservation rule

The V1 actual result remains `INVALID_TEST_CONTRACT`; V2 does not rewrite it. No placeholder file may count as Issue #22 completion.

## Current qualified EC scope

- S3 reframing: `EC_NATIVE`, reportable separately.
- S3 admissible-set selection: `EC_NATIVE_NOT_APPLICABLE` under the frozen generic contract because EC next-action authority is singleton while M003/M009 require multi-selection.
- S4 closure: `EC_NATIVE_NOT_APPLICABLE` under the frozen generic contract because the S3 interface is not closure-identifying.

GitHub Actions remain disabled. Google Drive model relay remains forbidden.
