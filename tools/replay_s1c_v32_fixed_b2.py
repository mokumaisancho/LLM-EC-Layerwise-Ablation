#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

import replay_s1c_v31_fixed_b2 as v31

PROTOCOL="S1C_V32_FIXED_B2_CAUSAL_REPLAY_V1"
EXPECTED_RUNTIME="FUNCTION_BOUNDARY_S1C_V32_PAIRED_V1"
EXPECTED_AUDIT="S1C_V32_POSTRUN_AUDIT_PASS"
SOLVER_BLOB="3ea2365b7d49f766fbdc14fd82c6ca44b2d29eb9"

def blob(path):
    raw=path.read_bytes();h=hashlib.sha1();h.update(f"blob {len(raw)}\0".encode());h.update(raw);return h.hexdigest()

def replay(runtime,audit,solver):
    if runtime.get("protocol")!=EXPECTED_RUNTIME:return {"pass":False,"terminal":"S1C_V32_CAUSAL_REPLAY_FAIL_CLOSED","reason":"RUNTIME_PROTOCOL_MISMATCH"}
    if audit.get("terminal")!=EXPECTED_AUDIT or audit.get("pass") is not True:return {"pass":False,"terminal":"S1C_V32_CAUSAL_REPLAY_FAIL_CLOSED","reason":"POSTRUN_AUDIT_NOT_PASS"}
    got=blob(solver)
    if got!=SOLVER_BLOB:return {"pass":False,"terminal":"S1C_V32_CAUSAL_REPLAY_FAIL_CLOSED","reason":"DOWNSTREAM_SOLVER_DRIFT","actual_blob":got}
    refs=runtime["oracle_validation"]["references"];dp=runtime["deterministic_predictions"];qp={r["task_id"]:json.loads(r["raw"]) for r in runtime["raw_qwen_rows"]}
    d_invalid={x["task_id"] for x in audit["deterministic"].get("semantic_invalid_tasks",[])}
    q_invalid={x["task_id"] for x in audit["qwen25_1p5b"].get("semantic_invalid_tasks",[])}
    total=on=dn=qn=0;rows=[]
    for tid in sorted(refs):
        ref=refs[tid]
        for eid in sorted(ref["heldout"]):
            rr=ref["heldout"][eid]
            if rr["status"]!="OK":continue
            o=v31.oracle_one(rr)
            if not o:return {"pass":False,"terminal":"S1C_V32_CAUSAL_REPLAY_FAIL_CLOSED","reason":"ORACLE_FIXED_B2_FAILED","task_id":tid,"example_id":eid}
            d=False if tid in d_invalid else v31.replay_one(dp[tid],ref,eid)
            q=False if tid in q_invalid else v31.replay_one(qp[tid],ref,eid)
            total+=1;on+=int(o);dn+=int(d);qn+=int(q)
            rows.append({"task_id":tid,"example_id":eid,"oracle":{"success":o},"deterministic":{"success":d},"qwen25_1p5b":{"success":q},
                         "deterministic_semantic_invalid":tid in d_invalid,"qwen_semantic_invalid":tid in q_invalid})
    return {"protocol":PROTOCOL,"pass":True,"terminal":"S1C_V32_FIXED_B2_CAUSAL_REPLAY_PASS","normal_heldout_count":total,
            "oracle_downstream_success":on/total,"deterministic_downstream_success":dn/total,"qwen25_1p5b_downstream_success":qn/total,
            "qwen_minus_deterministic_downstream":(qn-dn)/total,"rows":rows,
            "solver_contract":{"solver_blob_sha1":SOLVER_BLOB,"semantic_invalid_task_downstream_score":0.0,
                               "ambiguous_examples_excluded":True,"model_reinference":False}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("runtime",type=Path);ap.add_argument("audit",type=Path);ap.add_argument("--solver",type=Path,default=Path(__file__).resolve().with_name("s2b2b2_enumerative_inducer.py"));ap.add_argument("--output",type=Path);args=ap.parse_args()
    out=replay(json.loads(args.runtime.read_text()),json.loads(args.audit.read_text()),args.solver);txt=json.dumps(out,indent=2)+"\n"
    if args.output:args.output.write_text(txt)
    print(txt,end="");return 0 if out.get("pass") else 3
if __name__=="__main__":raise SystemExit(main())
