#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from generate_s1c_r_holdout import generate
from s1c_r_deterministic_grounder import predict as deterministic_predict
from score_s1c_r_typed_ir import score_rows

PROTOCOL = "S1C_R_POSTRUN_AUDIT_V1"
EXPECTED_RUNTIME_PROTOCOL = "FUNCTION_BOUNDARY_S1C_R_PAIRED_V1"
EXPECTED_TERMINAL = "R_PAIRED_METRICS_READY_AUDIT_REQUIRED"
EXPECTED_FIXTURES = 16
EXPECTED_FAMILIES = 8


def canon(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_text(v: Any) -> str:
    return hashlib.sha256(canon(v).encode()).hexdigest()


def _metric_projection(score: dict[str, Any]) -> dict[str, Any]:
    return {
        "primary": score.get("primary"),
        "secondary": score.get("secondary"),
        "valid_prediction_rate": score.get("valid_prediction_rate"),
        "invalid_prediction_count": score.get("invalid_prediction_count"),
        "reason_counts": score.get("reason_counts"),
        "per_family": score.get("per_family"),
        "rows": score.get("rows"),
    }


def fail(reason: str, detail: Any = None) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "pass": False,
        "terminal": "S1C_R_POSTRUN_AUDIT_FAIL_CLOSED",
        "reason": reason,
        "detail": detail,
        "model_reinference": False,
    }


def audit(runtime: dict[str, Any]) -> dict[str, Any]:
    if runtime.get("protocol") != EXPECTED_RUNTIME_PROTOCOL:
        return fail("RUNTIME_PROTOCOL_MISMATCH", runtime.get("protocol"))
    if runtime.get("terminal") != EXPECTED_TERMINAL:
        return fail("RUNTIME_TERMINAL_MISMATCH", runtime.get("terminal"))

    fixtures = generate()
    if len(fixtures) != EXPECTED_FIXTURES:
        return fail("FIXTURE_COUNT_MISMATCH", len(fixtures))
    if len({f["family"] for f in fixtures}) != EXPECTED_FAMILIES:
        return fail("FAMILY_COUNT_MISMATCH")

    expected_digest = sha_text(fixtures)
    if runtime.get("holdout_digest") != expected_digest:
        return fail("HOLDOUT_DIGEST_MISMATCH", {
            "runtime": runtime.get("holdout_digest"),
            "expected": expected_digest,
        })

    fixture_by_id = {f["id"]: f for f in fixtures}
    raw_rows = runtime.get("raw_qwen_rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != EXPECTED_FIXTURES:
        return fail("RAW_ROW_COUNT_MISMATCH", None if not isinstance(raw_rows, list) else len(raw_rows))

    seen: set[str] = set()
    qwen_predictions: dict[str, Any] = {}
    raw_hash_match = 0
    visible_hash_match = 0
    raw_parse_match = 0
    for row in raw_rows:
        if not isinstance(row, dict):
            return fail("RAW_ROW_NOT_OBJECT")
        fid = row.get("fixture_id")
        if fid not in fixture_by_id or fid in seen:
            return fail("RAW_FIXTURE_ID_INVALID_OR_DUPLICATE", fid)
        seen.add(fid)
        raw = row.get("raw")
        if not isinstance(raw, str):
            return fail("RAW_TEXT_MISSING", fid)
        got_raw_hash = hashlib.sha256(raw.encode()).hexdigest()
        if got_raw_hash != row.get("raw_sha256"):
            return fail("RAW_SHA_MISMATCH", fid)
        raw_hash_match += 1

        expected_visible_hash = sha_text(fixture_by_id[fid]["visible"])
        if row.get("visible_sha256") != expected_visible_hash:
            return fail("VISIBLE_SHA_MISMATCH", fid)
        if runtime.get("visible_hashes", {}).get(fid) != expected_visible_hash:
            return fail("RUNTIME_VISIBLE_SHA_MISMATCH", fid)
        visible_hash_match += 1

        reparsed = None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                reparsed = parsed
        except Exception:
            reparsed = None
        if reparsed != row.get("prediction"):
            return fail("RAW_REPARSE_MISMATCH", fid)
        raw_parse_match += 1
        qwen_predictions[fid] = reparsed

    if seen != set(fixture_by_id):
        return fail("RAW_FIXTURE_COVERAGE_MISMATCH")

    deterministic_predictions = {
        f["id"]: deterministic_predict({"visible": f["visible"]})
        for f in fixtures
    }
    deterministic = score_rows(fixtures, deterministic_predictions)
    qwen = score_rows(fixtures, qwen_predictions)
    if deterministic.get("pass") is not True or qwen.get("pass") is not True:
        return fail("INDEPENDENT_SCORER_FAILED")

    runtime_arms = runtime.get("arms") or {}
    if _metric_projection(deterministic) != _metric_projection(runtime_arms.get("deterministic") or {}):
        return fail("DETERMINISTIC_METRIC_RECOMPUTE_MISMATCH")
    if _metric_projection(qwen) != _metric_projection(runtime_arms.get("qwen25_1p5b") or {}):
        return fail("QWEN_METRIC_RECOMPUTE_MISMATCH")

    expected_delta = {
        "semantic_slot_accuracy": float(qwen["primary"]["semantic_slot_accuracy"]) - float(deterministic["primary"]["semantic_slot_accuracy"]),
        "exact_typed_ir_rate": float(qwen["primary"]["exact_typed_ir_rate"]) - float(deterministic["primary"]["exact_typed_ir_rate"]),
    }
    if runtime.get("primary_deltas_qwen_minus_deterministic") != expected_delta:
        return fail("PRIMARY_DELTA_MISMATCH", {
            "runtime": runtime.get("primary_deltas_qwen_minus_deterministic"),
            "expected": expected_delta,
        })

    preflight = runtime.get("preflight") or {}
    if preflight.get("terminal") != "S1C_R_PREINFERENCE_PASS" or preflight.get("pass") is not True:
        return fail("PREINFERENCE_EVIDENCE_NOT_PASS")

    return {
        "protocol": PROTOCOL,
        "pass": True,
        "terminal": "S1C_R_POSTRUN_AUDIT_PASS",
        "holdout_digest": expected_digest,
        "raw_hash_match": f"{raw_hash_match}/{EXPECTED_FIXTURES}",
        "visible_hash_match": f"{visible_hash_match}/{EXPECTED_FIXTURES}",
        "raw_reparse_match": f"{raw_parse_match}/{EXPECTED_FIXTURES}",
        "metric_recompute_match": True,
        "deterministic": _metric_projection(deterministic),
        "qwen25_1p5b": _metric_projection(qwen),
        "primary_deltas_qwen_minus_deterministic": expected_delta,
        "result_overturning_gate_failures": 0,
        "model_reinference": False,
        "final_branch_authorized": False,
        "required_next_gate": "R11_FIXED_B2_CAUSAL_REPLAY",
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
