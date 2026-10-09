#!/usr/bin/env python3
"""Versioned S3 public dynamic rule guard; no gold/native predictions in guard.

Extends the preceding frozen invariant guard only when dynamic_spec is present.
Scores offline over previously executed actual model outputs. EC fallback gains
are attributed to EC, not to the LLM. Intended for mechanism decomposition.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0,str(ROOT))
from tools.run_issue1_s3_public_guard_decomposition_v1 import (
    public_guard,public,evaluate as old_evaluate,blob
)

PROTOCOL="ISSUE1_NATIVE_NEXT_ACTION_PUBLIC_DYNAMIC_GUARD_V2"
CONTRACT=ROOT/"docs/ISSUE1_NATIVE_NEXT_ACTION_PUBLIC_DYNAMIC_GUARD_V2.json"


def dynamic_public_guard(visible:dict,decision:dict)->list[str]:
    """Only visible deterministic dependency and urgency facts.

    EC output, frozen gold, fixture ID, category, model performance and hidden
    labels are forbidden from this function and not needed for the result.
    """
    reasons=set(public_guard(visible,decision))
    dynamic=visible.get("dynamic_spec")
    if not isinstance(dynamic,dict) or decision.get("status")!="EXECUTE":
        return sorted(reasons)
    plan=visible["plan"]
    issues=plan["issues"]
    by_id={issue["issue_id"]:issue for issue in issues}
    if len(by_id)!=len(issues):
        raise ValueError("DYNAMIC_ISSUE_ID_DUPLICATED")
    graph=dynamic["dependency_graph"]
    state=dynamic["issue_state"]
    if set(graph)!=set(by_id) or set(state)!=set(by_id):
        raise ValueError("DYNAMIC_GRAPH_ISSUE_SET_MISMATCH")
    for links in graph.values():
        if not set(links).issubset(by_id):
            raise ValueError("DYNAMIC_DEPENDENCY_UNKNOWN_ISSUE")
    selected=[]
    for issue in issues:
        works=[w if isinstance(w,str) else w["work_id"] for w in issue.get("work",[])]
        if decision.get("work_id") in works:
            selected.append(issue["issue_id"])
    if len(selected)!=1:
        return sorted(reasons)
    chosen=selected[0]
    done=set(visible.get("completed_work_ids") or [])
    completed_issues=set()
    for issue in issues:
        works=[w if isinstance(w,str) else w["work_id"] for w in issue.get("work",[])]
        if set(works).issubset(done):
            completed_issues.add(issue["issue_id"])
    ready={issue_id for issue_id,deps in graph.items() if set(deps)<=completed_issues}
    if chosen not in ready:
        reasons.add("DYNAMIC_DEPENDENCY_NOT_READY")
        return sorted(reasons)
    # Frozen dynamic-frontier policy uses block/criticality/urgency Pareto
    # dominance. This sub-gate is deliberately narrower: detect a STRICT
    # higher-urgency ready peer only when all other compared dimensions tie.
    def descendants(issue_id:str,path:set[str])->set[str]:
        if issue_id in path:raise ValueError("DYNAMIC_DEPENDENCY_CYCLE")
        direct=set(graph[issue_id])
        result=set()
        for dep in direct:
            result.add(dep)
            result|=descendants(dep,path|{issue_id})
        return result
    criticality={issue_id:len(descendants(issue_id,set())-completed_issues)
                 for issue_id in by_id}
    def urgency(issue_id:str)->float:
        value=state[issue_id]["urgency"]
        if not isinstance(value,(int,float)) or not math.isfinite(float(value)):
            raise ValueError("INVALID_DYNAMIC_URGENCY")
        return float(value)
    for other_id in ready-{chosen}:
        a,b=by_id[chosen],by_id[other_id]
        if bool(a["blocker"])!=bool(b["blocker"]):
            continue
        if a["priority"]!=b["priority"] or criticality[chosen]!=criticality[other_id]:
            continue
        if urgency(other_id)>urgency(chosen):
            reasons.add("DYNAMIC_URGENCY_DOMINANCE")
    return sorted(reasons)


def evaluate()->dict:
    cfg=json.loads(CONTRACT.read_text())
    if cfg["protocol"]!=PROTOCOL or cfg["status"]!="VERSIONED_RETROSPECTIVE_SUCCESSOR_FROZEN_BEFORE_RUN":
        raise ValueError("DYNAMIC_GUARD_CONTRACT_INVALID")
    for rel,pin in (
        ("fixtures/function_boundary_next_action_v1.json","fixture_blob"),
        ("results/issue1_public_gate_gbnf_qwen17_actual_2026-10-10.json","qwen_real_result_blob"),
        ("results/issue1_ecv44_native_next_action_v2_local_replay_2026-10-10.json","ec_native_actual_blob"),
    ):
        if blob(ROOT/rel)!=cfg[pin]:
            raise ValueError("FROZEN_DYNAMIC_GUARD_SOURCE_CHANGED:"+rel)
    before=old_evaluate()
    fixture=json.loads((ROOT/"fixtures/function_boundary_next_action_v1.json").read_text())["fixtures"]
    rows=[]
    for fx,r in zip(fixture,before["rows"]):
        if fx["id"]!=r["id"]:
            raise ValueError("EARLIER_GUARD_CASE_MAPPING_CHANGED")
        gate_input=public(fx)
        # The only inputs to the validator are the public source state and
        # the actual model's decision. Scoring occurs below, separately.
        checked=dynamic_public_guard(gate_input,r["raw_Qwen_decision"])
        original=set(r["public_guard_rule_ids"])
        if not original.issubset(checked):
            raise ValueError("PUBLIC_GUARD_REGRESSION")
        rows.append({
           "id":r["id"],"dynamic_visible":bool(gate_input.get("dynamic_spec")),
           "original_public_reasons":sorted(original),
           "new_public_dynamic_reasons":sorted(checked),
           "new_dynamic_rule_ids":sorted(set(checked)-original),
           "rejected":bool(checked),
           "model_actual_decision":r["raw_Qwen_decision"],
           "native_actual_reference":r["ec_replay_prediction"],
           "frozen_oracle":r["frozen_reference"],
        })
    caught_wrong=wrong=correct_rejected=total_hybrid=ec_fallback=0
    uncovered=[]
    for row in rows:
        ref=row["frozen_oracle"];model=row["model_actual_decision"];ec=row["native_actual_reference"]
        model_ok=model.get("status")==ref["status"] and model.get("work_id")==ref["work_id"]
        ec_ok=ec.get("status")==ref["status"] and ec.get("work_id")==ref["work_id"]
        if not ec_ok:raise ValueError("PINNED_NATIVE_EC_CONTRADICTS_REFERENCE")
        row["model_correct"]=model_ok
        row["hybrid_correct"]=ec_ok if row["rejected"] else model_ok
        wrong+=int(not model_ok)
        caught_wrong+=int(row["rejected"] and not model_ok)
        correct_rejected+=int(row["rejected"] and model_ok)
        total_hybrid+=int(row["hybrid_correct"])
        ec_fallback+=int(row["rejected"])
        if not model_ok and not row["rejected"]:uncovered.append(row["id"])
    if len(rows)!=17 or len({r["id"] for r in rows})!=17:
        raise ValueError("PUBLIC_DYNAMIC_STUDY_COVERAGE_FAIL")
    reason_counts={}
    for row in rows:
        for why in row["new_dynamic_rule_ids"]:
            reason_counts[why]=reason_counts.get(why,0)+1
    return {
      "protocol":PROTOCOL,
      "contract_git_blob":blob(CONTRACT),
      "frozen_17_actual_model_predictions":True,
      "new_model_inferences":0,
      "reference_native_EC_reused_only_after_guard":True,
      "cases":len(rows),"original_model_wrong":wrong,
      "fixed_public_guard_detected_wrong":before["public_invariant_guards_detected_wrong"],
      "extended_guard_detected_wrong":caught_wrong,
      "extended_guard_false_rejected_correct":correct_rejected,
      "new_dynamic_rule_trigger_counts":reason_counts,
      "remaining_uncaught_wrong_case_ids":uncovered,
      "extended_native_EC_fallback_count":ec_fallback,
      "extended_hybrid_correct_with_native_fallback":total_hybrid,
      "pure_native_EC_correct":17,
      "pure_model_correct":len(rows)-wrong,
      "improvement_attributable_to_EC_invocations_not_model":True,
      "same_public_model_upstream_pinned":True,
      "independent_blind":False,
      "original_full_A_E_completed":False,
      "rows":rows,
      "terminal":"PUBLIC_DYNAMIC_S3_POLICY_GUARD_REPLAYED_RETROSPECTIVE",
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        r=evaluate();text=json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
        if a.out:
            a.out.write_text(text)
            print(json.dumps({"terminal":r["terminal"],"caught":r["extended_guard_detected_wrong"],
              "wrong":r["original_model_wrong"],"fallback":r["extended_native_EC_fallback_count"],
              "hybrid_correct":r["extended_hybrid_correct_with_native_fallback"],
              "false_reject":r["extended_guard_false_rejected_correct"],
              "remaining":r["remaining_uncaught_wrong_case_ids"]}))
        else:print(text,end="")
        return 0
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:350]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
