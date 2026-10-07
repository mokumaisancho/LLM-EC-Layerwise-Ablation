#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
from typing import Any

import audit_s1c_v31_independent as v31

PROTOCOL="S1C_V32_INDEPENDENT_POSTRUN_AUDIT_V1"
EXPECTED_RUNTIME="FUNCTION_BOUNDARY_S1C_V32_PAIRED_V1"
AUTHORITY="S1C_V31_INDEPENDENT_ORACLE_VALIDATOR_V1"
LOCAL_SLOT_IDS={"S01","S02","S03","S04"}
EVAL_IDS={"Q03","Q05","Q06","Q07"}
ALLOWED_POL={"POS","NEG"}
ALLOWED_MOD={"ASSERTED","REQUIRED","POSSIBLE"}

def canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def sha(x):return hashlib.sha256(canon(x).encode()).hexdigest()
def raw_sha(s):return hashlib.sha256(s.encode()).hexdigest()
def fail(reason,detail=None):return {"protocol":PROTOCOL,"pass":False,"terminal":"S1C_V32_POSTRUN_AUDIT_FAIL_CLOSED","reason":reason,"detail":detail,"model_reinference":False}

def schema_core(task:dict[str,Any],pred:Any)->tuple[bool,str]:
    if not isinstance(pred,dict) or set(pred)!={"discovered_slots","heldout_assignments","abstentions"}:return False,"TOP_LEVEL"
    v=task["visible"];train={str(x["example_id"]) for x in v["training_examples"]};held={str(x["example_id"]) for x in v["heldout_examples"]};types={str(x) for x in v["type_inventory"]};entities={str(e) for x in v["heldout_examples"] for e in x["entity_registry"]}
    slots=pred["discovered_slots"];assigns=pred["heldout_assignments"];abst=pred["abstentions"]
    if not all(isinstance(x,list) for x in (slots,assigns,abst)) or not 1<=len(slots)<=4:return False,"LIST_OR_SLOT_COUNT"
    for s in slots:
        if not isinstance(s,dict) or set(s)!={"slot_id","arg_types","training_members","evaluation_probe_predictions"} or s.get("slot_id") not in LOCAL_SLOT_IDS:return False,"SLOT_SCHEMA"
        at=s.get("arg_types");mem=s.get("training_members");ev=s.get("evaluation_probe_predictions")
        if not isinstance(at,list) or not 1<=len(at)<=2 or any(x not in types for x in at):return False,"ARG_TYPES_SCHEMA"
        if not isinstance(mem,list) or not 1<=len(mem)<=4 or any(str(x) not in train for x in mem):return False,"MEMBER_SCHEMA"
        if not isinstance(ev,list) or len(ev)!=4:return False,"EVAL_SCHEMA"
        for r in ev:
            if not isinstance(r,dict) or set(r)!={"probe_id","predicted_after"} or r.get("probe_id") not in EVAL_IDS:return False,"EVAL_ROW_SCHEMA"
            bits=r.get("predicted_after")
            if not isinstance(bits,list) or len(bits)!=3 or any(x not in (0,1) for x in bits):return False,"EVAL_BITS_SCHEMA"
    for r in assigns:
        if not isinstance(r,dict) or set(r)!={"example_id","slot_id","arguments","polarity","modality"}:return False,"ASSIGN_SCHEMA"
        if str(r.get("example_id") or "") not in held or r.get("slot_id") not in LOCAL_SLOT_IDS:return False,"ASSIGN_ENUM"
        args=r.get("arguments")
        if not isinstance(args,list) or not 1<=len(args)<=2 or any(str(x) not in entities for x in args):return False,"ASSIGN_ARGS"
        if r.get("polarity") not in ALLOWED_POL or r.get("modality") not in ALLOWED_MOD:return False,"ASSIGN_PM"
    for r in abst:
        if not isinstance(r,dict) or set(r)!={"example_id","status"} or str(r.get("example_id") or "") not in held or r.get("status")!="AMBIGUOUS":return False,"ABST_SCHEMA"
    return True,"VALID"

def semantic_valid(task:dict[str,Any],pred:dict[str,Any])->tuple[bool,str]:
    train={str(x["example_id"]) for x in task["visible"]["training_examples"]};held={str(x["example_id"]) for x in task["visible"]["heldout_examples"]}
    slots=[];owner={}
    for s in pred["discovered_slots"]:
        sid=str(s["slot_id"])
        if sid in slots:return False,"DUPLICATE_DISCOVERED_SLOT_ID"
        slots.append(sid)
        pids=[str(x["probe_id"]) for x in s["evaluation_probe_predictions"]]
        if len(set(pids))!=4 or set(pids)!=EVAL_IDS:return False,"EVALUATION_PROBE_COVERAGE_INVALID"
        for m in s["training_members"]:
            mid=str(m)
            if mid in owner:return False,"TRAINING_MEMBER_DUPLICATED"
            owner[mid]=sid
    if set(owner)!=train:return False,"TRAINING_MEMBER_MISSING"
    assign={};abst=set()
    for r in pred["heldout_assignments"]:
        eid=str(r["example_id"])
        if eid in assign:return False,"HELDOUT_ASSIGNMENT_DUPLICATED"
        if r["slot_id"] not in slots:return False,"ASSIGNMENT_REFERENCES_NONEMITTED_SLOT"
        assign[eid]=r
    for r in pred["abstentions"]:
        eid=str(r["example_id"])
        if eid in abst:return False,"ABSTENTION_DUPLICATED"
        if eid in assign:return False,"HELDOUT_BOTH_ASSIGNED_AND_ABSTAINED"
        abst.add(eid)
    if set(assign)|abst != held:return False,"HELDOUT_COVERAGE_INVALID"
    return True,"VALID"

def zero(reason):
    return {"semantic_output_validity":0.0,"training_partition_adjusted_rand_index":0.0,"training_partition_pairwise_accuracy":0.0,
            "unseen_probe_behavior_accuracy":0.0,"heldout_denotational_assignment_accuracy":0.0,"exact_discovery_and_grounding":False,
            "argument_binding_accuracy":0.0,"polarity_modality_accuracy":0.0,"abstention_accuracy":0.0,"slot_coverage":0.0,"prediction_reason":reason}

def score_one(task,pred,ref):
    ok,reason=schema_core(task,pred)
    if not ok:raise ValueError("SCHEMA_CORE_INVALID:"+reason)
    ok,reason=semantic_valid(task,pred)
    if not ok:return zero(reason)
    r=v31.score_one(task,pred,ref)
    return {"semantic_output_validity":1.0,**r,"prediction_reason":"VALID"}

def aggregate(tasks,preds,refs):
    rows=[]
    for task in tasks:
        tid=str(task["task_id"]);rows.append({"task_id":tid,**score_one(task,preds[tid],refs[tid])})
    n=len(rows)
    return {"primary":{"semantic_output_validity_rate":sum(r["semantic_output_validity"] for r in rows)/n,
                       "training_partition_adjusted_rand_index":sum(r["training_partition_adjusted_rand_index"] for r in rows)/n,
                       "unseen_probe_behavior_accuracy":sum(r["unseen_probe_behavior_accuracy"] for r in rows)/n,
                       "heldout_denotational_assignment_accuracy":sum(r["heldout_denotational_assignment_accuracy"] for r in rows)/n,
                       "exact_discovery_and_grounding_rate":sum(int(r["exact_discovery_and_grounding"]) for r in rows)/n},
            "secondary":{"training_partition_pairwise_accuracy":sum(r["training_partition_pairwise_accuracy"] for r in rows)/n,
                         "argument_binding_accuracy":sum(r["argument_binding_accuracy"] for r in rows)/n,
                         "polarity_modality_accuracy":sum(r["polarity_modality_accuracy"] for r in rows)/n,
                         "abstention_accuracy":sum(r["abstention_accuracy"] for r in rows)/n,
                         "slot_coverage":sum(r["slot_coverage"] for r in rows)/n},
            "semantic_invalid_tasks":[{"task_id":r["task_id"],"reason":r["prediction_reason"]} for r in rows if r["semantic_output_validity"]==0.0],
            "rows":rows}

def close(a,b):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):return abs(float(a)-float(b))<=1e-12
    if isinstance(a,dict) and isinstance(b,dict):return set(a)==set(b) and all(close(a[k],b[k]) for k in a)
    return a==b

def audit(runtime):
    if runtime.get("protocol")!=EXPECTED_RUNTIME:return fail("RUNTIME_PROTOCOL_MISMATCH")
    if runtime.get("terminal")!="V32_PAIRED_METRICS_READY_AUDIT_REQUIRED":return fail("RUNTIME_TERMINAL_MISMATCH")
    corpus=runtime.get("corpus");oracle=runtime.get("oracle_validation")
    if not isinstance(corpus,dict) or not isinstance(oracle,dict):return fail("EVIDENCE_BUNDLE_MISSING")
    if oracle.get("authority")!=AUTHORITY or oracle.get("pass") is not True:return fail("ORACLE_NOT_PASS")
    tasks=corpus.get("tasks")
    if not isinstance(tasks,list) or len(tasks)!=8:return fail("TASK_COUNT")
    if corpus.get("dataset_digest")!=sha(tasks):return fail("CORPUS_DIGEST_MISMATCH")
    refs=oracle.get("references") or {};tids={str(t["task_id"]) for t in tasks}
    if set(refs)!=tids:return fail("REFERENCE_COVERAGE")
    rawrows=runtime.get("raw_qwen_rows")
    if not isinstance(rawrows,list) or len(rawrows)!=8:return fail("RAW_ROW_COUNT")
    qpred={}
    for row in rawrows:
        tid=str(row.get("task_id") or "");raw=row.get("raw")
        if tid not in tids or tid in qpred:return fail("RAW_TASK_ID",tid)
        if not isinstance(raw,str) or raw_sha(raw)!=row.get("raw_sha256"):return fail("RAW_HASH",tid)
        task=next(t for t in tasks if str(t["task_id"])==tid)
        if sha(task["visible"])!=row.get("visible_sha256"):return fail("VISIBLE_HASH",tid)
        try:parsed=json.loads(raw)
        except Exception:return fail("PARSER_FAILURE",tid)
        if parsed!=row.get("prediction"):return fail("RAW_REPARSE_MISMATCH",tid)
        ok,reason=schema_core(task,parsed)
        if not ok:return fail("JSON_SCHEMA_RUNTIME_CONTRACT_FAILURE",{"task_id":tid,"reason":reason})
        qpred[tid]=parsed
    dp=runtime.get("deterministic_predictions")
    if not isinstance(dp,dict) or set(dp)!=tids:return fail("DETERMINISTIC_COVERAGE")
    try:dscore=aggregate(tasks,dp,refs);qscore=aggregate(tasks,qpred,refs)
    except Exception as exc:return fail("RECOMPUTE_FAILED",repr(exc))
    arms=runtime.get("arms") or {}
    for name,recomputed in (("deterministic",dscore),("qwen25_1p5b",qscore)):
        recorded=arms.get(name) or {};proj={"primary":recorded.get("primary"),"secondary":recorded.get("secondary"),"semantic_invalid_tasks":recorded.get("semantic_invalid_tasks")}
        exp={"primary":recomputed["primary"],"secondary":recomputed["secondary"],"semantic_invalid_tasks":recomputed["semantic_invalid_tasks"]}
        if not close(proj,exp):return fail("METRIC_RECOMPUTATION_MISMATCH",{"arm":name,"recorded":proj,"recomputed":exp})
    deltas={k:qscore["primary"][k]-dscore["primary"][k] for k in dscore["primary"]}
    if not close(deltas,runtime.get("primary_deltas_qwen_minus_deterministic")):return fail("DELTA_MISMATCH")
    return {"protocol":PROTOCOL,"pass":True,"terminal":"S1C_V32_POSTRUN_AUDIT_PASS","dataset_digest":corpus["dataset_digest"],
            "raw_qwen_rows_verified":8,"parser_failure_rate":0.0,"deterministic":{"primary":dscore["primary"],"secondary":dscore["secondary"],"semantic_invalid_tasks":dscore["semantic_invalid_tasks"]},
            "qwen25_1p5b":{"primary":qscore["primary"],"secondary":qscore["secondary"],"semantic_invalid_tasks":qscore["semantic_invalid_tasks"]},
            "primary_deltas_qwen_minus_deterministic":deltas,"result_overturning_gate_failures":0,"model_reinference":False,
            "final_branch_authorized":False,"required_next_gate":"S1C_V32_FIXED_B2_CAUSAL_REPLAY"}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("runtime",type=Path);ap.add_argument("--output",type=Path);args=ap.parse_args()
    out=audit(json.loads(args.runtime.read_text()));txt=json.dumps(out,indent=2)+"\n"
    if args.output:args.output.write_text(txt)
    print(txt,end="");return 0 if out.get("pass") else 3
if __name__=="__main__":raise SystemExit(main())
