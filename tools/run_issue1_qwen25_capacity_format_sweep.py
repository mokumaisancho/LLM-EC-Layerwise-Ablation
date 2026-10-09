#!/usr/bin/env python3
"""Same-family model-capacity × GBNF paired probe, exposed dev fixtures only.

This file implements one frozen, two-factor (model size and native formatting
constraint) mechanistic observation, not a scientific independent benchmark.
Gold, private policy, and any local owner secrets are never read.
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

from tools.run_issue1_pinned_smollm_probe import PROMPT_TEMPLATE, run_one, digest
from tests.test_semantic_runtime_v5_grammar import make_field_task
from tools.run_issue1_native_grammar_ablation import GRAMMAR

MODELS = {
    "qwen25_0p5b": {
        "filename": "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf",
        "repo": "bartowski/Qwen2.5-0.5B-Instruct-GGUF",
        "revision": "41ba88dbac95fed2528c92514c131d73eb5a174b",
        "sha256": "6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653",
        "size_bytes": 397808192,
    },
    "qwen25_1p5b": {
        "filename": "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        "repo": "bartowski/Qwen2.5-1.5B-Instruct-GGUF",
        "revision": "9eadc66189c7641e1ddd226b8267a9119b2ce2d4",
        "sha256": "1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370",
        "size_bytes": 986048768,
    },
}
TREATMENTS = ("unconstrained", "native_gbnf")
CONTRACT = {
    "benchmark": "EXPOSED_H01_H16_ONLY",
    "model_architecture": "Qwen2.5 Instruct (distinct model sizes, not identical weights)",
    "prompt": "byte-identical across sizes and grammar treatments",
    "decode": {"seed": 0, "temp": 0, "threads": 4, "n_gpu_layers": 0, "max_new_tokens": 16},
    "grammar": GRAMMAR,
    "no_prompt_selection_on_results": True,
    "non_independent_external_gold": True,
    "scientific_performance_certification": False,
}


def verify(path: Path, expected: dict) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size != expected["size_bytes"]:
        raise ValueError("MODEL_MISSING_OR_WRONG_BYTES:" + expected["filename"])
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for b in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            hasher.update(b)
    if hasher.hexdigest() != expected["sha256"]:
        raise ValueError("MODEL_PIN_MISMATCH:" + expected["filename"])


def run(model_dir: Path, llama: Path, seconds: int, *, head: str) -> dict:
    if not llama.is_file():
        raise ValueError("LLAMA_CLI_MISSING")
    model_paths = {name: model_dir / conf["filename"] for name, conf in MODELS.items()}
    for name, model in model_paths.items():
        verify(model, MODELS[name])
    public = make_field_task()
    cases = public["visible"]["heldout_examples"]
    if len(cases) != 16 or len({c["example_id"] for c in cases}) != 16:
        raise ValueError("DEV_CASES_CHANGED")
    results = []
    for row in cases:
        raw = row["raw_text"]
        prompt = PROMPT_TEMPLATE.format(input=raw)
        case_entry = {
            "case_id": row["example_id"],
            "input_sha256": digest(raw.encode()),
            "prompt_sha256": digest(prompt.encode()),
            "cells": {},
        }
        for name in MODELS:
            one_model = {}
            for treatment in TREATMENTS:
                item = run_one(
                    llama, model_paths[name], prompt,
                    seconds=seconds,
                    grammar=GRAMMAR if treatment == "native_gbnf" else None,
                )
                one_model[treatment] = {
                    "raw_response": item["raw_response"],
                    "parsed_action": item["parsed_action"],
                    "stdout_sha256": item["full_cli_stdout_sha256"],
                    "stderr_sha256": item["raw_stderr_sha256"],
                }
                if treatment == "native_gbnf" and item["parsed_action"] not in {"OPEN","CLOSE","ABSTAIN"}:
                    raise ValueError("GBNF_FORMAT_FAILED:" + name + ":" + row["example_id"])
            case_entry["cells"][name] = one_model
        results.append(case_entry)
    aggregate = {}
    for model in MODELS:
        aggregate[model] = {}
        for treatment in TREATMENTS:
            raw_rows = [case["cells"][model][treatment] for case in results]
            aggregate[model][treatment] = {
                "label_format_compliant": sum(x["parsed_action"] in {"OPEN", "CLOSE", "ABSTAIN"} for x in raw_rows),
                "format_error": sum(x["parsed_action"] == "FORMAT_ERROR" for x in raw_rows),
                "action_counts": {
                    action: sum(x["parsed_action"] == action for x in raw_rows)
                    for action in ("OPEN","CLOSE","ABSTAIN","FORMAT_ERROR")
                },
                "distinct_raw_response_count": len({x["raw_response"] for x in raw_rows}),
            }
    return {
        "protocol": "ISSUE1_QWEN25_CAPACITY_FORMAT_TWO_FACTOR_REAL_DEV_V1",
        "research_source_commit": head,
        "source": CONTRACT,
        "model_pins": MODELS,
        "llama_cpp_binary_sha256": hashlib.sha256(llama.read_bytes()).hexdigest(),
        "test_cases_sha256": digest(json.dumps(public,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()),
        "prompt_template_sha256": digest(PROMPT_TEMPLATE.encode()),
        "runtime": {"actual_inference": True, "model_count": 2, "treatment_count": 2,
                    "cases_per_cell": 16, "expected_total_model_invocations": 64},
        "observations": aggregate,
        "paired_cases": results,
        "independent_corpus": False,
        "original_llm0_research_definition": "NOT_ESTABLISHED",
        "genuine_v4_authorized": False,
        "scientific_four_arm_study": "NOT_RUN",
        "model_size_only_causal_inference": "NOT_ESTABLISHED: DIFFERENT_WEIGHT_FAMILIES_WITHIN_QWEN2.5",
        "terminal": "REAL_SAME_FAMILY_CAPACITY_FORMAT_DIAGNOSTIC_DONE_SCIENTIFIC_STUDY_OPEN",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", type=Path, required=True)
    ap.add_argument("--llama-cli", type=Path, required=True)
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--timeout-per-case", type=int, default=60)
    a = ap.parse_args()
    try:
        print(json.dumps(run(a.model_dir, a.llama_cli,
                             a.timeout_per_case, head=a.source_commit),
                         ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception as ex:
        print(json.dumps({"protocol":"ISSUE1_QWEN25_CAPACITY_FORMAT_TWO_FACTOR_REAL_DEV_V1",
                          "terminal":"FAIL_CLOSED","error":type(ex).__name__ + ":" + str(ex)[:500]}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
