#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any

from s2b2a_composition_core import compose as compose_known


def key_atom(atom: dict[str, Any]) -> str:
    return json.dumps(atom, sort_keys=True, separators=(",", ":"))


def canonical_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposal_kind": proposal["proposal_kind"],
        "action_class": proposal["action_class"],
        "parameters": list(proposal["parameters"]),
        "preconditions": sorted(proposal["preconditions"], key=key_atom),
        "effects": sorted(proposal["effects"], key=key_atom),
        "bindings": {k: proposal["bindings"][k] for k in sorted(proposal["bindings"])},
    }


def proposal_key(proposal: dict[str, Any]) -> str:
    return json.dumps(canonical_proposal(proposal), sort_keys=True, separators=(",", ":"))


def instantiate(atom: dict[str, Any], bindings: dict[str, str]) -> dict[str, Any]:
    return {"pred": atom["pred"], "args": [bindings[a] for a in atom["args"]]}


def template_valid(atom: Any, vocab: dict[str, int], params: set[str]) -> bool:
    return (
        isinstance(atom, dict)
        and set(atom) == {"pred", "args"}
        and atom["pred"] in vocab
        and isinstance(atom["args"], list)
        and len(atom["args"]) == vocab[atom["pred"]]
        and all(isinstance(a, str) and a in params for a in atom["args"])
    )


def validate_fixture_design(fixture: dict) -> dict[str, Any]:
    visible = fixture["visible"]
    known = compose_known(visible)
    return {
        "known_primitive_candidate_count": len(known),
        "known_primitive_absence_gate": len(known) == 0,
        "hidden_field_gate": not ({"oracle", "family", "category"} & set(visible)),
    }


def validate_proposal(fixture: dict, proposal: Any) -> dict[str, Any]:
    visible = fixture["visible"]
    design = validate_fixture_design(fixture)
    reasons: list[str] = []
    if not design["known_primitive_absence_gate"]:
        reasons.append("KNOWN_PRIMITIVE_CAN_SATISFY_TARGET")
    if not design["hidden_field_gate"]:
        reasons.append("HIDDEN_FIELD_LEAK")
    if not isinstance(proposal, dict):
        return {"valid": False, "reasons": reasons + ["PROPOSAL_NOT_OBJECT"], "design": design}

    fields = {"proposal_kind", "action_class", "parameters", "preconditions", "effects", "bindings"}
    if set(proposal) != fields:
        reasons.append("OUTPUT_FIELDS_MISMATCH")
    if proposal.get("proposal_kind") != "NEW_CLASS" or proposal.get("action_class") != "PROPOSED_NEW_CLASS":
        reasons.append("NOVEL_CLASS_MARKER_INVALID")

    params = visible["parameters"]
    pset = set(params)
    if proposal.get("parameters") != params:
        reasons.append("PARAMETERS_MISMATCH")
    bindings = proposal.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != pset:
        reasons.append("BINDINGS_KEYS_MISMATCH")
    elif any(bindings[p] not in visible["domains"][p] for p in params):
        reasons.append("BINDING_OUTSIDE_DOMAIN")

    vocab = visible["predicate_vocab"]
    pre = proposal.get("preconditions")
    eff = proposal.get("effects")
    if not isinstance(pre, list) or not all(template_valid(a, vocab, pset) for a in pre):
        reasons.append("INVALID_PRECONDITION_TEMPLATE")
    if not isinstance(eff, list) or not all(template_valid(a, vocab, pset) for a in eff):
        reasons.append("INVALID_EFFECT_TEMPLATE")
    if reasons:
        return {"valid": False, "reasons": reasons, "design": design}

    state = {key_atom(a) for a in visible["state"]}
    req_pre = {key_atom(a) for a in visible["relation"]["required_preconditions"]}
    req_eff = {key_atom(a) for a in visible["relation"]["required_effects"]}
    forbidden = {key_atom(a) for a in visible["relation"]["forbidden_effects"]}
    inst_pre = {key_atom(instantiate(a, bindings)) for a in pre}
    inst_eff = {key_atom(instantiate(a, bindings)) for a in eff}

    if not req_pre.issubset(inst_pre):
        reasons.append("REQUIRED_PRECONDITION_MISSING")
    if not inst_pre.issubset(state):
        reasons.append("PRECONDITION_NOT_SATISFIED")
    if not req_eff.issubset(inst_eff):
        reasons.append("REQUIRED_EFFECT_MISSING")
    if inst_eff & forbidden:
        reasons.append("FORBIDDEN_EFFECT_PRESENT")

    for primitive in visible["primitive_actions"]:
        same = (
            primitive.get("parameters", []) == proposal["parameters"]
            and {key_atom(a) for a in primitive.get("preconditions", [])} == {key_atom(a) for a in pre}
            and {key_atom(a) for a in primitive.get("effects", [])} == {key_atom(a) for a in eff}
        )
        if same:
            reasons.append("SCHEMA_NOT_NOVEL")
            break

    exact = False
    if not reasons:
        exact = proposal_key(proposal) == proposal_key(fixture["oracle"]["canonical_proposal"])
    return {
        "valid": not reasons,
        "exact_canonical": exact,
        "reasons": reasons,
        "design": design,
        "instantiated_preconditions": sorted(inst_pre),
        "instantiated_effects": sorted(inst_eff),
    }
