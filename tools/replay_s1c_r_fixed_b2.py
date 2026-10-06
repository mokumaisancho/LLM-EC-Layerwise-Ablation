#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from generate_s1c_r_holdout import generate
from score_s1c_r_typed_ir import validate_typed_ir
from s2b2b2_enumerative_inducer import apply_schema

PROTOCOL = "S1C_R_FIXED_B2_CAUSAL_REPLAY_V1"
EXPECTED_RUNTIME_PROTOCOL = "FUNCTION_BOUNDARY_S1C_R_PAIRED_V1"
EXPECTED_AUDIT_TERMINAL = "S1C_R_POSTRUN_AUDIT_PASS"


def encoded_pred(atom: dict[str, Any]) -> str:
    return f"{atom['predicate']}__{atom['polarity']}__{atom['modality']}"


def var_for_entity(entity_id: str) -> str:
    return "$" + entity_id


def state_from_ir(ir: dict[str, Any]) -> list[dict[str, Any]]:
    if ir.get("status") != "OK":
        return []
    rows = []
    for atom in ir.get("atoms", []):
        rows.append({
            "pred": encoded_pred(atom),
            "args": [str(x) for x in atom["arguments"]],
        })
    return rows


def fixed_schema_from_oracle(oracle_ir: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    entities = sorted({
        str(x)
        for atom in oracle_ir.get("atoms", [])
        for x in atom.get("arguments", [])
    })
    binding = {var_for_entity(eid): eid for eid in entities}
    binding["$TASK"] = "TASK"
    preconditions = [
        {
            "pred": encoded_pred(atom),
            "args": [var_for_entity(str(x)) for x in atom["arguments"]],
        }
        for atom in oracle_ir.get("atoms", [])
    ]
    schema = {
        "proposal_kind": "INDUCED_OPERATOR",
        "parameters": sorted(binding),
        "preconditions": preconditions,
        "add_effects": [{"pred": "GOAL_DONE", "args": ["$TASK"]}],
        "delete_effects": [{"pred": "PENDING", "args": ["$TASK"]}],
    }
    return schema, binding


def replay_one(fixture: dict[str, Any], prediction: Any) -> dict[str, Any]:
    visible = fixture["visible"]
    oracle_check = validate_typed_ir(visible, fixture["oracle"]["typed_ir"])
    pred_check = validate_typed_ir(visible, prediction)
    if not oracle_check["valid"]:
        return {"success": False, "reason": "ORACLE_INVALID"}
    oracle = oracle_check["canonical"]

    if oracle["status"] == "AMBIGUOUS":
        success = bool(
            pred_check["valid"]
            and pred_check["canonical"]["status"] == "AMBIGUOUS"
            and pred_check["canonical"]["atoms"] == []
        )
        return {
            "success": success,
            "reason": "AMBIGUOUS_ABSTENTION_PASS" if success else "AMBIGUOUS_ABSTENTION_FAIL",
            "solver_path": "FIXED_ABSTENTION_GATE",
        }

    if not pred_check["valid"] or pred_check["canonical"]["status"] != "OK":
        return {
            "success": False,
            "reason": "INVALID_OR_NON_OK_TYPED_IR",
            "solver_path": "FIXED_B2_APPLY_SCHEMA",
        }

    schema, binding = fixed_schema_from_oracle(oracle)
    before = state_from_ir(pred_check["canonical"]) + [{"pred": "PENDING", "args": ["TASK"]}]
    result = apply_schema(schema, before, binding)
    success = bool(result.get("applicable"))
    return {
        "success": success,
        "reason": "FIXED_B2_APPLICABLE" if success else "FIXED_B2_PRECONDITION_FAIL",
        "solver_path": "FIXED_B2_APPLY_SCHEMA",
    }


def _prediction_maps(runtime: dict[str, Any], fixtures: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    deterministic_rows = ((runtime.get("arms") or {}).get("deterministic") or {}).get("rows") or []
    det = {
        row["fixture_id"]: row.get("canonical_prediction")
        for row in deterministic_rows
        if isinstance(row, dict) and "fixture_id" in row
    }
    qwen = {
        row["fixture_id"]: row.get("prediction")
        for row in runtime.get("raw_qwen_rows", [])
        if isinstance(row, dict) and "fixture_id" in row
    }
    expected = {f["id"] for f in fixtures}
    if set(det) != expected:
        raise ValueError("DETERMINISTIC_PREDICTION_COVERAGE_MISMATCH")
    if set(qwen) != expected:
        raise ValueError("QWEN_PREDICTION_COVERAGE_MISMATCH")
    return det, qwen


def replay(runtime: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    if runtime.get("protocol") != EXPECTED_RUNTIME_PROTOCOL:
        return {"pass": False, "terminal": "S1C_R_CAUSAL_REPLAY_FAIL_CLOSED", "reason": "RUNTIME_PROTOCOL_MISMATCH"}
    if audit.get("terminal") != EXPECTED_AUDIT_TERMINAL or audit.get("pass") is not True:
        return {"pass": False, "terminal": "S1C_R_CAUSAL_REPLAY_FAIL_CLOSED", "reason": "POSTRUN_AUDIT_NOT_PASS"}

    fixtures = generate()
    try:
        det_predictions, qwen_predictions = _prediction_maps(runtime, fixtures)
    except Exception as exc:
        return {"pass": False, "terminal": "S1C_R_CAUSAL_REPLAY_FAIL_CLOSED", "reason": str(exc)}

    rows = []
    det_success = 0
    qwen_success = 0
    oracle_success = 0
    for fixture in fixtures:
        fid = fixture["id"]
        oracle_prediction = fixture["oracle"]["typed_ir"]
        o = replay_one(fixture, oracle_prediction)
        d = replay_one(fixture, det_predictions[fid])
        q = replay_one(fixture, qwen_predictions[fid])
        if not o["success"]:
            return {
                "pass": False,
                "terminal": "S1C_R_CAUSAL_REPLAY_FAIL_CLOSED",
                "reason": "ORACLE_DOWNSTREAM_REPLAY_FAILED",
                "fixture_id": fid,
                "oracle": o,
            }
        oracle_success += int(o["success"])
        det_success += int(d["success"])
        qwen_success += int(q["success"])
        rows.append({
            "fixture_id": fid,
            "family": fixture["family"],
            "oracle": o,
            "deterministic": d,
            "qwen25_1p5b": q,
        })

    n = len(fixtures)
    det_rate = det_success / n
    qwen_rate = qwen_success / n
    return {
        "protocol": PROTOCOL,
        "pass": True,
        "terminal": "S1C_R_FIXED_B2_CAUSAL_REPLAY_PASS",
        "fixture_count": n,
        "oracle_downstream_success": oracle_success / n,
        "deterministic_downstream_success": det_rate,
        "qwen25_1p5b_downstream_success": qwen_rate,
        "qwen_minus_deterministic_downstream": qwen_rate - det_rate,
        "rows": rows,
        "solver_contract": {
            "non_ambiguous": "byte-fixed s2b2b2_enumerative_inducer.apply_schema; gold typed atoms become fixed preconditions; only substituted upstream IR changes the before-state",
            "ambiguous": "fixed abstention gate; AMBIGUOUS+empty is required",
            "extra_atoms": "do not prevent applicability; causal replay measures presence of all required typed semantics rather than exact-IR duplication",
            "oracle_used_only_to_freeze_per-fixture downstream preconditions": True,
            "downstream_solver_tuned_to_arm": False,
        },
        "model_reinference": False,
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
