#!/usr/bin/env python3
"""One pre-registered real-LLM factor intervention: public gate masks REFRAME.

Reuses byte-exact historical V2 model prompt, GBNF and frozen 17-case state,
changing only grammar root alternative when the public issue-definition gate
is inactive. The actual model outputs are NOT synthesized. The reference gold
is read by the historical scorer after all inputs have been sent, never shown
to the predictor or status gate; no independent/scientific root completion.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools.run_issue1_llm_next_action_v2_local_mac import (
    load_historical,verify as verify_model,run_one_local, MODEL_SHA,
)
from tools.replay_issue1_ecv44_native_next_action_v2 import (
    verify as verify_ec,modules as pinned_modules,native_predict,public_fields,
)
from tools.run_issue1_s3_native_next_action_oracle_causal_v1 import blob

CONTRACT=ROOT/"docs/ISSUE1_NEXT_ACTION_PUBLIC_GATE_GBNF_ABLATION_V1.json"
BASE=ROOT/"results/issue1_qwen_next_action_v2_mac_actual_2026-10-10.json"
FIXTURE=ROOT/"fixtures/function_boundary_next_action_v1.json"
POLICY=ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json"
PROTOCOL="ISSUE1_NEXT_ACTION_PUBLIC_GATE_GBNF_CAUSAL_V1"
ROOT_ORIGINAL="root ::= execute | blocked | noopen | reframe | failclosed"
ROOT_RESTRICTED="root ::= execute | blocked | noopen | failclosed"

def gate_active(case:dict)->bool:
    """No id, category, oracle, correct decision or inferred gold access."""
    if set(case)-{"plan","completed_work_ids","blocked_work","dynamic_spec"}:
        raise ValueError("PRIVILEGED_GATE_FIELDS_FORBIDDEN")
    return any("action_class" in issue or "issue_contract" in issue
               for issue in case["plan"]["issues"])

def treatment_grammar(original:str,case:dict)->tuple[str,bool]:
    if not original.startswith(ROOT_ORIGINAL+"\n"):
        raise ValueError("HISTORICAL_GBNF_ROOT_CHANGED")
    active=gate_active(case)
    if active:
        return original,True
    return original.replace(ROOT_ORIGINAL,ROOT_RESTRICTED,1),False

def audit_frozen(model:Path,llama:Path,ec_root:Path)->tuple[dict,dict,dict]:
    v=json.loads(CONTRACT.read_text())
    if v["protocol"]!=PROTOCOL or v["status"]!="FROZEN_BEFORE_PREDICTIONS":
        raise ValueError("NOT_PREREGISTERED")
    if v["case_count"]!=17 or v["frozen_model_sha256"]!=MODEL_SHA:
        raise ValueError("FROZEN_STUDY_ASSUMPTIONS_CHANGED")
    files=[(FIXTURE,v["fixture_git_blob"]), (BASE,v["existing_real_baseline_report_git_blob"])]
    for path,expected in files:
        if not path.is_file() or blob(path)!=expected:
            raise ValueError("HISTORICAL_FILE_BLOB_CHANGED:"+path.name)
    archived=load_historical()
    if blob(ROOT/"verification/issue1_next_action_v2/archived_original_runner_2026_10_03.py")!=v["archived_historical_runner_git_blob"]:
        raise ValueError("ARCHIVED_PROMPT_SOURCE_CHANGED")
    verify_model(model,llama)
    src=verify_ec(ec_root,FIXTURE,POLICY)
    if ec_root.resolve().joinpath(".git").exists() is False:
        raise ValueError("PINNED_NATIVE_CHECKOUT_REQUIRED")
    fixture=json.loads(FIXTURE.read_text())
    policy=json.loads(POLICY.read_text())
    return v,fixture,policy

def actual_run(model:Path,llama:Path,ec_root:Path,seconds:int=90)->dict:
    contract,fixture,policy=audit_frozen(model,llama,ec_root)
    archived=load_historical()
    src=ec_root/"01_repo/src"
    ena,df=pinned_modules(src)
    ec_rows=[]
    for c in fixture["fixtures"]:
        visible=public_fields(c)
        _native,dynamic=native_predict(ena,df,visible)
        ec_rows.append({"dynamic_context":dynamic})

    recorded=[]
    def local_post(_server_url,payload,timeout=180):
        k=len(recorded)
        if k>=len(fixture["fixtures"]):
            raise RuntimeError("MORE_MODEL_CALLS_THAN_CASES")
        fc=fixture["fixtures"][k]
        visible=public_fields(fc)
        modified,active=treatment_grammar(payload["grammar"],visible)
        # The case-specific original prompt is preserved byte-for-byte;
        # gate is chosen from the public plan only, not the oracle outcome.
        q=run_one_local(model=model,binary=llama.resolve(strict=True),
                        prompt=payload["prompt"],grammar=modified,seconds=seconds)
        recorded.append({
          "case_id":fc["id"],"public_gate_active":active,
          "canonical_visible_sha256":hashlib.sha256(json.dumps(visible,sort_keys=True,
                   ensure_ascii=False,separators=(",",":")).encode()).hexdigest(),
          "historical_prompt_sha256":hashlib.sha256(payload["prompt"].encode()).hexdigest(),
          "original_GBNF_sha256":hashlib.sha256(payload["grammar"].encode()).hexdigest(),
          "treated_GBNF_sha256":hashlib.sha256(modified.encode()).hexdigest(),
          "root_choice":modified.splitlines()[0],
          "raw_response":q["raw_response"],"stdout_sha256":q["stdout_sha256"],
          "stderr_sha256":q["stderr_sha256"],
          "only_GBNF_root_modified":modified==payload["grammar"] if active else
                modified==payload["grammar"].replace(ROOT_ORIGINAL,ROOT_RESTRICTED,1),
          "all_hidden_reference_data_excluded":True,
        })
        print("CASE_REAL_MODEL_DONE:"+str(k+1)+"/17",file=sys.stderr,flush=True)
        return {"content":q["raw_response"]}
    archived.post_json=local_post
    with contextlib.redirect_stdout(io.StringIO()):
        rows=archived.run_llm("LOCAL_PINNED_QWEN",fixture,policy,ec_rows)
    if len(rows)!=17 or len(recorded)!=17:
        raise RuntimeError("REAL_MODEL_OUTPUT_COVERAGE_INCOMPLETE")
    for case,record,row in zip(fixture["fixtures"],recorded,rows):
        if record["case_id"]!=case["id"] or row["fixture_id"]!=case["id"]:
            raise ValueError("CASE_ALIGNMENT_MISMATCH")
        if not record["only_GBNF_root_modified"]:
            raise ValueError("GRAMMAR_CHANGED_OUTSIDE_PREREG_FACTOR")
        if record["raw_response"]!=row["raw"]:
            raise ValueError("MODEL_SCORER_RAW_RESPONSE_DIVERGED")
    baseline=json.loads(BASE.read_text())["run"]
    old=baseline["llm"]["rows"]
    if len(old)!=17 or baseline["llm_actual_inference_count"]!=17:
        raise ValueError("HISTORICAL_MODEL_PAIR_MISSING")
    paired=[]
    for oldrow,newrow,raw in zip(old,rows,recorded):
        if oldrow["fixture_id"]!=newrow["fixture_id"] or oldrow["fixture_id"]!=raw["case_id"]:
            raise ValueError("MODEL_CASE_ORDER_CHANGED")
        same_prompt=raw["historical_prompt_sha256"]==baseline["raw_inference"][len(paired)]["prompt_sha256"]
        same_orig_grammar=raw["original_GBNF_sha256"]==baseline["raw_inference"][len(paired)]["grammar_sha256"]
        if not same_prompt or not same_orig_grammar:
            raise ValueError("FROZEN_BASELINE_PROMPT_OR_GRAMMAR_MISMATCH")
        paired.append({
          "id":newrow["fixture_id"],"public_gate_active":raw["public_gate_active"],
          "baseline":oldrow["prediction"],"treatment":newrow["prediction"],
          "baseline_exact_decision_correct":oldrow["decision_correct"],
          "treatment_exact_decision_correct":newrow["decision_correct"],
          "baseline_reason_correct":oldrow["reason_correct"],
          "treatment_reason_correct":newrow["reason_correct"],
          "prompt_byte_identity":same_prompt,"baseline_GBNF_byte_identity":same_orig_grammar,
          "treated_GBNF_root":raw["root_choice"],
          "raw_real_inference":raw,
        })
    old_count=sum(row["baseline_exact_decision_correct"] for row in paired)
    new_count=sum(row["treatment_exact_decision_correct"] for row in paired)
    gain=(new_count-old_count)/17
    return {
      "protocol":PROTOCOL,"contract_git_blob":blob(CONTRACT),
      "original_fixture_blob":blob(FIXTURE),"original_qwen_actual_blob":blob(BASE),
      "actual_model_calls":len(recorded),"actual_model_pin":MODEL_SHA,
      "baseline_decision_correct":old_count,"gate_treatment_decision_correct":new_count,
      "paired_accuracy_gain":gain,"materiality_threshold":contract["frozen_analysis"]["materiality_threshold"],
      "material_effect_on_exposed_cases":gain>=contract["frozen_analysis"]["materiality_threshold"],
      "gate_inactive_count":sum(not row["public_gate_active"] for row in paired),
      "gate_active_count":sum(row["public_gate_active"] for row in paired),
      "treatment_REFRAME_count":sum(row["treatment"]["status"]=="REFRAME" for row in paired),
      "paired_cases":paired,"independent_unseen_gold":False,
      "all_Qwen_predictions_genuine_new_inference":True,
      "original_S1_S4_five_arm_complete":False,"original_issue_closure_authorized":False,
      "terminal":"ISSUE1_REAL_PINNED_QWEN_GBNF_ROOT_INTERVENTION_COMPLETE",
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--llama-cli",type=Path,required=True)
    p.add_argument("--ec-root",type=Path,required=True)
    p.add_argument("--seconds",type=int,default=90)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        v=actual_run(a.model,a.llama_cli,a.ec_root,a.seconds)
        encoded=json.dumps(v,sort_keys=True,indent=2,ensure_ascii=False)+"\n"
        if a.out:
            a.out.write_text(encoded)
            print(json.dumps({"terminal":v["terminal"],"baseline":v["baseline_decision_correct"],
               "treated":v["gate_treatment_decision_correct"],
               "gain":v["paired_accuracy_gain"],"actual_model_calls":v["actual_model_calls"],
               "out":str(a.out)}))
        else:print(encoded,end="")
        return 0
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:500]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
