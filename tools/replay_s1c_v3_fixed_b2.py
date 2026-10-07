from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from typing import Any
from s2b2b2_enumerative_inducer import apply_schema

PROTOCOL="S1C_V3_FIXED_B2_CAUSAL_REPLAY_V1"
SOLVER_BLOB="3ea2365b7d49f766fbdc14fd82c6ca44b2d29eb9"
EXPECTED_RUNTIME="FUNCTION_BOUNDARY_S1C_V3_PAIRED_V1"
TRUTH_PATH=Path(__file__).resolve().with_name("s1c_v3_reference_truth_tables.json")
TRUTH=json.loads(TRUTH_PATH.read_text())

def file_blob_sha(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def candidates(obs):
    out=set()
    for rid,table in TRUTH.items():
        if all(table.get("".join(map(str,o["before"])))=="".join(map(str,o["after"])) for o in obs):
            out.add(int(rid))
    return out

def align(task,pred):
    if not isinstance(pred,dict): return {}
    slots=pred.get("discovered_slots")
    if not isinstance(slots,list): return {}
    train={x["example_id"]:x for x in task["visible"]["training_examples"]}
    out={}
    for s in slots:
        if not isinstance(s,dict): continue
        sid=s.get("slot_id"); members=s.get("training_members"); types=s.get("arg_types")
        if not isinstance(sid,str) or not isinstance(members,list) or not isinstance(types,list) or not members: continue
        if any(str(m) not in train for m in members): continue
        obs=[]
        for m in members: obs.extend(train[str(m)]["behavior_observations"])
        c=candidates(obs)
        if len(c)==1: out[sid]=(next(iter(c)),tuple(map(str,types)))
    return out

def assignment_map(pred):
    if not isinstance(pred,dict): return {}
    out={}
    for a in pred.get("heldout_assignments",[]):
        if isinstance(a,dict) and isinstance(a.get("example_id"),str): out[a["example_id"]]=a
    return out

def encoded(rule:int,pol:str,mod:str)->str:
    return f"D{rule:02d}__{pol}__{mod}"

def fixed_schema(ref):
    args=list(ref["arguments"]); vars_=[f"$A{i+1}" for i in range(len(args))]
    binding={v:a for v,a in zip(vars_,args)}; binding["$TASK"]="TASK"
    schema={"proposal_kind":"INDUCED_OPERATOR","parameters":vars_+["$TASK"],
            "preconditions":[{"pred":encoded(int(ref["rule"]),ref["polarity"],ref["modality"]),"args":vars_}],
            "add_effects":[{"pred":"GOAL_DONE","args":["$TASK"]}],
            "delete_effects":[{"pred":"PENDING","args":["$TASK"]}]}
    return schema,binding

def replay_one(task,eid,pred,ref):
    amap=assignment_map(pred); row=amap.get(eid)
    if row is None:return {"success":False,"reason":"MISSING_ASSIGNMENT"}
    al=align(task,pred); key=al.get(row.get("slot_id"))
    if key is None:return {"success":False,"reason":"UNALIGNED_SLOT"}
    rule,types=key
    if types!=tuple(ref["arg_types"]): return {"success":False,"reason":"ARG_TYPE_MISMATCH"}
    atom={"pred":encoded(rule,str(row.get("polarity")),str(row.get("modality"))),"args":[str(x) for x in row.get("arguments",[])]}
    schema,binding=fixed_schema(ref)
    res=apply_schema(schema,[atom,{"pred":"PENDING","args":["TASK"]}],binding)
    return {"success":bool(res.get("applicable")),"reason":"FIXED_B2_APPLICABLE" if res.get("applicable") else "FIXED_B2_PRECONDITION_FAIL","derived_rule":rule}

def oracle_one(ref):
    schema,binding=fixed_schema(ref)
    atom={"pred":encoded(int(ref["rule"]),ref["polarity"],ref["modality"]),"args":list(ref["arguments"])}
    res=apply_schema(schema,[atom,{"pred":"PENDING","args":["TASK"]}],binding)
    return bool(res.get("applicable"))

def replay(runtime,corpus,oracle_validation,solver_path:Path):
    if runtime.get("protocol")!=EXPECTED_RUNTIME:
        return {"pass":False,"terminal":"S1C_V3_CAUSAL_REPLAY_FAIL_CLOSED","reason":"RUNTIME_PROTOCOL_MISMATCH"}
    if file_blob_sha(solver_path)!=SOLVER_BLOB:
        return {"pass":False,"terminal":"S1C_V3_CAUSAL_REPLAY_FAIL_CLOSED","reason":"DOWNSTREAM_SOLVER_DRIFT","actual_blob":file_blob_sha(solver_path)}
    refs=oracle_validation["references"]; tasks=corpus["tasks"]
    det=runtime.get("deterministic_predictions") or {}
    qpred={r["task_id"]:r.get("prediction") for r in runtime.get("raw_qwen_rows",[]) if isinstance(r,dict)}
    tids={t["task_id"] for t in tasks}
    if set(det)!=tids or set(qpred)!=tids:
        return {"pass":False,"terminal":"S1C_V3_CAUSAL_REPLAY_FAIL_CLOSED","reason":"PREDICTION_COVERAGE_MISMATCH"}
    rows=[]; on=dn=qn=total=0
    for task in tasks:
        tid=task["task_id"]
        for eid,ref in refs[tid]["heldout_semantics"].items():
            if ref["status"]!="OK": continue
            o=oracle_one(ref)
            if not o:
                return {"pass":False,"terminal":"S1C_V3_CAUSAL_REPLAY_FAIL_CLOSED","reason":"ORACLE_FIXED_B2_FAILED","task_id":tid,"example_id":eid}
            d=replay_one(task,eid,det[tid],ref); q=replay_one(task,eid,qpred[tid],ref)
            on+=1;dn+=int(d["success"]);qn+=int(q["success"]);total+=1
            rows.append({"task_id":tid,"example_id":eid,"oracle":{"success":True},"deterministic":d,"qwen25_1p5b":q})
    return {"protocol":PROTOCOL,"pass":True,"terminal":"S1C_V3_FIXED_B2_CAUSAL_REPLAY_PASS","normal_heldout_count":total,
            "oracle_downstream_success":on/total,"deterministic_downstream_success":dn/total,"qwen25_1p5b_downstream_success":qn/total,
            "qwen_minus_deterministic_downstream":(qn-dn)/total,"rows":rows,
            "solver_contract":{"solver_blob_sha1":SOLVER_BLOB,"solver":"s2b2b2_enumerative_inducer.apply_schema","ambiguous_examples_excluded":True,"arm_varying_input":"predicted upstream semantic assignment only","model_reinference":False}}

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("runtime",type=Path); ap.add_argument("corpus",type=Path); ap.add_argument("oracle",type=Path); ap.add_argument("--solver",type=Path,default=Path(__file__).resolve().with_name("s2b2b2_enumerative_inducer.py")); ap.add_argument("--output",type=Path); args=ap.parse_args()
    runtime=json.loads(args.runtime.read_text(encoding="utf-8")); corpus=json.loads(args.corpus.read_text(encoding="utf-8")); oracle=json.loads(args.oracle.read_text(encoding="utf-8")); out=replay(runtime,corpus,oracle,args.solver)
    if args.output: args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out.get(k) for k in ("protocol","pass","terminal","reason","normal_heldout_count","oracle_downstream_success","deterministic_downstream_success","qwen25_1p5b_downstream_success")},indent=2)); raise SystemExit(0 if out.get("pass") else 3)