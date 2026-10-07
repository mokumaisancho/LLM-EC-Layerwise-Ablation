"""V2 fail-closed execution authority. V1 pinned assets remain unchanged."""
from __future__ import annotations
import copy
from typing import Any
from .runtime import (
    RuntimeContractError, canonical_json, discover_and_ground,
    validate_task_contract, validate_semantic_ir,
)
from . import solver

PROTOCOL = "SEMANTIC_RUNTIME_EXECUTION_V2"
SOLVER_PROTOCOL = "SEMANTIC_RUNTIME_SOLVER_V1"


def deny(reason: str) -> None:
    raise RuntimeContractError(reason)


def _atom(atom: Any) -> None:
    if not isinstance(atom, dict) or set(atom) != {"pred", "args"}:
        deny("SOLVER_ATOM_INVALID")
    if not isinstance(atom["pred"], str) or not atom["pred"]:
        deny("SOLVER_ATOM_PRED_INVALID")
    if not isinstance(atom["args"], list) or any(not isinstance(x, str) or not x for x in atom["args"]):
        deny("SOLVER_ATOM_ARGS_INVALID")


def _solver_contract(contract: Any) -> None:
    required = {"protocol", "assignment_example_id", "parameter_from_arguments",
                "static_binding", "before", "operator_schema"}
    optional = {"required_polarity", "required_modality"}
    if not isinstance(contract, dict) or not required.issubset(contract) or not set(contract).issubset(required | optional):
        deny("SOLVER_CONTRACT_KEYS_INVALID")
    if contract["protocol"] != SOLVER_PROTOCOL:
        deny("SOLVER_PROTOCOL_INVALID")
    if not isinstance(contract["assignment_example_id"], str) or not contract["assignment_example_id"]:
        deny("SOLVER_EXAMPLE_ID_INVALID")
    if contract.get("required_polarity") not in (None, "POS", "NEG"):
        deny("SOLVER_POLARITY_INVALID")
    if contract.get("required_modality") not in (None, "ASSERTED", "REQUIRED", "POSSIBLE"):
        deny("SOLVER_MODALITY_INVALID")
    bindings, static = contract["parameter_from_arguments"], contract["static_binding"]
    if not isinstance(bindings, dict) or not isinstance(static, dict):
        deny("SOLVER_BINDINGS_INVALID")
    if set(bindings) & set(static):
        deny("SOLVER_BINDING_COLLISION")
    if any(not isinstance(k, str) or not k.startswith("$") or type(v) is not int or v < 0 for k,v in bindings.items()):
        deny("SOLVER_ARGUMENT_BINDING_INVALID")
    if any(not isinstance(k, str) or not k.startswith("$") or not isinstance(v, str) or not v for k,v in static.items()):
        deny("SOLVER_STATIC_BINDING_INVALID")
    before = contract["before"]
    if not isinstance(before, list):
        deny("SOLVER_STATE_INVALID")
    for atom in before:
        _atom(atom)
    schema = contract["operator_schema"]
    if not isinstance(schema, dict) or not {"preconditions", "add_effects", "delete_effects"}.issubset(schema):
        deny("SOLVER_SCHEMA_INVALID")
    allowed = {"preconditions", "add_effects", "delete_effects", "parameters", "proposal_kind"}
    if not set(schema).issubset(allowed):
        deny("SOLVER_SCHEMA_EXTRA_FIELDS")
    for k in ("preconditions", "add_effects", "delete_effects"):
        if not isinstance(schema[k], list):
            deny("SOLVER_SCHEMA_ATOMS_INVALID")
        for atom in schema[k]:
            _atom(atom)
    available = set(bindings) | set(static)
    for atom in [*before, *schema["preconditions"], *schema["add_effects"], *schema["delete_effects"]]:
        if atom in before:
            continue
        for v in atom["args"]:
            if v not in available:
                deny("SOLVER_SCHEMA_UNBOUND_PARAMETER")
    if "parameters" in schema:
        if not isinstance(schema["parameters"], list) or not all(isinstance(x,str) for x in schema["parameters"]):
            deny("SOLVER_SCHEMA_PARAMETERS_INVALID")
        if not set(schema["parameters"]).issubset(available):
            deny("SOLVER_SCHEMA_UNBOUND_PARAMETER")


def execute_validated_ir(ir: dict[str, Any], task_contract: dict[str, Any],
                         solver_contract: dict[str, Any]) -> dict[str, Any]:
    """Execute only when caller IR exactly equals independently re-derived trusted IR."""
    visible = validate_task_contract(task_contract)
    validate_semantic_ir(ir, visible)
    expected = discover_and_ground(task_contract)
    if canonical_json(ir) != canonical_json(expected):
        deny("IR_PROVENANCE_MISMATCH")
    _solver_contract(solver_contract)
    eid = solver_contract["assignment_example_id"]
    abstained = {x["example_id"] for x in expected["abstentions"]}
    if eid in abstained:
        deny("SOLVER_ASSIGNMENT_AMBIGUOUS")
    matching = [x for x in expected["heldout_assignments"] if x["example_id"] == eid]
    if len(matching) != 1:
        deny("SOLVER_ASSIGNMENT_NOT_FOUND")
    assignment = matching[0]
    if solver_contract.get("required_polarity") is not None and solver_contract["required_polarity"] != assignment["polarity"]:
        deny("SOLVER_POLARITY_MISMATCH")
    if solver_contract.get("required_modality") is not None and solver_contract["required_modality"] != assignment["modality"]:
        deny("SOLVER_MODALITY_MISMATCH")
    args = assignment["arguments"]
    binding = dict(solver_contract["static_binding"])
    for key,index in solver_contract["parameter_from_arguments"].items():
        if index >= len(args):
            deny("SOLVER_ARGUMENT_INDEX_INVALID")
        binding[key] = args[index]
    result = solver.apply_schema(copy.deepcopy(solver_contract["operator_schema"]),
                                 copy.deepcopy(solver_contract["before"]), binding)
    return {"protocol": PROTOCOL, "assignment_example_id": eid,
            "slot_id": assignment["slot_id"], "binding": dict(sorted(binding.items())),
            "result": result}
