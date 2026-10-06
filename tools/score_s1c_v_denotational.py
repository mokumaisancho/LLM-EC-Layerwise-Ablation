#!/usr/bin/env python3
from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Any

PROTOCOL = "S1C_V_INDEPENDENT_DENOTATIONAL_EQUIVALENCE_SCORER_V1"
MIN_SLOTS = 1
MAX_SLOTS = 8
ALLOWED_POLARITY = {"POS", "NEG"}
ALLOWED_MODALITY = {"ASSERTED", "REQUIRED", "POSSIBLE"}


def _visible_training_ids(task: dict[str, Any]) -> list[str]:
    return [str(x["example_id"]) for x in task["visible"]["training_examples"]]


def _visible_heldout_ids(task: dict[str, Any]) -> list[str]:
    return [str(x["example_id"]) for x in task["visible"]["heldout_examples"]]


def _validate_prediction_shape(task: dict[str, Any], prediction: Any) -> dict[str, Any]:
    if not isinstance(prediction, dict):
        return {"valid": False, "reason": "NOT_OBJECT"}
    if set(prediction) != {"discovered_slots", "heldout_assignments", "abstentions"}:
        return {"valid": False, "reason": "WRONG_TOP_LEVEL_KEYS"}

    slots = prediction["discovered_slots"]
    assignments = prediction["heldout_assignments"]
    abstentions = prediction["abstentions"]
    if not isinstance(slots, list) or not isinstance(assignments, list) or not isinstance(abstentions, list):
        return {"valid": False, "reason": "TOP_LEVEL_NOT_LISTS"}
    if not (MIN_SLOTS <= len(slots) <= MAX_SLOTS):
        return {"valid": False, "reason": "SLOT_COUNT_OUT_OF_BOUND"}

    train_ids = set(_visible_training_ids(task))
    heldout_ids = set(_visible_heldout_ids(task))

    slot_ids: list[str] = []
    member_owner: dict[str, str] = {}
    slot_members: dict[str, list[str]] = {}
    slot_types: dict[str, tuple[str, ...]] = {}

    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {"slot_id", "arg_types", "training_members"}:
            return {"valid": False, "reason": "INVALID_SLOT_SHAPE"}
        sid = slot.get("slot_id")
        arg_types = slot.get("arg_types")
        members = slot.get("training_members")
        if not isinstance(sid, str) or not sid:
            return {"valid": False, "reason": "INVALID_SLOT_ID"}
        if sid in slot_ids:
            return {"valid": False, "reason": "DUPLICATE_SLOT_ID"}
        slot_ids.append(sid)
        if not isinstance(arg_types, list) or not all(isinstance(x, str) and x for x in arg_types):
            return {"valid": False, "reason": "INVALID_SLOT_ARG_TYPES"}
        if not isinstance(members, list) or not members:
            return {"valid": False, "reason": "EMPTY_OR_INVALID_SLOT_MEMBERS"}
        smembers: list[str] = []
        for member in members:
            mid = str(member)
            if mid not in train_ids:
                return {"valid": False, "reason": "UNKNOWN_TRAINING_MEMBER"}
            if mid in member_owner:
                return {"valid": False, "reason": "TRAINING_MEMBER_ASSIGNED_TWICE"}
            member_owner[mid] = sid
            smembers.append(mid)
        slot_members[sid] = smembers
        slot_types[sid] = tuple(arg_types)

    if set(member_owner) != train_ids:
        return {"valid": False, "reason": "TRAINING_PARTITION_INCOMPLETE"}

    assignment_by_id: dict[str, dict[str, Any]] = {}
    for row in assignments:
        if not isinstance(row, dict) or set(row) != {"example_id", "slot_id", "arguments", "polarity", "modality"}:
            return {"valid": False, "reason": "INVALID_ASSIGNMENT_SHAPE"}
        eid = str(row.get("example_id"))
        if eid not in heldout_ids:
            return {"valid": False, "reason": "UNKNOWN_HELDOUT_ASSIGNMENT"}
        if eid in assignment_by_id:
            return {"valid": False, "reason": "DUPLICATE_HELDOUT_ASSIGNMENT"}
        sid = row.get("slot_id")
        args = row.get("arguments")
        if sid not in slot_members:
            return {"valid": False, "reason": "ASSIGNMENT_UNKNOWN_SLOT"}
        if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
            return {"valid": False, "reason": "ASSIGNMENT_ARGUMENTS_INVALID"}
        if row.get("polarity") not in ALLOWED_POLARITY:
            return {"valid": False, "reason": "ASSIGNMENT_POLARITY_INVALID"}
        if row.get("modality") not in ALLOWED_MODALITY:
            return {"valid": False, "reason": "ASSIGNMENT_MODALITY_INVALID"}
        assignment_by_id[eid] = row

    abstain_ids: set[str] = set()
    for row in abstentions:
        if not isinstance(row, dict) or set(row) != {"example_id", "status"}:
            return {"valid": False, "reason": "INVALID_ABSTENTION_SHAPE"}
        eid = str(row.get("example_id"))
        if eid not in heldout_ids:
            return {"valid": False, "reason": "UNKNOWN_HELDOUT_ABSTENTION"}
        if row.get("status") != "AMBIGUOUS":
            return {"valid": False, "reason": "INVALID_ABSTENTION_STATUS"}
        if eid in abstain_ids:
            return {"valid": False, "reason": "DUPLICATE_ABSTENTION"}
        if eid in assignment_by_id:
            return {"valid": False, "reason": "HELDOUT_BOTH_ASSIGNED_AND_ABSTAINED"}
        abstain_ids.add(eid)

    if set(assignment_by_id) | abstain_ids != heldout_ids:
        return {"valid": False, "reason": "HELDOUT_COVERAGE_INCOMPLETE"}

    return {
        "valid": True,
        "reason": "VALID",
        "slot_ids": slot_ids,
        "slot_members": slot_members,
        "slot_types": slot_types,
        "training_owner": member_owner,
        "assignment_by_id": assignment_by_id,
        "abstain_ids": abstain_ids,
    }


def _oracle(task: dict[str, Any]) -> dict[str, Any]:
    oracle = task.get("oracle")
    if not isinstance(oracle, dict):
        raise ValueError("ORACLE_MISSING")
    required = {
        "training_denotation_by_example",
        "heldout_denotation_by_example",
        "denotation_arg_types",
        "heldout_semantics",
    }
    if set(oracle) != required:
        raise ValueError("ORACLE_KEYS_INVALID")
    return oracle


def _pairwise_partition_accuracy(train_ids: list[str], owner: dict[str, str], denotation: dict[str, str]) -> tuple[float, int, int]:
    correct = 0
    total = 0
    for a, b in itertools.combinations(sorted(train_ids), 2):
        pred_same = owner[a] == owner[b]
        gold_same = denotation[a] == denotation[b]
        correct += int(pred_same == gold_same)
        total += 1
    return (correct / total if total else 1.0, correct, total)


def _slot_alignment(
    slot_members: dict[str, list[str]],
    slot_types: dict[str, tuple[str, ...]],
    train_denotation: dict[str, str],
    denotation_arg_types: dict[str, list[str]],
) -> tuple[dict[str, str], dict[str, Any]]:
    alignment: dict[str, str] = {}
    details: dict[str, Any] = {}
    for sid, members in slot_members.items():
        dens = {train_denotation[m] for m in members}
        if len(dens) != 1:
            details[sid] = {"aligned": False, "reason": "MIXED_DENOTATION", "denotations": sorted(dens)}
            continue
        den = next(iter(dens))
        expected_types = tuple(denotation_arg_types[den])
        if slot_types[sid] != expected_types:
            details[sid] = {
                "aligned": False,
                "reason": "ARG_TYPE_MISMATCH",
                "denotation": den,
                "expected_arg_types": list(expected_types),
                "actual_arg_types": list(slot_types[sid]),
            }
            continue
        alignment[sid] = den
        details[sid] = {"aligned": True, "denotation": den}
    return alignment, details


def score_task(task: dict[str, Any], prediction: Any) -> dict[str, Any]:
    try:
        oracle = _oracle(task)
    except Exception as exc:
        return {"pass": False, "terminal": "S1C_V_SCORER_FAIL_CLOSED", "reason": str(exc)}

    shape = _validate_prediction_shape(task, prediction)
    if not shape["valid"]:
        return {
            "pass": True,
            "terminal": "S1C_V_SCORE_COMPLETE",
            "prediction_valid": False,
            "prediction_reason": shape["reason"],
            "training_partition_pairwise_accuracy": 0.0,
            "heldout_denotational_assignment_accuracy": 0.0,
            "exact_discovery_and_grounding": False,
            "argument_binding_accuracy": 0.0,
            "polarity_modality_accuracy": 0.0,
            "abstention_accuracy": 0.0,
            "slot_purity": 0.0,
            "slot_coverage": 0.0,
        }

    train_ids = _visible_training_ids(task)
    heldout_ids = _visible_heldout_ids(task)
    train_den = {str(k): str(v) for k, v in oracle["training_denotation_by_example"].items()}
    held_den = {str(k): (None if v is None else str(v)) for k, v in oracle["heldout_denotation_by_example"].items()}
    den_types = {str(k): list(v) for k, v in oracle["denotation_arg_types"].items()}
    held_sem = oracle["heldout_semantics"]

    if set(train_den) != set(train_ids) or set(held_den) != set(heldout_ids):
        return {"pass": False, "terminal": "S1C_V_SCORER_FAIL_CLOSED", "reason": "ORACLE_COVERAGE_MISMATCH"}

    pair_acc, pair_correct, pair_total = _pairwise_partition_accuracy(train_ids, shape["training_owner"], train_den)
    alignment, alignment_detail = _slot_alignment(shape["slot_members"], shape["slot_types"], train_den, den_types)

    pure_member_count = sum(
        len(shape["slot_members"][sid])
        for sid in alignment
    )
    slot_purity = pure_member_count / len(train_ids) if train_ids else 1.0
    slot_coverage = len(shape["training_owner"]) / len(train_ids) if train_ids else 1.0

    held_correct = 0
    held_total = len(heldout_ids)
    arg_num = arg_den = 0
    pm_num = pm_den = 0
    abstain_num = abstain_den = 0
    held_rows = []

    for eid in heldout_ids:
        semantics = held_sem[eid]
        expected_status = semantics["status"]
        if expected_status == "AMBIGUOUS":
            abstain_den += 1
            ok = eid in shape["abstain_ids"]
            abstain_num += int(ok)
            held_correct += int(ok)
            held_rows.append({"example_id": eid, "correct": ok, "reason": "AMBIGUOUS" if ok else "ABSTENTION_FAIL"})
            continue

        row = shape["assignment_by_id"].get(eid)
        if row is None:
            held_rows.append({"example_id": eid, "correct": False, "reason": "MISSING_ASSIGNMENT"})
            continue
        sid = row["slot_id"]
        aligned_den = alignment.get(sid)
        den_ok = aligned_den is not None and aligned_den == held_den[eid]
        expected_args = list(semantics["arguments"])
        args_ok = list(row["arguments"]) == expected_args
        pm_ok = row["polarity"] == semantics["polarity"] and row["modality"] == semantics["modality"]

        arg_den += 1
        arg_num += int(args_ok)
        pm_den += 1
        pm_num += int(pm_ok)
        ok = den_ok and args_ok and pm_ok
        held_correct += int(ok)
        held_rows.append({
            "example_id": eid,
            "correct": ok,
            "reason": "VALID" if ok else "DENOTATION_OR_ARGUMENT_OR_MODALITY_MISMATCH",
            "aligned_denotation": aligned_den,
            "expected_denotation": held_den[eid],
            "arguments_correct": args_ok,
            "polarity_modality_correct": pm_ok,
        })

    held_acc = held_correct / held_total if held_total else 1.0
    abstention_accuracy = abstain_num / abstain_den if abstain_den else None
    exact = bool(
        pair_acc == 1.0
        and held_acc == 1.0
        and slot_purity == 1.0
        and slot_coverage == 1.0
        and len(alignment) == len(shape["slot_members"])
    )

    return {
        "pass": True,
        "terminal": "S1C_V_SCORE_COMPLETE",
        "prediction_valid": True,
        "prediction_reason": "VALID",
        "training_partition_pairwise_accuracy": pair_acc,
        "training_partition_pairwise_correct": pair_correct,
        "training_partition_pairwise_total": pair_total,
        "heldout_denotational_assignment_accuracy": held_acc,
        "heldout_correct": held_correct,
        "heldout_total": held_total,
        "exact_discovery_and_grounding": exact,
        "argument_binding_accuracy": arg_num / arg_den if arg_den else None,
        "polarity_modality_accuracy": pm_num / pm_den if pm_den else None,
        "abstention_accuracy": abstention_accuracy,
        "slot_purity": slot_purity,
        "slot_coverage": slot_coverage,
        "slot_alignment": alignment_detail,
        "heldout_rows": held_rows,
    }


def aggregate(tasks: list[dict[str, Any]], predictions: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for task in tasks:
        tid = str(task["task_id"])
        rows.append({"task_id": tid, **score_task(task, predictions.get(tid))})

    if any(r.get("pass") is not True for r in rows):
        return {
            "protocol": PROTOCOL,
            "pass": False,
            "terminal": "S1C_V_SCORER_FAIL_CLOSED",
            "rows": rows,
        }

    n = len(rows)
    return {
        "protocol": PROTOCOL,
        "pass": True,
        "terminal": "S1C_V_SCORE_COMPLETE",
        "task_count": n,
        "primary": {
            "training_partition_pairwise_accuracy": sum(r["training_partition_pairwise_accuracy"] for r in rows) / n if n else 0.0,
            "heldout_denotational_assignment_accuracy": sum(r["heldout_denotational_assignment_accuracy"] for r in rows) / n if n else 0.0,
            "exact_discovery_and_grounding_rate": sum(int(r["exact_discovery_and_grounding"]) for r in rows) / n if n else 0.0,
        },
        "secondary": {
            "slot_purity": sum(r["slot_purity"] for r in rows) / n if n else 0.0,
            "slot_coverage": sum(r["slot_coverage"] for r in rows) / n if n else 0.0,
            "abstention_accuracy": (
                sum(r["abstention_accuracy"] for r in rows if r["abstention_accuracy"] is not None)
                / max(1, sum(1 for r in rows if r["abstention_accuracy"] is not None))
            ),
        },
        "rows": rows,
    }
