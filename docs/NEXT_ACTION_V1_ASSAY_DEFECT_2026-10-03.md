# Next-action V1 assay defect — 2026-10-03

Status: `V1_RESULT_NON_REPORTABLE_FOR_EC_VS_LLM_PERFORMANCE`

The frozen V1 fixtures and EC oracle are preserved unchanged. During the first LLM execution, a protocol-completeness defect was identified by comparing the frozen LLM-visible policy to the pinned EC source, not by changing any oracle label.

Pinned EC behavior in `ec_next_action_authority._issue_definition_gate`:
- if an issue contains neither `action_class` nor `issue_contract`, the issue-definition gate is `NOT_APPLICABLE` (legacy compatibility);
- if either field is present, `evaluate_issue_contract` applies and a non-PASS result forces `REFRAME`.

V1 LLM-visible policy only stated that insufficient governed issue definition forces `REFRAME`; it omitted the legacy `NOT_APPLICABLE` activation rule. Therefore ordinary legacy fixtures N201–N216 were underspecified for the LLM while the EC implementation bypassed that gate.

V1 must finish and be retained as diagnostic evidence, but its EC-vs-LLM accuracy gap is not a valid function-replacement estimate.

Successor V2 rules:
1. Keep all 17 structured plan/current-state fixtures and oracle labels unchanged.
2. Add the exact issue-definition gate activation condition.
3. Constrain output schema so `status`, `work_id`, and `reason_code` combinations obey the already-frozen control contract; this removes format inconsistency without revealing which status applies to a fixture.
4. Before model inference, execute pinned EC on all fixtures and require 17/17 oracle agreement.
5. Freeze V2 digest before model inference; no further prompt/fixture/metric edits after that gate.
6. GitHub Actions disabled; Google Drive unused.
