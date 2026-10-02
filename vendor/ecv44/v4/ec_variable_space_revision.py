from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Iterable, Mapping


PROTOCOL = "EC_V4_VARIABLE_SPACE_REVISION_V1"
FLEXIBILITY = {"IMMUTABLE", "BOUNDED", "REVISABLE", "REPLACEABLE", "EMERGENT"}
TARGET_OPS = {"REPLACE", "SPLIT", "MERGE", "REMOVE"}
ALLOWED_BY_FLEXIBILITY = {
    "IMMUTABLE": frozenset(),
    "BOUNDED": frozenset({"REPLACE"}),
    "REVISABLE": frozenset({"REPLACE"}),
    "REPLACEABLE": frozenset({"REPLACE", "SPLIT", "MERGE", "REMOVE"}),
    "EMERGENT": frozenset({"REPLACE", "SPLIT", "MERGE", "REMOVE"}),
}


class VariableSpaceRevisionError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def variable_space_digest(space: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(space).encode("utf-8")).hexdigest()


def _variables(space: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw = space.get("variables")
    if not isinstance(raw, Mapping):
        raise VariableSpaceRevisionError("VARIABLES_REQUIRED")
    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(value, Mapping):
            raise VariableSpaceRevisionError(f"VARIABLE_INVALID:{key}")
        item = dict(value)
        flex = str(item.get("flexibility") or "").upper()
        if flex not in FLEXIBILITY:
            raise VariableSpaceRevisionError(f"FLEXIBILITY_INVALID:{key}:{flex}")
        out[str(key)] = item
    return out


def _edges(space: Mapping[str, Any], valid_ids: set[str]) -> set[tuple[str, str]]:
    raw = space.get("edges") or ()
    if isinstance(raw, (str, bytes, Mapping)) or not isinstance(raw, Iterable):
        raise VariableSpaceRevisionError("EDGES_INVALID")
    edges: set[tuple[str, str]] = set()
    for edge in raw:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise VariableSpaceRevisionError("EDGE_INVALID")
        dependent, prerequisite = str(edge[0]), str(edge[1])
        if dependent not in valid_ids or prerequisite not in valid_ids:
            raise VariableSpaceRevisionError(f"EDGE_TARGET_UNKNOWN:{dependent}:{prerequisite}")
        if dependent == prerequisite:
            raise VariableSpaceRevisionError(f"SELF_EDGE_FORBIDDEN:{dependent}")
        edges.add((dependent, prerequisite))
    _assert_acyclic(valid_ids, edges)
    return edges


def _assert_acyclic(nodes: set[str], edges: set[tuple[str, str]]) -> None:
    deps = {node: set() for node in nodes}
    for dependent, prerequisite in edges:
        deps[dependent].add(prerequisite)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise VariableSpaceRevisionError("VARIABLE_GRAPH_CYCLE")
        visiting.add(node)
        for dep in deps[node]:
            visit(dep)
        visiting.remove(node)
        visited.add(node)

    for node in nodes:
        visit(node)


def _require_authority(operation: Mapping[str, Any]) -> str:
    ref = str(operation.get("evidence_ref") or "").strip()
    if not ref:
        raise VariableSpaceRevisionError("REVISION_EVIDENCE_REF_REQUIRED")
    return ref


def _check_target_permission(variables: Mapping[str, Mapping[str, Any]], variable_id: str, op: str) -> None:
    if variable_id not in variables:
        raise VariableSpaceRevisionError(f"REVISION_TARGET_UNKNOWN:{variable_id}")
    flex = str(variables[variable_id].get("flexibility") or "").upper()
    if op not in ALLOWED_BY_FLEXIBILITY[flex]:
        raise VariableSpaceRevisionError(f"REVISION_NOT_ALLOWED:{op}:{variable_id}:{flex}")


def apply_variable_space_revision(
    space: Mapping[str, Any],
    operations: Iterable[Mapping[str, Any]],
    *,
    expected_revision_id: int,
    authority_ref: str,
) -> dict[str, Any]:
    """Apply evidence-bound representation changes before EC hard binding.

    The operation set is intentionally explicit. Closure/frontier authority is not
    weakened: the output receives a new revision id and digest, and every mutation
    requires evidence provenance.
    """
    if not str(authority_ref or "").strip():
        raise VariableSpaceRevisionError("REVISION_AUTHORITY_REQUIRED")
    revision = space.get("revision_id")
    if not isinstance(revision, int) or revision < 0:
        raise VariableSpaceRevisionError("VARIABLE_SPACE_REVISION_ID_REQUIRED")
    if revision != expected_revision_id:
        raise VariableSpaceRevisionError("VARIABLE_SPACE_REVISION_STALE")

    variables = _variables(space)
    edges = _edges(space, set(variables))
    trace: list[dict[str, Any]] = []

    for raw in operations:
        if not isinstance(raw, Mapping):
            raise VariableSpaceRevisionError("REVISION_OPERATION_INVALID")
        op = str(raw.get("op") or "").upper()
        evidence_ref = _require_authority(raw)

        if op == "ADD":
            variable_id = str(raw.get("id") or "").strip()
            value = raw.get("value")
            if not variable_id or not isinstance(value, Mapping):
                raise VariableSpaceRevisionError("ADD_ARGUMENTS_INVALID")
            if variable_id in variables:
                raise VariableSpaceRevisionError(f"ADD_TARGET_EXISTS:{variable_id}")
            item = dict(value)
            flex = str(item.get("flexibility") or "").upper()
            if flex not in FLEXIBILITY:
                raise VariableSpaceRevisionError(f"FLEXIBILITY_INVALID:{variable_id}:{flex}")
            variables[variable_id] = item

        elif op == "REPLACE":
            variable_id = str(raw.get("id") or "").strip()
            value = raw.get("value")
            _check_target_permission(variables, variable_id, op)
            if not isinstance(value, Mapping):
                raise VariableSpaceRevisionError("REPLACE_VALUE_INVALID")
            item = dict(value)
            flex = str(item.get("flexibility") or variables[variable_id].get("flexibility") or "").upper()
            if flex not in FLEXIBILITY:
                raise VariableSpaceRevisionError(f"FLEXIBILITY_INVALID:{variable_id}:{flex}")
            item["flexibility"] = flex
            variables[variable_id] = item

        elif op == "SPLIT":
            variable_id = str(raw.get("id") or "").strip()
            _check_target_permission(variables, variable_id, op)
            into = raw.get("into")
            if not isinstance(into, (list, tuple)) or len(into) < 2:
                raise VariableSpaceRevisionError("SPLIT_TARGETS_REQUIRED")
            incident = {(a, b) for a, b in edges if a == variable_id or b == variable_id}
            edges -= incident
            variables.pop(variable_id)
            for child in into:
                if not isinstance(child, Mapping):
                    raise VariableSpaceRevisionError("SPLIT_CHILD_INVALID")
                child_id = str(child.get("id") or "").strip()
                value = child.get("value")
                if not child_id or child_id in variables or not isinstance(value, Mapping):
                    raise VariableSpaceRevisionError(f"SPLIT_CHILD_INVALID:{child_id}")
                item = dict(value)
                flex = str(item.get("flexibility") or "").upper()
                if flex not in FLEXIBILITY:
                    raise VariableSpaceRevisionError(f"FLEXIBILITY_INVALID:{child_id}:{flex}")
                variables[child_id] = item
            for edge in raw.get("edges") or ():
                if not isinstance(edge, (list, tuple)) or len(edge) != 2:
                    raise VariableSpaceRevisionError("SPLIT_EDGE_INVALID")
                edges.add((str(edge[0]), str(edge[1])))

        elif op == "MERGE":
            ids = [str(x) for x in raw.get("ids") or ()]
            merged_id = str(raw.get("id") or "").strip()
            value = raw.get("value")
            if len(set(ids)) < 2 or not merged_id or not isinstance(value, Mapping):
                raise VariableSpaceRevisionError("MERGE_ARGUMENTS_INVALID")
            for variable_id in ids:
                _check_target_permission(variables, variable_id, op)
            incident = {(a, b) for a, b in edges if a in ids or b in ids}
            edges -= incident
            for variable_id in ids:
                variables.pop(variable_id)
            item = dict(value)
            flex = str(item.get("flexibility") or "").upper()
            if flex not in FLEXIBILITY:
                raise VariableSpaceRevisionError(f"FLEXIBILITY_INVALID:{merged_id}:{flex}")
            variables[merged_id] = item
            for dependent, prerequisite in incident:
                new_dependent = merged_id if dependent in ids else dependent
                new_prerequisite = merged_id if prerequisite in ids else prerequisite
                if new_dependent != new_prerequisite:
                    edges.add((new_dependent, new_prerequisite))

        elif op == "REMOVE":
            variable_id = str(raw.get("id") or "").strip()
            _check_target_permission(variables, variable_id, op)
            incident = {(a, b) for a, b in edges if a == variable_id or b == variable_id}
            if incident and raw.get("cascade_edges") is not True:
                raise VariableSpaceRevisionError(f"REMOVE_HAS_EDGES:{variable_id}")
            edges -= incident
            variables.pop(variable_id)

        else:
            raise VariableSpaceRevisionError(f"REVISION_OPERATION_UNKNOWN:{op}")

        valid_ids = set(variables)
        for dependent, prerequisite in edges:
            if dependent not in valid_ids or prerequisite not in valid_ids:
                raise VariableSpaceRevisionError(f"EDGE_TARGET_UNKNOWN:{dependent}:{prerequisite}")
        _assert_acyclic(valid_ids, edges)
        trace.append({"op": op, "evidence_ref": evidence_ref})

    output = {
        "protocol": PROTOCOL,
        "revision_id": revision + 1,
        "parent_revision_id": revision,
        "authority_ref": str(authority_ref),
        "variables": {key: variables[key] for key in sorted(variables)},
        "edges": [list(edge) for edge in sorted(edges)],
        "revision_trace": trace,
    }
    output["digest"] = variable_space_digest(output)
    return output


def validate_revision_request(
    space: Mapping[str, Any],
    request: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Dry-run a proposed revision; used by the Issue Definition Gate."""
    req = dict(request or {})
    operations = req.get("operations") or ()
    if not operations:
        return {"status": "PRESERVE", "required": False, "reason": "NO_REVISION_REQUEST"}
    try:
        revised = apply_variable_space_revision(
            space,
            operations,
            expected_revision_id=int(req.get("expected_revision_id")),
            authority_ref=str(req.get("authority_ref") or ""),
        )
    except (TypeError, ValueError, VariableSpaceRevisionError) as exc:
        return {"status": "INVALID", "required": True, "reason": str(exc)}
    return {
        "status": "REVISE",
        "required": True,
        "reason": "VALID_EVIDENCE_BOUND_VARIABLE_SPACE_REVISION",
        "next_revision_id": revised["revision_id"],
        "next_digest": revised["digest"],
        "operation_count": len(list(operations)),
    }


__all__ = [
    "PROTOCOL",
    "VariableSpaceRevisionError",
    "apply_variable_space_revision",
    "validate_revision_request",
    "variable_space_digest",
]
