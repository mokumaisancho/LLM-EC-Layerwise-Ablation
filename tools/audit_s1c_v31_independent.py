#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path
from typing import Any

PROTOCOL = "S1C_V31_INDEPENDENT_POSTRUN_AUDIT_V1"
EXPECTED_RUNTIME = "FUNCTION_BOUNDARY_S1C_V31_PAIRED_V1"
AUTHORITY = "S1C_V31_INDEPENDENT_ORACLE_VALIDATOR_V1"
EVAL_IDS = ("Q03","Q05","Q06","Q07")
ALLOWED_POL = {"POS","NEG"}
ALLOWED_MOD = {"ASSERTED","REQUIRED","POSSIBLE"}


def canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",",":"), ensure_ascii=False)


def sha(x: Any) -> str:
    return hashlib.sha256(canon(x).encode()).hexdigest()


def raw_sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def fail(reason: str, detail: Any = None) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "pass": False,
        "terminal": "S1C_V31_POSTRUN_AUDIT_FAIL_CLOSED",
        "reason": reason,
        "detail": detail,
        "model_reinference": False,
    }


def ari(gold: list[str], pred: list[str]) -> float:
    n=len(gold)
    if n!=len(pred) or n<2:
        return 1.0 if gold==pred else 0.0
    table=Counter(zip(gold,pred)); row=Counter(gold); col=Counter(pred)
    c2=lambda x:x*(x-1)//2
    a=sum(c2(v) for v in table.values()); b=sum(c2(v) for v in row.values()); c=sum(c2(v) for v in col.values()); total=c2(n)
    if total==0:return 1.0
    expected=(b*c)/total; max_index=0.5*(b+c); denom=max_index-expected
    if denom==0:return 1.0 if a==max_index else 0.0
    return (a-expected)/denom


def pairwise(gold: list[str], pred: list[str]) -> float:
    ok=total=0
    for i,j in itertools.combinations(range(len(gold)),2):
        ok+=int((gold[i]==gold[j])==(pred[i]==pred[j])); total+=1
    return ok/total if total else 1.0


def eval_map(rows: Any) -> dict[str,tuple[int,int,int]] | None:
    if not isinstance(rows,list) or len(rows)!=4:return None
    out={}
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"probe_id","predicted_after"}:return None
        pid=str(row.get("probe_id") or ""); bits=row.get("predicted_after")
        if pid not in EVAL_IDS or pid in out:return None
        if not isinstance(bits,list) or len(bits)!=3 or any(x not in (0,1) for x in bits):return None
        out[pid]=tuple(int(x) for x in bits)
    return out if set(out)==set(EVAL_IDS) else None


def parse_shape(task: dict[str,Any], pred: Any) -> dict[str,Any] | None:
    if not isinstance(pred,dict) or set(pred)!={"discovered_slots","heldout_assignments","abstentions"}:return None
    v=task["visible"]; train_ids={str(x["example_id"]) for x in v["training_examples"]}; held_ids={str(x["example_id"]) for x in v["heldout_examples"]}
    slots=pred["discovered_slots"]; assigns=pred["heldout_assignments"]; abst=pred["abstentions"]
    if not all(isinstance(x,list) for x in (slots,assigns,abst)):return None
    if not int(v["slot_count_bound"]["min"])<=len(slots)<=int(v["slot_count_bound"]["max"]):return None
    owner={}; types={}; ev={}; slot_ids=set()
    for slot in slots:
        if not isinstance(slot,dict) or set(slot)!={"slot_id","arg_types","training_members","evaluation_probe_predictions"}:return None
        sid=slot.get("slot_id")
        if not isinstance(sid,str) or not sid or sid in slot_ids:return None
        slot_ids.add(sid)
        at=slot.get("arg_types"); members=slot.get("training_members")
        if not isinstance(at,list) or not (1<=len(at)<=2) or not all(isinstance(x,str) and x for x in at):return None
        if not isinstance(members,list) or not members:return None
        for m in members:
            mid=str(m)
            if mid not in train_ids or mid in owner:return None
            owner[mid]=sid
        em=eval_map(slot.get("evaluation_probe_predictions"))
        if em is None:return None
        types[sid]=tuple(at); ev[sid]=em
    if set(owner)!=train_ids:return None
    byid={}
    for row in assigns:
        if not isinstance(row,dict) or set(row)!={"example_id","slot_id","arguments","polarity","modality"}:return None
        eid=str(row.get("example_id") or "")
        if eid not in held_ids or eid in byid or row.get("slot_id") not in slot_ids:return None
        args=row.get("arguments")
        if not isinstance(args,list) or not all(isinstance(x,str) for x in args):return None
        if row.get("polarity") not in ALLOWED_POL or row.get("modality") not in ALLOWED_MOD:return None
        byid[eid]=row
    abst_ids=set()
    for row in abst:
        if not isinstance(row,dict) or set(row)!={"example_id","status"}:return None
        eid=str(row.get("example_id") or "")
        if eid not in held_ids or eid in abst_ids or eid in byid or row.get("status")!="AMBIGUOUS":return None
        abst_ids.add(eid)
    if set(byid)|abst_ids != held_ids:return None
    return {"slot_ids":sorted(slot_ids),"owner":owner,"types":types,"eval":ev,"assign":byid,"abst":abst_ids}


def probe_matches(a: dict[str,tuple[int,int,int]], b: dict[str,tuple[int,int,int]]) -> int:
    return sum(int(a.get(k)==b.get(k)) for k in EVAL_IDS)


def ref_eval(ref: dict[str,Any]) -> dict[str,dict[str,tuple[int,int,int]]]:
    out={}
    for key,item in ref["slot_references"].items():
        em=eval_map(item["evaluation_probe_expected"])
        if em is None: raise ValueError("REFERENCE_EVAL_INVALID")
        out[str(key)]=em
    return out


def score_one(task: dict[str,Any], pred: Any, ref: dict[str,Any]) -> dict[str,Any]:
    shape=parse_shape(task,pred)
    if shape is None: raise ValueError("MALFORMED_PREDICTION")
    train_ids=sorted(ref["training_gold"])
    gold=[ref["training_gold"][x] for x in train_ids]; pl=[shape["owner"][x] for x in train_ids]
    a=ari(gold,pl); pw=pairwise(gold,pl)
    gold_keys=sorted(ref["slot_references"]); ge=ref_eval(ref)
    if len(gold_keys)!=2: raise ValueError("REFERENCE_SLOT_COUNT")
    alignments=[]
    for chosen in itertools.permutations(shape["slot_ids"],2):
        mapping={sid:g for sid,g in zip(chosen,gold_keys)}
        score=0
        for sid,g in mapping.items():
            types_ok=shape["types"][sid]==tuple(ref["slot_references"][g]["arg_types"])
            score += probe_matches(shape["eval"][sid], ge[g]) if types_ok else 0
        alignments.append((score,mapping))
    if not alignments: raise ValueError("NO_ALIGNMENT")
    best_score=max(x[0] for x in alignments); best=[x for x in alignments if x[0]==best_score]
    vectors=[]; details=[]
    for _,mapping in best:
        vec=[]; det={}
        for eid in sorted(ref["heldout"]):
            rr=ref["heldout"][eid]
            if rr["status"]=="AMBIGUOUS":
                ok=eid in shape["abst"]; vec.append(ok); det[eid]={"correct":ok,"status":"AMBIGUOUS"}; continue
            row=shape["assign"].get(eid)
            if row is None:
                vec.append(False);det[eid]={"correct":False};continue
            den=mapping.get(row["slot_id"])==rr["target_code"]
            args=list(row["arguments"])==list(rr["arguments"])
            pm=row["polarity"]==rr["polarity"] and row["modality"]==rr["modality"]
            ok=den and args and pm; vec.append(ok)
            det[eid]={"correct":ok,"denotation_correct":den,"arguments_correct":args,"polarity_modality_correct":pm}
        vectors.append(tuple(vec));details.append(det)
    if len(set(vectors))>1: raise ValueError("ALIGNMENT_TIE_CHANGES_HELDOUT")
    pick=min(range(len(best)),key=lambda i:tuple(sorted(best[i][1].items())))
    vec=list(vectors[pick]); det=details[pick]
    unseen=best_score/(2*len(EVAL_IDS)); held=sum(map(int,vec))/len(vec)
    normals=[eid for eid,r in ref["heldout"].items() if r["status"]=="OK"]; amb=[eid for eid,r in ref["heldout"].items() if r["status"]=="AMBIGUOUS"]
    return {
        "training_partition_adjusted_rand_index":a,
        "training_partition_pairwise_accuracy":pw,
        "unseen_probe_behavior_accuracy":unseen,
        "heldout_denotational_assignment_accuracy":held,
        "exact_discovery_and_grounding":bool(len(shape["slot_ids"])==2 and a==1.0 and unseen==1.0 and held==1.0),
        "argument_binding_accuracy":sum(int(det[e].get("arguments_correct",False)) for e in normals)/len(normals),
        "polarity_modality_accuracy":sum(int(det[e].get("polarity_modality_correct",False)) for e in normals)/len(normals),
        "abstention_accuracy":sum(int(det[e].get("correct",False)) for e in amb)/len(amb),
        "slot_coverage":len(shape["owner"])/len(train_ids),
    }


def aggregate(tasks: list[dict[str,Any]], preds: dict[str,Any], refs: dict[str,Any]) -> dict[str,Any]:
    rows=[]
    for task in tasks:
        tid=str(task["task_id"]); rows.append({"task_id":tid,**score_one(task,preds[tid],refs[tid])})
    n=len(rows)
    return {
        "primary":{
            "training_partition_adjusted_rand_index":sum(r["training_partition_adjusted_rand_index"] for r in rows)/n,
            "unseen_probe_behavior_accuracy":sum(r["unseen_probe_behavior_accuracy"] for r in rows)/n,
            "heldout_denotational_assignment_accuracy":sum(r["heldout_denotational_assignment_accuracy"] for r in rows)/n,
            "exact_discovery_and_grounding_rate":sum(int(r["exact_discovery_and_grounding"]) for r in rows)/n,
        },
        "secondary":{
            "training_partition_pairwise_accuracy":sum(r["training_partition_pairwise_accuracy"] for r in rows)/n,
            "argument_binding_accuracy":sum(r["argument_binding_accuracy"] for r in rows)/n,
            "polarity_modality_accuracy":sum(r["polarity_modality_accuracy"] for r in rows)/n,
            "abstention_accuracy":sum(r["abstention_accuracy"] for r in rows)/n,
            "slot_coverage":sum(r["slot_coverage"] for r in rows)/n,
        },
        "rows":rows,
    }


def metrics_close(a: Any,b: Any) -> bool:
    if isinstance(a,(int,float)) and isinstance(b,(int,float)): return abs(float(a)-float(b))<=1e-12
    if isinstance(a,dict) and isinstance(b,dict): return set(a)==set(b) and all(metrics_close(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list): return len(a)==len(b) and all(metrics_close(x,y) for x,y in zip(a,b))
    return a==b


def audit(runtime: dict[str,Any]) -> dict[str,Any]:
    if runtime.get("protocol")!=EXPECTED_RUNTIME:return fail("RUNTIME_PROTOCOL_MISMATCH")
    if runtime.get("terminal")!="V31_PAIRED_METRICS_READY_AUDIT_REQUIRED":return fail("RUNTIME_TERMINAL_MISMATCH")
    corpus=runtime.get("corpus"); oracle=runtime.get("oracle_validation")
    if not isinstance(corpus,dict) or not isinstance(oracle,dict):return fail("EVIDENCE_BUNDLE_MISSING")
    if oracle.get("authority")!=AUTHORITY or oracle.get("pass") is not True or oracle.get("terminal")!="S1C_V31_ORACLE_VALIDATION_PASS":return fail("ORACLE_VALIDATION_NOT_PASS")
    tasks=corpus.get("tasks")
    if not isinstance(tasks,list) or len(tasks)!=8:return fail("TASK_COUNT_MISMATCH")
    if corpus.get("dataset_digest")!=sha(tasks):return fail("CORPUS_DIGEST_MISMATCH",{"runtime":corpus.get("dataset_digest"),"recomputed":sha(tasks)})
    tids={str(t["task_id"]) for t in tasks}; refs=oracle.get("references") or {}
    if set(refs)!=tids:return fail("REFERENCE_COVERAGE_MISMATCH")

    rawrows=runtime.get("raw_qwen_rows")
    if not isinstance(rawrows,list) or len(rawrows)!=8:return fail("RAW_QWEN_ROW_COUNT")
    qpred={}; invalid=[]
    for row in rawrows:
        tid=str(row.get("task_id") or "")
        if tid not in tids or tid in qpred:return fail("RAW_TASK_ID_INVALID_OR_DUPLICATE",tid)
        raw=row.get("raw")
        if not isinstance(raw,str) or raw_sha(raw)!=row.get("raw_sha256"):return fail("RAW_HASH_MISMATCH",tid)
        task=next(t for t in tasks if str(t["task_id"])==tid)
        if sha(task["visible"])!=row.get("visible_sha256"):return fail("VISIBLE_HASH_MISMATCH",tid)
        try:
            parsed=json.loads(raw)
        except Exception:
            invalid.append({"task_id":tid,"raw_prefix":raw[:160]}); parsed=None
        if parsed!=row.get("prediction"):return fail("RAW_REPARSE_MISMATCH",tid)
        qpred[tid]=parsed
    if invalid:return fail("PARSER_FAILURE_RATE_NONZERO",invalid)

    dpred=runtime.get("deterministic_predictions")
    if not isinstance(dpred,dict) or set(dpred)!=tids:return fail("DETERMINISTIC_PREDICTION_COVERAGE")
    try:
        dscore=aggregate(tasks,dpred,refs); qscore=aggregate(tasks,qpred,refs)
    except Exception as exc:
        return fail("INDEPENDENT_RECOMPUTATION_FAILED",repr(exc))

    arms=runtime.get("arms") or {}
    for name,recomputed in (("deterministic",dscore),("qwen25_1p5b",qscore)):
        recorded=arms.get(name) or {}
        projection={"primary":recorded.get("primary"),"secondary":recorded.get("secondary")}
        expected={"primary":recomputed["primary"],"secondary":recomputed["secondary"]}
        if not metrics_close(projection,expected):return fail("METRIC_RECOMPUTATION_MISMATCH",{"arm":name,"recorded":projection,"recomputed":expected})
    deltas={k:qscore["primary"][k]-dscore["primary"][k] for k in dscore["primary"]}
    if not metrics_close(deltas,runtime.get("primary_deltas_qwen_minus_deterministic")):return fail("DELTA_RECOMPUTATION_MISMATCH")

    return {
        "protocol":PROTOCOL,"pass":True,"terminal":"S1C_V31_POSTRUN_AUDIT_PASS",
        "dataset_digest":corpus["dataset_digest"],"raw_qwen_rows_verified":8,"parser_failure_rate":0.0,
        "deterministic":{"primary":dscore["primary"],"secondary":dscore["secondary"]},
        "qwen25_1p5b":{"primary":qscore["primary"],"secondary":qscore["secondary"]},
        "primary_deltas_qwen_minus_deterministic":deltas,
        "result_overturning_gate_failures":0,"model_reinference":False,"final_branch_authorized":False,
        "required_next_gate":"S1C_V31_FIXED_B2_CAUSAL_REPLAY"
    }


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("runtime",type=Path);ap.add_argument("--output",type=Path);args=ap.parse_args()
    out=audit(json.loads(args.runtime.read_text(encoding="utf-8"))); text=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    if args.output:args.output.write_text(text,encoding="utf-8")
    print(text,end="");return 0 if out.get("pass") else 3


if __name__=="__main__":raise SystemExit(main())
