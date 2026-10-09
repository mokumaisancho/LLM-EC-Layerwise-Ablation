#!/usr/bin/env python3
"""Same-model, same-input, same-prompt constrained-output control experiment.

This is deliberately a grammar-format ablation against already witnessed
development-fixture model output. Never interpret output validity as intent
correctness, independent gold, genuine V4 or EC replacement non-degradation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_semantic_runtime_v5_grammar import make_field_task
from tools.run_issue1_pinned_smollm_probe import (
    EXPECTED_MODEL_SHA256, LABELS, PROMPT_TEMPLATE, digest, run_one, verify_model,
)

GRAMMAR = 'root ::= "OPEN" | "CLOSE" | "ABSTAIN"'
BASELINE = ROOT / "results/issue1_sha_pinned_smollm_actual_dev_2026-10-09.json"
BASELINE_PROTOCOL = "ISSUE1_ACTUAL_SHA_PINNED_REFERENCE_INFERENCE_DEVELOPMENT_DIAGNOSTIC_V1"


def load_baseline(path: Path, *, model_sha: str, cli_sha: str) -> dict:
    original = json.loads(path.read_text(encoding="utf-8"))
    if original.get("protocol") != BASELINE_PROTOCOL:
        raise ValueError("BASELINE_PROTOCOL_MISMATCH")
    if original.get("model", {}).get("file_sha256") != model_sha:
        raise ValueError("BASELINE_MODEL_SHA_MISMATCH")
    if original.get("runtime", {}).get("llama_cpp_binary_sha256") != cli_sha:
        raise ValueError("BASELINE_LLAMA_CPP_BINARY_SHA_MISMATCH")
    if original.get("prompt_sha256") != digest(PROMPT_TEMPLATE.encode()):
        raise ValueError("BASELINE_PROMPT_DRIFT")
    observations = original.get("observations", {})
    if observations.get("cases") != 16 or observations.get("repeat_raw_response_equal_count") != 16:
        raise ValueError("BASELINE_REPEAT_NOT_VERIFIED")
    if original.get("limits", {}).get("dev_fixture_seen") is not True:
        raise ValueError("BASELINE_STATUS_NOT_DEVELOPMENT")
    data = original.get("per_case", [])
    if not isinstance(data, list) or len(data) != 16 or len({v["case_id"] for v in data}) != 16:
        raise ValueError("BASELINE_CASE_COVERAGE_INVALID")
    return original


def run(model: Path, llama: Path, seconds: int, baseline: Path) -> dict:
    pin = verify_model(model)
    if not llama.is_file():
        raise ValueError("LLAMA_CLI_NOT_FOUND")
    binary_digest = hashlib.sha256(llama.read_bytes()).hexdigest()
    baseline_data = load_baseline(baseline, model_sha=pin["file_sha256"], cli_sha=binary_digest)
    earlier = {x["case_id"]: x for x in baseline_data["per_case"]}
    task = make_field_task()
    cases = task["visible"]["heldout_examples"]
    if len(cases) != len(earlier) or {x["example_id"] for x in cases} != set(earlier):
        raise ValueError("BASELINE_TASK_CHANGED")
    rows = []
    for fixture in cases:
        cid = fixture["example_id"]
        text = fixture["raw_text"]
        prompt = PROMPT_TEMPLATE.format(input=text)
        before = earlier[cid]
        if before["prompt_sha256"] != digest(prompt.encode()) or before["input_sha256"] != digest(text.encode()):
            raise ValueError("UPSTREAM_INPUT_OR_PROMPT_NOT_IDENTICAL:" + cid)
        # Exactly ONE intervention: native output GBNF; rest of the CLI args
        # stay identical to the unconstrained frozen run.
        actual = run_one(llama, model, prompt, seconds=seconds, grammar=GRAMMAR)
        if actual["parsed_action"] not in LABELS:
            raise ValueError("NATIVE_GBNF_FORMAT_NOT_ENFORCED:" + cid)
        previous = before["model_strict_parsed_action"]
        if previous not in LABELS | {"FORMAT_ERROR"}:
            raise ValueError("BASELINE_LABEL_INVALID:" + cid)
        rows.append({
            "case_id": cid,
            "input_sha256": before["input_sha256"],
            "prompt_sha256": before["prompt_sha256"],
            "unconstrained_real_raw_response": before["model_raw_response"],
            "unconstrained_parsed_action": previous,
            "native_grammar_raw_response": actual["raw_response"],
            "native_grammar_parsed_action": actual["parsed_action"],
            "response_changed": actual["raw_response"] != before["model_raw_response"],
            "both_well_formed_action_flipped": (
                previous in LABELS and actual["parsed_action"] != previous
            ),
            "format_error_repaired": previous == "FORMAT_ERROR",
            "grammar_stdout_sha256": actual["full_cli_stdout_sha256"],
            "grammar_stdout_bytes": actual["full_cli_stdout_bytes"],
        })
    return {
        "protocol": "ISSUE1_NATIVE_GBNF_SOLE_VARIABLE_FORMAT_ABLATION_V1",
        "source": "EXPOSED_DEVELOPMENT_FIXTURE_H01_H16",
        "model": pin,
        "runtime": {
            "llama_cpp_binary_sha256": binary_digest,
            "temperature": 0, "seed": 0, "threads": 4,
            "n_gpu_layers": 0, "max_new_tokens": 16,
            "single_turn": True,
            "one_changed_argument": "--grammar",
        },
        "baseline_evidence": str(baseline.relative_to(ROOT)) if baseline.is_relative_to(ROOT) else str(baseline),
        "intervention": {"type": "NATIVE_GBNF_OUTPUT_CONSTRAINT",
                         "grammar": GRAMMAR,
                         "grammar_sha256": digest(GRAMMAR.encode()),
                         "semantic_grounder_unchanged": True,
                         "prompt_bytes_unchanged": True,
                         "model_bytes_unchanged": True,
                         "runtime_flags_except_grammar_unchanged": True},
        "pair_count": len(rows),
        "format_validity_before": sum(x["unconstrained_parsed_action"] in LABELS for x in rows),
        "format_validity_after": sum(x["native_grammar_parsed_action"] in LABELS for x in rows),
        "format_error_repaired_count": sum(x["format_error_repaired"] for x in rows),
        "full_raw_response_changed_count": sum(x["response_changed"] for x in rows),
        "well_formed_action_flips": sum(x["both_well_formed_action_flipped"] for x in rows),
        "paired_cases": rows,
        "read_private_gold": False,
        "independent_blind": False,
        "semantic_accuracy_established": False,
        "genuine_v4_authorized": False,
        "scientific_four_arm_study": "NOT_RUN",
        "non_degradation_established": False,
        "interpretation": "An isolated formatting constraint can improve syntax compliance, but provides no independent evidence of correctness, judgment preservation, or safety.",
        "terminal": "FORMAT_GBNF_ABLATION_ACTUAL_DIAGNOSTIC_ONLY"
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--llama-cli", required=True, type=Path)
    p.add_argument("--baseline", type=Path, default=BASELINE)
    p.add_argument("--seconds", type=int, default=35)
    a = p.parse_args()
    try:
        result = run(a.model, a.llama_cli, a.seconds, a.baseline)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"protocol": "ISSUE1_NATIVE_GBNF_SOLE_VARIABLE_FORMAT_ABLATION_V1",
                          "terminal": "FAIL_CLOSED",
                          "reason_code": type(exc).__name__, "detail": str(exc)[:500]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
