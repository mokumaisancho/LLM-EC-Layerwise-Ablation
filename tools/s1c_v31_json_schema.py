from __future__ import annotations

import json
from typing import Any

PROTOCOL = "S1C_V31_JSON_SCHEMA_V1"
LOCAL_SLOT_IDS = ("S01", "S02", "S03", "S04")
EVAL_PROBE_IDS = ("Q03", "Q05", "Q06", "Q07")


def _string_enum(values: list[str] | tuple[str, ...]) -> dict[str, Any]:
    return {"type": "string", "enum": list(values)}


def _bit_vector() -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": 3,
        "maxItems": 3,
        "items": {"type": "integer", "enum": [0, 1]},
    }


def schema_for(task: dict[str, Any]) -> dict[str, Any]:
    visible = task["visible"]
    train_ids = [str(x["example_id"]) for x in visible["training_examples"]]
    held_ids = [str(x["example_id"]) for x in visible["heldout_examples"]]
    type_ids = [str(x) for x in visible["type_inventory"]]
    entity_ids = sorted(
        {
            str(eid)
            for ex in visible["heldout_examples"]
            for eid in ex["entity_registry"]
        }
    )

    eval_prediction = {
        "type": "object",
        "additionalProperties": False,
        "required": ["probe_id", "predicted_after"],
        "properties": {
            "probe_id": _string_enum(EVAL_PROBE_IDS),
            "predicted_after": _bit_vector(),
        },
    }
    slot = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "slot_id",
            "arg_types",
            "training_members",
            "evaluation_probe_predictions",
        ],
        "properties": {
            "slot_id": _string_enum(LOCAL_SLOT_IDS),
            "arg_types": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": _string_enum(type_ids),
            },
            "training_members": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": _string_enum(train_ids),
            },
            "evaluation_probe_predictions": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": eval_prediction,
            },
        },
    }
    assignment = {
        "type": "object",
        "additionalProperties": False,
        "required": ["example_id", "slot_id", "arguments", "polarity", "modality"],
        "properties": {
            "example_id": _string_enum(held_ids),
            "slot_id": _string_enum(LOCAL_SLOT_IDS),
            "arguments": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": _string_enum(entity_ids),
            },
            "polarity": _string_enum(("POS", "NEG")),
            "modality": _string_enum(("ASSERTED", "REQUIRED", "POSSIBLE")),
        },
    }
    abstention = {
        "type": "object",
        "additionalProperties": False,
        "required": ["example_id", "status"],
        "properties": {
            "example_id": _string_enum(held_ids),
            "status": {"type": "string", "const": "AMBIGUOUS"},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["discovered_slots", "heldout_assignments", "abstentions"],
        "properties": {
            "discovered_slots": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": slot,
            },
            "heldout_assignments": {
                "type": "array",
                "minItems": 0,
                "maxItems": 3,
                "items": assignment,
            },
            "abstentions": {
                "type": "array",
                "minItems": 0,
                "maxItems": 3,
                "items": abstention,
            },
        },
    }


def canonical_positive(task: dict[str, Any]) -> dict[str, Any]:
    visible = task["visible"]
    train = [str(x["example_id"]) for x in visible["training_examples"]]
    held = [str(x["example_id"]) for x in visible["heldout_examples"]]
    types = list(visible["type_inventory"])
    args = sorted(visible["heldout_examples"][0]["entity_registry"])
    eval_rows = [
        {"probe_id": pid, "predicted_after": [0, 0, 0]}
        for pid in EVAL_PROBE_IDS
    ]
    return {
        "discovered_slots": [
            {
                "slot_id": "S01",
                "arg_types": types,
                "training_members": train,
                "evaluation_probe_predictions": eval_rows,
            }
        ],
        "heldout_assignments": [
            {
                "example_id": held[0],
                "slot_id": "S01",
                "arguments": args,
                "polarity": "POS",
                "modality": "ASSERTED",
            }
        ],
        "abstentions": [
            {"example_id": eid, "status": "AMBIGUOUS"}
            for eid in held[1:]
        ],
    }


def static_contract_check(task: dict[str, Any]) -> dict[str, Any]:
    schema = schema_for(task)
    encoded = json.dumps(canonical_positive(task), separators=(",", ":"), ensure_ascii=False)
    failures = []

    for required in (
        '"S01"',
        '"Q03"',
        '"Q05"',
        '"Q06"',
        '"Q07"',
        '"AMBIGUOUS"',
        '"evaluation_probe_predictions"',
    ):
        if required not in json.dumps(schema, separators=(",", ":")):
            failures.append({"gate": "SCHEMA_REQUIRED_LITERAL_MISSING", "literal": required})

    if '"slot_id":"S01"' not in encoded:
        failures.append({"gate": "CANONICAL_JSON_STRING_LITERAL_ENCODING_FAIL"})
    if '"slot_id":S01' in encoded:
        failures.append({"gate": "BARE_SLOT_ID_REAPPEARED"})

    if schema.get("additionalProperties") is not False:
        failures.append({"gate": "ROOT_ADDITIONAL_PROPERTIES_NOT_FALSE"})

    return {
        "protocol": PROTOCOL,
        "pass": not failures,
        "failure_count": len(failures),
        "failures": failures,
        "schema": schema,
        "canonical_positive_json": encoded,
        "runtime_smoke_required": True,
        "runtime_smoke_endpoint": "/completion",
        "runtime_constraint_field": "json_schema",
    }


__all__ = [
    "PROTOCOL",
    "LOCAL_SLOT_IDS",
    "EVAL_PROBE_IDS",
    "canonical_positive",
    "schema_for",
    "static_contract_check",
]
