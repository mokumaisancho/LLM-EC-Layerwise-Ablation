from __future__ import annotations

import json
from typing import Any

from . import discovery
from . import solver

PROTOCOL = "SEMANTIC_RUNTIME_V1"
TASK_PROTOCOL = "SEMANTIC_RUNTIME_TASK_V1"
IR_PROTOCOL = "SEMANTIC_RUNTIME_IR_V1"
SOLVER_PROTOCOL = "SEMANTIC_RUNTIME_SOLVER_V1"
EVAL_IDS = ("Q03", "Q05", "Q06", "Q07")
FORBIDDEN_INPUT_KEYS = {"oracle", "family", "audit", "hidden", "gold", "answer"}


class RuntimeContractError(ValueError):
    pass


def _fail(code: str) -> None:
    raise RuntimeContractError(code)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reject_hidden_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            low = str(key).lower()
            if low in FORBIDDEN_INPUT_KEYS or low.startswith("oracle_") or low.startswith("hidden_"):
                _fail(f"FORBIDDEN_INPUT_KEY:{path}.{key}")
            _reject_hidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            _reject_hidden_keys(child, f"{path}[{i}]")


def _bits3(value: Any, code: str) -> None:
    if not isinstance(value, list) or len(value) != 3 or any(x not in (0, 1) for x in value):
        _fail(code)


def _registry(registry: Any, types: set[str]) -> None:
    if not isinstance(registry, dict) or not registry:
        _fail("ENTITY_REGISTRY_REQUIRED")
    for eid, item in registry.items():
        if not isinstance(eid, str) or not eid or not isinstance(item, dict):
            _fail("ENTITY_ENTRY_INVALID")
        if item.get("type") not in types:
            _fail("ENTITY_TYPE_UNKNOWN")
        forms = item.get("surface_forms")
        if not isinstance(forms, list) or not forms or any(not isinstance(x, str) or not x for x in forms):
            _fail("ENTITY_SURFACE_FORMS_INVALID")


def validate_task_contract(task_contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(task_contract, dict):
        _fail("TASK_OBJECT_REQUIRED")
    _reject_hidden_keys(task_contract)
    if "protocol" in task_contract and task_contract["protocol"] != TASK_PROTOCOL:
        _fail("TASK_PROTOCOL_INVALID")
    visible = task_contract.get("visible", task_contract)
    if not isinstance(visible, dict):
        _fail("VISIBLE_OBJECT_REQUIRED")
    types = visible.get("type_inventory")
    if not isinstance(types, list) or not types or len(types) != len(set(types)) or any(not isinstance(x, str) or not x for x in types):
        _fail("TYPE_INVENTORY_INVALID")
    type_set = set(types)

    public = visible.get("public_behavior_hypothesis")
    if public is not None:
        if not isinstance(public, dict):
            _fail("PUBLIC_HYPOTHESIS_MANIFEST_INVALID")
        if public.get("function_count") != 64:
            _fail("PUBLIC_HYPOTHESIS_FUNCTION_COUNT_INVALID")
        if public.get("coordinate_operations") != ["KEEP", "SET0", "SET1", "FLIP"]:
            _fail("PUBLIC_HYPOTHESIS_OPERATIONS_INVALID")
        if public.get("selected_target_functions_visible") is not False:
            _fail("PUBLIC_HYPOTHESIS_TARGET_VISIBILITY_FORBIDDEN")
        if public.get("semantic_slot_names_encoded") is not False:
            _fail("PUBLIC_HYPOTHESIS_SLOT_NAME_ENCODING_FORBIDDEN")

    bound = visible.get("slot_count_bound")
    if bound is not None:
        if (
            not isinstance(bound, dict)
            or not isinstance(bound.get("min"), int)
            or not isinstance(bound.get("max"), int)
            or not (bound["min"] <= 2 <= bound["max"])
        ):
            _fail("SLOT_COUNT_BOUND_EXCLUDES_RUNTIME_OUTPUT")

    train = visible.get("training_examples")
    held = visible.get("heldout_examples")
    probes = visible.get("evaluation_probes")
    if not isinstance(train, list) or len(train) != 4:
        _fail("EXACTLY_FOUR_TRAINING_EXAMPLES_REQUIRED")
    if not isinstance(held, list) or not held:
        _fail("HELDOUT_EXAMPLES_REQUIRED")
    if not isinstance(probes, list) or [p.get("probe_id") for p in probes if isinstance(p, dict)] != list(EVAL_IDS):
        _fail("EVALUATION_PROBES_Q03_Q05_Q06_Q07_REQUIRED")
    for row in probes:
        if not isinstance(row, dict):
            _fail("EVALUATION_PROBE_INVALID")
        _bits3(row.get("before"), "EVALUATION_PROBE_BITS_INVALID")

    seen: set[str] = set()
    for ex in train:
        if not isinstance(ex, dict):
            _fail("TRAINING_EXAMPLE_INVALID")
        eid = ex.get("example_id")
        if not isinstance(eid, str) or not eid or eid in seen:
            _fail("TRAINING_EXAMPLE_ID_INVALID")
        seen.add(eid)
        if not isinstance(ex.get("raw_text"), str) or not ex["raw_text"].strip():
            _fail("TRAINING_RAW_TEXT_REQUIRED")
        _registry(ex.get("entity_registry"), type_set)
        observations = ex.get("behavior_observations")
        if not isinstance(observations, list) or not observations:
            _fail("BEHAVIOR_OBSERVATIONS_REQUIRED")
        for obs in observations:
            if not isinstance(obs, dict):
                _fail("OBSERVATION_OBJECT_REQUIRED")
            _bits3(obs.get("before"), "OBSERVATION_BITS_INVALID")
            _bits3(obs.get("after"), "OBSERVATION_BITS_INVALID")

    held_seen: set[str] = set()
    for ex in held:
        if not isinstance(ex, dict):
            _fail("HELDOUT_EXAMPLE_INVALID")
        eid = ex.get("example_id")
        if not isinstance(eid, str) or not eid or eid in held_seen or eid in seen:
            _fail("HELDOUT_EXAMPLE_ID_INVALID")
        held_seen.add(eid)
        if not isinstance(ex.get("raw_text"), str) or not ex["raw_text"].strip():
            _fail("HELDOUT_RAW_TEXT_REQUIRED")
        _registry(ex.get("entity_registry"), type_set)
    return visible


def validate_semantic_ir(ir: dict[str, Any], visible: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(ir, dict) or ir.get("protocol") != IR_PROTOCOL:
        _fail("IR_PROTOCOL_INVALID")
    slots = ir.get("discovered_slots")
    assignments = ir.get("heldout_assignments")
    abstentions = ir.get("abstentions")
    if not isinstance(slots, list) or len(slots) != 2:
        _fail("EXACTLY_TWO_DISCOVERED_SLOTS_REQUIRED")

    train_ids = {str(x["example_id"]) for x in visible["training_examples"]}
    held_ids = {str(x["example_id"]) for x in visible["heldout_examples"]}
    slot_ids: set[str] = set()
    all_members: list[str] = []

    for slot in slots:
        if not isinstance(slot, dict):
            _fail("SLOT_INVALID")
        sid = slot.get("slot_id")
        if not isinstance(sid, str) or not sid or sid in slot_ids:
            _fail("SLOT_ID_INVALID_OR_DUPLICATED")
        slot_ids.add(sid)
        arg_types = slot.get("arg_types")
        if not isinstance(arg_types, list) or not arg_types or any(x not in visible["type_inventory"] for x in arg_types):
            _fail("SLOT_ARG_TYPES_INVALID")
        members = slot.get("training_members")
        if not isinstance(members, list) or len(members) != 2 or len(set(members)) != 2:
            _fail("SLOT_TRAINING_MEMBERS_INVALID")
        all_members.extend(str(x) for x in members)
        predictions = slot.get("evaluation_probe_predictions")
        if not isinstance(predictions, list) or [x.get("probe_id") for x in predictions if isinstance(x, dict)] != list(EVAL_IDS):
            _fail("SLOT_EVALUATION_PROBES_INVALID")
        for row in predictions:
            _bits3(row.get("predicted_after"), "SLOT_EVALUATION_BITS_INVALID")

    if set(all_members) != train_ids or len(all_members) != len(set(all_members)):
        _fail("TRAINING_PARTITION_NOT_EXACT")
    if not isinstance(assignments, list) or not isinstance(abstentions, list):
        _fail("HELDOUT_DECISIONS_REQUIRED")

    decided: list[str] = []
    for row in assignments:
        if not isinstance(row, dict):
            _fail("ASSIGNMENT_INVALID")
        eid, sid = row.get("example_id"), row.get("slot_id")
        if eid not in held_ids or sid not in slot_ids:
            _fail("ASSIGNMENT_REFERENCE_INVALID")
        if not isinstance(row.get("arguments"), list) or not row["arguments"]:
            _fail("ASSIGNMENT_ARGUMENTS_INVALID")
        if row.get("polarity") not in ("POS", "NEG") or row.get("modality") not in ("ASSERTED", "REQUIRED", "POSSIBLE"):
            _fail("ASSIGNMENT_QUALIFIER_INVALID")
        decided.append(str(eid))

    for row in abstentions:
        if not isinstance(row, dict) or row.get("status") != "AMBIGUOUS" or row.get("example_id") not in held_ids:
            _fail("ABSTENTION_INVALID")
        decided.append(str(row["example_id"]))

    if set(decided) != held_ids or len(decided) != len(set(decided)):
        _fail("HELDOUT_DECISION_COVERAGE_INVALID")
    return ir


def discover_and_ground(task_contract: dict[str, Any]) -> dict[str, Any]:
    visible = validate_task_contract(task_contract)
    if discovery.discover_partition(visible["training_examples"]) is None:
        _fail("DISCOVERY_NOT_UNIQUELY_IDENTIFIABLE")
    raw = discovery.predict({"visible": visible})
    ir = {
        "protocol": IR_PROTOCOL,
        "discovered_slots": raw["discovered_slots"],
        "heldout_assignments": raw["heldout_assignments"],
        "abstentions": raw["abstentions"],
    }
    return validate_semantic_ir(ir, visible)


def execute_validated_ir(validated_semantic_ir: dict[str, Any], solver_contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(validated_semantic_ir, dict) or validated_semantic_ir.get("protocol") != IR_PROTOCOL:
        _fail("VALIDATED_IR_REQUIRED")
    if not isinstance(solver_contract, dict) or solver_contract.get("protocol") != SOLVER_PROTOCOL:
        _fail("SOLVER_PROTOCOL_INVALID")
    eid = solver_contract.get("assignment_example_id")
    if not isinstance(eid, str) or not eid:
        _fail("SOLVER_ASSIGNMENT_EXAMPLE_ID_REQUIRED")
    if any(x.get("example_id") == eid for x in validated_semantic_ir.get("abstentions", [])):
        _fail("SOLVER_ASSIGNMENT_IS_AMBIGUOUS")

    matches = [x for x in validated_semantic_ir.get("heldout_assignments", []) if x.get("example_id") == eid]
    if len(matches) != 1:
        _fail("SOLVER_ASSIGNMENT_NOT_FOUND")
    assignment = matches[0]
    if solver_contract.get("required_polarity") is not None and assignment.get("polarity") != solver_contract["required_polarity"]:
        _fail("SOLVER_POLARITY_MISMATCH")
    if solver_contract.get("required_modality") is not None and assignment.get("modality") != solver_contract["required_modality"]:
        _fail("SOLVER_MODALITY_MISMATCH")

    static = solver_contract.get("static_binding", {})
    arg_map = solver_contract.get("parameter_from_arguments", {})
    if not isinstance(static, dict) or not isinstance(arg_map, dict):
        _fail("SOLVER_BINDING_CONTRACT_INVALID")
    binding = {str(k): str(v) for k, v in static.items()}
    arguments = assignment["arguments"]
    for var, index in arg_map.items():
        if not isinstance(index, int) or index < 0 or index >= len(arguments):
            _fail("SOLVER_ARGUMENT_INDEX_INVALID")
        binding[str(var)] = str(arguments[index])

    try:
        result = solver.apply_schema(
            solver_contract.get("operator_schema"),
            solver_contract.get("before", []),
            binding,
        )
    except (KeyError, TypeError, ValueError) as exc:
        _fail(f"SOLVER_CONTRACT_INVALID:{type(exc).__name__}")
    return {
        "protocol": "SEMANTIC_RUNTIME_EXECUTION_RESULT_V1",
        "assignment_example_id": eid,
        "slot_id": assignment["slot_id"],
        "binding": dict(sorted(binding.items())),
        "result": result,
    }


def bounded_log(event: str, **fields: Any) -> dict[str, Any]:
    safe: dict[str, Any] = {"event": str(event)[:64]}
    for key, value in sorted(fields.items()):
        k = str(key)[:64]
        low = k.lower()
        if low in FORBIDDEN_INPUT_KEYS or "oracle" in low or "hidden" in low or "raw" in low:
            continue
        if isinstance(value, str):
            safe[k] = value[:256]
        elif isinstance(value, (int, float, bool)) or value is None:
            safe[k] = value
    if len(canonical_json(safe).encode("utf-8")) > 2048:
        _fail("LOG_EVENT_TOO_LARGE")
    return safe


__all__ = [
    "RuntimeContractError",
    "bounded_log",
    "canonical_json",
    "discover_and_ground",
    "execute_validated_ir",
    "validate_semantic_ir",
    "validate_task_contract",
]
