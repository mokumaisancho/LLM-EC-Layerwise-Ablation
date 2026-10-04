#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any

PROTOCOL = "S2B2_B1_EXPLICIT_SCHEMA_SYNTH_CORE_V1"


def _canon(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _canon(v[k]) for k in sorted(v)}
    if isinstance(v, list):
        keyed = {json.dumps(_canon(x), sort_keys=True, separators=(",", ":")): _canon(x) for x in v}
        return [keyed[k] for k in sorted(keyed)]
    return v


def _collect_vars(v: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(v, str) and v.startswith("$"):
        out.add(v)
    elif isinstance(v, dict):
        for x in v.values():
            out |= _collect_vars(x)
    elif isinstance(v, list):
        for x in v:
            out |= _collect_vars(x)
    return out


def _validate_atoms(atoms: list[dict[str, Any]], allowed_predicates: dict[str, int], params: set[str]) -> None:
    for atom in atoms:
        if set(atom) != {"pred", "args"}:
            raise ValueError("INVALID_ATOM_SHAPE")
        pred = atom["pred"]
        args = atom["args"]
        if pred not in allowed_predicates or allowed_predicates[pred] != len(args):
            raise ValueError("PREDICATE_NOT_ALLOWED_OR_WRONG_ARITY")
        if not _collect_vars(atom).issubset(params):
            raise ValueError("UNKNOWN_PARAMETER")


def synthesize(visible: dict[str, Any]) -> dict[str, Any]:
    """Build the minimum authorized NEW_CLASS schema from explicit structured requirements.

    This is intentionally a B1 composition function, not ontology/operator induction.
    It consumes only predictor-visible requirements and never inspects Oracle/gold/family/category.
    """
    req = visible["schema_requirements"]
    params = list(req["parameters"])
    if len(params) != len(set(params)) or any(not isinstance(p, str) or not p.startswith("$") for p in params):
        raise ValueError("INVALID_PARAMETERS")
    pset = set(params)
    allowed = visible["predicate_vocabulary"]
    if not isinstance(allowed, dict) or not allowed:
        raise ValueError("INVALID_PREDICATE_VOCAB")

    pre = req.get("required_preconditions", [])
    effects = req.get("required_effects", [])
    forbidden = req.get("forbidden_effects", [])
    if not effects:
        raise ValueError("NO_REQUIRED_EFFECT")
    _validate_atoms(pre, allowed, pset)
    _validate_atoms(effects, allowed, pset)
    _validate_atoms(forbidden, allowed, pset)

    return _canon({
        "proposal_kind": "NEW_CLASS",
        "action_class": "PROPOSED_NEW_CLASS",
        "parameters": params,
        "preconditions": pre,
        "effects": effects,
        "constraints": {"forbidden_effects": forbidden},
    })


def semantic_signature(schema: dict[str, Any]) -> str:
    x = {
        "parameters": schema.get("parameters", []),
        "preconditions": schema.get("preconditions", []),
        "effects": schema.get("effects", []),
        "constraints": schema.get("constraints", {}),
    }
    return json.dumps(_canon(x), sort_keys=True, separators=(",", ":"))
