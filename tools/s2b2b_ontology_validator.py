#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any

from s2b2a_composition_core import compose


def _atom_key(atom: dict[str, Any]) -> str:
    return json.dumps(atom, sort_keys=True, separators=(",", ":"))


def _schema_key(parameters: list[str], preconditions: list[dict], effects: list[dict]) -> str:
    return json.dumps({
        "parameters": sorted(parameters),
        "preconditions": sorted((_atom_key(a) for a in preconditions)),
        "effects": sorted((_atom_key(a) for a in effects)),
    }, sort_keys=True, separators=(",", ":"))


def _valid_template_atom(atom: Any, predicate_vocab: dict[str, int], parameters: set[str]) -> bool:
    if not isinstance(atom, dict) or set(atom) != {"pred", "args"}:
        return False
    pred = atom.get("pred")
    args = atom.get("args")
    if pred not in predicate_vocab or not isinstance(args, list) or len(args) != predicate_vocab[pred]:
        return False
    return all(isinstance(a, str) and a in parameters for a in args)


def _instantiate(atom: dict, bindings: dict[str, str]) -> dict:
    return {"pred": atom["pred"], "args": [bindings[a] for a in atom["args"]]}


def validate_fixture_design(fixture: dict) -> dict:
    visible = fixture["visible"]
    known = compose(visible)
    return {
        "known_primitive_candidate_count": len(known),
        "known_primitive_gate_pass": len(known) == 0,
        "oracle_hidden_from_visible": "oracle" not in visible and "family" not in visible and "category" not in visible,
    }


def validate_proposal(fixture: dict, proposal: Any) -> dict:
    visible = fixture["visible"]
    design = validate_fixture_design(fixture)
    reasons: list[str] = []

    if not design["known_primitive_gate_pass"]:
        reasons.append("KNOWN_PRIMITIVE_CAN_SATISFY_TARGET")

    if not isinstance(proposal, dict):
        return {"valid": False, "reasons": reasons + ["PROPOSAL_NOT_OBJECT"], "design": design}

    required_fields = {"proposal_kind", "action_class", "parameters", "preconditions", "effects", "bindings"}
    if set(proposal) != required_fields:
        reasons.append("OUTPUT_FIELDS_MISMATCH")

    if proposal.get("proposal_kind") != "NEW_CLASS":
        reasons.append("NOT_NEW_CLASS")
    if proposal.get("action_class") != "PROPOSED_NEW_CLASS":
        reasons.append("ACTION_CLASS_MARKER_INVALID")

    parameters = proposal.get("parameters")
    preconditions = proposal.get("preconditions")
    effects = proposal.get("effects")
    bindings = proposal.get("bindings")
    expected_parameters = list(visible["parameters"])
    parameter_set = set(expected_parameters)

    if not isinstance(parameters, list) or parameters != expected_parameters:
        reasons.append("PARAMETERS_MISMATCH")
    if not isinstance(bindings, dict) or set(bindings) != parameter_set:
        reasons.append("BINDINGS_KEYS_MISMATCH")
    elif any(bindings[p] not in visible["domains"][p] for p in expected_parameters):
        reasons.append("BINDING_OUTSIDE_DOMAIN")

    predicate_vocab = visible["predicate_vocab"]
    if not isinstance(preconditions, list) or not all(_valid_template_atom(a, predicate_vocab, parameter_set) for a in preconditions):
        reasons.append("INVALID_PRECONDITION_TEMPLATE")
    if not isinstance(effects, list) or not all(_valid_template_atom(a, predicate_vocab, parameter_set) for a in effects):
        reasons.append("INVALID_EFFECT_TEMPLATE")

    if reasons:
        return {"valid": False, "reasons": reasons, "design": design}

    instantiated_pre = {_atom_key(_instantiate(a, bindings)) for a in preconditions}
    instantiated_eff = {_atom_key(_instantiate(a, bindings)) for a in effects}
    state = {_atom_key(a) for a in visible["state"]}
    target = {_atom_key(a) for a in visible["relation"]["required_effects"]}
    forbidden = {_atom_key(a) for a in visible["relation"]["forbidden_effects"]}

    if not instantiated_pre.issubset(state):
        reasons.append("PRECONDITION_NOT_SATISFIED")
    if not target.issubset(instantiated_eff):
        reasons.append("TARGET_EFFECT_MISSING")
    if instantiated_eff & forbidden:
        reasons.append("FORBIDDEN_EFFECT_PRESENT")

    proposal_schema = _schema_key(parameters, preconditions, effects)
    existing_schema_keys = {
        _schema_key(p.get("parameters", []), p.get("preconditions", []), p.get("effects", []))
        for p in visible["primitive_actions"]
    }
    if proposal_schema in existing_schema_keys:
        reasons.append("SCHEMA_NOT_NOVEL")

    return {
        "valid": not reasons,
        "reasons": reasons,
        "design": design,
        "instantiated_preconditions": sorted(instantiated_pre),
        "instantiated_effects": sorted(instantiated_eff),
        "target_effects": sorted(target),
        "forbidden_effects": sorted(forbidden),
    }


def outcome_for(fixture: dict, proposal: Any | None) -> str:
    design = validate_fixture_design(fixture)
    if not design["known_primitive_gate_pass"]:
        return "AUTHORIZED_KNOWN_COMPOSITION"
    if proposal is None:
        return "FAIL_CLOSED_NO_AUTHORIZED_CLASS"
    validation = validate_proposal(fixture, proposal)
    return "NOVEL_CLASS_PROPOSED_AND_ORACLE_VALID" if validation["valid"] else "NOVEL_CLASS_INVALID"
