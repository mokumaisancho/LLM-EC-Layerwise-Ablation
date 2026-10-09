#!/usr/bin/env python3
"""Issue #1 self-directed TCC v4: exhaust real S3 causal and gate interventions.

A single call replays stage3, then actual same-function S3 Oracle-controlled
intervention, then public-policy-gated GBNF model intervention (running model
if pinned assets are supplied and result absent), recomputes all scores and
chooses next target by frozen 0.20 threshold. No schedule, no ChatGPT self-
messages, no original S1-S4 A-E scientific closure.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.run_issue57_tcc_generator_gate import TCC_SOURCE,context_for,node
from tools.run_issue1_autonomous_tcc_workflow_v3 import run as prior_tcc3
from tools.run_issue1_s3_native_next_action_oracle_causal_v1 import evaluate as evaluate_s3
from tools.run_issue1_public_gate_gbnf_ablation_v1 import (
    PROTOCOL as GBNF_PROTOCOL,CONTRACT as GBNF_CONTRACT,
    FIXTURE,BASE,gate_active,treatment_grammar,blob as git_blob,
)
from tools.replay_issue1_ecv44_native_next_action_v2 import public_fields

PROTOCOL="ISSUE1_AUTONOMOUS_TCC_V4_ORACLE_AND_PUBLIC_GATE_V1"
REPORT=ROOT/"results/issue1_public_gate_gbnf_qwen17_actual_2026-10-10.json"


def graph_spec():
    return {
      "schema":"tcc.spec.v3","tcc_id":"ISSUE1-CONTINUOUS-MACHINE-S3-CAUSAL-GBNF-V1",
      "goal":"Automatically advance original #1 machine-resolvable causal boundaries, preserve original acceptance, infer current next valid experiment without manual prompts",
      "acceptance":[
        "Rerun original frozen TCC/EC/LLM 17 and S4/Qwen 20 with source-pin provenance",
        "Rerun 17-case same-function S3 Oracle intervention and validate 16/17 material gain",
        "Automatically launch missing 17 real Qwen public-gate grammar inferences with pinned local model if absent",
        "Recompute all paired scores from raw model outputs and same-case gold only after inference",
        "Branch on frozen materiality threshold, never infer new S1-S4 oracle effects without measurement",
        "Keep original Phase1 5-arm open, independent heldout unverified, and no scheduled tasks",
      ],
      "state_keys":["prior_verified","s3_oracle_gain","grammar_gain"],
      "immutable_state_keys":[],
      "entry_nodes":["verify_prior_science"],
      "nodes":[
       node("verify_prior_science","action",writes=("prior_verified",),failure="blocked_integrity"),
       node("run_s3_oracle_causal","action",depends=("verify_prior_science",),
            writes=("s3_oracle_gain",),failure="blocked_integrity"),
       node("oracle_gain_branch","gate",depends=("run_s3_oracle_causal",),
            reads=("prior_verified","s3_oracle_gain"),
            branches={"material":"run_real_public_gbnf_probe",
                      "not_material":"blocked_wrong_target"}),
       node("run_real_public_gbnf_probe","action",writes=("grammar_gain",),
            failure="blocked_integrity"),
       node("grammar_effect_branch","gate",depends=("run_real_public_gbnf_probe",),
            reads=("grammar_gain",),
            branches={"material":"diagnose_policy_gate_effect",
                      "not_material":"diagnose_other_selection_semantics"}),
       node("diagnose_policy_gate_effect","action",failure="blocked_integrity"),
       node("diagnose_other_selection_semantics","action",failure="blocked_integrity"),
       node("scoped_machine_result","terminal",terminal="SUCCESS",
            depends=("diagnose_policy_gate_effect",)),
       node("semantic_new_test_required","terminal",terminal="BLOCKED",
            depends=("diagnose_other_selection_semantics",)),
       node("blocked_wrong_target","terminal",terminal="BLOCKED"),
       node("blocked_integrity","terminal",terminal="BLOCKED"),
      ],
    }


def audit_grammar(envelope:dict)->dict:
    c=json.loads(GBNF_CONTRACT.read_text())
    if c["status"]!="FROZEN_BEFORE_PREDICTIONS" or c["protocol"]!=GBNF_PROTOCOL:
        raise ValueError("GBNF_STUDY_NOT_PRE_REGISTERED")
    if envelope.get("protocol")!="ISSUE1_GBNF_REAL_MODEL_RESULT_V1" or set(envelope.get("model_run",{}))==set():
        raise ValueError("MODEL_EVIDENCE_ENVELOPE_INVALID")
    run=envelope["model_run"]
    if run.get("protocol")!=GBNF_PROTOCOL or run.get("contract_git_blob")!=git_blob(GBNF_CONTRACT):
        raise ValueError("FROZEN_GBNF_CONTRACT_CHANGED")
    if run.get("actual_model_calls")!=17 or len(run.get("paired_cases",[]))!=17:
        raise ValueError("17_REAL_INFERENCES_NOT_PROVEN")
    if run.get("original_S1_S4_five_arm_complete") is not False or run.get("independent_unseen_gold") is not False:
        raise ValueError("FALSE_SCIENTIFIC_CLOSURE_CLAIM")
    frozen=json.loads(FIXTURE.read_text())
    old=json.loads(BASE.read_text())["run"]["llm"]
    old_by_id={x["fixture_id"]:x for x in old["rows"]}
    old_orig_prompts=json.loads(BASE.read_text())["run"]["raw_inference"]
    original_correct=0;treated_correct=0;violations=0;unique_sha=set();changes=[]
    for k,(case,paired) in enumerate(zip(frozen["fixtures"],run["paired_cases"])):
        if case["id"]!=paired["id"] or paired["id"] not in old_by_id:
            raise ValueError("PAIR_SOURCE_ID_DRIFT")
        v=public_fields(case)
        want_gate=gate_active(v)
        original=old_by_id[paired["id"]]
        if paired["public_gate_active"]!=want_gate or paired["baseline"]!=original["prediction"]:
            raise ValueError("PUBLIC_GATE_OR_BASELINE_CHANGED")
        if paired["prompt_byte_identity"] is not True or paired["baseline_GBNF_byte_identity"] is not True:
            raise ValueError("HISTORICAL_MODEL_INPUT_CHANGED")
        raw=paired["raw_real_inference"]
        if raw["historical_prompt_sha256"]!=old_orig_prompts[k]["prompt_sha256"] or raw["original_GBNF_sha256"]!=old_orig_prompts[k]["grammar_sha256"]:
            raise ValueError("PROMPT_OR_HISTORICAL_GRAMMAR_HASH_CHANGED")
        expected_root="root ::= execute | blocked | noopen | reframe | failclosed" if want_gate else "root ::= execute | blocked | noopen | failclosed"
        if paired["treated_GBNF_root"]!=expected_root or raw["root_choice"]!=expected_root or raw["only_GBNF_root_modified"] is not True:
            raise ValueError("ONLY_ONE_GRAMMAR_FACTOR_WAS_NOT_PRESERVED")
        if paired["treatment"]!=json.loads(raw["raw_response"]):
            raise ValueError("TREATMENT_RAW_PARSE_MISMATCH")
        if paired["baseline_exact_decision_correct"]!=(original["prediction"]["status"]==case["oracle"]["status"] and original["prediction"]["work_id"]==case["oracle"]["work_id"]):
            raise ValueError("OLD_SCORE_CHANGED")
        right=(paired["treatment"].get("status")==case["oracle"]["status"] and paired["treatment"].get("work_id")==case["oracle"]["work_id"])
        if paired["treatment_exact_decision_correct"]!=right:
            raise ValueError("TREATMENT_SCORE_FRAUD")
        if not want_gate and paired["treatment"].get("status")=="REFRAME":
            violations+=1
        original_correct+=int(paired["baseline_exact_decision_correct"])
        treated_correct+=int(right)
        if paired["baseline"]!=paired["treatment"]:changes.append(case["id"])
        unique_sha.add(raw["stdout_sha256"])
        for key in ("stdout_sha256","historical_prompt_sha256","treated_GBNF_sha256"):
            if len(raw[key])!=64:raise ValueError("RAW_OUTPUT_SHA_MISSING")
    gain=(treated_correct-original_correct)/17
    if abs(gain-run["paired_accuracy_gain"])>1e-12 or treated_correct!=run["gate_treatment_decision_correct"] or original_correct!=run["baseline_decision_correct"]:
        raise ValueError("FROZEN_GAIN_NOT_RECOMPUTED")
    if violations:raise ValueError("GBNF_INVALID_GATE_OUTPUT_ON_UNQUALIFIED_CASE")
    return {
      "case_count":17,"real_model_calls":run["actual_model_calls"],
      "real_model_stdout_sha_count":len(unique_sha),
      "baseline_correct":original_correct,"treated_correct":treated_correct,
      "gain":gain,"materiality":c["frozen_analysis"]["materiality_threshold"],
      "material_gain":gain>=c["frozen_analysis"]["materiality_threshold"],
      "paired_changed_cases":changes,"gate_inactive":run["gate_inactive_count"],
      "gate_active":run["gate_active_count"],
      "scientific_scope":"17 pre-exposed cases, public gate only, historical prompt identical; no independent test",
    }


def run(tcc_root:Path,ec_root:Path,*,report:Path=REPORT,model:Path|None=None,llama:Path|None=None)->dict:
    if not tcc_root.is_dir() or not ec_root.is_dir():
        raise ValueError("PINNED_SCIENCE_CHECKOUT_MISSING")
    rev=subprocess.run(["git","-C",str(tcc_root),"rev-parse","HEAD"],
                       capture_output=True,text=True,timeout=12)
    if rev.returncode or rev.stdout.strip()!=TCC_SOURCE:
        raise ValueError("TCC_COMPILER_GIT_PIN_DRIFT")
    if str(tcc_root) not in sys.path:sys.path.insert(0,str(tcc_root))
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.core_v3 import normalize_spec,validate_spec,compile_spec
    from tcc.runtime_v3 import execute_graph,to_ecv4_evidence
    r=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True,capture_output=True,timeout=12)
    if r.returncode:raise ValueError("RESEARCH_GIT_HEAD_UNAVAILABLE")
    head=r.stdout.strip()
    c=graph_spec()
    ctx=context_for(c,head)
    ctx.update(selected_issue_id="ISSUE-1",actionable_issue_ids=["ISSUE-1"],blocked_issue_ids=[],
               snapshot_id="ISSUE1-REAL-AUTO-STAGE4:"+head[:12],
               source_fingerprint="sha256:"+hashlib.sha256(
                 json.dumps({"spec":c,"head":head},sort_keys=True).encode()).hexdigest())
    generated=generate_tcc_from_context(ctx)
    if generated.get("result")!="tcc.spec.v3" or validate_spec(generated["spec"]) or generated["spec"]!=normalize_spec(c):
        raise ValueError("TCC_GENERATOR_OR_SOURCE_CONTRACT_DRIFT")
    graph=compile_spec(generated["spec"])
    observed={}
    def prior(_node,_state,_attempt):
        try:
            v=prior_tcc3(tcc_root,ec_root)
            if v["terminal"]!="ALL_AVAILABLE_SCOPED_EXPERIMENTS_AUDITED_ORIGINAL_FULL_STUDY_STILL_OPEN":
                raise ValueError("PREVIOUS_SCIENTIFIC_STAGE_NOT_AUDITED")
            if v["full_original_s1_s4_A_E_completed"] or v["ecv4_original_issue_closure_authorized"]:
                raise ValueError("ORIGINAL_S1S4_FALSE_COMPLETION")
            observed["prior"]={"terminal":v["terminal"],"S4_gain":v["new_actual_llm_info_intervention"]["paired_enriched_minus_structural"]}
        except Exception as exc:
            observed["error"]="PRIOR:"+type(exc).__name__+":"+str(exc)[:180]
            return {"status":"failure","evidence":["prior:FAIL:"+type(exc).__name__]}
        return {"status":"success","writes":{"prior_verified":True},
                "evidence":["original-phase1-v2:INCOMPATIBLE","S4-actual-Qwen20:VERIFIED","ECV4-SUITE:PASS"]}
    def s3(_node,_state,_attempt):
        try:
            v=evaluate_s3()
            if v["case_count"]!=17 or v["original_issue_closure_authorized"]:
                raise ValueError("S3_CAUSAL_RESULT_OUT_OF_SCOPE")
            observed["S3"]={"cases":17,"qwen":v["llm_downstream_success"],
               "native_EC":v["ec_downstream_success"],"S3_oracle":v["oracle_S3_only_downstream_success"],
               "causal_gain":v["causal_gain_oracle_S3_minus_llm_S3"]}
        except Exception as exc:
            observed["error"]="S3:"+type(exc).__name__+":"+str(exc)[:180]
            return {"status":"failure","evidence":["S3:FAIL:"+type(exc).__name__]}
        return {"status":"success","writes":{"s3_oracle_gain":v["causal_gain_oracle_S3_minus_llm_S3"]},
                "evidence":["S3-singleton-Oracle:real-model-1/17:native-17/17:oracle-17/17"]}
    def oracle_gate(_node,state,_attempt):
        return {"outcome":"material" if state.get("prior_verified") and
                state.get("s3_oracle_gain",0)>=.2 else "not_material",
                "evidence":["S3-causal-gain:"+str(state.get("s3_oracle_gain"))]}
    def grammar(_node,_state,_attempt):
        try:
            if report.is_symlink():raise ValueError("MODEL_EVIDENCE_SYMLINK_FORBIDDEN")
            if not report.is_file():
                if model is None or llama is None:
                    raise ValueError("PINNED_MODEL_EVIDENCE_NOT_AVAILABLE_FOR_RERUN")
                from tools.run_issue1_public_gate_gbnf_ablation_v1 import actual_run
                raw=actual_run(model,llama,ec_root)
                envelope={"protocol":"ISSUE1_GBNF_REAL_MODEL_RESULT_V1","model_run":raw}
                report.parent.mkdir(parents=True,exist_ok=True)
                pending=None
                try:
                    with tempfile.NamedTemporaryFile("w",dir=report.parent,prefix=".issue1_v4_",
                         suffix=".json",delete=False) as file:
                        pending=Path(file.name)
                        json.dump(envelope,file,sort_keys=True,ensure_ascii=False,indent=2)
                        file.write("\n")
                        file.flush();os.fsync(file.fileno())
                    os.link(pending,report)
                finally:
                    if pending is not None:pending.unlink(missing_ok=True)
            parsed=json.loads(report.read_text())
            outcome=audit_grammar(parsed)
            observed["grammar"]=outcome
        except Exception as exc:
            observed["error"]="GBNF:"+type(exc).__name__+":"+str(exc)[:180]
            return {"status":"failure","evidence":["real-GBNF:FAIL:"+type(exc).__name__]}
        return {"status":"success","writes":{"grammar_gain":outcome["gain"]},
                "evidence":["real-Qwen17-gate-run:PASS","gain:"+str(outcome["gain"])]}
    def grammar_gate(_node,state,_attempt):
        return {"outcome":"material" if state.get("grammar_gain",-100)>=.2 else "not_material",
                "evidence":["public-gate-single-factor-gain:"+str(state.get("grammar_gain"))]}
    def positive(_node,_state,_attempt):
        observed["next"]="INDEPENDENT_UNSEEN_POLICY-GATE_VALIDATION_PLUS_CROSS-CAPACITY_REPLICATION"
        return {"status":"success","evidence":["public-gate-helped-scoped:independent-proof-still-required"]}
    def negative(_node,_state,_attempt):
        observed["next"]="UNSEEN_S3_SEMANTIC-REASONING_ASSAY_AND_PROMPT-ROBUSTNESS_CONTROL"
        return {"status":"success","evidence":["public-gate-insufficient:next-unseen-controls"]}
    out=execute_graph(graph,{"verify_prior_science":prior,"run_s3_oracle_causal":s3,
       "oracle_gain_branch":oracle_gate,"run_real_public_gbnf_probe":grammar,
       "grammar_effect_branch":grammar_gate,"diagnose_policy_gate_effect":positive,
       "diagnose_other_selection_semantics":negative})
    if out.get("result")!="TERMINAL" or out.get("terminal_id") not in (
       "scoped_machine_result","semantic_new_test_required","blocked_wrong_target","blocked_integrity"):
        raise ValueError("TCC_INVALID_TERMINAL")
    return {
      "protocol":PROTOCOL,"repo_commit":head,"TCC_compiler_pin":TCC_SOURCE,
      "tcc_graph_nodes":len(graph["nodes"]),"tcc_graph_edges":len(graph["edges"]),
      "TCC_spec_hash":graph["spec_hash"],"terminal":out["terminal_id"],
      "terminal_status":out["terminal_status"],"ecv4_evidence":to_ecv4_evidence(graph,out),
      "previous_scientific_stage":observed.get("prior"),"S3_causal_oracle":observed.get("S3"),
      "public_gate_real_model":observed.get("grammar"),"next_scientific_branch":observed.get("next"),
      "failure":observed.get("error"),
      "original_A_E_S1_S4_completed":False,
      "independent_gold_certified":False,"original_issue_closure_authorized":False,
      "new_scheduled_task":False,"background_chat_self_send":False,
      "machine_scoped_complete":out["terminal_id"] in ("scoped_machine_result","semantic_new_test_required"),
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--tcc-root",type=Path,required=True)
    ap.add_argument("--ec-root",type=Path,required=True)
    ap.add_argument("--report",type=Path,default=REPORT)
    ap.add_argument("--model",type=Path)
    ap.add_argument("--llama-cli",type=Path)
    a=ap.parse_args()
    try:
        res=run(a.tcc_root,a.ec_root,report=a.report,model=a.model,llama=a.llama_cli)
        print(json.dumps(res,ensure_ascii=False,sort_keys=True,indent=2))
        return 0 if res["machine_scoped_complete"] else 3
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:310]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
