from __future__ import annotations

from typing import Any, Mapping

from .ec_equation_contract import validate_equation_contract, verify_equation_evidence
from .ec_execution_semantics import validate_execution_contract, verify_execution_evidence
from .ec_variable_space_revision import validate_revision_request


PROTOCOL = "EC_V4_ISSUE_DEFINITION_GATE_V4"
MUTATING_ACTIONS = {"MUTATION", "REPAIR", "WRITE", "DEPLOY", "INSTALL", "EXECUTE"}
BROWSER_MUTATION_DOMAINS = {"BROWSER", "BROWSER_CONVERSATION", "CHROME_EXTENSION"}
EXPERIMENT_DOMAINS = {"EXPERIMENT", "ML_EXPERIMENT", "SCIENTIFIC_EXPERIMENT"}
BASE_FIELDS = (
    "problem_statement",
    "actors",
    "invariants",
    "failure_modes",
    "positive_acceptance_criteria",
    "evidence_authority",
    "scope_revision_id",
)
MUTATION_FIELDS = (
    "target_identity",
    "protected_non_targets",
    "negative_acceptance_criteria",
)
BROWSER_IDENTITY_FIELDS = ("window_id", "tab_id", "conversation_id")
FORBIDDEN_MUTATION_SELECTORS = {
    "active",
    "frontmost",
    "currentwindow",
    "first matching",
    "first_matching",
    "implicit singleton",
    "implicit_singleton",
}
PLACEHOLDER_VALUES = {"", "?", "unknown", "tbd", "todo", "any", "*", "none", "null"}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return _norm(value).lower() not in PLACEHOLDER_VALUES
    if isinstance(value, Mapping):
        return bool(value) and all(_nonempty(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return bool(value) and all(_nonempty(v) for v in value)
    return True


def required_variables(*, action_class: str, domain: str = "") -> list[str]:
    action = _norm(action_class).upper() or "ANALYSIS"
    domain_norm = _norm(domain).upper()
    required = list(BASE_FIELDS)
    if action in MUTATING_ACTIONS:
        required.extend(MUTATION_FIELDS)
    if action in MUTATING_ACTIONS and domain_norm in BROWSER_MUTATION_DOMAINS:
        required.extend(f"target_identity.{name}" for name in BROWSER_IDENTITY_FIELDS)
        required.extend(("discovery_selector", "mutation_selector"))
    if domain_norm in EXPERIMENT_DOMAINS:
        required.append("experiment_execution")
    return required


def _identity_value(contract: Mapping[str, Any], name: str) -> Any:
    identity = contract.get("target_identity")
    return identity.get(name) if isinstance(identity, Mapping) else None


def _selector_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(f"{k}:{v}" for k, v in sorted(value.items()))
    return _norm(value)


def evaluate_issue_contract(
    contract: Mapping[str, Any] | None,
    *,
    action_class: str,
    domain: str = "",
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    c = dict(contract or {})
    action = _norm(action_class).upper() or "ANALYSIS"
    domain_norm = _norm(domain).upper()
    required = required_variables(action_class=action, domain=domain_norm)
    missing: list[str] = []
    ambiguous: list[str] = []
    reasons: list[str] = []
    trace: list[dict[str, Any]] = []

    for field in BASE_FIELDS:
        ok = _nonempty(c.get(field))
        trace.append({"check": f"FIELD:{field}", "ok": ok})
        if not ok:
            missing.append(field)

    if action in MUTATING_ACTIONS:
        for field in MUTATION_FIELDS:
            ok = _nonempty(c.get(field))
            trace.append({"check": f"MUTATION_FIELD:{field}", "ok": ok})
            if not ok:
                missing.append(field)

    if action in MUTATING_ACTIONS and domain_norm in BROWSER_MUTATION_DOMAINS:
        for field in BROWSER_IDENTITY_FIELDS:
            value = _identity_value(c, field)
            ok = _nonempty(value)
            trace.append({"check": f"TARGET_IDENTITY:{field}", "ok": ok, "value": value})
            if not ok:
                missing.append(f"target_identity.{field}")
        discovery = c.get("discovery_selector")
        mutation = c.get("mutation_selector")
        if not _nonempty(discovery):
            missing.append("discovery_selector")
        if not _nonempty(mutation):
            missing.append("mutation_selector")
        mutation_text = _selector_text(mutation).lower()
        bad = sorted(x for x in FORBIDDEN_MUTATION_SELECTORS if x in mutation_text)
        if bad:
            ambiguous.append("mutation_selector")
            reasons.append("FORBIDDEN_MUTATION_SELECTOR:" + ",".join(bad))
        trace.append({
            "check": "DISCOVERY_MUTATION_SELECTOR_SEPARATION",
            "ok": _nonempty(discovery) and _nonempty(mutation) and not bad,
            "discovery_selector": discovery,
            "mutation_selector": mutation,
        })

    ev = dict(evidence or {})
    execution_contract_result: dict[str, Any] | None = None
    execution_evidence_result: dict[str, Any] | None = None
    if domain_norm in EXPERIMENT_DOMAINS:
        execution_contract = c.get("experiment_execution")
        if not isinstance(execution_contract, Mapping):
            missing.append("experiment_execution")
            execution_contract_result = {
                "status": "REFRAME",
                "errors": [{"type": "EXPERIMENT_EXECUTION_CONTRACT_REQUIRED"}],
            }
        else:
            execution_contract_result = validate_execution_contract(execution_contract)
            if execution_contract_result["status"] != "PASS":
                reasons.append("EXPERIMENT_EXECUTION_CONTRACT_INVALID")
            runtime_evidence = ev.get("experiment_execution_evidence")
            if runtime_evidence is not None:
                execution_evidence_result = verify_execution_evidence(
                    execution_contract,
                    runtime_evidence if isinstance(runtime_evidence, Mapping) else {},
                )
                if execution_evidence_result["status"] != "PASS":
                    reasons.append("EXPERIMENT_EXECUTION_EVIDENCE_INCOMPLETE")
        trace.append({
            "check": "EXPERIMENT_EXECUTION_SEMANTICS",
            "ok": bool(
                execution_contract_result
                and execution_contract_result.get("status") == "PASS"
                and (
                    execution_evidence_result is None
                    or execution_evidence_result.get("status") == "PASS"
                )
            ),
            "definition": execution_contract_result,
            "runtime_evidence": execution_evidence_result,
        })

    equation_contract_result: dict[str, Any] | None = None
    equation_evidence_result: dict[str, Any] | None = None
    if c.get("mathematical_semantics_required") is True:
        equation_contract = c.get("equation_contract")
        if not isinstance(equation_contract, Mapping):
            missing.append("equation_contract")
            equation_contract_result = {
                "status": "REFRAME",
                "errors": [{"type": "EQUATION_CONTRACT_REQUIRED"}],
            }
        else:
            equation_contract_result = validate_equation_contract(equation_contract)
            if equation_contract_result["status"] != "PASS":
                reasons.append("EQUATION_CONTRACT_INVALID")
            implementation_evidence = ev.get("equation_implementation_evidence")
            if implementation_evidence is not None:
                equation_evidence_result = verify_equation_evidence(
                    equation_contract,
                    implementation_evidence if isinstance(implementation_evidence, Mapping) else {},
                )
                if equation_evidence_result["status"] != "PASS":
                    reasons.append("EQUATION_IMPLEMENTATION_SEMANTICS_MISMATCH")
        trace.append({
            "check": "EQUATION_OBJECTIVE_SEMANTICS",
            "ok": bool(
                equation_contract_result
                and equation_contract_result.get("status") == "PASS"
                and (
                    equation_evidence_result is None
                    or equation_evidence_result.get("status") == "PASS"
                )
            ),
            "definition": equation_contract_result,
            "implementation_evidence": equation_evidence_result,
        })

    revision_result: dict[str, Any] | None = None
    revision_request = ev.get("variable_space_revision")
    if revision_request is not None:
        variable_space = c.get("variable_space")
        if not isinstance(variable_space, Mapping):
            revision_result = {
                "status": "INVALID",
                "required": True,
                "reason": "VARIABLE_SPACE_REQUIRED_FOR_REVISION",
            }
        elif not isinstance(revision_request, Mapping):
            revision_result = {
                "status": "INVALID",
                "required": True,
                "reason": "VARIABLE_SPACE_REVISION_REQUEST_INVALID",
            }
        else:
            revision_result = validate_revision_request(variable_space, revision_request)

        if revision_result["status"] == "REVISE":
            reasons.append("VARIABLE_SPACE_REVISION_REQUIRED")
        elif revision_result["status"] == "INVALID":
            reasons.append("VARIABLE_SPACE_REVISION_INVALID:" + str(revision_result.get("reason") or ""))
        trace.append({
            "check": "VARIABLE_SPACE_REVISION",
            "ok": revision_result["status"] == "PRESERVE",
            "result": revision_result,
        })

    if ev.get("unexpected_side_effect") is True:
        reasons.append("UNEXPECTED_SIDE_EFFECT")
    if int(ev.get("failed_repair_count") or 0) >= 2:
        reasons.append("REPEATED_REPAIR_FAILURE")
    if ev.get("new_actor_discovered") is True:
        reasons.append("NEW_ACTOR_DISCOVERED")
    if ev.get("new_target_or_resource_discovered") is True:
        reasons.append("NEW_TARGET_OR_RESOURCE_DISCOVERED")
    if ev.get("scope_contradictions"):
        reasons.append("SCOPE_CONTRADICTED_BY_EVIDENCE")
    observed_revision = ev.get("scope_revision_id")
    if observed_revision is not None and _norm(observed_revision) != _norm(c.get("scope_revision_id")):
        reasons.append("SCOPE_REVISION_STALE")

    missing = sorted(set(missing))
    ambiguous = sorted(set(ambiguous))
    status = "PASS" if not missing and not ambiguous and not reasons else "REFRAME"
    return {
        "protocol": PROTOCOL,
        "authority": "EC_V4_ISSUE_DEFINITION_GATE",
        "status": status,
        "action_class": action,
        "domain": domain_norm,
        "required_variables": required,
        "missing_variables": missing,
        "ambiguous_variables": ambiguous,
        "reframe_reasons": reasons,
        "scope_revision_id": c.get("scope_revision_id"),
        "variable_space_revision": revision_result,
        "experiment_execution": execution_contract_result,
        "experiment_execution_evidence": execution_evidence_result,
        "equation_contract": equation_contract_result,
        "equation_implementation_evidence": equation_evidence_result,
        "decision_trace": trace,
    }
