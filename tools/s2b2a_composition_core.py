#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
from typing import Any

VAR_PREFIX = "$"


def _is_var(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(VAR_PREFIX)


def _subst(value: Any, binding: dict[str, str]) -> Any:
    if _is_var(value):
        return binding[value]
    if isinstance(value, list):
        return [_subst(v, binding) for v in value]
    if isinstance(value, dict):
        return {k: _subst(v, binding) for k, v in value.items()}
    return value


def _atom_key(atom: dict[str, Any]) -> str:
    return json.dumps(atom, sort_keys=True, separators=(",", ":"))


def _candidate_key(candidate: dict[str, Any]) -> str:
    return json.dumps(candidate, sort_keys=True, separators=(",", ":"))


def _instantiate_atoms(atoms: list[dict[str, Any]], binding: dict[str, str]) -> list[dict[str, Any]]:
    return [_subst(atom, binding) for atom in atoms]


def _binding_space(parameters: list[str], domains: dict[str, list[str]]) -> list[dict[str, str]]:
    if not parameters:
        return [{}]
    values = []
    for parameter in parameters:
        if parameter not in domains or not domains[parameter]:
            return []
        values.append(domains[parameter])
    return [dict(zip(parameters, combo)) for combo in itertools.product(*values)]


def compose(visible: dict[str, Any]) -> list[dict[str, Any]]:
    """Construct authorized candidate instances from a frozen symbolic vocabulary.

    Predictor-visible inputs only:
    - structured relation requirements/forbidden effects;
    - current symbolic state;
    - primitive action schemas;
    - parameter domains;
    - optional distractor existing_candidates (ignored by composition).

    No oracle/gold/category/family access and no operator-specific branching.
    """
    relation = visible["relation"]
    state_keys = {_atom_key(atom) for atom in visible.get("state", [])}
    required_keys = {_atom_key(atom) for atom in relation.get("required_effects", [])}
    forbidden_keys = {_atom_key(atom) for atom in relation.get("forbidden_effects", [])}
    domains = visible.get("domains", {})

    emitted: dict[str, dict[str, Any]] = {}
    for primitive in visible.get("primitive_actions", []):
        action_class = primitive["action_class"]
        parameters = primitive.get("parameters", [])
        for binding in _binding_space(parameters, domains):
            preconditions = _instantiate_atoms(primitive.get("preconditions", []), binding)
            if any(_atom_key(atom) not in state_keys for atom in preconditions):
                continue

            effects = _instantiate_atoms(primitive.get("effects", []), binding)
            effect_keys = {_atom_key(atom) for atom in effects}
            if required_keys and not (effect_keys & required_keys):
                continue
            if effect_keys & forbidden_keys:
                continue

            candidate = {
                "action_class": action_class,
                "bindings": {k: binding[k] for k in sorted(binding)},
            }
            emitted[_candidate_key(candidate)] = candidate

    return [emitted[k] for k in sorted(emitted)]


def canonical_candidate_set(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dedup = {_candidate_key(c): c for c in candidates}
    return [dedup[k] for k in sorted(dedup)]
