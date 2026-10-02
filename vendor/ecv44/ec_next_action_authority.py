from __future__ import annotations

from typing import Any, Iterable, Mapping

from ec_dynamic_frontier import (
    DynamicFrontierError,
    DynamicStateAuthority,
    choose_dynamic_issue,
    validate_dynamic_observation,
)
from v4.ec_issue_definition_gate import evaluate_issue_contract


class ECNextActionError(ValueError):
    pass


_BASE_PHASE_ORDER = ("REPAIR", "REGRESSION", "EVIDENCE")
_OPTIONAL_PREFIX_PHASES = ("PRIOR_ART",)
_ACCEPTED_LIMITATION = "ACCEPTED_ARCHITECTURAL_LIMITATION"


def _priority(issue: Mapping[str, Any]) -> int:
    value = str(issue.get("priority") or "").upper()
    if not value.startswith("P") or not value[1:].isdigit():
        raise ECNextActionError("INVALID_ISSUE_PRIORITY")
    return int(value[1:])


def _work_map(issue: Mapping[str, Any]) -> tuple[dict[str, str], tuple[str, ...]]:
    out: dict[str, str] = {}
    allowed = set(_BASE_PHASE_ORDER) | set(_OPTIONAL_PREFIX_PHASES)
    for raw in issue.get("work") or ():
        if isinstance(raw, str):
            wid = raw
            kind = wid.rsplit(":", 1)[-1].replace("-", "_").upper()
        else:
            wid = str(raw.get("work_id") or "")
            kind = str(raw.get("kind") or wid.rsplit(":", 1)[-1]).replace("-", "_").upper()
        if wid and kind in allowed:
            if kind in out and out[kind] != wid:
                raise ECNextActionError(f"DUPLICATE_REMEDIATION_PHASE:{kind}")
            out[kind] = wid
    if any(k not in out for k in _BASE_PHASE_ORDER):
        raise ECNextActionError("ISSUE_REMEDIATION_PHASES_INCOMPLETE")
    order = (("PRIOR_ART",) if "PRIOR_ART" in out else ()) + _BASE_PHASE_ORDER
    return out, order


def _normalize_blocked(blocked_work: Mapping[str, str] | None) -> dict[str, str]:
    blocked_raw = dict(blocked_work or {})
    blocked: dict[str, str] = {}
    for wid, reason in blocked_raw.items():
        work_id = str(wid).strip()
        why = str(reason).strip()
        if not work_id or not why:
            raise ECNextActionError("BLOCKED_WORK_REQUIRES_ID_AND_REASON")
        blocked[work_id] = why
    return blocked


def _issue_definition_gate(issue: Mapping[str, Any]) -> dict[str, Any] | None:
    if "action_class" not in issue and "issue_contract" not in issue:
        return None
    return evaluate_issue_contract(
        issue.get("issue_contract") if isinstance(issue.get("issue_contract"), Mapping) else {},
        action_class=str(issue.get("action_class") or "ANALYSIS"),
        domain=str(issue.get("domain") or ""),
        evidence=issue.get("issue_definition_evidence") if isinstance(issue.get("issue_definition_evidence"), Mapping) else None,
    )


def _require_dynamic_work_state_binding(
    dynamic_context: Mapping[str, Any],
    *,
    completed_work_ids: set[str],
    blocked_work: Mapping[str, str],
) -> None:
    raw_done = dynamic_context.get("completed_work_ids")
    raw_blocked = dynamic_context.get("blocked_work")
    if raw_done is None and raw_blocked is None:
        if completed_work_ids or blocked_work:
            raise ECNextActionError("DYNAMIC_CONTEXT_WORK_STATE_REQUIRED")
        return
    if raw_done is None or raw_blocked is None:
        raise ECNextActionError("DYNAMIC_CONTEXT_WORK_STATE_REQUIRED")
    if isinstance(raw_done, (str, bytes, Mapping)):
        raise ECNextActionError("DYNAMIC_CONTEXT_COMPLETED_WORK_INVALID")
    if not isinstance(raw_blocked, Mapping):
        raise ECNextActionError("DYNAMIC_CONTEXT_BLOCKED_WORK_INVALID")
    expected_done = {str(x) for x in raw_done}
    expected_blocked = {str(k): str(v) for k, v in raw_blocked.items()}
    if expected_done != completed_work_ids or expected_blocked != dict(blocked_work):
        raise ECNextActionError("DYNAMIC_CONTEXT_WORK_STATE_MISMATCH")


def _require_prior_art_admission(
    issue: Mapping[str, Any],
    works: Mapping[str, str],
    done: set[str],
) -> None:
    prior_art_present = "PRIOR_ART" in works
    prior_art_completed = prior_art_present and works["PRIOR_ART"] in done
    gate_required = prior_art_completed or (bool(issue.get("design_heavy")) and not prior_art_present)
    if not gate_required:
        return
    gate = issue.get("prior_art_gate")
    if not isinstance(gate, Mapping) or str(gate.get("status") or "").upper() != "PASS":
        raise ECNextActionError(f"PRIOR_ART_GATE_PASS_REQUIRED:{issue.get('issue_id')}")


def select_next_action(
    plan: Mapping[str, Any],
    *,
    completed_work_ids: Iterable[str] = (),
    blocked_work: Mapping[str, str] | None = None,
    dynamic_context: Mapping[str, Any] | None = None,
    dynamic_state_authority: DynamicStateAuthority | None = None,
) -> dict[str, Any]:
    """Return exactly one EC-authoritative actionable next step.

    Issue-definition sufficiency is a hard gate above both static and dynamic V4
    selection. Any active governed issue that requires REFRAME prevents all
    ActionPermit-style execution until the issue revision is repaired. Legacy
    issues that declare neither action_class nor issue_contract retain existing
    V3/V4-compatible behavior.
    """
    if not isinstance(plan, Mapping):
        raise ECNextActionError("EC_PLAN_REQUIRED")
    if plan.get("protocol") != "EC_REMEDIATION_PLAN_V1":
        raise ECNextActionError("EC_PLAN_PROTOCOL_INVALID")
    if plan.get("authority") != "EC_REMEDIATION_PLANNER_PROPOSAL":
        raise ECNextActionError("EC_PLAN_AUTHORITY_INVALID")
    if not str(plan.get("primary_goal") or "").strip():
        raise ECNextActionError("EC_PRIMARY_GOAL_REQUIRED")

    done = {str(x) for x in completed_work_ids}
    blocked = _normalize_blocked(blocked_work)
    for work_id in blocked:
        if work_id in done:
            raise ECNextActionError("WORK_CANNOT_BE_BOTH_COMPLETE_AND_BLOCKED")

    if dynamic_context is not None:
        _require_dynamic_work_state_binding(
            dynamic_context,
            completed_work_ids=done,
            blocked_work=blocked,
        )

    candidates: list[tuple[tuple[int, int, str], Mapping[str, Any], dict[str, str], tuple[str, ...], str, dict[str, Any] | None]] = []
    blocked_open: list[dict[str, str]] = []
    reframe_open: list[dict[str, Any]] = []
    accepted_limitations: list[str] = []
    completed_issue_ids: set[str] = set()
    for issue in plan.get("issues") or ():
        issue_id = str(issue.get("issue_id") or "")
        if not issue_id:
            raise ECNextActionError("ISSUE_ID_REQUIRED")
        if str(issue.get("disposition") or "").upper() == _ACCEPTED_LIMITATION:
            accepted_limitations.append(issue_id)
            completed_issue_ids.add(issue_id)
            continue

        gate = _issue_definition_gate(issue)
        if gate is not None and gate.get("status") != "PASS":
            reframe_open.append({
                "issue_id": issue_id,
                "action_class": gate.get("action_class"),
                "domain": gate.get("domain"),
                "required_variables": gate.get("required_variables") or [],
                "missing_variables": gate.get("missing_variables") or [],
                "ambiguous_variables": gate.get("ambiguous_variables") or [],
                "reframe_reasons": gate.get("reframe_reasons") or [],
                "scope_revision_id": gate.get("scope_revision_id"),
            })
            continue

        works, phase_order = _work_map(issue)
        _require_prior_art_admission(issue, works, done)
        if all(works[p] in done for p in phase_order):
            completed_issue_ids.add(issue_id)
            continue
        next_phase = next(p for p in phase_order if works[p] not in done)
        next_work = works[next_phase]
        if next_work in blocked:
            blocked_open.append({
                "issue_id": issue_id,
                "work_id": next_work,
                "phase": next_phase,
                "reason": blocked[next_work],
            })
            continue
        rank = (0 if bool(issue.get("blocker")) else 1, _priority(issue), issue_id)
        candidates.append((rank, issue, works, phase_order, next_phase, gate))

    if reframe_open:
        return {
            "protocol": "EC_NEXT_ACTION_V1",
            "authority": "EC_NEXT_ACTION_AUTHORITY",
            "status": "REFRAME",
            "work_id": None,
            "primary_goal": plan["primary_goal"],
            "reframe_open_issues": reframe_open,
            "blocked_open_work": blocked_open,
            "accepted_limitations": accepted_limitations,
            "selection_rule": "ISSUE_DEFINITION_GATE_FAIL_CLOSED_BEFORE_STATIC_OR_DYNAMIC_SELECTION",
        }

    if not candidates:
        terminal_dynamic: dict[str, Any] | None = None
        if dynamic_context is not None:
            try:
                terminal_dynamic = validate_dynamic_observation(
                    plan=plan,
                    context=dynamic_context,
                    state_authority=dynamic_state_authority,
                )
            except DynamicFrontierError as exc:
                raise ECNextActionError(str(exc)) from exc
            terminal_dynamic["reason"] = "TERMINAL_OR_BLOCKED_STATE_VERIFIED"
        out = {
            "protocol": "EC_NEXT_ACTION_V1",
            "authority": "EC_NEXT_ACTION_AUTHORITY",
            "status": "BLOCKED" if blocked_open else "NO_OPEN_WORK",
            "work_id": None,
            "primary_goal": plan["primary_goal"],
            "blocked_open_work": blocked_open,
            "reframe_open_issues": [],
            "accepted_limitations": accepted_limitations,
        }
        if terminal_dynamic is not None:
            out["dynamic_frontier"] = terminal_dynamic
        return out

    static = min(candidates, key=lambda x: x[0])
    selected = static
    dynamic_decision: dict[str, Any] | None = None
    if dynamic_context is not None:
        try:
            dynamic_decision = choose_dynamic_issue(
                plan=plan,
                candidate_issues=[item[1] for item in candidates],
                completed_issue_ids=completed_issue_ids,
                static_issue_id=str(static[1]["issue_id"]),
                context=dynamic_context,
                state_authority=dynamic_state_authority,
            )
        except DynamicFrontierError as exc:
            raise ECNextActionError(str(exc)) from exc
        if dynamic_decision["status"] == "BLOCKED":
            return {
                "protocol": "EC_NEXT_ACTION_V1",
                "authority": "EC_NEXT_ACTION_AUTHORITY",
                "status": "BLOCKED",
                "work_id": None,
                "primary_goal": plan["primary_goal"],
                "blocked_open_work": blocked_open,
                "reframe_open_issues": [],
                "accepted_limitations": accepted_limitations,
                "dynamic_frontier": dynamic_decision,
            }
        chosen_issue_id = str(dynamic_decision["issue_id"])
        selected = next(item for item in candidates if str(item[1]["issue_id"]) == chosen_issue_id)

    _, issue, works, _phase_order, phase, gate = selected
    static_rule = "ISSUE_DEFINITION_GATE__SKIP_ACCEPTED_LIMITATIONS__BLOCKER_THEN_PRIORITY_THEN_ISSUE_ID__PHASE_PRIOR_ART_IF_PRESENT_THEN_REPAIR_REGRESSION_EVIDENCE__SKIP_EXPLICITLY_BLOCKED_OPEN_WORK"
    selection_rule = static_rule if dynamic_context is None else (
        "ISSUE_DEFINITION_GATE__AUTHORITY_BOUND_DYNAMIC_FRONTIER__DEPENDENCY_READY__V3_PRESERVE_UNLESS_PARETO_DOMINATED__"
        "BLOCKER_DEPENDENCY_CRITICALITY_CURRENT_URGENCY__WORK_STATE_BOUND__THEN_PHASE_ORDER"
    )
    out = {
        "protocol": "EC_NEXT_ACTION_V1",
        "authority": "EC_NEXT_ACTION_AUTHORITY",
        "status": "EXECUTE",
        "work_id": works[phase],
        "phase": phase,
        "issue_id": issue["issue_id"],
        "priority": issue["priority"],
        "blocker": bool(issue.get("blocker")),
        "primary_goal": plan["primary_goal"],
        "issue_definition_gate": gate or {"status": "NOT_APPLICABLE"},
        "selection_rule": selection_rule,
        "blocked_open_work": blocked_open,
        "reframe_open_issues": [],
        "accepted_limitations": accepted_limitations,
    }
    if dynamic_decision is not None:
        out["dynamic_frontier"] = dynamic_decision
    return out
