#!/usr/bin/env python3
"""Development-fixture-only V1-grounder vs V5 strict grammar diagnostic.

Not four-arm evidence, not unseen holdout, not a semantic correctness study.
A bypassed grammar here is a *computed counterfactual*, not an authorized
V5 policy installation, and must never execute actions.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from semantic_runtime import discover_and_ground
from semantic_runtime.constrained_v5 import classify_explicit
from tests.test_semantic_runtime_v5_grammar import make_field_task, make_grammar

def stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(stable(value).encode()).hexdigest()

def main():
    task, grammar = make_field_task(), make_grammar()
    upstream1 = discover_and_ground(task)
    upstream2 = discover_and_ground(task)
    if stable(upstream1) != stable(upstream2):
        raise AssertionError("UPSTREAM_NOT_REPRODUCIBLE")
    v5 = classify_explicit(task, grammar)
    decisions = {x["example_id"]: x for x in v5["decisions"]}
    inputs = {x["example_id"]: x for x in task["visible"]["heldout_examples"]}
    if len(inputs) != 16 or set(decisions) != set(inputs):
        raise AssertionError("V5_COVERAGE_DRIFT")
    slots = {frozenset(s["training_members"]): s["slot_id"]
             for s in upstream1["discovered_slots"]}
    opening = slots[frozenset(("T01", "T02"))]
    closing = slots[frozenset(("T03", "T04"))]
    slot_action = {opening: "OPEN", closing: "CLOSE"}
    upstream = {x["example_id"]: x for x in upstream1["heldout_assignments"]}
    if not set(upstream) <= set(inputs):
        raise AssertionError("UNKNOWN_UPSTREAM_CASE")
    cases = []
    for cid in sorted(inputs):
        a = upstream.get(cid)
        bypass = (slot_action.get(a["slot_id"], "ABSTAIN")
                  if a is not None and a["polarity"] == "POS"
                  and a["modality"] == "ASSERTED" else None if a is None else "ABSTAIN")
        item = decisions[cid]
        strict = slot_action.get(item["slot_id"], "ABSTAIN") if item["status"] == "EXPLICIT_MATCH" else "ABSTAIN"
        if strict != "ABSTAIN" and strict != bypass:
            raise AssertionError("STRICT_GATE_CHANGED_UPSTREAM_ACTION:" + cid)
        cases.append({
            "case_id": cid,
            "raw_text": inputs[cid]["raw_text"],
            "upstream_available": a is not None,
            "bypass_grammar_only_counterfactual": bypass if a is not None else "UPSTREAM_MISSING",
            "strict_v5": strict,
            "strict_status": item["status"],
            "difference": a is not None and strict != bypass,
        })
    changed = [x["case_id"] for x in cases if x["difference"]]
    missing = [x["case_id"] for x in cases if not x["upstream_available"]]
    h10 = next(x for x in cases if x["case_id"] == "H10")
    if h10["bypass_grammar_only_counterfactual"] != "OPEN" or h10["strict_v5"] != "ABSTAIN":
        raise AssertionError("EXPECTED_H10_GATE_WITNESS_CHANGED")
    if set(missing) != {"H04", "H15"}:
        raise AssertionError("UPSTREAM_COVERAGE_DRIFT")
    # Japanese counterfactuals show H07 accidental OPEN caused by ASCII-only semantics.
    japanese = {}
    for label, example in {
        "start": "Claim K を審査開始する",
        "end": "Claim K を審査終了する",
        "nonsense": "Claim K よくわからない",
        "random": "Claim K xyzqvblp",
    }.items():
        t = make_field_task()
        for row in t["visible"]["heldout_examples"]:
            if row["example_id"] == "H07":
                row["raw_text"] = example
                break
        assignments = discover_and_ground(t)["heldout_assignments"]
        selected = next((a for a in assignments if a["example_id"] == "H07"), None)
        japanese[label] = None if selected is None else {
            "slot_id": selected["slot_id"], "polarity": selected["polarity"], "modality": selected["modality"]
        }
    if len({stable(v) for v in japanese.values()}) != 1:
        raise AssertionError("JAPANESE_TOKENIZER_FAILURE_NOT_REPRODUCED")
    report = {
        "protocol": "ISSUE57_V5_GRAMMAR_SUBTRACTION_DIAGNOSTIC_V1",
        "source": "EXPOSED_HISTORICAL_DEVELOPMENT_FIXTURE",
        "independent_holdout": False,
        "original_llm0_observed": False,
        "v4_authorized_observed": False,
        "gold_used": False,
        "method": "same frozen task, entity registries, ontology, and upstream V1 output; strict V5 classify_explicit vs offline bypass of grammar check only",
        "upstream_sha256": digest(upstream1),
        "upstream_repeat_sha256": digest(upstream2),
        "task_sha256": digest(task),
        "grammar_sha256": digest(grammar),
        "v5_full_case_count": len(inputs),
        "v1_upstream_assignment_count": len(upstream),
        "unmatched_missing_upstream_cases": missing,
        "matched_case_count": len(upstream),
        "strict_grammar_rejected_upstream_actions": changed,
        "strict_grammar_rejected_upstream_action_count": len(changed),
        "H10_observation": "Development fixture: upstream OPEN; strict grammar ABSTAIN. This localizes a gate output difference, NOT external semantic correctness or four-arm non-degradation.",
        "H07_japanese_counterfactuals": japanese,
        "H07_warning": "Opposite Japanese meanings and nonsense map to identical V1 assignment. H07 is not evidence of Japanese semantic capacity.",
        "per_case": cases,
        "scientific_four_arm_comparison": "NOT_RUN",
        "causal_generalization": "NOT_ESTABLISHED",
        "terminal": "HISTORICAL_DIAGNOSTIC_ONLY_EXTERNAL_FOUR_ARM_REQUIRED"
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
