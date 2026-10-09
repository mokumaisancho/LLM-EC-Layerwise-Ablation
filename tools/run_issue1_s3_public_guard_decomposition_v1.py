#!/usr/bin/env python3
"""Decompose actual S3 model error into public invariant gates vs dynamic authority.

Guard sees only frozen model-visible plan/state and the raw actual Qwen action;
it does NOT read ground truth or native EC reference. After all guard calls,
evaluation separately scores detections and optional pinned-EC fallback.
Fallback gains are attributed to EC invocations, NEVER to model competence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL="ISSUE1_NEXT_ACTION_S3_PUBLIC_GUARD_DECOMPOSITION_V1"
CONTRACT=ROOT/"docs/ISSUE1_NEXT_ACTION_S3_PUBLIC_GUARD_DECOMPOSITION_V1.json"
FIXTURE=ROOT/"fixtures/function_boundary_next_action_v1.json"
TREATED=ROOT/"results/issue1_public_gate_gbnf_qwen17_actual_2026-10-10.json"
NATIVE=ROOT/"results/issue1_ecv44_native_next_action_v2_local_replay_2026-10-10.json"
ALLOWED=("plan","completed_work_ids","blocked_work","dynamic_spec")
VALID_STATUSES={"EXECUTE","NO_OPEN_WORK","BLOCKED","REFRAME","FAIL_CLOSED"}

def blob(path:Path)->str:
    d=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def public(case:dict)->dict:
    out={key:case[key] for key in ALLOWED if key in case}
    if "oracle" in json.dumps(out).lower() or "gold" in json.dumps(out).lower():
        raise ValueError("ORACLE_VISIBLE_IN_POLICY_GUARD")
    return out

def all_work(plan:dict)->set[str]:
    x=[]
    for issue in plan["issues"]:
        for raw in issue.get("work",[]):
            w=raw if isinstance(raw,str) else raw.get("work_id") if isinstance(raw,dict) else None
            if not isinstance(w,str) or not w:raise ValueError("WORK_ID_INVALID")
            x.append(w)
    if len(x)!=len(set(x)):raise ValueError("WORK_ID_DUPLICATED")
    return set(x)

def public_guard(visible:dict,decision:dict)->list[str]:
    """Strict public-only invariants. Intentionally excludes dynamic dominance.

    This function must never use fixture id, gold, category, stored EC answer,
    Qwen model weight, previously measured correctness, or private gold labels.
    """
    if not isinstance(visible,dict) or set(visible)-set(ALLOWED):
        raise ValueError("NONPUBLIC_INPUT_REJECTED")
    if not isinstance(decision,dict) or set(decision)!={"status","work_id","reason_code"}:
        return ["DECISION_SCHEMA_INVALID"]
    if decision["status"] not in VALID_STATUSES:
        return ["STATUS_NOT_RECOGNIZED"]
    plan=visible["plan"]
    if not isinstance(plan,dict) or not isinstance(plan.get("issues"),list):
        raise ValueError("PLAN_SCHEMA_INVALID")
    done=visible.get("completed_work_ids") or []
    blocked=visible.get("blocked_work") or {}
    if not isinstance(done,list) or not isinstance(blocked,dict):
        raise ValueError("WORK_STATE_SCHEMA_INVALID")
    works=all_work(plan)
    if not set(done).issubset(works) or not set(blocked).issubset(works):
        raise ValueError("OUT_OF_PLAN_WORK_STATE")
    status=decision["status"];wid=decision["work_id"]
    triggers=[]
    if plan.get("authority")!="EC_REMEDIATION_PLANNER_PROPOSAL" and status!="FAIL_CLOSED":
        triggers.append("INVALID_PLAN_AUTHORITY")
    if set(done)&set(blocked) and status!="FAIL_CLOSED":
        triggers.append("INCONSISTENT_WORK_STATE")
    active=any(("action_class" in i or "issue_contract" in i) for i in plan["issues"])
    if status=="REFRAME" and not active:
        triggers.append("INACTIVE_ISSUE_DEFINITION_GATE")
    for issue in plan["issues"]:
        p=[w if isinstance(w,str) else w["work_id"] for w in issue.get("work",[])]
        art=[w for w in p if w.endswith(":prior-art")]
        if art and art[0] in done and issue.get("prior_art_gate",{}).get("status")!="PASS":
            if status!="FAIL_CLOSED":
                triggers.append("UNSATISFIED_PRIOR_ART_GATE")
    if status=="EXECUTE":
        if wid not in works or wid in done or wid in blocked:
            triggers.append("EXECUTION_WORK_NOT_ACTIONABLE")
    elif wid!="NONE":
        triggers.append("NONEXECUTE_MUST_HAVE_NONE_WORK_ID")
    remaining=works-set(done)
    ready=remaining-set(blocked)
    if status=="NO_OPEN_WORK" and ready:
        triggers.append("OPEN_ACTIONABLE_WORK_EXISTS")
    if status=="BLOCKED" and ready:
        triggers.append("BLOCKED_BUT_OPEN_ACTIONABLE_EXISTS")
    return sorted(set(triggers))

def evaluate()->dict:
    cfg=json.loads(CONTRACT.read_text())
    if cfg["protocol"]!=PROTOCOL or cfg["status"]!="FIXED_RULES_BEFORE_GUARD_RUN_RETROSPECTIVE":
        raise ValueError("PREDECLARED_GUARD_POLICY_CHANGED")
    for p,h in [(FIXTURE,cfg["fixture_blob"]),(TREATED,cfg["frozen_actual_Qwen_gate_model_blob"]),
                (NATIVE,cfg["native_reference_ec_v44_replay_blob"])]:
        if not p.is_file() or blob(p)!=h:raise ValueError("HISTORICAL_FROZEN_SOURCE_BLOB_DRIFT:"+p.name)
    fixtures=json.loads(FIXTURE.read_text())["fixtures"]
    model=json.loads(TREATED.read_text())["model_run"]["paired_cases"]
    native=json.loads(NATIVE.read_text())["result"]["rows"]
    if not(len(fixtures)==len(model)==len(native)==cfg["exact_case_count"]==17):
        raise ValueError("17_CASE_COVERAGE_MISMATCH")
    seen=set();rows=[]
    # 1. Capture guard verdict on public input and actual prior model decisions.
    for fx,q,ec in zip(fixtures,model,native):
        if not (fx["id"]==q["id"]==ec["case_id"]):
            raise ValueError("FIXTURE_MODEL_NATIVE_CASE_ALIGNMENT")
        if fx["id"] in seen:raise ValueError("CASE_DUPLICATE")
        seen.add(fx["id"])
        treated=q["treatment"]
        raw=q["raw_real_inference"]["raw_response"]
        if treated!=json.loads(raw):
            raise ValueError("MODEL_PREDICTION_NOT_FROM_REAL_RAW")
        if ec["frozen_gold"]!=fx["oracle"]:
            raise ValueError("HISTORICAL_SCORER_GOLD_DIVERGENCE")
        vis=public(fx)
        reason=public_guard(vis,treated)
        rows.append({"id":fx["id"],"raw_Qwen_decision":treated,
                     "raw_Qwen_output_sha256":hashlib.sha256(raw.encode()).hexdigest(),
                     "public_input_sha256":hashlib.sha256(json.dumps(vis,sort_keys=True,ensure_ascii=False,
                         separators=(",",":")).encode()).hexdigest(),
                     "guard_rejected":bool(reason),"public_guard_rule_ids":reason,
                     "guard_policy_scope":"local invariants only, no dynamic dependency/urgency",
                     "ec_replay_prediction":ec["prediction"],"frozen_reference":fx["oracle"]})
    # 2. Score *after* guard verdicts have been sealed, using pre-existing
    # frozen gold. Guard itself is pure public and not trained on these labels.
    rejected_wrong=wrong=correct_rejected=model_correct=hybrid_correct=ec_invocations=0
    for row in rows:
        ref=row["frozen_reference"];llm=row["raw_Qwen_decision"];ec=row["ec_replay_prediction"]
        llm_correct=llm.get("status")==ref["status"] and llm.get("work_id")==ref["work_id"]
        ec_correct=ec.get("status")==ref["status"] and ec.get("work_id")==ref["work_id"]
        if not ec_correct:raise ValueError("REFERENCE_EC_NATIVE_AGREEMENT_BROKEN")
        row["llm_exact_correct"]=llm_correct
        row["ec_exact_correct"]=ec_correct
        row["hybrid_actual_decision"]=ec if row["guard_rejected"] else llm
        row["hybrid_correct"]=ec_correct if row["guard_rejected"] else llm_correct
        wrong+=int(not llm_correct)
        model_correct+=int(llm_correct)
        rejected_wrong+=int(row["guard_rejected"] and not llm_correct)
        correct_rejected+=int(row["guard_rejected"] and llm_correct)
        ec_invocations+=int(row["guard_rejected"])
        hybrid_correct+=int(row["hybrid_correct"])
    covered=[r["id"] for r in rows if not r["llm_exact_correct"] and r["guard_rejected"]]
    uncovered=[r["id"] for r in rows if not r["llm_exact_correct"] and not r["guard_rejected"]]
    by_reason={}
    for row in rows:
        for reason in row["public_guard_rule_ids"]:
            by_reason[reason]=by_reason.get(reason,0)+1
    return {
      "protocol":PROTOCOL,"predeclared_guard_git_blob_sha1":blob(CONTRACT),
      "actual_Qwen_model_report_git_blob_sha1":blob(TREATED),
      "source_native_git_blob_sha1":blob(NATIVE),
      "cases":len(rows),"actual_model_inference_reused":17,
      "new_model_calls":0,
      "Qwen_baseline_correct":model_correct,
      "Qwen_wrong":wrong,
      "public_invariant_guards_detected_wrong":rejected_wrong,
      "public_invariant_guards_false_rejected_correct":correct_rejected,
      "guard_missed_wrong_case_ids":uncovered,
      "guard_detected_wrong_case_ids":covered,
      "guard_rejection_reason_counts":by_reason,
      "hybrid_native_EC_invocations_due_to_guard":ec_invocations,
      "hybrid_total_correct_using_EC_fallback":hybrid_correct,
      "pure_native_EC_total_correct":len(rows),
      "interpreted_remaining_subfunction":"dynamic dependency readiness/urgency arbitration" if uncovered else
        "further heldout policy validation",
      "no_oracle_input_in_guard":True,
      "no_native_EC_input_in_guard":True,
      "LLM_semantic_accuracy_improved_by_guard":False,
      "hybrid_gains_attributable_to_native_EC":True,
      "independent_holdout":False,
      "original_full_A_E_completed":False,
      "rows":rows,
      "terminal":"RETROSPECTIVE_PUBLIC_S3_INVARIANT_COVERAGE_DIAGNOSTIC_COMPLETE",
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        v=evaluate()
        text=json.dumps(v,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            a.out.write_text(text)
            print(json.dumps({"terminal":v["terminal"],"baseline":v["Qwen_baseline_correct"],
               "caught":v["public_invariant_guards_detected_wrong"],
               "false_rejects":v["public_invariant_guards_false_rejected_correct"],
               "hybrid_correct":v["hybrid_total_correct_using_EC_fallback"],
               "remaining":v["guard_missed_wrong_case_ids"]}))
        else:print(text,end="")
        return 0
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:400]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
