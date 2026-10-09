#!/usr/bin/env python3
"""Actual native-next-action S3 Oracle controlled intervention (historical 17).

Uses only pre-existing real source-pinned native EC and real Qwen outputs.
Same frozen visible upstream and EXACT same downstream transition function are
used for A/Qwen, B/native EC, E/Oracle, and no-change placebo. Strictly scoped
to the native one-action function, never the original generic Phase1 A-E.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL="ISSUE1_NEXT_ACTION_S3_ORACLE_CAUSAL_INTERVENTION_V1"
CONTRACT=ROOT/"docs/ISSUE1_S3_NATIVE_NEXT_ACTION_ORACLE_INTERVENTION_V1.json"
FIXTURE=ROOT/"fixtures/function_boundary_next_action_v1.json"
LLM_REPORT=ROOT/"results/issue1_qwen_next_action_v2_mac_actual_2026-10-10.json"
EC_REPORT=ROOT/"results/issue1_ecv44_native_next_action_v2_local_replay_2026-10-10.json"
POLICY=ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json"
VISIBLE_KEYS=("plan","completed_work_ids","blocked_work","dynamic_spec")
NONEXECUTE=("REFRAME","FAIL_CLOSED","BLOCKED","NO_OPEN_WORK")

def sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
                                      separators=(",",":")).encode()).hexdigest()

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def visible_upstream(row:dict)->dict:
    result={k:row[k] for k in VISIBLE_KEYS if k in row}
    if not isinstance(result.get("plan"),dict):
        raise ValueError("UPSTREAM_PLAN_MISSING")
    if "oracle" in json.dumps(result).lower() or "gold" in json.dumps(result).lower():
        raise ValueError("ORACLE_DATA_LEAKED_TO_UPSTREAM")
    return result

def work_ids(plan:dict)->set[str]:
    issues=plan.get("issues")
    if not isinstance(issues,list):raise ValueError("PLAN_ISSUES_NOT_LIST")
    work=[]
    for issue in issues:
        for entry in issue.get("work",[]):
            name=entry if isinstance(entry,str) else entry.get("work_id") if isinstance(entry,dict) else None
            if not name or not isinstance(name,str):
                raise ValueError("INVALID_PLAN_WORK_ID")
            work.append(name)
    if len(set(work))!=len(work):
        raise ValueError("DUPLICATE_PLAN_WORK_ID")
    return set(work)

def downstream(upstream:dict,decision:dict)->dict:
    """One immutable deterministic side-effect-free action transition.

    NEVER reads case id, oracle, gold, model identity or prediction confidence.
    Returns new state; doesn't run arbitrary program or mutate any original.
    """
    if set(upstream)-set(VISIBLE_KEYS):raise ValueError("NON_PUBLIC_UPSTREAM_FIELD")
    if not isinstance(decision,dict) or set(decision)!={"status","work_id","reason_code"}:
        raise ValueError("DECISION_SCHEMA_VIOLATION")
    plan=upstream["plan"];valid=work_ids(plan)
    before=upstream.get("completed_work_ids") or []
    blocked=upstream.get("blocked_work") or {}
    if not isinstance(before,list) or not isinstance(blocked,dict):
        raise ValueError("COMPLETION_OR_BLOCKING_STATE_INVALID")
    if not set(before).issubset(valid) or not set(blocked).issubset(valid):
        raise ValueError("UPSTREAM_REFS_INVALID")
    if len(set(before))!=len(before):
        raise ValueError("DUPLICATE_COMPLETION_STATE")
    status=decision["status"];wid=decision["work_id"]
    if status=="EXECUTE":
        if not isinstance(wid,str) or wid not in valid:
            return {"event":"REJECTED_UNKNOWN_WORK_ID","next_completed_work_ids":sorted(before),
                    "work_id":"NONE","reason":"INVALID_CANDIDATE"}
        if wid in before or wid in blocked:
            return {"event":"REJECTED_ALREADY_COMPLETED_OR_BLOCKED","next_completed_work_ids":sorted(before),
                    "work_id":"NONE","reason":"INVALID_STATE_TRANSITION"}
        return {"event":"ACTION_APPLIED","next_completed_work_ids":sorted(set(before)|{wid}),
                "work_id":wid,"reason":"ONE_VISIBLE_ACTION_APPLIED"}
    if status not in NONEXECUTE or wid!="NONE":
        return {"event":"REJECTED_INVALID_DECISION_FORMAT",
                "next_completed_work_ids":sorted(before),"work_id":"NONE",
                "reason":"NO_ALLOWED_TRANSITION"}
    return {"event":status,"next_completed_work_ids":sorted(before),
            "work_id":"NONE","reason":"NO_WORK_MUTATION"}

def outcome_matches(actual:dict,expected:dict)->bool:
    return (actual["event"]==expected["event"]
            and actual["work_id"]==expected["work_id"]
            and actual["next_completed_work_ids"]==expected["next_completed_work_ids"])

def assert_pins(contract:dict)->None:
    if contract["protocol"]!=PROTOCOL or contract["status"]!="FROZEN_BEFORE_EVALUATION":
        raise ValueError("PREREGISTRATION_INVALID")
    for path,expected in (
      (FIXTURE,contract["frozen_sources"]["fixture_git_blob"]),
      (LLM_REPORT,contract["frozen_sources"]["qwen_actual_git_blob"]),
      (EC_REPORT,contract["frozen_sources"]["ec_actual_git_blob"]),
      (POLICY,contract["frozen_sources"]["prior_v2_contract_git_blob"])):
        if not path.is_file() or blob(path)!=expected:
            raise ValueError("FROZEN_SOURCE_BLOB_CHANGED:"+path.name)
    if contract["materiality_threshold"]!=0.2 or contract["original_A_E_complete"] is not False:
        raise ValueError("PREDEFINED_MATERIALITY_OR_SCOPE_INVALID")

def evaluate()->dict:
    contract=json.loads(CONTRACT.read_text())
    assert_pins(contract)
    fixture=json.loads(FIXTURE.read_text())
    llm=json.loads(LLM_REPORT.read_text())["run"]
    ec=json.loads(EC_REPORT.read_text())["result"]
    if not (fixture["fixture_count"]==len(fixture["fixtures"])==17
            and llm["llm_actual_inference_count"]==17
            and ec["cases_replayed"]==17
            and len(llm["llm"]["rows"])==len(ec["rows"])==17):
        raise ValueError("FROZEN_CASE_COVERAGE_MISMATCH")
    if llm["qwen_model_sha256"]!=contract["frozen_sources"]["model_sha256"]:
        raise ValueError("S3_LLM_MODEL_IDENTITY_MISMATCH")
    if ec["source_ec_commit"]!=contract["frozen_sources"]["ec_commit"]:
        raise ValueError("S3_EC_SOURCE_COMMIT_MISMATCH")
    observations=[]
    for fx,er,lr in zip(fixture["fixtures"],ec["rows"],llm["llm"]["rows"]):
        case_id=fx["id"]
        if case_id!=er["case_id"] or case_id!=lr["fixture_id"]:
            raise ValueError("ARMS_NOT_SAME_CASE_ORDER")
        upstream=visible_upstream(fx)
        if er["public_input_sha256"]!=sha(upstream):
            raise ValueError("UPSTREAM_HASH_DIFFERS_FROM_REPLAY")
        if lr["oracle"]!=fx["oracle"] or er["frozen_gold"]!=fx["oracle"]:
            raise ValueError("HISTORICAL_GOLD_CHANGED_AFTER_MODEL_RUN")
        model=lr["prediction"]
        native=er["prediction"]
        if model!=json.loads(lr["raw"]):
            raise ValueError("MODEL_PARSED_DECISION_NOT_RAW")
        if er["raw_prediction_sha256"]!=sha(native):
            raise ValueError("EC_PREDICTION_RAW_HASH_CHANGED")
        oracle=fx["oracle"]
        # No labels are passed to either cached raw model or native EC arm.
        model_result=downstream(upstream,model)
        ec_result=downstream(upstream,native)
        placebo_result=downstream(upstream,model)
        oracle_result=downstream(upstream,oracle)
        if model_result!=placebo_result:
            raise ValueError("NEGATIVE_CONTROL_IDENTICAL_INTERVENTION_DRIFT")
        if oracle["status"]=="EXECUTE" and oracle_result["event"]!="ACTION_APPLIED":
            raise ValueError("ORACLE_EXPECTED_EXECUTE_NOT_APPLICABLE")
        baseline_success=outcome_matches(model_result,oracle_result)
        native_success=outcome_matches(ec_result,oracle_result)
        observations.append({
            "case_id":case_id,"upstream_sha256":sha(upstream),
            "same_upstream_across_arms":True,
            "cached_actual_qwen_s3":model,
            "actual_pinned_native_ec_s3":native,
            "oracle_s3_only":oracle,
            "downstream_llm_A":model_result,
            "downstream_native_EC_B":ec_result,
            "downstream_oracle_intervention_E":oracle_result,
            "downstream_placebo":placebo_result,
            "llm_S3_selection_correct":model["status"]==oracle["status"] and model["work_id"]==oracle["work_id"],
            "ec_S3_selection_correct":native["status"]==oracle["status"] and native["work_id"]==oracle["work_id"],
            "llm_downstream_success":baseline_success,
            "ec_downstream_success":native_success,
            "oracle_intervention_downstream_success":True,
            "model_exact_reason_correct":model["reason_code"]==oracle["reason_code"],
            "model_intervention_gain":int(not baseline_success),
            "oracle_visible_only_in_evaluation_and_E":True,
        })
    if len({row["case_id"] for row in observations})!=17:
        raise ValueError("DUPLICATE_SOURCE_CASE")
    n=len(observations)
    llm_success=sum(r["llm_downstream_success"] for r in observations)
    ec_success=sum(r["ec_downstream_success"] for r in observations)
    oracle_success=sum(r["oracle_intervention_downstream_success"] for r in observations)
    llm_selection=sum(r["llm_S3_selection_correct"] for r in observations)
    ec_selection=sum(r["ec_S3_selection_correct"] for r in observations)
    gain=(oracle_success-llm_success)/n
    return {
        "protocol":PROTOCOL,
        "preregistered_contract_blob_sha1":blob(CONTRACT),
        "fixture_git_blob_sha1":blob(FIXTURE),
        "ec_report_git_blob_sha1":blob(EC_REPORT),
        "llm_report_git_blob_sha1":blob(LLM_REPORT),
        "ec_pinned_source_commit":ec["source_ec_commit"],
        "same_visible_upstream_for_all_arms":True,
        "counterfactual_target":"S3 singleton next-action only",
        "downstream":"pure fixed visible governed work transition, NOT full generic EC-native S4",
        "case_count":n,
        "llm_selection_correct":llm_selection,
        "ec_selection_correct":ec_selection,
        "llm_downstream_success":llm_success,
        "ec_downstream_success":ec_success,
        "oracle_S3_only_downstream_success":oracle_success,
        "causal_gain_oracle_S3_minus_llm_S3":gain,
        "materiality_threshold":contract["materiality_threshold"],
        "material_causal_gain_on_exposed_structured_next_action":gain>=contract["materiality_threshold"],
        "placebo_effect":0.0,
        "cases":observations,
        "cached_real_LLM_outputs_used":True,
        "actual_native_EC_outputs_used":True,
        "new_LLM_inferences":0,
        "independent_gold":False,
        "original_generic_s3_multiselection_tested":False,
        "original_s1_s4_A_to_E_completed":False,
        "original_issue_closure_authorized":False,
        "conclusion_limit":"S3 Oracle substitution causally fixes errors for this pre-exposed structured native next-action selection, not original unrestricted S1-S4 A-E semantics.",
        "terminal":"VERSIONED_S3_ORACLE_CAUSAL_GAIN_MEASURED_SCOPED",
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    try:
        out=evaluate()
        text=json.dumps(out,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            if a.out.is_symlink():raise ValueError("NO_EVIDENCE_SYMLINK")
            a.out.write_text(text,encoding="utf-8")
            print(json.dumps({"terminal":out["terminal"],"case_count":out["case_count"],
                              "causal_gain":out["causal_gain_oracle_S3_minus_llm_S3"],
                              "llm_success":out["llm_downstream_success"],
                              "ec_success":out["ec_downstream_success"],
                              "oracle_success":out["oracle_S3_only_downstream_success"],
                              "out":str(a.out)}))
        else:print(text,end="")
        return 0
    except Exception as exc:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(exc).__name__+":"+str(exc)[:350]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
