from __future__ import annotations

import argparse
import json
from pathlib import Path

from ec_v4_adapter import ECV4SuiteBridge, EXPECTED_V4_REF
from suite_v4_atomic_gate import evaluate_atomic_candidate


class _Ledger:
    @staticmethod
    def is_authoritative(ref: str) -> bool:
        return str(ref).startswith("auth:")


class _Decision:
    action = "ABSTAIN"
    reasons = ()
    commit_allowed = False


class _BaseController:
    @staticmethod
    def decide(_request):
        return _Decision()

    @staticmethod
    def consume_verified_outcome(**_kwargs) -> bool:
        return True


def _issue(issue_id: str, priority: str) -> dict:
    stem = issue_id.split(":")[-1]
    return {
        "issue_id": issue_id,
        "priority": priority,
        "blocker": False,
        "work": [
            {"work_id": f"work:{stem}:repair", "kind": "REPAIR"},
            {"work_id": f"work:{stem}:regression", "kind": "REGRESSION"},
            {"work_id": f"work:{stem}:evidence", "kind": "EVIDENCE"},
        ],
    }


def _plan() -> dict:
    return {
        "protocol": "EC_REMEDIATION_PLAN_V1",
        "authority": "EC_REMEDIATION_PLANNER_PROPOSAL",
        "primary_goal": "verify Suite-to-V4 dynamic authority flow",
        "issues": [_issue("issue:A", "P0"), _issue("issue:B", "P1"), _issue("issue:C", "P2")],
    }


def _context(bridge: ECV4SuiteBridge, plan: dict, revision: int, *, graph=None, urgency=None) -> dict:
    graph = graph or {"issue:A": ["issue:B"], "issue:B": [], "issue:C": []}
    urgency = urgency or {"issue:A": 0.9, "issue:B": 0.7, "issue:C": 0.2}
    context = {
        "protocol": "EC_DYNAMIC_FRONTIER_CONTEXT_V2",
        "plan_digest": bridge.runtime.v4_control.plan_digest(plan),
        "state_revision": revision,
        "dependency_graph": graph,
        "issue_state": {key: {"urgency": value} for key, value in urgency.items()},
        "observation_ref": f"auth:e2e:state:{revision}",
    }
    context["state_digest"] = bridge.runtime.v4_control.state_digest(context)
    return context


def _state_authority(ref: str, digest: str, revision: int) -> bool:
    return ref == f"auth:e2e:state:{revision}" and len(digest) == 64 and revision >= 0


def _exercise_dynamic_authority(bridge: ECV4SuiteBridge) -> str:
    plan = _plan()
    context = _context(bridge, plan, 1)
    out = bridge.select_next_action(
        plan,
        dynamic_context=context,
        dynamic_state_authority=_state_authority,
    )
    if out.get("issue_id") != "issue:B":
        raise SystemExit("DYNAMIC_AUTHORITY_E2E_FAILED")
    return str(out["dynamic_frontier"]["reason"])


def _exercise_r3_state_binding(bridge: ECV4SuiteBridge) -> None:
    plan = _plan()
    newer = _context(bridge, plan, 2)
    bridge.select_next_action(plan, dynamic_context=newer, dynamic_state_authority=_state_authority)

    older = _context(bridge, plan, 1)
    try:
        bridge.select_next_action(plan, dynamic_context=older, dynamic_state_authority=_state_authority)
    except ValueError as exc:
        if "DYNAMIC_CONTEXT_STATE_REVISION_ROLLBACK" not in str(exc):
            raise SystemExit("R3_REVISION_ROLLBACK_WRONG_ERROR") from exc
    else:
        raise SystemExit("R3_REVISION_ROLLBACK_NOT_BLOCKED")

    conflict = _context(bridge, plan, 2, urgency={"issue:A": 0.8, "issue:B": 0.7, "issue:C": 0.2})
    try:
        bridge.select_next_action(plan, dynamic_context=conflict, dynamic_state_authority=_state_authority)
    except ValueError as exc:
        if "DYNAMIC_CONTEXT_STATE_REVISION_CONFLICT" not in str(exc):
            raise SystemExit("R3_REVISION_CONFLICT_WRONG_ERROR") from exc
    else:
        raise SystemExit("R3_REVISION_CONFLICT_NOT_BLOCKED")

    fresh_bridge_plan = _plan()
    stale_context = _context(bridge, fresh_bridge_plan, 3)
    fresh_bridge_plan["issues"][2]["disposition"] = "ACCEPTED_ARCHITECTURAL_LIMITATION"
    try:
        bridge.select_next_action(
            fresh_bridge_plan,
            dynamic_context=stale_context,
            dynamic_state_authority=_state_authority,
        )
    except ValueError as exc:
        if "DYNAMIC_CONTEXT_STALE_OR_UNBOUND" not in str(exc):
            raise SystemExit("R3_DISPOSITION_BINDING_WRONG_ERROR") from exc
    else:
        raise SystemExit("R3_DISPOSITION_BINDING_NOT_BLOCKED")

    critical_plan = _plan()
    critical_plan["issues"][2]["disposition"] = "ACCEPTED_ARCHITECTURAL_LIMITATION"
    critical_context = _context(
        bridge,
        critical_plan,
        4,
        graph={"issue:A": [], "issue:B": [], "issue:C": ["issue:B"]},
        urgency={"issue:A": 0.5, "issue:B": 0.5, "issue:C": 0.5},
    )
    critical = bridge.select_next_action(
        critical_plan,
        dynamic_context=critical_context,
        dynamic_state_authority=_state_authority,
    )
    if critical.get("issue_id") != "issue:A":
        raise SystemExit("R3_COMPLETED_DESCENDANT_CRITICALITY_FAILED")


def _exercise_relevance_authority(bridge: ECV4SuiteBridge) -> None:
    from v4.ec_decision_binding import prior_art_subject_digest

    binding = {
        "primary_goal_digest": "goal:e2e",
        "focus_frame_id": "focus:e2e",
        "intent_revision": 1,
        "graph_digest": "graph:e2e",
    }
    packet = {
        "problem_signature": "dynamic dependency scheduling under changing state",
        "search_queries": ["dynamic scheduling authority binding"],
        "search_attempts": [
            {"channel": "INTERNAL", "query": "EC next action", "result_count": 1},
            {"channel": "LITERATURE", "query": "reactive scheduling", "result_count": 1},
            {"channel": "GITHUB", "query": "RCPSP", "result_count": 1},
        ],
        "sources": [{"ref": "e2e:source:1"}],
        "existing_methods": ["reactive scheduling"],
        "github_repos": ["example/rcpsp"],
        "reuse_class": "EXTEND",
        "gap": "decision-bound authority verification",
        "license_constraints": "Reference only.",
        "selected_basis": "Extend with authority-bound evidence.",
        "decision_binding": dict(binding),
    }
    binding_digest = bridge.runtime.v4_control.decision_binding_digest(binding)
    subject_digest = prior_art_subject_digest(packet)
    packet["relevance_evidence"] = {
        "status": "PASS",
        "authority": "EXTERNAL_VERIFIER",
        "authority_ref": "auth:e2e:relevance:1",
        "binding_digest": binding_digest,
        "subject_digest": subject_digest,
    }

    def relevance_authority(ref: str, subject: str, decision: str) -> bool:
        return ref == "auth:e2e:relevance:1" and subject == subject_digest and decision == binding_digest

    out = bridge.evaluate_prior_art(
        packet,
        expected_binding=binding,
        relevance_authority=relevance_authority,
    )
    if out.get("status") != "PASS":
        raise SystemExit("RELEVANCE_AUTHORITY_E2E_FAILED")

    blocked = bridge.evaluate_prior_art(packet, expected_binding=binding)
    if blocked.get("status") != "BLOCKED" or "RELEVANCE_AUTHORITY_RESOLVER_REQUIRED" not in blocked.get("reasons", []):
        raise SystemExit("RELEVANCE_AUTHORITY_FAIL_CLOSED_MISSING")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-root", type=Path, required=True)
    parser.add_argument("--ec-v4-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    gate = evaluate_atomic_candidate(args.suite_root)
    if gate["status"] != "PASS":
        raise SystemExit("ATOMIC_GATE_BLOCKED:" + ",".join(gate["reasons"]))

    bridge = ECV4SuiteBridge.from_ec_v4_checkout(
        ec_v4_root=args.ec_v4_root,
        base_controller=_BaseController(),
        ledger=_Ledger(),
        suite_root=args.suite_root,
        runtime_stage="EXPERIMENTAL",
    )
    snapshot = bridge.runtime.v4_control.snapshot()
    if snapshot.protocol != "EC_V4_CONTROL_PLANE_V1":
        raise SystemExit("V4_CONTROL_PROTOCOL_MISMATCH")

    dynamic_reason = _exercise_dynamic_authority(bridge)
    _exercise_r3_state_binding(bridge)
    _exercise_relevance_authority(bridge)

    result = {
        "protocol": "SUITE_EC_V4_R3_ATOMIC_E2E_V3",
        "status": "PASS",
        "suite_atomic_gate": gate["status"],
        "ec_v4_ref": EXPECTED_V4_REF,
        "runtime_stage": bridge.runtime_stage,
        "v4_control_protocol": snapshot.protocol,
        "v4_control_mode": snapshot.mode,
        "dynamic_authority_flow": "PASS",
        "dynamic_selection_reason": dynamic_reason,
        "revision_rollback_fail_closed": "PASS",
        "same_revision_digest_conflict_fail_closed": "PASS",
        "plan_disposition_stale_context_fail_closed": "PASS",
        "completed_descendant_criticality_filter": "PASS",
        "relevance_authority_flow": "PASS"
    }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
