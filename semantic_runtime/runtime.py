from __future__ import annotations

import json
import re
from typing import Any

from . import discovery
from . import solver
from .public_hypotheses import candidates, evaluation_predictions, probe_input

PROTOCOL = "SEMANTIC_RUNTIME_V1"
TASK_PROTOCOL = "SEMANTIC_RUNTIME_TASK_V1"
IR_PROTOCOL = "SEMANTIC_RUNTIME_IR_V1"
SOLVER_PROTOCOL = "SEMANTIC_RUNTIME_SOLVER_V1"
EVAL_IDS = ("Q03", "Q05", "Q06", "Q07")
FORBIDDEN_INPUT_KEYS = {"oracle", "family", "audit", "hidden", "gold", "answer"}
PROBE_ID_RE = re.compile(r"^Q([0-9]{2})$")


class RuntimeContractError(ValueError):
    pass


def _fail(code: str) -> None:
    raise RuntimeContractError(code)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _exact_keys(obj: Any, required: set[str], code: str, optional: set[str] | None = None) -> None:
    if not isinstance(obj, dict):
        _fail(code)
    optional = optional or set()
    keys = set(obj)
    if not required.issubset(keys) or not keys.issubset(required | optional):
        _fail(code)


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
    if not isinstance(value, list) or len(value) != 3 or any(type(x) is not int or x not in (0, 1) for x in value):
        _fail(code)


def _probe_index(probe_id: Any) -> int:
    if not isinstance(probe_id, str):
        _fail("PROBE_ID_INVALID")
    m = PROBE_ID_RE.fullmatch(probe_id)
    if m is None:
        _fail("PROBE_ID_INVALID")
    index = int(m.group(1))
    if not 0 <= index <= 7:
        _fail("PROBE_ID_OUTSIDE_PUBLIC_STATE_SPACE")
    return index


def _registry(registry: Any, types: set[str]) -> None:
    if not isinstance(registry, dict) or not registry:
        _fail("ENTITY_REGISTRY_REQUIRED")
    for eid, item in registry.items():
        if not isinstance(eid, str) or not eid:
            _fail("ENTITY_ENTRY_INVALID")
        _exact_keys(item, {"type", "surface_forms"}, "ENTITY_ENTRY_INVALID")
        if item.get("type") not in types:
            _fail("ENTITY_TYPE_UNKNOWN")
        forms = item.get("surface_forms")
        if not isinstance(forms, list) or not forms or any(not isinstance(x, str) or not x for x in forms):
            _fail("ENTITY_SURFACE_FORMS_INVALID")


def _arg_types(registry: dict[str, Any]) -> list[str]:
    return [str(registry[eid]["type"]) for eid in sorted(registry)]


def validate_task_contract(task_contract: dict[str, Any]) -> dict[str, Any]:
    _reject_hidden_keys(task_contract)
    _exact_keys(task_contract, {"protocol", "visible"}, "TASK_ROOT_KEYS_INVALID")
    if task_contract["protocol"] != TASK_PROTOCOL:
        _fail("TASK_PROTOCOL_INVALID")

    visible = task_contract["visible"]
    _exact_keys(
        visible,
        {"type_inventory", "training_examples", "evaluation_probes", "heldout_examples"},
        "VISIBLE_KEYS_INVALID",
    )
    types = visible["type_inventory"]
    if not isinstance(types, list) or not types or len(types) != len(set(types)) or any(not isinstance(x, str) or not x for x in types):
        _fail("TYPE_INVENTORY_INVALID")
    type_set = set(types)

    train = visible["training_examples"]
    held = visible["heldout_examples"]
    probes = visible["evaluation_probes"]
    if not isinstance(train, list) or len(train) != 4:
        _fail("EXACTLY_FOUR_TRAINING_EXAMPLES_REQUIRED")
    if not isinstance(held, list) or not held:
        _fail("HELDOUT_EXAMPLES_REQUIRED")
    if not isinstance(probes, list) or len(probes) != 4:
        _fail("EVALUATION_PROBES_Q03_Q05_Q06_Q07_REQUIRED")

    expected_eval = list(EVAL_IDS)
    actual_eval: list[str] = []
    for row in probes:
        _exact_keys(row, {"probe_id", "before"}, "EVALUATION_PROBE_INVALID")
        pid = row["probe_id"]
        actual_eval.append(pid)
        index = _probe_index(pid)
        if list(probe_input(index)) != row["before"]:
            _fail("EVALUATION_PROBE_BEFORE_MISMATCH")
    if actual_eval != expected_eval:
        _fail("EVALUATION_PROBES_Q03_Q05_Q06_Q07_REQUIRED")

    seen: set[str] = set()
    for ex in train:
        _exact_keys(
            ex,
            {"example_id", "raw_text", "entity_registry", "behavior_observations"},
            "TRAINING_EXAMPLE_KEYS_INVALID",
        )
        eid = ex["example_id"]
        if not isinstance(eid, str) or not eid or eid in seen:
            _fail("TRAINING_EXAMPLE_ID_INVALID")
        seen.add(eid)
        if not isinstance(ex["raw_text"], str) or not ex["raw_text"].strip():
            _fail("TRAINING_RAW_TEXT_REQUIRED")
        _registry(ex["entity_registry"], type_set)
        observations = ex["behavior_observations"]
        if not isinstance(observations, list) or not observations:
            _fail("BEHAVIOR_OBSERVATIONS_REQUIRED")
        observation_ids: list[str] = []
        for obs in observations:
            _exact_keys(obs, {"probe_id", "before", "after"}, "OBSERVATION_KEYS_INVALID")
            index = _probe_index(obs["probe_id"])
            observation_ids.append(obs["probe_id"])
            _bits3(obs["before"], "OBSERVATION_BITS_INVALID")
            _bits3(obs["after"], "OBSERVATION_BITS_INVALID")
            if list(probe_input(index)) != obs["before"]:
                _fail("OBSERVATION_BEFORE_MISMATCH")
        if len(observation_ids) != len(set(observation_ids)):
            _fail("OBSERVATION_PROBE_DUPLICATED")

    held_seen: set[str] = set()
    for ex in held:
        _exact_keys(ex, {"example_id", "raw_text", "entity_registry"}, "HELDOUT_EXAMPLE_KEYS_INVALID")
        eid = ex["example_id"]
        if not isinstance(eid, str) or not eid or eid in held_seen or eid in seen:
            _fail("HELDOUT_EXAMPLE_ID_INVALID")
        held_seen.add(eid)
        if not isinstance(ex["raw_text"], str) or not ex["raw_text"].strip():
            _fail("HELDOUT_RAW_TEXT_REQUIRED")
        _registry(ex["entity_registry"], type_set)
    return visible


def validate_semantic_ir(ir: dict[str, Any], visible: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(
        ir,
        {"protocol", "discovered_slots", "heldout_assignments", "abstentions"},
        "IR_ROOT_KEYS_INVALID",
    )
    if ir["protocol"] != IR_PROTOCOL:
        _fail("IR_PROTOCOL_INVALID")

    slots = ir["discovered_slots"]
    assignments = ir["heldout_assignments"]
    abstentions = ir["abstentions"]
    if not isinstance(slots, list) or len(slots) != 2:
        _fail("EXACTLY_TWO_DISCOVERED_SLOTS_REQUIRED")

    train = visible["training_examples"]
    train_by_id = {str(x["example_id"]): x for x in train}
    train_ids = set(train_by_id)
    held_by_id = {str(x["example_id"]): x for x in visible["heldout_examples"]}
    held_ids = set(held_by_id)
    expected_groups = discovery.discover_partition(train)
    if expected_groups is None:
        _fail("DISCOVERY_NOT_UNIQUELY_IDENTIFIABLE")
    expected_by_members = {
        frozenset(members): {"code": code, "types": _arg_types(train[pair[0]]["entity_registry"])}
        for members, code, pair in expected_groups
    }

    slot_ids: set[str] = set()
    slot_by_id: dict[str, dict[str, Any]] = {}
    all_members: list[str] = []
    for slot in slots:
        _exact_keys(
            slot,
            {"slot_id", "arg_types", "training_members", "evaluation_probe_predictions"},
            "SLOT_KEYS_INVALID",
        )
        sid = slot["slot_id"]
        if not isinstance(sid, str) or not sid or sid in slot_ids:
            _fail("SLOT_ID_INVALID_OR_DUPLICATED")
        slot_ids.add(sid)
        slot_by_id[sid] = slot
        arg_types = slot["arg_types"]
        if not isinstance(arg_types, list) or not arg_types or any(x not in visible["type_inventory"] for x in arg_types):
            _fail("SLOT_ARG_TYPES_INVALID")
        members = slot["training_members"]
        if not isinstance(members, list) or len(members) != 2 or len(set(members)) != 2:
            _fail("SLOT_TRAINING_MEMBERS_INVALID")
        member_key = frozenset(str(x) for x in members)
        if member_key not in expected_by_members:
            _fail("SLOT_MEMBERS_NOT_DISCOVERED_PARTITION")
        for member in member_key:
            if member not in train_by_id:
                _fail("SLOT_TRAINING_MEMBER_UNKNOWN")
            if _arg_types(train_by_id[member]["entity_registry"]) != arg_types:
                _fail("SLOT_MEMBER_ARG_TYPES_MISMATCH")
        expected = expected_by_members[member_key]
        if arg_types != expected["types"]:
            _fail("SLOT_ARG_TYPES_MISMATCH")
        all_members.extend(str(x) for x in members)

        predictions = slot["evaluation_probe_predictions"]
        if not isinstance(predictions, list) or len(predictions) != 4:
            _fail("SLOT_EVALUATION_PROBES_INVALID")
        for row in predictions:
            _exact_keys(row, {"probe_id", "predicted_after"}, "SLOT_EVALUATION_ROW_INVALID")
            _bits3(row["predicted_after"], "SLOT_EVALUATION_BITS_INVALID")
        if predictions != evaluation_predictions(expected["code"]):
            _fail("SLOT_EVALUATION_PREDICTIONS_INCONSISTENT")

    if set(all_members) != train_ids or len(all_members) != len(set(all_members)):
        _fail("TRAINING_PARTITION_NOT_EXACT")
    if not isinstance(assignments, list) or not isinstance(abstentions, list):
        _fail("HELDOUT_DECISIONS_REQUIRED")

    decided: list[str] = []
    for row in assignments:
        _exact_keys(
            row,
            {"example_id", "slot_id", "arguments", "polarity", "modality"},
            "ASSIGNMENT_KEYS_INVALID",
        )
        eid, sid = row["example_id"], row["slot_id"]
        if eid not in held_ids or sid not in slot_ids:
            _fail("ASSIGNMENT_REFERENCE_INVALID")
        arguments = row["arguments"]
        if not isinstance(arguments, list) or not arguments or len(arguments) != len(set(arguments)):
            _fail("ASSIGNMENT_ARGUMENTS_INVALID")
        registry = held_by_id[eid]["entity_registry"]
        if any(arg not in registry for arg in arguments):
            _fail("ASSIGNMENT_ARGUMENT_UNKNOWN")
        argument_types = [registry[arg]["type"] for arg in arguments]
        if argument_types != slot_by_id[sid]["arg_types"]:
            _fail("ASSIGNMENT_ARGUMENT_TYPES_MISMATCH")
        if row["polarity"] not in ("POS", "NEG") or row["modality"] not in ("ASSERTED", "REQUIRED", "POSSIBLE"):
            _fail("ASSIGNMENT_QUALIFIER_INVALID")
        decided.append(str(eid))

    for row in abstentions:
        _exact_keys(row, {"example_id", "status"}, "ABSTENTION_KEYS_INVALID")
        if row["status"] != "AMBIGUOUS" or row["example_id"] not in held_ids:
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
    _exact_keys(
        solver_contract,
        {"protocol", "assignment_example_id", "parameter_from_arguments", "static_binding", "before", "operator_schema"},
        "SOLVER_ROOT_KEYS_INVALID",
        optional={"required_polarity", "required_modality"},
    )
    if solver_contract["protocol"] != SOLVER_PROTOCOL:
        _fail("SOLVER_PROTOCOL_INVALID")
    eid = solver_contract["assignment_example_id"]
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

    static = solver_contract["static_binding"]
    arg_map = solver_contract["parameter_from_arguments"]
    if not isinstance(static, dict) or not isinstance(arg_map, dict):
        _fail("SOLVER_BINDING_CONTRACT_INVALID")
    binding = {str(k): str(v) for k, v in static.items()}
    arguments = assignment["arguments"]
    for var, index in arg_map.items():
        if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(arguments):
            _fail("SOLVER_ARGUMENT_INDEX_INVALID")
        binding[str(var)] = str(arguments[index])

    try:
        result = solver.apply_schema(
            solver_contract["operator_schema"],
            solver_contract["before"],
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
