#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
from typing import Any


def _key(atom: dict[str, Any]) -> str:
    return json.dumps(atom, sort_keys=True, separators=(",", ":"))


def _instantiate(atom: dict[str, Any], binding: dict[str, str]) -> dict[str, Any]:
    return {"pred": atom["pred"], "args": [binding.get(a, a) for a in atom["args"]]}


def _templify(atom: dict[str, Any], binding: dict[str, str]) -> dict[str, Any] | None:
    inverse: dict[str, str] = {}
    for param, value in binding.items():
        if value in inverse and inverse[value] != param:
            return None
        inverse[value] = param
    args: list[str] = []
    for value in atom["args"]:
        if value not in inverse:
            return None
        args.append(inverse[value])
    return {"pred": atom["pred"], "args": args}


def synthesize(visible: dict[str, Any]) -> list[dict[str, Any]]:
    """Mechanically synthesize novel schema proposals from explicit structured requirements.

    This is deliberately generic and contains no fixture/family/operator-specific rules.
    It is authorized to emit a new schema marker, unlike the closed-world Stage-A composer.
    """
    parameters = list(visible["parameters"])
    domains = visible["domains"]
    relation = visible["relation"]
    required_pre = list(relation.get("required_preconditions", []))
    required_eff = list(relation.get("required_effects", []))
    forbidden = {_key(a) for a in relation.get("forbidden_effects", [])}
    state = {_key(a) for a in visible.get("state", [])}

    if any(p not in domains or not domains[p] for p in parameters):
        return []

    proposals: dict[str, dict[str, Any]] = {}
    for values in itertools.product(*(domains[p] for p in parameters)):
        binding = dict(zip(parameters, values))
        if len(set(binding.values())) != len(binding.values()):
            continue

        if any(_key(a) not in state for a in required_pre):
            continue
        if any(_key(a) in forbidden for a in required_eff):
            continue

        pre_templates = [_templify(a, binding) for a in required_pre]
        eff_templates = [_templify(a, binding) for a in required_eff]
        if any(a is None for a in pre_templates + eff_templates):
            continue

        proposal = {
            "proposal_kind": "NEW_CLASS",
            "action_class": "PROPOSED_NEW_CLASS",
            "parameters": parameters,
            "preconditions": pre_templates,
            "effects": eff_templates,
            "bindings": binding,
        }
        k = json.dumps(proposal, sort_keys=True, separators=(",", ":"))
        proposals[k] = proposal

    return [proposals[k] for k in sorted(proposals)]
