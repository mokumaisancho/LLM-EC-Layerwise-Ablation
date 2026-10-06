#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

PROTOCOL = "S1C_R_INDEPENDENT_TYPED_IR_SCORER_V1"
ALLOWED_STATUS = {"OK", "AMBIGUOUS"}
ALLOWED_POLARITY = {"POS", "NEG"}
ALLOWED_MODALITY = {"ASSERTED", "REQUIRED", "POSSIBLE"}


def _entity_type(registry: dict[str, Any], entity_id: str) -> str | None:
    item = registry.get(entity_id)
    return item.get("type") if isinstance(item, dict) else None


def _atom_key(atom: dict[str, Any]) -> tuple[str, tuple[str, ...], str, str]:
    return (
        str(atom["predicate"]),
        tuple(str(x) for x in atom["arguments"]),
        str(atom["polarity"]),
        str(atom["modality"]),
    )


def _slot_key(atom: dict[str, Any]) -> tuple[str, str, str]:
    return (str(atom["predicate"]), str(atom["polarity"]), str(atom["modality"]))


def _canonical_atoms(atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keyed = {_atom_key(a): {
        "predicate": str(a["predicate"]),
        "arguments": [str(x) for x in a["arguments"]],
        "polarity": str(a["polarity"]),
        "modality": str(a["modality"]),
    } for a in atoms}
    return [keyed[k] for k in sorted(keyed)]


def validate_typed_ir(visible: dict[str, Any], value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"valid": False, "reason": "NOT_OBJECT", "canonical": None, "emitted_atom_count": 0, "valid_atom_count": 0}
    if set(value) != {"status", "atoms"}:
        return {"valid": False, "reason": "WRONG_KEYS", "canonical": None, "emitted_atom_count": 0, "valid_atom_count": 0}
    status = value.get("status")
    atoms = value.get("atoms")
    if status not in ALLOWED_STATUS:
        return {"valid": False, "reason": "INVALID_STATUS", "canonical": None, "emitted_atom_count": 0, "valid_atom_count": 0}
    if not isinstance(atoms, list):
        return {"valid": False, "reason": "ATOMS_NOT_LIST", "canonical": None, "emitted_atom_count": 0, "valid_atom_count": 0}
    if status == "AMBIGUOUS" and atoms:
        return {"valid": False, "reason": "AMBIGUOUS_WITH_ATOMS", "canonical": None, "emitted_atom_count": len(atoms), "valid_atom_count": 0}

    inventory = visible.get("opaque_semantic_inventory")
    registry = visible.get("entity_registry")
    if not isinstance(inventory, dict) or not isinstance(registry, dict):
        return {"valid": False, "reason": "VISIBLE_CONTRACT_INVALID", "canonical": None, "emitted_atom_count": len(atoms), "valid_atom_count": 0}

    valid_atoms: list[dict[str, Any]] = []
    for atom in atoms:
        if not isinstance(atom, dict) or set(atom) != {"predicate", "arguments", "polarity", "modality"}:
            return {"valid": False, "reason": "INVALID_ATOM_SHAPE", "canonical": None, "emitted_atom_count": len(atoms), "valid_atom_count": len(valid_atoms)}
        pred = atom.get("predicate")
        args = atom.get("arguments")
        polarity = atom.get("polarity")
        modality = atom.get("modality")
        if pred not in inventory:
            return {"valid": False, "reason": "UNKNOWN_PREDICATE", "canonical": None, "emitted_atom_count": len(atoms), "valid_atom_count": len(valid_atoms)}
        if not isinstance(args, list):
            return {"valid": False, "reason": "ARGUMENTS_NOT_LIST", "canonical": None, "emitted_atom_count": len(atoms), "valid_atom_count": len(valid_atoms)}
        signature = inventory[pred].get("arg_types") if isinstance(inventory[pred], dict) else None
        if not isinstance(signature, list) or len(signature) != len(args):
            return {"valid": False, "reason": "ARITY_MISMATCH", "canonical": None, "emitted_atom_count": len(atoms), "valid_atom_count": len(valid_atoms)}
        if polarity not in ALLOWED_POLARITY:
            return {"valid": False, "reason": "INVALID_POLARITY", "canonical": None, "emitted_atom_count": len(atoms), "valid_atom_count": len(valid_atoms)}
        if modality not in ALLOWED_MODALITY:
            return {"valid": False, "reason": "INVALID_MODALITY", "canonical": None, "emitted_atom_count": len(atoms), "valid_atom_count": len(valid_atoms)}
        for entity_id, expected_type in zip(args, signature):
            if entity_id not in registry:
                return {"valid": False, "reason": "UNKNOWN_ENTITY", "canonical": None, "emitted_atom_count": len(atoms), "valid_atom_count": len(valid_atoms)}
            if _entity_type(registry, entity_id) != expected_type:
                return {"valid": False, "reason": "ARGUMENT_TYPE_MISMATCH", "canonical": None, "emitted_atom_count": len(atoms), "valid_atom_count": len(valid_atoms)}
        valid_atoms.append(atom)

    canonical = {"status": status, "atoms": _canonical_atoms(valid_atoms)}
    return {
        "valid": True,
        "reason": "VALID",
        "canonical": canonical,
        "emitted_atom_count": len(atoms),
        "valid_atom_count": len(valid_atoms),
    }


def _jaccard(a: set[Any], b: set[Any], *, correct_ambiguous_empty: bool) -> float:
    if not a and not b:
        return 1.0 if correct_ambiguous_empty else 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def score_fixture(fixture: dict[str, Any], prediction: Any) -> dict[str, Any]:
    visible = fixture["visible"]
    oracle_raw = fixture["oracle"]["typed_ir"]
    oracle_check = validate_typed_ir(visible, oracle_raw)
    if not oracle_check["valid"]:
        return {
            "fixture_valid": False,
            "terminal": "ORACLE_TYPED_IR_INVALID",
            "oracle_reason": oracle_check["reason"],
        }

    pred_check = validate_typed_ir(visible, prediction)
    oracle = oracle_check["canonical"]
    pred = pred_check["canonical"] if pred_check["valid"] else None

    gold_atoms = oracle["atoms"]
    pred_atoms = pred["atoms"] if pred is not None else []

    gold_slots = {_slot_key(a) for a in gold_atoms}
    pred_slots = {_slot_key(a) for a in pred_atoms}
    correct_ambiguous = (
        pred is not None
        and oracle["status"] == "AMBIGUOUS"
        and pred["status"] == "AMBIGUOUS"
        and not gold_atoms
        and not pred_atoms
    )
    semantic_slot_accuracy = _jaccard(gold_slots, pred_slots, correct_ambiguous_empty=correct_ambiguous)

    exact_typed_ir = bool(pred is not None and pred == oracle)
    abstention_correct = bool(pred is not None and ((pred["status"] == "AMBIGUOUS") == (oracle["status"] == "AMBIGUOUS")))

    pred_keys = {_atom_key(a) for a in pred_atoms}
    gold_keys = {_atom_key(a) for a in gold_atoms}

    argument_num = sum(1 for a in gold_atoms if _atom_key(a) in pred_keys)
    argument_den = len(gold_atoms)

    direction_num = 0
    direction_den = 0
    for gold in gold_atoms:
        if len(gold["arguments"]) < 2:
            continue
        candidates = [
            p for p in pred_atoms
            if p["predicate"] == gold["predicate"]
            and p["polarity"] == gold["polarity"]
            and p["modality"] == gold["modality"]
            and sorted(p["arguments"]) == sorted(gold["arguments"])
        ]
        if candidates:
            direction_den += 1
            if any(p["arguments"] == gold["arguments"] for p in candidates):
                direction_num += 1

    negmod_num = 0
    negmod_den = 0
    for gold in gold_atoms:
        candidates = [
            p for p in pred_atoms
            if p["predicate"] == gold["predicate"] and p["arguments"] == gold["arguments"]
        ]
        if candidates:
            negmod_den += 1
            if any(p["polarity"] == gold["polarity"] and p["modality"] == gold["modality"] for p in candidates):
                negmod_num += 1

    emitted = pred_check["emitted_atom_count"]
    valid_emitted = pred_check["valid_atom_count"] if pred_check["valid"] else 0

    return {
        "fixture_valid": True,
        "prediction_valid": bool(pred_check["valid"]),
        "prediction_reason": pred_check["reason"],
        "canonical_prediction": pred,
        "canonical_oracle": oracle,
        "semantic_slot_accuracy": semantic_slot_accuracy,
        "exact_typed_ir": exact_typed_ir,
        "abstention_correct": abstention_correct,
        "argument_binding_num": argument_num,
        "argument_binding_den": argument_den,
        "type_arity_valid_num": valid_emitted,
        "type_arity_valid_den": emitted,
        "relation_direction_num": direction_num,
        "relation_direction_den": direction_den,
        "negation_modality_num": negmod_num,
        "negation_modality_den": negmod_den,
        "gold_atom_count": len(gold_keys),
        "pred_atom_count": len(pred_keys),
    }


def _safe_ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def score_rows(fixtures: list[dict[str, Any]], predictions: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = defaultdict(int)
    family_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for fixture in fixtures:
        fid = fixture["id"]
        family = fixture.get("family", "UNSPECIFIED")
        scored = score_fixture(fixture, predictions.get(fid))
        if not scored.get("fixture_valid"):
            return {
                "protocol": PROTOCOL,
                "pass": False,
                "terminal": scored["terminal"],
                "fixture_id": fid,
                "detail": scored,
            }
        reason_counts[scored["prediction_reason"]] += 1
        row = {"fixture_id": fid, "family": family, **scored}
        rows.append(row)
        family_rows[family].append(row)

    def aggregate(xs: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(xs)
        arg_num = sum(r["argument_binding_num"] for r in xs)
        arg_den = sum(r["argument_binding_den"] for r in xs)
        type_num = sum(r["type_arity_valid_num"] for r in xs)
        type_den = sum(r["type_arity_valid_den"] for r in xs)
        dir_num = sum(r["relation_direction_num"] for r in xs)
        dir_den = sum(r["relation_direction_den"] for r in xs)
        nm_num = sum(r["negation_modality_num"] for r in xs)
        nm_den = sum(r["negation_modality_den"] for r in xs)
        return {
            "fixture_count": n,
            "semantic_slot_accuracy": sum(r["semantic_slot_accuracy"] for r in xs) / n if n else 0.0,
            "exact_typed_ir_rate": sum(int(r["exact_typed_ir"]) for r in xs) / n if n else 0.0,
            "argument_binding_accuracy": _safe_ratio(arg_num, arg_den),
            "type_arity_valid_rate": _safe_ratio(type_num, type_den),
            "relation_direction_accuracy": _safe_ratio(dir_num, dir_den),
            "negation_modality_accuracy": _safe_ratio(nm_num, nm_den),
            "abstention_accuracy": sum(int(r["abstention_correct"]) for r in xs) / n if n else 0.0,
            "valid_prediction_rate": sum(int(r["prediction_valid"]) for r in xs) / n if n else 0.0,
            "invalid_prediction_count": sum(int(not r["prediction_valid"]) for r in xs),
        }

    aggregate_all = aggregate(rows)
    return {
        "protocol": PROTOCOL,
        "pass": True,
        "terminal": "S1C_R_SCORE_COMPLETE",
        "primary": {
            "semantic_slot_accuracy": aggregate_all["semantic_slot_accuracy"],
            "exact_typed_ir_rate": aggregate_all["exact_typed_ir_rate"],
        },
        "secondary": {
            k: aggregate_all[k] for k in (
                "argument_binding_accuracy",
                "type_arity_valid_rate",
                "relation_direction_accuracy",
                "negation_modality_accuracy",
                "abstention_accuracy",
            )
        },
        "valid_prediction_rate": aggregate_all["valid_prediction_rate"],
        "invalid_prediction_count": aggregate_all["invalid_prediction_count"],
        "reason_counts": dict(sorted(reason_counts.items())),
        "per_family": {family: aggregate(xs) for family, xs in sorted(family_rows.items())},
        "rows": rows,
    }
