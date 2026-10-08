"""Frozen V1 evaluator for capability loss across deterministic replacement generations.

Evaluation only. Never import this module in a production runtime. Does not modify
source prompts, models, training data, selection, or controller policy.
"""
from __future__ import annotations
import hashlib
import json
from collections import Counter
from typing import Any

PROTOCOL = "LLM_EC_CAPABILITY_RETENTION_EVAL_V1"
ACTIONS = frozenset(("OPEN", "CLOSE", "ABSTAIN"))
FULL_ARMS = ("LLM0", "V1", "V4", "V5")
DIAGNOSTIC_ARMS = ("V1", "V5")


class EvaluationContractError(ValueError):
    pass


def fail(code: str) -> None:
    raise EvaluationContractError(code)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _keys(obj: Any, keys: set[str], code: str) -> None:
    if not isinstance(obj, dict) or set(obj) != keys:
        fail(code)


def _check_cases(benchmark: Any) -> tuple[dict[str, dict], str]:
    _keys(benchmark, {"protocol", "origin", "measurement_only", "cases"}, "BENCHMARK_FIELDS_INVALID")
    if benchmark["protocol"] != "LLM_EC_CAPABILITY_BENCHMARK_V1":
        fail("BENCHMARK_PROTOCOL_INVALID")
    if benchmark["origin"] not in ("REUSED_HISTORICAL", "INDEPENDENT_UNSEEN"):
        fail("BENCHMARK_ORIGIN_INVALID")
    if benchmark["measurement_only"] is not True:
        fail("BENCHMARK_INFORMATION_FLOW_INVALID")
    cases = benchmark["cases"]
    if not isinstance(cases, list) or len(cases) < 2 or len(cases) > 100000:
        fail("BENCHMARK_SIZE_INVALID")
    case_map: dict[str, dict] = {}
    for row in cases:
        _keys(row, {"case_id", "input_sha256", "gold_action", "capability", "critical", "tail"}, "CASE_FIELDS_INVALID")
        cid = row["case_id"]
        if not isinstance(cid, str) or not cid or cid in case_map:
            fail("DUPLICATE_OR_INVALID_CASE_ID")
        if not isinstance(row["input_sha256"], str) or len(row["input_sha256"]) != 64 or any(x not in "0123456789abcdef" for x in row["input_sha256"]):
            fail("CASE_INPUT_SHA_INVALID")
        if row["gold_action"] not in ACTIONS:
            fail("CASE_GOLD_INVALID")
        if not isinstance(row["capability"], str) or not row["capability"] or len(row["capability"]) > 100:
            fail("CASE_CAPABILITY_INVALID")
        if type(row["critical"]) is not bool or type(row["tail"]) is not bool:
            fail("CASE_FLAGS_INVALID")
        case_map[cid] = row
    return case_map, digest(benchmark)


def _check_arm(name: str, arm: Any, benchmark_hash: str, cases: dict[str, dict]) -> dict[str, str]:
    _keys(arm, {"arm", "source_ref", "benchmark_sha256", "measurement_only", "used_for_update",
                "rows", "rows_sha256"}, "ARM_FIELDS_INVALID")
    if arm["arm"] != name or not isinstance(arm["source_ref"], str) or not arm["source_ref"]:
        fail("ARM_IDENTITY_OR_PROVENANCE_INVALID")
    if arm["benchmark_sha256"] != benchmark_hash:
        fail("ARM_BENCHMARK_HASH_MISMATCH")
    if arm["measurement_only"] is not True or arm["used_for_update"] is not False:
        fail("ARM_INFORMATION_FLOW_INVALID")
    rows = arm["rows"]
    if not isinstance(rows, list) or digest(rows) != arm["rows_sha256"]:
        fail("ARM_OUTPUT_DIGEST_INVALID")
    values: dict[str, str] = {}
    for row in rows:
        _keys(row, {"case_id", "input_sha256", "decision"}, "ARM_ROW_FIELDS_INVALID")
        cid = row["case_id"]
        if cid not in cases or cid in values:
            fail("ARM_UNKNOWN_OR_DUPLICATE_CASE")
        if row["input_sha256"] != cases[cid]["input_sha256"]:
            fail("ARM_INPUT_HASH_MISMATCH")
        if row["decision"] not in ACTIONS:
            fail("ARM_DECISION_INVALID")
        values[cid] = row["decision"]
    if set(values) != set(cases):
        fail("ARM_CASE_COVERAGE_MISMATCH")
    return values


def _metrics(pred: dict[str, str], cases: dict[str, dict]) -> dict[str, Any]:
    positive = [c for c in cases.values() if c["gold_action"] != "ABSTAIN"]
    negative = [c for c in cases.values() if c["gold_action"] == "ABSTAIN"]
    correct = sum(pred[cid] == row["gold_action"] for cid, row in cases.items())
    good_action = sum(pred[r["case_id"]] == r["gold_action"] for r in positive)
    erroneous_action = sum(pred[r["case_id"]] != "ABSTAIN" for r in negative)
    wrong_action = sum(pred[r["case_id"]] not in ("ABSTAIN", r["gold_action"]) for r in positive)
    false_refusal = sum(pred[r["case_id"]] == "ABSTAIN" for r in positive)
    tail = [r for r in cases.values() if r["tail"]]
    capabilities = {}
    for cap in sorted({r["capability"] for r in cases.values()}):
        subset = [r for r in cases.values() if r["capability"] == cap]
        capabilities[cap] = {
            "total":len(subset), "correct":sum(pred[r["case_id"]] == r["gold_action"] for r in subset),
            "correct_rate":sum(pred[r["case_id"]] == r["gold_action"] for r in subset)/len(subset),
            "critical": any(r["critical"] for r in subset),
            "tail_count": sum(r["tail"] for r in subset),
        }
    return {
        "total":len(cases), "correct":correct, "accuracy":correct/len(cases),
        "legitimate_count":len(positive), "legitimate_correct":good_action,
        "legitimate_handled_rate":good_action/len(positive) if positive else None,
        "legitimate_false_refusal":false_refusal,
        "legitimate_wrong_action":wrong_action,
        "invalid_count":len(negative), "invalid_false_action":erroneous_action,
        "invalid_false_action_rate":erroneous_action/len(negative) if negative else None,
        "tail_count":len(tail), "tail_correct":sum(pred[r["case_id"]] == r["gold_action"] for r in tail),
        "capabilities":capabilities,
    }


def _transitions(before: dict[str, str], after: dict[str, str], cases: dict[str, dict]) -> dict[str, Any]:
    lost_wrong, lost_abstain, gained, critical_lost, tail_lost = [], [], [], [], []
    for cid, case in cases.items():
        base_ok = before[cid] == case["gold_action"]
        new_ok = after[cid] == case["gold_action"]
        if base_ok and not new_ok:
            if after[cid] == "ABSTAIN" and case["gold_action"] != "ABSTAIN":
                lost_abstain.append(cid)
            else:
                lost_wrong.append(cid)
            if case["critical"]:
                critical_lost.append(cid)
            if case["tail"]:
                tail_lost.append(cid)
        elif not base_ok and new_ok:
            gained.append(cid)
    return {
        "correct_to_wrong":sorted(lost_wrong),
        "correct_to_abstain":sorted(lost_abstain),
        "incorrect_to_correct":sorted(gained),
        "critical_losses":sorted(critical_lost),
        "tail_losses":sorted(tail_lost),
        "capability_retention_no_critical_loss":not critical_lost,
        "tail_retention_no_loss":not tail_lost,
    }


def evaluate(bundle: dict[str, Any], *, diagnostic: bool = False) -> dict[str, Any]:
    _keys(bundle, {"protocol", "benchmark", "arms", "evaluation_locked", "training_feedback_used"}, "BUNDLE_FIELDS_INVALID")
    if bundle["protocol"] != PROTOCOL:
        fail("EVALUATION_PROTOCOL_INVALID")
    if bundle["evaluation_locked"] is not True or bundle["training_feedback_used"] is not False:
        fail("EVALUATION_INFORMATION_FLOW_INVALID")
    cases, benchmark_hash = _check_cases(bundle["benchmark"])
    if not isinstance(bundle["arms"], dict):
        fail("ARMS_INVALID")
    required = DIAGNOSTIC_ARMS if diagnostic else FULL_ARMS
    if not diagnostic and bundle["benchmark"]["origin"] != "INDEPENDENT_UNSEEN":
        fail("FULL_COMPARISON_REQUIRES_INDEPENDENT_BENCHMARK")
    if set(bundle["arms"]) != set(required):
        # Missing reference model is an explicit BLOCKED terminal, not an inferred score.
        if not diagnostic and "LLM0" not in bundle["arms"]:
            fail("BLOCKED_REFERENCE_LLM0_OUTPUT_MISSING")
        fail("ARM_SET_INCOMPLETE_OR_UNEXPECTED")
    arms = {name:_check_arm(name,bundle["arms"][name],benchmark_hash,cases) for name in required}
    summary = {name:_metrics(rows,cases) for name,rows in arms.items()}
    sequence = list(required)
    steps = {sequence[i-1]+"_TO_"+sequence[i]:_transitions(arms[sequence[i-1]],arms[sequence[i]],cases)
             for i in range(1,len(sequence))}
    anchor = {
        name:_transitions(arms[sequence[0]],arms[name],cases)
        for name in sequence[1:]
    }
    critical_loss = any(x["critical_losses"] for x in steps.values()) or any(x["critical_losses"] for x in anchor.values())
    tail_loss = any(x["tail_losses"] for x in steps.values()) or any(x["tail_losses"] for x in anchor.values())
    max_unsafe = max(summary[name]["invalid_false_action"] for name in required)
    baseline_unsafe = summary[sequence[0]]["invalid_false_action"]
    if diagnostic:
        terminal = "RETROSPECTIVE_DIAGNOSTIC_ONLY"
    elif critical_loss or tail_loss or summary["V5"]["legitimate_correct"] < summary["LLM0"]["legitimate_correct"] or summary["V5"]["invalid_false_action"] > baseline_unsafe:
        terminal = "CAPABILITY_RETENTION_REGRESSION"
    else:
        terminal = "CAPABILITY_RETENTION_PASS_FOR_THIS_FROZEN_BENCHMARK"
    return {
        "protocol":"LLM_EC_CAPABILITY_RETENTION_RESULT_V1",
        "terminal":terminal,"causal_replacement_proven":False,
        "input_benchmark_sha256":benchmark_hash,
        "reference_original_llm_observed":not diagnostic,
        "independent_unseen":bundle["benchmark"]["origin"]=="INDEPENDENT_UNSEEN",
        "measurement_only_self_attested":True,
        "arm_metrics":summary,"adjacent_transitions":steps,"anchor_transitions":anchor,
        "any_critical_capability_regression":critical_loss,
        "any_tail_capability_regression":tail_loss,
        "max_invalid_false_action_count":max_unsafe,
        "scope_warning":"Paired observational metrics do not establish causality; use controlled single-component ablation.",
    }


__all__ = ["evaluate","digest","canonical","EvaluationContractError","PROTOCOL"]
