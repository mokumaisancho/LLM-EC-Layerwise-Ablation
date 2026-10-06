#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from generate_s1c_v_holdout import generate
from s1c_v_deterministic_discovery import predict as deterministic_predict
from s2b2b2_enumerative_inducer import apply_schema

PROTOCOL = "S1C_V_FIXED_B2_CAUSAL_REPLAY_V2"
EXPECTED_RUNTIME_PROTOCOL = "FUNCTION_BOUNDARY_S1C_V_PAIRED_V2"
EXPECTED_AUDIT_TERMINAL = "S1C_V_POSTRUN_AUDIT_PASS"


def _align_slots(task: dict[str, Any], prediction: Any) -> dict[str, str]:
    if not isinstance(prediction, dict):
        return {}
    slots = prediction.get("discovered_slots")
    if not isinstance(slots, list):
        return {}
    oracle = task["oracle"]
    train_den = oracle["training_denotation_by_example"]
    den_types = oracle["denotation_arg_types"]
    alignment: dict[str, str] = {}
    seen_members: set[str] = set()
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        sid = slot.get("slot_id")
        members = slot.get("training_members")
        arg_types = slot.get("arg_types")
        if not isinstance(sid, str) or not isinstance(members, list) or not isinstance(arg_types, list):
            continue
        mids = [str(x) for x in members]
        if any(x in seen_members for x in mids):
            continue
        if any(x not in train_den for x in mids) or not mids:
            continue
        seen_members.update(mids)
        dens = {train_den[x] for x in mids}
        if len(dens) != 1:
            continue
        den = next(iter(dens))
        if list(arg_types) != list(den_types[den]):
            continue
        alignment[sid] = den
    return alignment


def _assignment_map(prediction: Any) -> tuple[dict[str, dict[str, Any]], set[str]]:
    if not isinstance(prediction, dict):
        return {}, set()
    rows = prediction.get("heldout_assignments")
    abstentions = prediction.get("abstentions")
    assignments: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("example_id"), str):
                assignments[row["example_id"]] = row
    abstain_ids: set[str] = set()
    if isinstance(abstentions, list):
        for row in abstentions:
            if isinstance(row, dict) and row.get("status") == "AMBIGUOUS" and isinstance(row.get("example_id"), str):
                abstain_ids.add(row["example_id"])
    return assignments, abstain_ids


def _encoded_pred(den: str, polarity: str, modality: str) -> str:
    return f"D{den}__{polarity}__{modality}"


def _schema_for_oracle(den: str, semantics: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    args = [str(x) for x in semantics["arguments"]]
    vars_ = [f"$A{i+1}" for i in range(len(args))]
    binding = {v: a for v, a in zip(vars_, args)}
    binding["$TASK"] = "TASK"
    pre = {
        "pred": _encoded_pred(den, semantics["polarity"], semantics["modality"]),
        "args": vars_,
    }
    schema = {
        "proposal_kind": "INDUCED_OPERATOR",
        "parameters": vars_ + ["$TASK"],
        "preconditions": [pre],
        "add_effects": [{"pred": "GOAL_DONE", "args": ["$TASK"]}],
        "delete_effects": [{"pred": "PENDING", "args": ["$TASK"]}],
    }
    return schema, binding


def _state_from_prediction(
    eid: str,
    prediction: Any,
    alignment: dict[str, str],
) -> tuple[list[dict[str, Any]], bool]:
    assignments, abstentions = _assignment_map(prediction)
    if eid in abstentions:
        return [], True
    row = assignments.get(eid)
    if not isinstance(row, dict):
        return [], False
    sid = row.get("slot_id")
    den = alignment.get(sid)
    if den is None:
        return [], False
    args = row.get("arguments")
    polarity = row.get("polarity")
    modality = row.get("modality")
    if not isinstance(args, list) or not isinstance(polarity, str) or not isinstance(modality, str):
        return [], False
    return [{
        "pred": _encoded_pred(den, polarity, modality),
        "args": [str(x) for x in args],
    }], False


def replay_one(task: dict[str, Any], eid: str, prediction: Any) -> dict[str, Any]:
    oracle = task["oracle"]
    semantics = oracle["heldout_semantics"][eid]
    den = oracle["heldout_denotation_by_example"][eid]

    if semantics["status"] == "AMBIGUOUS":
        _, abstained = _state_from_prediction(eid, prediction, _align_slots(task, prediction))
        return {
            "success": abstained,
            "reason": "AMBIGUOUS_ABSTENTION_PASS" if abstained else "AMBIGUOUS_ABSTENTION_FAIL",
        }

    alignment = _align_slots(task, prediction)
    state, abstained = _state_from_prediction(eid, prediction, alignment)
    if abstained:
        return {"success": False, "reason": "UNEXPECTED_ABSTENTION"}
    schema, binding = _schema_for_oracle(den, semantics)
    before = state + [{"pred": "PENDING", "args": ["TASK"]}]
    result = apply_schema(schema, before, binding)
    return {
        "success": bool(result.get("applicable")),
        "reason": "FIXED_B2_APPLICABLE" if result.get("applicable") else "FIXED_B2_PRECONDITION_FAIL",
    }


def oracle_success(task: dict[str, Any], eid: str) -> bool:
    semantics = task["oracle"]["heldout_semantics"][eid]
    if semantics["status"] == "AMBIGUOUS":
        return True
    den = task["oracle"]["heldout_denotation_by_example"][eid]
    schema, binding = _schema_for_oracle(den, semantics)
    atom = {
        "pred": _encoded_pred(den, semantics["polarity"], semantics["modality"]),
        "args": [str(x) for x in semantics["arguments"]],
    }
    result = apply_schema(schema, [atom, {"pred": "PENDING", "args": ["TASK"]}], binding)
    return bool(result.get("applicable"))


def replay(runtime: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    if runtime.get("protocol") != EXPECTED_RUNTIME_PROTOCOL:
        return {"pass": False, "terminal": "S1C_V_CAUSAL_REPLAY_FAIL_CLOSED", "reason": "RUNTIME_PROTOCOL_MISMATCH"}
    if audit.get("terminal") != EXPECTED_AUDIT_TERMINAL or audit.get("pass") is not True:
        return {"pass": False, "terminal": "S1C_V_CAUSAL_REPLAY_FAIL_CLOSED", "reason": "POSTRUN_AUDIT_NOT_PASS"}

    tasks = generate()
    qwen_predictions = {
        row["task_id"]: row.get("prediction")
        for row in runtime.get("raw_qwen_rows", [])
        if isinstance(row, dict) and isinstance(row.get("task_id"), str)
    }
    deterministic_predictions = {
        task["task_id"]: deterministic_predict({"visible": task["visible"]})
        for task in tasks
    }
    if set(qwen_predictions) != {t["task_id"] for t in tasks}:
        return {"pass": False, "terminal": "S1C_V_CAUSAL_REPLAY_FAIL_CLOSED", "reason": "QWEN_PREDICTION_COVERAGE_MISMATCH"}

    rows = []
    oracle_n = det_n = qwen_n = total = 0
    for task in tasks:
        tid = task["task_id"]
        heldouts = task["visible"]["heldout_examples"]
        for ex in heldouts:
            eid = ex["example_id"]
            o = oracle_success(task, eid)
            if not o:
                return {
                    "pass": False,
                    "terminal": "S1C_V_CAUSAL_REPLAY_FAIL_CLOSED",
                    "reason": "ORACLE_DOWNSTREAM_REPLAY_FAILED",
                    "task_id": tid,
                    "example_id": eid,
                }
            d = replay_one(task, eid, deterministic_predictions[tid])
            q = replay_one(task, eid, qwen_predictions[tid])
            oracle_n += int(o)
            det_n += int(d["success"])
            qwen_n += int(q["success"])
            total += 1
            rows.append({
                "task_id": tid,
                "family": task["family"],
                "example_id": eid,
                "oracle": {"success": o},
                "deterministic": d,
                "qwen25_1p5b": q,
            })

    return {
        "protocol": PROTOCOL,
        "pass": True,
        "terminal": "S1C_V_FIXED_B2_CAUSAL_REPLAY_PASS",
        "heldout_count": total,
        "oracle_downstream_success": oracle_n / total if total else 0.0,
        "deterministic_downstream_success": det_n / total if total else 0.0,
        "qwen25_1p5b_downstream_success": qwen_n / total if total else 0.0,
        "qwen_minus_deterministic_downstream": (qwen_n - det_n) / total if total else 0.0,
        "rows": rows,
        "solver_contract": {
            "solver": "byte-fixed s2b2b2_enumerative_inducer.apply_schema",
            "oracle_hidden_denotation_used_only_to_define_fixed_per-example precondition": True,
            "predicted_upstream_representation_is_only_arm-varying_input": True,
            "extra_predicted_atoms": "not generated by this V output contract; one heldout assignment maps to one semantic atom",
            "model_reinference": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runtime_json", type=Path)
    ap.add_argument("audit_json", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    runtime = json.loads(args.runtime_json.read_text(encoding="utf-8"))
    audit = json.loads(args.audit_json.read_text(encoding="utf-8"))
    result = replay(runtime, audit)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result.get("pass") else 3


if __name__ == "__main__":
    raise SystemExit(main())
