#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
from typing import Any

PROTOCOL = "S2B2_B2_TYPED_ENUMERATIVE_INDUCER_V1"
MAX_PRECONDITIONS = 3
MAX_ADD_EFFECTS = 3
DELETE_EFFECT_COUNT = 1


def _canon_atom(atom: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    return atom["pred"], tuple(atom["args"])


def _atom(pred: str, args: tuple[str, ...] | list[str]) -> dict[str, Any]:
    return {"pred": pred, "args": list(args)}


def _state_set(state: list[dict[str, Any]]) -> set[tuple[str, tuple[str, ...]]]:
    return {_canon_atom(a) for a in state}


def _schema_key(schema: dict[str, Any]) -> str:
    def aset(xs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [_atom(p, a) for p, a in sorted({_canon_atom(x) for x in xs})]
    return json.dumps({
        "proposal_kind": "INDUCED_OPERATOR",
        "parameters": list(schema["parameters"]),
        "preconditions": aset(schema["preconditions"]),
        "add_effects": aset(schema["add_effects"]),
        "delete_effects": aset(schema["delete_effects"]),
    }, sort_keys=True, separators=(",", ":"))


def canonical_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return json.loads(_schema_key(schema))


def type_compatible_atoms(visible: dict[str, Any]) -> list[dict[str, Any]]:
    parameters = visible["parameters"]
    ptype = {p["name"]: p["type"] for p in parameters}
    vars_by_type: dict[str, list[str]] = {}
    for name, typ in ptype.items():
        vars_by_type.setdefault(typ, []).append(name)
    out: list[dict[str, Any]] = []
    for pred, arg_types in sorted(visible["predicate_vocabulary"].items()):
        domains: list[list[str]] = []
        for typ in arg_types:
            vals = sorted(vars_by_type.get(typ, []))
            if not vals:
                domains = []
                break
            domains.append(vals)
        if not domains and arg_types:
            continue
        for args in itertools.product(*domains) if domains else [()]:
            out.append(_atom(pred, args))
    return out


def _inverse_binding(binding: dict[str, str]) -> dict[str, str] | None:
    inv: dict[str, str] = {}
    for var, value in binding.items():
        if value in inv:
            return None
        inv[value] = var
    return inv


def _lift(atom: tuple[str, tuple[str, ...]], binding: dict[str, str]) -> tuple[str, tuple[str, ...]] | None:
    inv = _inverse_binding(binding)
    if inv is None:
        return None
    pred, args = atom
    if any(a not in inv for a in args):
        return None
    return pred, tuple(inv[a] for a in args)


def _instantiate(atom: tuple[str, tuple[str, ...]], binding: dict[str, str]) -> tuple[str, tuple[str, ...]]:
    pred, args = atom
    return pred, tuple(binding[a] for a in args)


def _positive_delta(example: dict[str, Any]) -> tuple[set[tuple[str, tuple[str, ...]]], set[tuple[str, tuple[str, ...]]]]:
    before = _state_set(example["before"])
    after = _state_set(example["after"])
    add_concrete = after - before
    delete_concrete = before - after
    add: set[tuple[str, tuple[str, ...]]] = set()
    delete: set[tuple[str, tuple[str, ...]]] = set()
    for atom in add_concrete:
        lifted = _lift(atom, example["binding"])
        if lifted is None:
            raise ValueError("UNLIFTABLE_POSITIVE_ADD")
        add.add(lifted)
    for atom in delete_concrete:
        lifted = _lift(atom, example["binding"])
        if lifted is None:
            raise ValueError("UNLIFTABLE_POSITIVE_DELETE")
        delete.add(lifted)
    return add, delete


def _consistent(schema: dict[str, Any], positives: list[dict[str, Any]], negatives: list[dict[str, Any]]) -> bool:
    pre = {_canon_atom(a) for a in schema["preconditions"]}
    add = {_canon_atom(a) for a in schema["add_effects"]}
    delete = {_canon_atom(a) for a in schema["delete_effects"]}
    for ex in positives:
        before = _state_set(ex["before"])
        instantiated_pre = {_instantiate(a, ex["binding"]) for a in pre}
        if not instantiated_pre.issubset(before):
            return False
        after_calc = (before - {_instantiate(a, ex["binding"]) for a in delete}) | {_instantiate(a, ex["binding"]) for a in add}
        if after_calc != _state_set(ex["after"]):
            return False
    for ex in negatives:
        before = _state_set(ex["before"])
        if _state_set(ex["after"]) != before:
            return False
        instantiated_pre = {_instantiate(a, ex["binding"]) for a in pre}
        if instantiated_pre.issubset(before):
            return False
    return True


def _all_parameters_used(schema: dict[str, Any]) -> bool:
    declared = {p for p in schema["parameters"]}
    used: set[str] = set()
    for field in ("preconditions", "add_effects", "delete_effects"):
        for atom in schema[field]:
            used.update(a for a in atom["args"] if isinstance(a, str) and a.startswith("$"))
    return declared.issubset(used)


def induce(visible: dict[str, Any]) -> dict[str, Any]:
    parameters = [p["name"] for p in visible["parameters"]]
    positives = visible["positive_examples"]
    negatives = visible["negative_examples"]
    if len(positives) < 2 or not negatives:
        return {"status": "INVALID_EXAMPLE_CONTRACT", "consistent_count": 0}

    deltas = [_positive_delta(ex) for ex in positives]
    add_sets = {frozenset(a) for a, _ in deltas}
    del_sets = {frozenset(d) for _, d in deltas}
    if len(add_sets) != 1 or len(del_sets) != 1:
        return {"status": "INCONSISTENT_POSITIVE_DELTAS", "consistent_count": 0}
    add = set(next(iter(add_sets)))
    delete = set(next(iter(del_sets)))
    if not (1 <= len(add) <= MAX_ADD_EFFECTS) or len(delete) != DELETE_EFFECT_COUNT or add & delete:
        return {"status": "OUTSIDE_FROZEN_EFFECT_GRAMMAR", "consistent_count": 0}

    universe = [_canon_atom(a) for a in type_compatible_atoms(visible)]
    candidates: list[dict[str, Any]] = []
    for n in range(1, MAX_PRECONDITIONS + 1):
        for combo in itertools.combinations(universe, n):
            schema = {
                "proposal_kind": "INDUCED_OPERATOR",
                "parameters": parameters,
                "preconditions": [_atom(p, a) for p, a in combo],
                "add_effects": [_atom(p, a) for p, a in add],
                "delete_effects": [_atom(p, a) for p, a in delete],
            }
            if not _all_parameters_used(schema):
                continue
            if _consistent(schema, positives, negatives):
                candidates.append(canonical_schema(schema))
    unique = {_schema_key(c): c for c in candidates}
    rows = [unique[k] for k in sorted(unique)]
    if len(rows) == 1:
        return {"status": "UNIQUE", "consistent_count": 1, "schema": rows[0]}
    if len(rows) == 0:
        return {"status": "NONE", "consistent_count": 0}
    return {"status": "AMBIGUOUS", "consistent_count": len(rows), "schemas": rows}


def apply_schema(schema: dict[str, Any], before: list[dict[str, Any]], binding: dict[str, str]) -> dict[str, Any]:
    b = _state_set(before)
    pre = {_instantiate(_canon_atom(a), binding) for a in schema["preconditions"]}
    if not pre.issubset(b):
        return {"applicable": False, "after": [_atom(p, a) for p, a in sorted(b)]}
    delete = {_instantiate(_canon_atom(a), binding) for a in schema["delete_effects"]}
    add = {_instantiate(_canon_atom(a), binding) for a in schema["add_effects"]}
    after = (b - delete) | add
    return {"applicable": True, "after": [_atom(p, a) for p, a in sorted(after)]}
