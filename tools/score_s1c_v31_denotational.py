from __future__ import annotations

import itertools
from collections import Counter, defaultdict
from typing import Any

from s1c_v31_public_hypotheses import EVALUATION_PROBE_INDICES

PROTOCOL = "S1C_V31_INDEPENDENT_DENOTATIONAL_SCORER_V1"
AUTHORITY = "S1C_V31_INDEPENDENT_ORACLE_VALIDATOR_V1"
ALLOWED_POLARITY = {"POS", "NEG"}
ALLOWED_MODALITY = {"ASSERTED", "REQUIRED", "POSSIBLE"}


def _fail(reason: str, detail: Any = None) -> dict[str, Any]:
    return {
        "pass": False,
        "terminal": "S1C_V31_SCORER_FAIL_CLOSED",
        "reason": reason,
        "detail": detail,
    }


def _ari(gold: list[str], pred: list[str]) -> float:
    n = len(gold)
    if n != len(pred) or n < 2:
        return 1.0 if gold == pred else 0.0
    table: dict[tuple[str, str], int] = Counter(zip(gold, pred))
    row = Counter(gold)
    col = Counter(pred)

    def c2(x: int) -> int:
        return x * (x - 1) // 2

    sum_comb = sum(c2(v) for v in table.values())
    sum_row = sum(c2(v) for v in row.values())
    sum_col = sum(c2(v) for v in col.values())
    total = c2(n)
    if total == 0:
        return 1.0
    expected = (sum_row * sum_col) / total
    max_index = 0.5 * (sum_row + sum_col)
    denom = max_index - expected
    if denom == 0:
        return 1.0 if sum_comb == max_index else 0.0
    return (sum_comb - expected) / denom


def _pairwise_accuracy(gold: list[str], pred: list[str]) -> float:
    correct = total = 0
    for i, j in itertools.combinations(range(len(gold)), 2):
        correct += int((gold[i] == gold[j]) == (pred[i] == pred[j]))
        total += 1
    return correct / total if total else 1.0


def _eval_map(rows: Any, *, predicted: bool) -> dict[str, tuple[int, int, int]] | None:
    if not isinstance(rows, list) or len(rows) != len(EVALUATION_PROBE_INDICES):
        return None
    key = "predicted_after" if predicted else "predicted_after"
    out = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"probe_id", key}:
            return None
        pid = str(row.get("probe_id") or "")
        bits = row.get(key)
        if not isinstance(bits, list) or len(bits) != 3 or any(x not in (0, 1) for x in bits):
            return None
        if pid in out:
            return None
        out[pid] = tuple(int(x) for x in bits)
    expected = {f"Q{i:02d}" for i in EVALUATION_PROBE_INDICES}
    if set(out) != expected:
        return None
    return out


def validate_prediction(task: dict[str, Any], prediction: Any) -> dict[str, Any]:
    if not isinstance(prediction, dict):
        return {"valid": False, "reason": "PREDICTION_NOT_OBJECT"}
    if set(prediction) != {"discovered_slots", "heldout_assignments", "abstentions"}:
        return {"valid": False, "reason": "TOP_LEVEL_KEYS_INVALID"}

    visible = task["visible"]
    train_ids = {str(x["example_id"]) for x in visible["training_examples"]}
    held_ids = {str(x["example_id"]) for x in visible["heldout_examples"]}
    slot_bound = visible["slot_count_bound"]

    slots = prediction["discovered_slots"]
    assignments = prediction["heldout_assignments"]
    abstentions = prediction["abstentions"]
    if not all(isinstance(x, list) for x in (slots, assignments, abstentions)):
        return {"valid": False, "reason": "TOP_LEVEL_LIST_REQUIRED"}
    if not int(slot_bound["min"]) <= len(slots) <= int(slot_bound["max"]):
        return {"valid": False, "reason": "SLOT_COUNT_OUT_OF_BOUND"}

    slot_ids = set()
    owner = {}
    slot_types = {}
    slot_eval = {}

    for slot in slots:
        if not isinstance(slot, dict) or set(slot) != {
            "slot_id",
            "arg_types",
            "training_members",
            "evaluation_probe_predictions",
        }:
            return {"valid": False, "reason": "SLOT_SHAPE_INVALID"}
        sid = slot.get("slot_id")
        if not isinstance(sid, str) or not sid or sid in slot_ids:
            return {"valid": False, "reason": "SLOT_ID_INVALID_OR_DUPLICATE"}
        slot_ids.add(sid)

        types = slot.get("arg_types")
        members = slot.get("training_members")
        if not isinstance(types, list) or not all(isinstance(x, str) and x for x in types):
            return {"valid": False, "reason": "SLOT_ARG_TYPES_INVALID"}
        if not isinstance(members, list) or not members:
            return {"valid": False, "reason": "SLOT_MEMBERS_INVALID"}
        for member in members:
            mid = str(member)
            if mid not in train_ids:
                return {"valid": False, "reason": "UNKNOWN_TRAINING_MEMBER"}
            if mid in owner:
                return {"valid": False, "reason": "TRAINING_MEMBER_DUPLICATED"}
            owner[mid] = sid

        emap = _eval_map(slot.get("evaluation_probe_predictions"), predicted=True)
        if emap is None:
            return {"valid": False, "reason": "EVALUATION_PROBE_PREDICTIONS_INVALID"}
        slot_types[sid] = tuple(types)
        slot_eval[sid] = emap

    if set(owner) != train_ids:
        return {"valid": False, "reason": "TRAINING_PARTITION_INCOMPLETE"}

    assign_by_id = {}
    for row in assignments:
        if not isinstance(row, dict) or set(row) != {
            "example_id",
            "slot_id",
            "arguments",
            "polarity",
            "modality",
        }:
            return {"valid": False, "reason": "HELDOUT_ASSIGNMENT_SHAPE_INVALID"}
        eid = str(row.get("example_id") or "")
        if eid not in held_ids or eid in assign_by_id:
            return {"valid": False, "reason": "HELDOUT_ASSIGNMENT_ID_INVALID_OR_DUPLICATE"}
        sid = row.get("slot_id")
        if sid not in slot_ids:
            return {"valid": False, "reason": "HELDOUT_ASSIGNMENT_UNKNOWN_SLOT"}
        args = row.get("arguments")
        if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
            return {"valid": False, "reason": "HELDOUT_ARGUMENTS_INVALID"}
        if row.get("polarity") not in ALLOWED_POLARITY:
            return {"valid": False, "reason": "HELDOUT_POLARITY_INVALID"}
        if row.get("modality") not in ALLOWED_MODALITY:
            return {"valid": False, "reason": "HELDOUT_MODALITY_INVALID"}
        assign_by_id[eid] = row

    abstain_ids = set()
    for row in abstentions:
        if not isinstance(row, dict) or set(row) != {"example_id", "status"}:
            return {"valid": False, "reason": "ABSTENTION_SHAPE_INVALID"}
        eid = str(row.get("example_id") or "")
        if eid not in held_ids or eid in abstain_ids:
            return {"valid": False, "reason": "ABSTENTION_ID_INVALID_OR_DUPLICATE"}
        if row.get("status") != "AMBIGUOUS":
            return {"valid": False, "reason": "ABSTENTION_STATUS_INVALID"}
        if eid in assign_by_id:
            return {"valid": False, "reason": "HELDOUT_BOTH_ASSIGNED_AND_ABSTAINED"}
        abstain_ids.add(eid)

    if set(assign_by_id) | abstain_ids != held_ids:
        return {"valid": False, "reason": "HELDOUT_COVERAGE_INCOMPLETE"}

    return {
        "valid": True,
        "slot_ids": sorted(slot_ids),
        "owner": owner,
        "slot_types": slot_types,
        "slot_eval": slot_eval,
        "assign_by_id": assign_by_id,
        "abstain_ids": abstain_ids,
    }


def _reference_eval_map(reference: dict[str, Any]) -> dict[str, dict[str, tuple[int, int, int]]]:
    out = {}
    for key, item in reference["slot_references"].items():
        rows = item["evaluation_probe_expected"]
        parsed = _eval_map(rows, predicted=True)
        if parsed is None:
            raise ValueError("REFERENCE_EVALUATION_PROBE_INVALID")
        out[str(key)] = parsed
    return out


def _probe_match_count(pred: dict[str, tuple[int, int, int]], gold: dict[str, tuple[int, int, int]]) -> int:
    return sum(int(pred.get(pid) == gold.get(pid)) for pid in sorted(gold))


def _candidate_alignments(shape: dict[str, Any], reference: dict[str, Any]) -> list[dict[str, Any]]:
    gold_keys = sorted(reference["slot_references"])
    if len(gold_keys) != 2:
        raise ValueError("REFERENCE_SLOT_COUNT_NOT_TWO")
    pred_ids = shape["slot_ids"]
    gold_eval = _reference_eval_map(reference)

    rows = []
    for chosen in itertools.permutations(pred_ids, len(gold_keys)):
        pred_to_gold = {sid: g for sid, g in zip(chosen, gold_keys)}
        score = 0
        detail = {}
        for sid, g in pred_to_gold.items():
            expected_types = tuple(reference["slot_references"][g]["arg_types"])
            types_ok = shape["slot_types"][sid] == expected_types
            matches = _probe_match_count(shape["slot_eval"][sid], gold_eval[g]) if types_ok else 0
            detail[sid] = {"gold": g, "types_ok": types_ok, "probe_matches": matches}
            score += matches
        rows.append({"pred_to_gold": pred_to_gold, "score": score, "detail": detail})
    return rows


def _heldout_correctness(shape: dict[str, Any], reference: dict[str, Any], alignment: dict[str, str]) -> tuple[list[bool], dict[str, Any]]:
    correctness = []
    details = {}
    for eid in sorted(reference["heldout"]):
        ref = reference["heldout"][eid]
        if ref["status"] == "AMBIGUOUS":
            ok = eid in shape["abstain_ids"]
            correctness.append(ok)
            details[eid] = {"correct": ok, "status": "AMBIGUOUS"}
            continue

        row = shape["assign_by_id"].get(eid)
        if row is None:
            correctness.append(False)
            details[eid] = {"correct": False, "reason": "MISSING_ASSIGNMENT"}
            continue
        mapped = alignment.get(row["slot_id"])
        den_ok = mapped == ref["target_code"]
        args_ok = list(row["arguments"]) == list(ref["arguments"])
        pm_ok = row["polarity"] == ref["polarity"] and row["modality"] == ref["modality"]
        ok = den_ok and args_ok and pm_ok
        correctness.append(ok)
        details[eid] = {
            "correct": ok,
            "denotation_correct": den_ok,
            "arguments_correct": args_ok,
            "polarity_modality_correct": pm_ok,
            "mapped_target": mapped,
            "expected_target": ref["target_code"],
        }
    return correctness, details


def score_task(task: dict[str, Any], prediction: Any, reference: dict[str, Any]) -> dict[str, Any]:
    if reference.get("authority") != AUTHORITY:
        return _fail("REFERENCE_AUTHORITY_INVALID")
    if reference.get("task_id") != task.get("task_id"):
        return _fail("REFERENCE_TASK_BINDING_MISMATCH")

    shape = validate_prediction(task, prediction)
    if not shape["valid"]:
        return _fail("MALFORMED_PREDICTION_ASSAY_INVALID", shape["reason"])

    train_ids = sorted(reference["training_gold"])
    gold_labels = [reference["training_gold"][eid] for eid in train_ids]
    pred_labels = [shape["owner"][eid] for eid in train_ids]
    ari = _ari(gold_labels, pred_labels)
    pairwise = _pairwise_accuracy(gold_labels, pred_labels)

    try:
        alignments = _candidate_alignments(shape, reference)
    except Exception as exc:
        return _fail("ALIGNMENT_BUILD_FAILED", str(exc))
    if not alignments:
        return _fail("NO_ONE_TO_ONE_ALIGNMENT")

    best_score = max(x["score"] for x in alignments)
    best = [x for x in alignments if x["score"] == best_score]

    heldout_vectors = []
    heldout_details = []
    for row in best:
        vector, detail = _heldout_correctness(shape, reference, row["pred_to_gold"])
        heldout_vectors.append(tuple(vector))
        heldout_details.append(detail)

    if len(set(heldout_vectors)) > 1:
        return _fail(
            "ALIGNMENT_TIE_CHANGES_HELDOUT_CORRECTNESS",
            {"best_probe_score": best_score, "alignment_count": len(best), "heldout_vectors": heldout_vectors},
        )

    chosen_index = min(
        range(len(best)),
        key=lambda i: tuple(sorted(best[i]["pred_to_gold"].items())),
    )
    chosen = best[chosen_index]
    held_vector = list(heldout_vectors[chosen_index])
    held_detail = heldout_details[chosen_index]

    unseen_probe_accuracy = best_score / (2 * len(EVALUATION_PROBE_INDICES))
    heldout_accuracy = sum(int(x) for x in held_vector) / len(held_vector)

    normal_ids = [eid for eid, ref in reference["heldout"].items() if ref["status"] == "OK"]
    arg_correct = sum(int(held_detail[eid].get("arguments_correct", False)) for eid in normal_ids)
    pm_correct = sum(int(held_detail[eid].get("polarity_modality_correct", False)) for eid in normal_ids)
    ambiguous_ids = [eid for eid, ref in reference["heldout"].items() if ref["status"] == "AMBIGUOUS"]
    abst_correct = sum(int(held_detail[eid].get("correct", False)) for eid in ambiguous_ids)

    exact = bool(
        len(shape["slot_ids"]) == 2
        and ari == 1.0
        and unseen_probe_accuracy == 1.0
        and heldout_accuracy == 1.0
    )

    return {
        "pass": True,
        "terminal": "S1C_V31_SCORE_COMPLETE",
        "prediction_valid": True,
        "training_partition_adjusted_rand_index": ari,
        "training_partition_pairwise_accuracy": pairwise,
        "unseen_probe_behavior_accuracy": unseen_probe_accuracy,
        "heldout_denotational_assignment_accuracy": heldout_accuracy,
        "exact_discovery_and_grounding": exact,
        "argument_binding_accuracy": arg_correct / len(normal_ids) if normal_ids else 1.0,
        "polarity_modality_accuracy": pm_correct / len(normal_ids) if normal_ids else 1.0,
        "abstention_accuracy": abst_correct / len(ambiguous_ids) if ambiguous_ids else None,
        "slot_coverage": len(shape["owner"]) / len(train_ids) if train_ids else 1.0,
        "alignment": {
            "probe_match_score": best_score,
            "probe_match_total": 2 * len(EVALUATION_PROBE_INDICES),
            "best_alignment_count": len(best),
            "selected_pred_to_gold": chosen["pred_to_gold"],
            "selected_detail": chosen["detail"],
        },
        "heldout_rows": held_detail,
    }


def aggregate(tasks: list[dict[str, Any]], predictions: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for task in tasks:
        tid = str(task["task_id"])
        reference = references.get(tid)
        if not isinstance(reference, dict):
            return _fail("REFERENCE_MISSING", tid)
        row = score_task(task, predictions.get(tid), reference)
        rows.append({"task_id": tid, **row})
        if row.get("pass") is not True:
            return {
                "protocol": PROTOCOL,
                "pass": False,
                "terminal": "S1C_V31_SCORER_FAIL_CLOSED",
                "reason": "TASK_SCORE_FAIL_CLOSED",
                "failed_task_id": tid,
                "rows": rows,
            }

    n = len(rows)
    return {
        "protocol": PROTOCOL,
        "pass": True,
        "terminal": "S1C_V31_SCORE_COMPLETE",
        "task_count": n,
        "primary": {
            "training_partition_adjusted_rand_index": sum(r["training_partition_adjusted_rand_index"] for r in rows) / n,
            "unseen_probe_behavior_accuracy": sum(r["unseen_probe_behavior_accuracy"] for r in rows) / n,
            "heldout_denotational_assignment_accuracy": sum(r["heldout_denotational_assignment_accuracy"] for r in rows) / n,
            "exact_discovery_and_grounding_rate": sum(int(r["exact_discovery_and_grounding"]) for r in rows) / n,
        },
        "secondary": {
            "training_partition_pairwise_accuracy": sum(r["training_partition_pairwise_accuracy"] for r in rows) / n,
            "argument_binding_accuracy": sum(r["argument_binding_accuracy"] for r in rows) / n,
            "polarity_modality_accuracy": sum(r["polarity_modality_accuracy"] for r in rows) / n,
            "abstention_accuracy": sum(r["abstention_accuracy"] for r in rows if r["abstention_accuracy"] is not None)
            / max(1, sum(1 for r in rows if r["abstention_accuracy"] is not None)),
            "slot_coverage": sum(r["slot_coverage"] for r in rows) / n,
        },
        "rows": rows,
    }


__all__ = ["PROTOCOL", "aggregate", "score_task", "validate_prediction"]
