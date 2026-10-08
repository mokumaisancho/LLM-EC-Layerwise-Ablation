#!/usr/bin/env python3
"""Historical V1->V5 observational diagnostics. No model inference, no updates.

Historical V5 benchmark has already been examined during development and MUST
NOT be described as an independent unseen holdout. Original LLM0 is absent.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from tools.capability_retention_v1 import PROTOCOL,digest,evaluate,EvaluationContractError
from semantic_runtime import discover_and_ground
from semantic_runtime.constrained_v5 import classify_explicit
from tests.test_semantic_runtime_v5_grammar import make_field_task,make_grammar

LABELS=ROOT/"evaluation/capability_retention_historical_labels_v1.json"
LABELS_BLOB_EXPECTED="__PIN_LABELS_BLOB_SHA__"


def main()->int:
    raw=LABELS.read_bytes()
    import hashlib
    blob=hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
    if blob!=LABELS_BLOB_EXPECTED:
        print(json.dumps({"terminal":"HISTORICAL_LABELS_BLOB_DRIFT"}))
        return 3
    # Crucial separation: predictor outputs computed BEFORE fetching labels.
    task=make_field_task()
    grounded=discover_and_ground(task)
    strict=classify_explicit(task,make_grammar())
    slot_members={frozenset(s["training_members"]):s["slot_id"] for s in grounded["discovered_slots"]}
    expected_slots={slot_members[frozenset(("T01","T02"))]:"OPEN",
                    slot_members[frozenset(("T03","T04"))]:"CLOSE"}
    v1={}
    for entry in grounded["heldout_assignments"]:
        decision=expected_slots[entry["slot_id"]] if entry["polarity"]=="POS" and entry["modality"]=="ASSERTED" else "ABSTAIN"
        v1[entry["example_id"]]=decision
    v5={}
    for item in strict["decisions"]:
        v5[item["example_id"]]=expected_slots[item["slot_id"]] if item["status"]=="EXPLICIT_MATCH" else "ABSTAIN"
    inputs={e["example_id"]:e for e in task["visible"]["heldout_examples"]}
    labels=json.loads(raw.decode("utf-8"))
    if labels["protocol"]!="LLM_EC_RETROSPECTIVE_GOLD_LABELS_V1" or labels["not_independent"] is not True or labels["not_heldout"] is not True:
        raise ValueError("HISTORICAL_GOLD_LABELS_NOT_LOCKED")
    if set(inputs)!={x["case_id"] for x in labels["labels"]}:
        raise ValueError("HISTORICAL_LABEL_COVERAGE_DRIFT")
    cases=[]
    for label in labels["labels"]:
        cid=label["case_id"]
        case={k:label[k] for k in ("case_id","gold_action","capability","critical","tail")}
        case["input_sha256"]=digest({"raw_text":inputs[cid]["raw_text"],
                                      "entity_registry":inputs[cid]["entity_registry"]})
        cases.append(case)
    benchmark={"protocol":"LLM_EC_CAPABILITY_BENCHMARK_V1","origin":"REUSED_HISTORICAL",
               "measurement_only":True,"cases":cases}
    bench_hash=digest(benchmark)
    arms={}
    for name,predictions in (("V1",v1),("V5",v5)):
        rows=[{"case_id":c["case_id"],"input_sha256":c["input_sha256"],
               "decision":predictions.get(c["case_id"],"ABSTAIN")} for c in cases]
        arms[name]={"arm":name,"source_ref":"PINNED_CODE:"+("semantic_runtime/discovery.py" if name=="V1" else "semantic_runtime/constrained_v5.py"),
                    "benchmark_sha256":bench_hash,"measurement_only":True,"used_for_update":False,
                    "rows":rows,"rows_sha256":digest(rows)}
    if set(v1)-set(inputs) or set(v5)!=set(inputs):
        raise ValueError("ARM_OUTPUT_COVERAGE_INVALID")
    # Controlled strict-gate intervention: the V5 action set must be a subset of
    # the same upstream V1 classifier actions (never substitute a new wrong action).
    if any(v5[c]!="ABSTAIN" and v5[c]!=v1.get(c,"ABSTAIN") for c in inputs):
        raise ValueError("STRICT_GATE_CHANGED_UPSTREAM_ACTION")
    bundle={"protocol":PROTOCOL,"benchmark":benchmark,"arms":arms,
            "evaluation_locked":True,"training_feedback_used":False}
    report=evaluate(bundle,diagnostic=True)
    full_blocker=""
    try:
        evaluate(bundle,diagnostic=False)
    except EvaluationContractError as exc:
        full_blocker=str(exc)
    if full_blocker!="FULL_COMPARISON_REQUIRES_INDEPENDENT_BENCHMARK":
        raise ValueError("FULL_COMPARISON_INCORRECTLY_PERMITTED")
    if report["terminal"]!="RETROSPECTIVE_DIAGNOSTIC_ONLY":
        raise ValueError("QUALITY_CERTIFICATE_WRONGLY_GRANTED")
    result={"protocol":"LLM_EC_CAPABILITY_RETENTION_HISTORICAL_REPORT_V1",
            "terminal":"HISTORICAL_DIAGNOSTIC_COMPLETE_FULL_QUALITY_BLOCKED",
            "report":report,
            "original_llm_same_input":"MISSING_NOT_INFERRED",
            "v4_end_to_end":"NOT_MEASURED_V4_USES_SAME_LEXICAL_GROUNDER_BUT_POLICY_DIFFERS",
            "frozen_gold_label_blob":blob,
            "correct_control":"UPSTREAM_V1_UNCHANGED_STRICT_GRAMMAR_GATE_ONLY",
            "full_comparison_blocker":full_blocker,
            "warning":"Previously visible V5 cases; no independent generalization or original LLM non-degradation claim."}
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
