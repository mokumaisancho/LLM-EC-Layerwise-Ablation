#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

from s2b2b2_enumerative_inducer import apply_schema

PROTOCOL="S1C_V31_FIXED_B2_CAUSAL_REPLAY_V1"
EXPECTED_RUNTIME="FUNCTION_BOUNDARY_S1C_V31_PAIRED_V1"
EXPECTED_AUDIT="S1C_V31_POSTRUN_AUDIT_PASS"
SOLVER_BLOB="3ea2365b7d49f766fbdc14fd82c6ca44b2d29eb9"
EVAL_IDS=("Q03","Q05","Q06","Q07")


def blob_sha(path:Path)->str:
    raw=path.read_bytes();h=hashlib.sha1();h.update(f"blob {len(raw)}\0".encode());h.update(raw);return h.hexdigest()


def eval_map(rows:Any):
    if not isinstance(rows,list) or len(rows)!=4:return None
    out={}
    for row in rows:
        if not isinstance(row,dict):return None
        pid=str(row.get("probe_id") or "");bits=row.get("predicted_after")
        if pid not in EVAL_IDS or pid in out or not isinstance(bits,list) or len(bits)!=3 or any(x not in (0,1) for x in bits):return None
        out[pid]=tuple(bits)
    return out if set(out)==set(EVAL_IDS) else None


def shape(pred:Any):
    if not isinstance(pred,dict):return None
    slots=pred.get("discovered_slots");assigns=pred.get("heldout_assignments");abst=pred.get("abstentions")
    if not all(isinstance(x,list) for x in (slots,assigns,abst)):return None
    sev={};types={}
    for s in slots:
        if not isinstance(s,dict) or not isinstance(s.get("slot_id"),str):return None
        em=eval_map(s.get("evaluation_probe_predictions"))
        if em is None:return None
        sev[s["slot_id"]]=em;types[s["slot_id"]]=tuple(s.get("arg_types") or ())
    amap={str(r.get("example_id")):r for r in assigns if isinstance(r,dict)}
    return {"eval":sev,"types":types,"assign":amap}


def ref_eval(ref):
    out={}
    for key,item in ref["slot_references"].items():
        em=eval_map(item["evaluation_probe_expected"])
        if em is None:raise ValueError("REFERENCE_EVAL_INVALID")
        out[str(key)]=em
    return out


def alignment(pred:Any,ref:dict[str,Any]):
    s=shape(pred)
    if s is None:return None
    pids=sorted(s["eval"]);gids=sorted(ref["slot_references"])
    if len(gids)!=2 or len(pids)<2:return None
    ge=ref_eval(ref);best=[];bestscore=-1
    for chosen in itertools.permutations(pids,2):
        m={p:g for p,g in zip(chosen,gids)};score=0
        for p,g in m.items():
            if s["types"][p]!=tuple(ref["slot_references"][g]["arg_types"]):continue
            score+=sum(int(s["eval"][p][q]==ge[g][q]) for q in EVAL_IDS)
        if score>bestscore:bestscore=score;best=[m]
        elif score==bestscore:best.append(m)
    if not best:return None
    return min(best,key=lambda m:tuple(sorted(m.items())))


def encoded(target:str,pol:str,mod:str)->str:
    return f"D{target}__{pol}__{mod}"


def fixed_schema(refrow:dict[str,Any]):
    args=[str(x) for x in refrow["arguments"]];vars_=[f"$A{i+1}" for i in range(len(args))];binding={v:a for v,a in zip(vars_,args)};binding["$TASK"]="TASK"
    schema={"proposal_kind":"INDUCED_OPERATOR","parameters":vars_+["$TASK"],
            "preconditions":[{"pred":encoded(refrow["target_code"],refrow["polarity"],refrow["modality"]),"args":vars_}],
            "add_effects":[{"pred":"GOAL_DONE","args":["$TASK"]}],
            "delete_effects":[{"pred":"PENDING","args":["$TASK"]}]}
    return schema,binding


def replay_one(pred:Any,ref:dict[str,Any],eid:str)->bool:
    rowref=ref["heldout"][eid];s=shape(pred);m=alignment(pred,ref)
    if s is None or m is None:return False
    row=s["assign"].get(eid)
    if not isinstance(row,dict):return False
    mapped=m.get(row.get("slot_id"))
    if mapped is None:return False
    atom={"pred":encoded(mapped,str(row.get("polarity")),str(row.get("modality"))),"args":[str(x) for x in row.get("arguments") or []]}
    schema,binding=fixed_schema(rowref)
    result=apply_schema(schema,[atom,{"pred":"PENDING","args":["TASK"]}],binding)
    return bool(result.get("applicable"))


def oracle_one(refrow:dict[str,Any])->bool:
    schema,binding=fixed_schema(refrow)
    atom={"pred":encoded(refrow["target_code"],refrow["polarity"],refrow["modality"]),"args":[str(x) for x in refrow["arguments"]]}
    return bool(apply_schema(schema,[atom,{"pred":"PENDING","args":["TASK"]}],binding).get("applicable"))


def replay(runtime:dict[str,Any],audit:dict[str,Any],solver:Path)->dict[str,Any]:
    if runtime.get("protocol")!=EXPECTED_RUNTIME:return {"pass":False,"terminal":"S1C_V31_CAUSAL_REPLAY_FAIL_CLOSED","reason":"RUNTIME_PROTOCOL_MISMATCH"}
    if audit.get("terminal")!=EXPECTED_AUDIT or audit.get("pass") is not True:return {"pass":False,"terminal":"S1C_V31_CAUSAL_REPLAY_FAIL_CLOSED","reason":"POSTRUN_AUDIT_NOT_PASS"}
    got=blob_sha(solver)
    if got!=SOLVER_BLOB:return {"pass":False,"terminal":"S1C_V31_CAUSAL_REPLAY_FAIL_CLOSED","reason":"DOWNSTREAM_SOLVER_DRIFT","actual_blob":got}
    oracle=runtime["oracle_validation"];refs=oracle["references"];dp=runtime["deterministic_predictions"]
    qp={}
    for row in runtime["raw_qwen_rows"]:
        try:qp[row["task_id"]]=json.loads(row["raw"])
        except Exception:return {"pass":False,"terminal":"S1C_V31_CAUSAL_REPLAY_FAIL_CLOSED","reason":"QWEN_RAW_PARSE_FAIL"}
    total=on=dn=qn=0;rows=[]
    for tid in sorted(refs):
        ref=refs[tid]
        for eid in sorted(ref["heldout"]):
            rr=ref["heldout"][eid]
            if rr["status"]!="OK":continue
            o=oracle_one(rr)
            if not o:return {"pass":False,"terminal":"S1C_V31_CAUSAL_REPLAY_FAIL_CLOSED","reason":"ORACLE_FIXED_B2_FAILED","task_id":tid,"example_id":eid}
            d=replay_one(dp[tid],ref,eid);q=replay_one(qp[tid],ref,eid)
            total+=1;on+=int(o);dn+=int(d);qn+=int(q)
            rows.append({"task_id":tid,"example_id":eid,"oracle":{"success":o},"deterministic":{"success":d},"qwen25_1p5b":{"success":q}})
    return {"protocol":PROTOCOL,"pass":True,"terminal":"S1C_V31_FIXED_B2_CAUSAL_REPLAY_PASS","normal_heldout_count":total,
            "oracle_downstream_success":on/total,"deterministic_downstream_success":dn/total,"qwen25_1p5b_downstream_success":qn/total,
            "qwen_minus_deterministic_downstream":(qn-dn)/total,"rows":rows,
            "solver_contract":{"solver_blob_sha1":SOLVER_BLOB,"solver":"s2b2b2_enumerative_inducer.apply_schema","ambiguous_examples_excluded":True,
                               "arm_varying_input":"predicted upstream semantic assignment only","model_reinference":False}}


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("runtime",type=Path);ap.add_argument("audit",type=Path);ap.add_argument("--solver",type=Path,default=Path(__file__).resolve().with_name("s2b2b2_enumerative_inducer.py"));ap.add_argument("--output",type=Path);args=ap.parse_args()
    out=replay(json.loads(args.runtime.read_text()),json.loads(args.audit.read_text()),args.solver);txt=json.dumps(out,indent=2)+"\n"
    if args.output:args.output.write_text(txt,encoding="utf-8")
    print(txt,end="");return 0 if out.get("pass") else 3


if __name__=="__main__":raise SystemExit(main())
