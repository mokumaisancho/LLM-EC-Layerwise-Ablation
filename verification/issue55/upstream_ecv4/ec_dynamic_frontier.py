from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Iterable, Mapping


PROTOCOL = "EC_DYNAMIC_FRONTIER_CONTEXT_V2"
DynamicStateAuthority = Callable[[str, str, int], bool]


class DynamicFrontierError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def plan_digest(plan: Mapping[str, Any]) -> str:
    """Digest all fields that may change next-action authority."""
    issues = []
    for issue in plan.get("issues") or ():
        issues.append({
            "issue_id": str(issue.get("issue_id") or ""),
            "priority": str(issue.get("priority") or ""),
            "blocker": bool(issue.get("blocker")),
            "disposition": str(issue.get("disposition") or "").upper(),
            "decision_binding": issue.get("decision_binding"),
            "evidence_binding_mode": issue.get("evidence_binding_mode"),
            "acceptance_criterion": issue.get("acceptance_criterion"),
            "work": [
                {
                    "work_id": str(work.get("work_id") or "") if isinstance(work, Mapping) else str(work),
                    "kind": str(work.get("kind") or "") if isinstance(work, Mapping) else "",
                    "depends_on": list(work.get("depends_on") or ()) if isinstance(work, Mapping) else [],
                }
                for work in (issue.get("work") or ())
            ],
        })
    subject = {
        "protocol": plan.get("protocol"),
        "authority": plan.get("authority"),
        "primary_goal": plan.get("primary_goal"),
        "additional_goals": plan.get("additional_goals"),
        "issues": issues,
    }
    return _digest(subject)


def state_subject(context: Mapping[str, Any]) -> dict[str, Any]:
    """Exact mutable state covered by the authoritative observation."""
    return {
        "protocol": context.get("protocol"),
        "plan_digest": context.get("plan_digest"),
        "state_revision": context.get("state_revision"),
        "dependency_graph": context.get("dependency_graph"),
        "issue_state": context.get("issue_state"),
    }


def state_digest(context: Mapping[str, Any]) -> str:
    return _digest(state_subject(context))


def _priority(issue: Mapping[str, Any]) -> int:
    raw = str(issue.get("priority") or "").upper()
    if not raw.startswith("P") or not raw[1:].isdigit():
        raise DynamicFrontierError("INVALID_ISSUE_PRIORITY")
    return int(raw[1:])


def _context(
    plan: Mapping[str, Any],
    context: Mapping[str, Any],
    candidate_issue_ids: set[str],
    *,
    state_authority: DynamicStateAuthority | None,
) -> tuple[dict[str, tuple[str, ...]], dict[str, float]]:
    if context.get("protocol") != PROTOCOL:
        raise DynamicFrontierError("DYNAMIC_CONTEXT_PROTOCOL_INVALID")
    if context.get("plan_digest") != plan_digest(plan):
        raise DynamicFrontierError("DYNAMIC_CONTEXT_STALE_OR_UNBOUND")
    revision = context.get("state_revision")
    if not isinstance(revision, int) or revision < 0:
        raise DynamicFrontierError("DYNAMIC_CONTEXT_STATE_REVISION_REQUIRED")

    supplied_state_digest = str(context.get("state_digest") or "")
    expected_state_digest = state_digest(context)
    if not supplied_state_digest:
        raise DynamicFrontierError("DYNAMIC_STATE_DIGEST_REQUIRED")
    if supplied_state_digest != expected_state_digest:
        raise DynamicFrontierError("DYNAMIC_STATE_DIGEST_MISMATCH")
    observation_ref = str(context.get("observation_ref") or "").strip()
    if not observation_ref:
        raise DynamicFrontierError("DYNAMIC_OBSERVATION_REF_REQUIRED")
    if state_authority is None:
        raise DynamicFrontierError("DYNAMIC_STATE_AUTHORITY_REQUIRED")
    try:
        authoritative = bool(
            state_authority(observation_ref, expected_state_digest, revision)
        )
    except Exception:
        authoritative = False
    if not authoritative:
        raise DynamicFrontierError("DYNAMIC_STATE_NOT_AUTHORITATIVE")

    all_issue_ids = {str(issue.get("issue_id") or "") for issue in plan.get("issues") or ()}
    if "" in all_issue_ids:
        raise DynamicFrontierError("ISSUE_ID_REQUIRED")

    raw_graph = context.get("dependency_graph") or {}
    if not isinstance(raw_graph, Mapping):
        raise DynamicFrontierError("DEPENDENCY_GRAPH_REQUIRED")
    graph: dict[str, tuple[str, ...]] = {}
    for issue_id in all_issue_ids:
        raw = raw_graph.get(issue_id, ())
        if isinstance(raw, (str, bytes)) or not isinstance(raw, Iterable):
            raise DynamicFrontierError(f"DEPENDENCY_LIST_INVALID:{issue_id}")
        deps = tuple(str(x) for x in raw)
        unknown = sorted(set(deps) - all_issue_ids)
        if unknown:
            raise DynamicFrontierError(
                f"DEPENDENCY_TARGET_UNKNOWN:{issue_id}:{','.join(unknown)}"
            )
        if issue_id in deps:
            raise DynamicFrontierError(f"SELF_DEPENDENCY_FORBIDDEN:{issue_id}")
        graph[issue_id] = deps

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise DynamicFrontierError("DEPENDENCY_GRAPH_CYCLE")
        visiting.add(node)
        for dep in graph[node]:
            visit(dep)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)

    raw_state = context.get("issue_state")
    if not isinstance(raw_state, Mapping):
        raise DynamicFrontierError("ISSUE_STATE_REQUIRED")
    urgency: dict[str, float] = {}
    for issue_id in candidate_issue_ids:
        item = raw_state.get(issue_id)
        if not isinstance(item, Mapping):
            raise DynamicFrontierError(f"ISSUE_STATE_ENTRY_REQUIRED:{issue_id}")
        try:
            value = float(item.get("urgency"))
        except (TypeError, ValueError):
            raise DynamicFrontierError(f"URGENCY_REQUIRED:{issue_id}") from None
        if not 0.0 <= value <= 1.0:
            raise DynamicFrontierError(f"URGENCY_OUT_OF_RANGE:{issue_id}")
        urgency[issue_id] = value
    return graph, urgency


def _criticality(
    graph: Mapping[str, tuple[str, ...]],
    *,
    completed_issue_ids: Iterable[str] = (),
) -> dict[str, int]:
    """Count unresolved downstream issues influenced by each issue.

    Completed/accepted-limitation descendants cannot benefit from executing an
    upstream issue now, so they must not inflate current dependency criticality.
    Traversal still crosses them so unresolved descendants beyond a completed
    node remain visible if the current authoritative graph contains such a path.
    """
    completed = {str(x) for x in completed_issue_ids}
    successors = {node: set() for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            successors[dep].add(node)

    memo: dict[str, set[str]] = {}

    def descendants(node: str) -> set[str]:
        if node in memo:
            return memo[node]
        out: set[str] = set()
        for nxt in successors[node]:
            out.add(nxt)
            out.update(descendants(nxt))
        memo[node] = out
        return out

    return {
        node: len(descendants(node) - completed)
        for node in graph
    }


def choose_dynamic_issue(
    *,
    plan: Mapping[str, Any],
    candidate_issues: Iterable[Mapping[str, Any]],
    completed_issue_ids: Iterable[str],
    static_issue_id: str,
    context: Mapping[str, Any],
    state_authority: DynamicStateAuthority | None,
) -> dict[str, Any]:
    """Conservatively override static V3 ordering using authoritative current state."""
    candidates = [dict(issue) for issue in candidate_issues]
    candidate_ids = {str(issue.get("issue_id") or "") for issue in candidates}
    if not candidate_ids or "" in candidate_ids:
        raise DynamicFrontierError("DYNAMIC_CANDIDATES_REQUIRED")
    if static_issue_id not in candidate_ids:
        raise DynamicFrontierError("STATIC_SELECTION_NOT_IN_CANDIDATES")

    graph, urgency = _context(
        plan,
        context,
        candidate_ids,
        state_authority=state_authority,
    )
    completed = {str(x) for x in completed_issue_ids}
    criticality = _criticality(graph, completed_issue_ids=completed)
    by_id = {str(issue["issue_id"]): issue for issue in candidates}
    ready = [
        issue_id
        for issue_id in candidate_ids
        if set(graph.get(issue_id, ())) <= completed
    ]
    if not ready:
        return {
            "status": "BLOCKED",
            "issue_id": None,
            "reason": "NO_DEPENDENCY_READY_ISSUE",
            "blocked_dependencies": {
                issue_id: sorted(set(graph.get(issue_id, ())) - completed)
                for issue_id in sorted(candidate_ids)
            },
        }

    def vector(issue_id: str) -> tuple[int, int, float]:
        issue = by_id[issue_id]
        return (
            1 if bool(issue.get("blocker")) else 0,
            criticality.get(issue_id, 0),
            urgency[issue_id],
        )

    def dominates(a: str, b: str) -> bool:
        av = vector(a)
        bv = vector(b)
        return all(x >= y for x, y in zip(av, bv)) and any(
            x > y for x, y in zip(av, bv)
        )

    def deterministic_best(ids: Iterable[str]) -> str:
        ids = list(ids)
        max_criticality = max((criticality.get(i, 0) for i in ready), default=0)
        denominator = max(1, max_criticality)
        return max(
            ids,
            key=lambda issue_id: (
                vector(issue_id)[0],
                criticality.get(issue_id, 0) / denominator + urgency[issue_id],
                criticality.get(issue_id, 0),
                urgency[issue_id],
                -_priority(by_id[issue_id]),
                issue_id,
            ),
        )

    if static_issue_id not in ready:
        selected = deterministic_best(ready)
        reason = "STATIC_SELECTION_DEPENDENCY_INELIGIBLE"
    else:
        dominators = [
            issue_id for issue_id in ready
            if issue_id != static_issue_id and dominates(issue_id, static_issue_id)
        ]
        if not dominators:
            selected = static_issue_id
            reason = "V3_STATIC_SELECTION_PRESERVED"
        else:
            selected = deterministic_best(dominators)
            reason = "PARETO_DOMINANT_DYNAMIC_OVERRIDE"

    return {
        "status": "SELECTED",
        "issue_id": selected,
        "reason": reason,
        "static_issue_id": static_issue_id,
        "state_revision": context["state_revision"],
        "plan_digest": context["plan_digest"],
        "state_digest": context["state_digest"],
        "observation_ref": context["observation_ref"],
        "selected_vector": {
            "blocker": vector(selected)[0],
            "dependency_criticality": vector(selected)[1],
            "urgency": vector(selected)[2],
        },
    }


__all__ = [
    "DynamicFrontierError",
    "DynamicStateAuthority",
    "PROTOCOL",
    "choose_dynamic_issue",
    "plan_digest",
    "state_digest",
    "state_subject",
]
