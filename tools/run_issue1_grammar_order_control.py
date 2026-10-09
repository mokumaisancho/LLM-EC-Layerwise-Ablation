#!/usr/bin/env python3
"""Order-permutation control for native GBNF (three predeclared development cases).

Uses the same source-pinned actual GGUF and byte-identical prompts. It is not
a gold-blind correctness trial; it distinguishes simple grammar-alternative
enumeration order from the observed persistent OPEN output.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from tests.test_semantic_runtime_v5_grammar import make_field_task
from tools.run_issue1_pinned_smollm_probe import (
    LABELS, PROMPT_TEMPLATE, digest, run_one, verify_model,
)

CASES = ("H02", "H12", "H15")
ALTERNATIVES = {
    "OPEN_FIRST": 'root ::= "OPEN" | "CLOSE" | "ABSTAIN"',
    "ABSTAIN_FIRST": 'root ::= "ABSTAIN" | "CLOSE" | "OPEN"',
    "CLOSE_FIRST": 'root ::= "CLOSE" | "OPEN" | "ABSTAIN"',
}


def run(model: Path, llama: Path) -> dict:
    pin = verify_model(model)
    binary_sha256 = hashlib.sha256(llama.read_bytes()).hexdigest()
    inventory = {row["example_id"]: row["raw_text"]
                 for row in make_field_task()["visible"]["heldout_examples"]}
    outputs = []
    for case_id in CASES:
        prompt = PROMPT_TEMPLATE.format(input=inventory[case_id])
        actions = {}
        for treatment, grammar in ALTERNATIVES.items():
            actual = run_one(llama, model, prompt, seconds=35, grammar=grammar)
            if actual["parsed_action"] not in LABELS:
                raise RuntimeError("GRAMMAR_CONTROL_GENERATED_INVALID_ACTION:" + case_id)
            actions[treatment] = {
                "grammar_sha256": digest(grammar.encode()),
                "raw": actual["raw_response"],
                "action": actual["parsed_action"],
                "stdout_sha256": actual["full_cli_stdout_sha256"],
            }
        outputs.append({
            "case_id": case_id, "prompt_sha256": digest(prompt.encode()),
            "raw_input_sha256": digest(inventory[case_id].encode()),
            "permutation_count": len(actions), "actions": actions,
            "all_permutations_equal": len({v["raw"] for v in actions.values()}) == 1,
        })
    return {
        "protocol": "ISSUE1_GBNF_ALTERNATIVE_ORDER_CONTROL_ACTUAL_V1",
        "case_count": len(outputs), "runs": len(CASES) * len(ALTERNATIVES),
        "source": "EXPOSED_DEVELOPMENT_FIXTURE_NOT_SCIENTIFIC_GOLD",
        "model": pin, "llama_cpp_binary_sha256": binary_sha256,
        "permutation_manifest": ALTERNATIVES,
        "prompt_template_sha256": digest(PROMPT_TEMPLATE.encode()),
        "results": outputs,
        "order_invariance_on_selected_cases": all(x["all_permutations_equal"] for x in outputs),
        "semantic_correctness_established": False,
        "overall_order_independence_across_all_cases": "NOT_TESTED",
        "terminal": "LOCAL_CONTROL_DONE_INDEPENDENT_GOLD_REQUIRED"
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--llama-cli", type=Path, required=True)
    args = ap.parse_args()
    try:
        print(json.dumps(run(args.model, args.llama_cli), indent=2, sort_keys=True,
                         ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"protocol": "ISSUE1_GBNF_ALTERNATIVE_ORDER_CONTROL_ACTUAL_V1",
                          "terminal": "FAIL_CLOSED", "error": str(exc)[:500]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
