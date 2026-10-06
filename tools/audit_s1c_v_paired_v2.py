#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from generate_s1c_v_holdout import generate
from s1c_v_deterministic_discovery import predict as deterministic_predict
from score_s1c_v_denotational import aggregate

PROTOCOL = "S1C_V_POSTRUN_AUDIT_V2"
EXPECTED_RUNTIME_PROTOCOL = "FUNCTION_BOUNDARY_S1C_V_PAIRED_V2"
EXPECTED_TERMINAL = "V_PAIRED_METRICS_READY_AUDIT_REQUIRED"
EXPECTED_TASKS = 8


def canon(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_text(v: Any) -> str:
    return hashlib.sha256(canon(v).encode()).hexdigest()


def _metric_projection(score: dict[str, Any]) -> dict[str, Any]:
    return {
        "primary": score.get("primary"),
        "secondary": score.get("secondary"),
        "rows": score.get("rows"),
    }


def fail(reason: str, detail: Any = None) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "pass": False,
        "terminal": "S1C_V_POSTRUN_AUDIT_FAIL_CLOSED",
        "reason": reason,
        "detail": detail,
        "model_reinference": False,
    }


def audit(runtime: dict[str, Any]) -> dict[str, Any]:
    if runtime.get("protocol") != EXPECTED_RUNTIME_PROTOCOL:
        return fail("RUNTIME_PROTOCOL_MISMATCH", runtime.get("protocol"))
    if runtime.get("terminal") != EXPECTED_TERMINAL:
        return fail("RUNTIME_TERMINAL_MISMATCH", runtime.get("terminal"))

    tasks = generate()
    if len(tasks) != EXPECTED_TASKS:
        return fail("TASK_COUNT_MISMATCH", len(tasks))
    expected_digest = sha_text(tasks)
    if runtime.get("dataset_digest") != expected_digest:
        return fail("DATASET_DIGEST_MISMATCH", {
            "runtime": runtime.get("dataset_digest"),
            "expected": expected_digest,
        })

    task_by_id = {t["task_id"]: t for t in tasks}
    raw_rows = runtime.get("raw_qwen_rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != EXPECTED_TASKS:
        return fail("RAW_ROW_COUNT_MISMATCH", None if not isinstance(raw_rows, list) else len(raw_rows))

    seen: set[str] = set()
    qwen_predictions: dict[str, Any] = {}
    raw_hash_match = 0
    visible_hash_match = 0
    raw_parse_match = 0

    for row in raw_rows:
        if not isinstance(row, dict):
            return fail("RAW_ROW_NOT_OBJECT")
        tid = row.get("task_id")
        if tid not in task_by_id or tid in seen:
            return fail("RAW_TASK_ID_INVALID_OR_DUPLICATE", tid)
        seen.add(tid)
        raw = row.get("raw")
        if not isinstance(raw, str):
            return fail("RAW_TEXT_MISSING", tid)
        if hashlib.sha256(raw.encode()).hexdigest() != row.get("raw_sha256"):
            return fail("RAW_SHA_MISMATCH", tid)
        raw_hash_match += 1

        expected_visible_hash = sha_text(task_by_id[tid]["visible"])
        if row.get("visible_sha256") != expected_visible_hash:
            return fail("VISIBLE_SHA_MISMATCH", tid)
        if runtime.get("visible_hashes", {}).get(tid) != expected_visible_hash:
            return fail("RUNTIME_VISIBLE_SHA_MISMATCH", tid)
        visible_hash_match += 1

        reparsed = None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                reparsed = parsed
        except Exception:
            reparsed = None
        if reparsed != row.get("prediction"):
            return fail("RAW_REPARSE_MISMATCH", tid)
        raw_parse_match += 1
        qwen_predictions[tid] = reparsed

    if seen != set(task_by_id):
        return fail("RAW_TASK_COVERAGE_MISMATCH")

    deterministic_predictions = {
        t["task_id"]: deterministic_predict({"visible": t["visible"]})
        for t in tasks
    }
    deterministic = aggregate(tasks, deterministic_predictions)
    qwen = aggregate(tasks, qwen_predictions)
    if deterministic.get("pass") is not True or qwen.get("pass") is not True:
        return fail("INDEPENDENT_SCORER_FAILED")

    runtime_arms = runtime.get("arms") or {}
    if _metric_projection(deterministic) != _metric_projection(runtime_arms.get("deterministic") or {}):
        return fail("DETERMINISTIC_METRIC_RECOMPUTE_MISMATCH")
    if _metric_projection(qwen) != _metric_projection(runtime_arms.get("qwen25_1p5b") or {}):
        return fail("QWEN_METRIC_RECOMPUTE_MISMATCH")

    keys = (
        "training_partition_pairwise_accuracy",
        "heldout_denotational_assignment_accuracy",
        "exact_discovery_and_grounding_rate",
    )
    expected_delta = {
        k: float(qwen["primary"][k]) - float(deterministic["primary"][k])
        for k in keys
    }
    if runtime.get("primary_deltas_qwen_minus_deterministic") != expected_delta:
        return fail("PRIMARY_DELTA_MISMATCH", {
            "runtime": runtime.get("primary_deltas_qwen_minus_deterministic"),
            "expected": expected_delta,
        })

    preflight = runtime.get("preflight") or {}
    if preflight.get("terminal") != "S1C_V_PREINFERENCE_PASS" or preflight.get("pass") is not True:
        return fail("PREINFERENCE_EVIDENCE_NOT_PASS")

    return {
        "protocol": PROTOCOL,
        "pass": True,
        "terminal": "S1C_V_POSTRUN_AUDIT_PASS",
        "dataset_digest": expected_digest,
        "raw_hash_match": f"{raw_hash_match}/{EXPECTED_TASKS}",
        "visible_hash_match": f"{visible_hash_match}/{EXPECTED_TASKS}",
        "raw_reparse_match": f"{raw_parse_match}/{EXPECTED_TASKS}",
        "metric_recompute_match": True,
        "deterministic": _metric_projection(deterministic),
        "qwen25_1p5b": _metric_projection(qwen),
        "primary_deltas_qwen_minus_deterministic": expected_delta,
        "result_overturning_gate_failures": 0,
        "model_reinference": False,
        "final_branch_authorized": False,
        "required_next_gate": "V_FIXED_B2_CAUSAL_REPLAY",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runtime_json", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    runtime = json.loads(args.runtime_json.read_text(encoding="utf-8"))
    result = audit(runtime)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result.get("pass") else 3


if __name__ == "__main__":
    raise SystemExit(main())
