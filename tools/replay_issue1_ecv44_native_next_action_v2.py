#!/usr/bin/env python3
"""Replay native EC next-action V2 on real frozen 17-case historical dataset.

This is NOT original Phase1 A-E, a full EC S3/S4 measure, an LLM0 comparison,
or independent heldout. It reconstructs actual pinned EC execution safely.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL="ISSUE1_ACTUAL_ECV44_NATIVE_NEXT_ACTION_REPLAY_V2"
ORIGINAL_EC="d5ec423968f1c9242c590e5e77ccfd92d1f59eb2"
FIXTURE_SHA="12faa9a4cacf0c91694d25f1ccce45e093d95e44"
CONTRACT_SHA="af2b29c3fbd6318fc8083bfd8035eb053d3d8304"
PINS={
 "ec_next_action_authority.py":"89806d27da266de9bb8a9541129fc47722dea36c",
 "ec_dynamic_frontier.py":"3cb8eb34c49d90edf2b2fd9bf10f47bb52d38147",
 "v4/ec_issue_definition_gate.py":"cfa5085cde33cd4629583392adcc7ed088ad10b1",
 "v4/ec_equation_contract.py":"16962f1eecfb3822395fd24c9d12f092f07a3d9f",
 "v4/ec_execution_semantics.py":"29814179c19bee3154807be475516173bbe841ef",
 "v4/ec_variable_space_revision.py":"1c1a41a510271ac121cc4c629937296daffef861",
}

def blob_sha(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def digest(obj)->str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def verify(ec_root:Path,fixture:Path,contract:Path)->Path:
    if not (ec_root/".git").exists():raise ValueError("EC_PINNED_GIT_CHECKOUT_REQUIRED")
    p=subprocess.run(["git","-C",str(ec_root),"rev-parse","HEAD"],text=True,capture_output=True,timeout=12)
    if p.returncode or p.stdout.strip()!=ORIGINAL_EC:raise ValueError("EC_SOURCE_COMMIT_MISMATCH")
    if not fixture.is_file() or blob_sha(fixture.read_bytes())!=FIXTURE_SHA:
        raise ValueError("FROZEN_FIXTURE_BLOB_MISMATCH")
    if not contract.is_file() or blob_sha(contract.read_bytes())!=CONTRACT_SHA:
        raise ValueError("FROZEN_CONTRACT_BLOB_MISMATCH")
    src=ec_root/"01_repo/src"
    for path,sha in PINS.items():
        actual=src/("v4/"+path if path in ("ec_next_action_authority.py","ec_dynamic_frontier.py") else path)
        if not actual.is_file() or blob_sha(actual.read_bytes())!=sha:
            raise ValueError("EC_NATIVE_SOURCE_BLOB_MISMATCH:"+path)
    return src

def modules(src:Path):
    # Exact historical V2 vendor resolution imports the v4 versions before the base src.
    sys.path[:0]=[str(src/"v4"),str(src)]
    importlib.invalidate_caches()
    for name in ("ec_next_action_authority","ec_dynamic_frontier"):
        if name in sys.modules:
            existing=Path(sys.modules[name].__file__).resolve(strict=True)
            expected=(src/"v4"/(name+".py")).resolve(strict=True)
            if existing!=expected or blob_sha(existing.read_bytes())!=PINS[name+".py"]:
                raise ValueError("IMPORTED_MODULE_CACHE_NOT_PINNED:"+name)
    ena=importlib.import_module("ec_next_action_authority")
    df=importlib.import_module("ec_dynamic_frontier")
    for name,module in (("ec_next_action_authority.py",ena),("ec_dynamic_frontier.py",df)):
        if Path(module.__file__).resolve(strict=True)!=(src/"v4"/name).resolve(strict=True):
            raise ValueError("NATIVE_IMPORT_PATH_DRIFT:"+name)
    return ena,df

def public_fields(fx:dict)->dict:
    keys=("plan","completed_work_ids","blocked_work","dynamic_spec")
    x={key:fx[key] for key in keys if key in fx}
    if "oracle" in json.dumps(x).lower() or "gold" in json.dumps(x).lower():
        raise ValueError("PRIVILEGED_PREDICTOR_INPUT")
    return x

def native_predict(ena,df,x:dict)->tuple[dict,dict|None]:
    if set(x)-{"plan","completed_work_ids","blocked_work","dynamic_spec"}:
        raise ValueError("UNDECLARED_NATIVE_INPUT")
    plan=x["plan"];done=x.get("completed_work_ids") or [];blocked=x.get("blocked_work") or {}
    kwargs={};dynamic=None
    if x.get("dynamic_spec"):
        s=x["dynamic_spec"]
        ctx={"protocol":df.PROTOCOL,"plan_digest":df.plan_digest(plan),
             "state_revision":s["state_revision"],"dependency_graph":s["dependency_graph"],
             "issue_state":s["issue_state"],"completed_work_ids":sorted(done),
             "blocked_work":blocked,"observation_ref":f"auth:{s['state_revision']}"}
        ctx["state_digest"]=df.state_digest(ctx);dynamic=ctx
        def authority(ref,digest,revision):
            return ref==f"auth:{revision}" and digest==ctx["state_digest"]
        kwargs={"dynamic_context":ctx,"dynamic_state_authority":authority}
    try:
        out=ena.select_next_action(plan,completed_work_ids=done,blocked_work=blocked,**kwargs)
        status=out["status"];work=out.get("work_id") or "NONE";reason="NONE"
        if status=="BLOCKED":reason="ALL_REMAINING_WORK_BLOCKED"
        elif status=="NO_OPEN_WORK":reason="NO_OPEN_WORK"
        elif status=="REFRAME":reason="ISSUE_DEFINITION_REFRAME"
        return {"status":status,"work_id":work,"reason_code":reason},dynamic
    except Exception as e:
        msg=str(e)
        reason=msg.split(":",1)[0] if msg.startswith("PRIOR_ART_GATE_PASS_REQUIRED:") else msg
        return {"status":"FAIL_CLOSED","work_id":"NONE","reason_code":reason},dynamic

def replay(ec_root:Path,*,fixture:Path|None=None,contract:Path|None=None)->dict:
    fixture=fixture or ROOT/"fixtures/function_boundary_next_action_v1.json"
    contract=contract or ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json"
    src=verify(ec_root,fixture,contract)
    frozen=json.loads(fixture.read_text());policy=json.loads(contract.read_text())
    if frozen["status"]!="FROZEN_BEFORE_MODEL_RUN" or frozen["fixture_count"]!=17 or len(frozen["fixtures"])!=17:
        raise ValueError("FIXTURE_COVERAGE_NOT_FROZEN")
    if policy["status"]!="FROZEN_BEFORE_MODEL_RUN" or policy["fixture_oracle_mutation"] is not False or policy["fixture_count"]!=17:
        raise ValueError("CONTRACT_NOT_FROZEN")
    ena,df=modules(src);rows=[]
    for fx in frozen["fixtures"]:
        visible=public_fields(fx)
        predicted,dynamic=native_predict(ena,df,visible)
        gold=fx["oracle"]  # evaluator-only; read after predictor returns
        rows.append({
          "case_id":fx["id"],"public_input_sha256":digest(visible),
          "native_dynamic_sha256":digest(dynamic) if dynamic else None,
          "prediction":predicted,"raw_prediction_sha256":digest(predicted),
          "frozen_gold":gold,
          "decision_correct":predicted["status"]==gold["status"] and predicted["work_id"]==gold["work_id"],
          "reason_correct":predicted["reason_code"]==gold["reason_code"],
        })
    if len({r["case_id"] for r in rows})!=17:raise ValueError("DUPLICATE_CASES")
    correct=sum(r["decision_correct"] for r in rows)
    reasons=sum(r["reason_correct"] for r in rows)
    old=json.loads((ROOT/"results/function_boundary_next_action_v2_actual_2026-10-03.json").read_text())
    if old["fixture_blob_sha"]!=FIXTURE_SHA or old["ec"]["commit"]!=ORIGINAL_EC:
        raise ValueError("HISTORICAL_SOURCE_PROVENANCE_CHANGED")
    return {
     "protocol":PROTOCOL,"source_ec_commit":ORIGINAL_EC,"source_blobs":PINS,
     "frozen_fixture_git_sha1":FIXTURE_SHA,"frozen_contract_git_sha1":CONTRACT_SHA,
     "cases_replayed":17,"ec_decision_correct":correct,"ec_reason_correct":reasons,
     "prior_report_ec_decision_correct":old["ec"]["decision_correct"],
     "prior_report_ec_reason_correct":old["ec"]["reason_correct"],
     "historical_ec_aggregate_reproduced":correct==old["ec"]["decision_correct"] and reasons==old["ec"]["reason_correct"],
     "rows":rows,
     "original_llm0_compared":False,"llm_reinferred":False,
     "original_phase1_five_arm_complete":False,"independent_holdout":False,
     "native_scope":"governed remediation-plan singleton next-action authority only; not generic S3 multiselection / S4 closure",
     "terminal":"NATIVE_EC_17_CASE_REPLAY_MATCH" if correct==17 and reasons==17 else "NATIVE_EC_17_CASE_REPLAY_DIVERGED",
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--ec-root",type=Path,required=True)
    a=ap.parse_args()
    try:
        result=replay(a.ec_root)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
        return 0 if result["terminal"]=="NATIVE_EC_17_CASE_REPLAY_MATCH" else 3
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:350]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
