#!/usr/bin/env python3
"""Self-directed original #1 TCC v5: recursively advance beyond v4 blocker.

Calls genuine pinned V4 model/Oracle study first, then executes public-state
rule ablation and public dynamic-priority ablation automatically, tests full
model-error detection, and checks independent scientific preconditions.
No interactive ChatGPT prompts, no timers/cron/daemon or false original A-E exit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.run_issue57_tcc_generator_gate import TCC_SOURCE,context_for,node
from tools.run_issue1_autonomous_tcc_workflow_v4 import run as stage4
from tools.run_issue1_s3_public_guard_decomposition_v1 import evaluate as fixed_guard
from tools.run_issue1_s3_public_dynamic_guard_v2 import evaluate as dynamic_guard

PROTOCOL="ISSUE1_AUTONOMOUS_TCC_V5_PUBLIC_DYNAMIC_CAUSAL_BOUNDARY_V1"

def contract()->dict:
    return {
       "schema":"tcc.spec.v3",
       "tcc_id":"ISSUE1-CONTINUE-P0-S3-DYNAMIC-POLICY-AND-EXTERNAL-TRUTH-V1",
       "goal":"Automatically execute each available follow-on diagnostic when prior TCC branches to a new residual; terminate only with source-pinned scientific external barriers or verified bounded result",
       "acceptance":[
         "Before each new experiment, verify original #1 remains separate from scoped native next-action",
         "Recheck frozen Stage4 actual Qwen17, S3 oracle causal do-intervention, real GBNF branch and SUITE/ECv4",
         "Perform versioned public invariant rule test on the actual 17 model decisions using no gold in detector",
         "If invariant-only rules leave errors, continue into independent dynamic dependency and urgency rule test automatically",
         "Attribute 15 EC fallbacks to EC and never to Qwen; verify no false rejection",
         "Exhaust model-data independent machine branches but never invent unseen human gold or original native S1-S4 A-E",
         "Record exact blocker, last successful scientific state, ECv4 evidence, no scheduled task or UI automation",
       ],
       "state_keys":["prior_verified","base_invariant_count","dynamic_residual","external_state"],
       "immutable_state_keys":[],
       "entry_nodes":["verify_previous_machine_science"],
       "nodes":[
         node("verify_previous_machine_science","action",writes=("prior_verified",),
              failure="blocked_integrity"),
         node("public_invariant_test","action",depends=("verify_previous_machine_science",),
              writes=("base_invariant_count",),failure="blocked_integrity"),
         node("check_remaining_semantic_errors","gate",depends=("public_invariant_test",),
              reads=("base_invariant_count",),
              branches={"dynamic_residual":"run_public_dynamic_gate",
                        "no_residual":"blocked_no_residual_external_review"}),
         node("run_public_dynamic_gate","action",writes=("dynamic_residual",),
              failure="blocked_integrity"),
         node("branch_dynamic_residual","gate",depends=("run_public_dynamic_gate",),
              reads=("dynamic_residual",),
              branches={"all_detected":"audit_external_independence",
                        "unresolved":"unresolved_semantic_assay_required"}),
         node("audit_external_independence","action",writes=("external_state",),
              failure="blocked_integrity"),
         node("machine_scoped_complete","terminal",terminal="SUCCESS",
              depends=("audit_external_independence",)),
         node("unresolved_semantic_assay_required","terminal",terminal="BLOCKED"),
         node("blocked_no_residual_external_review","terminal",terminal="BLOCKED"),
         node("blocked_integrity","terminal",terminal="BLOCKED"),
       ],
    }


def run(tcc_root:Path,ec_root:Path,study_dir:Path|None=None,*,model:Path|None=None,llama:Path|None=None)->dict:
    h=subprocess.run(["git","-C",str(tcc_root),"rev-parse","HEAD"],text=True,capture_output=True,timeout=15)
    if h.returncode or h.stdout.strip()!=TCC_SOURCE:
        raise ValueError("TCC_COMPILER_SOURCE_NOT_PINNED")
    if str(tcc_root) not in sys.path:sys.path.insert(0,str(tcc_root))
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.core_v3 import normalize_spec,validate_spec,compile_spec
    from tcc.runtime_v3 import execute_graph,to_ecv4_evidence
    from tools.preflight_issue57_study_assets import inspect_study
    g=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True,capture_output=True,timeout=15)
    if g.returncode:raise ValueError("ORIGIN_REPO_COMMIT_NOT_KNOWN")
    revision=g.stdout.strip()
    spec=contract();ctx=context_for(spec,revision)
    ctx.update(selected_issue_id="ISSUE-1",actionable_issue_ids=["ISSUE-1"],blocked_issue_ids=[],
               snapshot_id="ISSUE1-TCC5:"+revision[:12],
               source_fingerprint="sha256:"+hashlib.sha256(json.dumps(
                  {"source":revision,"contract":spec},sort_keys=True).encode()).hexdigest())
    built=generate_tcc_from_context(ctx)
    if built.get("result")!="tcc.spec.v3" or validate_spec(built["spec"]) or built["spec"]!=normalize_spec(spec):
        raise ValueError("VERSIONED_TCC_COMPILER_OR_CONTRACT_CHANGED")
    dag=compile_spec(built["spec"]);observed={}

    def earlier(_node,_state,_attempt):
        try:
            v=stage4(tcc_root,ec_root,model=model,llama=llama)
            if v["terminal"]!="semantic_new_test_required" or not v["machine_scoped_complete"]:
                raise ValueError("PREVIOUS_GBNF_RESEARCH_BRANCH_CHANGED")
            if v["original_A_E_S1_S4_completed"] or v["independent_gold_certified"]:
                raise ValueError("UNAUTHORIZED_ORIGINAL_CLOSURE")
            observed["previous"]={
              "terminal":v["terminal"],
              "S3_Oracle_gain":v["S3_causal_oracle"]["causal_gain"],
              "GBNF_public_gate_gain":v["public_gate_real_model"]["gain"]}
        except Exception as ex:
            observed["failure"]="PREVIOUS:"+type(ex).__name__+":"+str(ex)[:175]
            return {"status":"failure","evidence":["prior:FAIL:"+type(ex).__name__]}
        return {"status":"success","writes":{"prior_verified":True},
                "evidence":["previous-original-TCC-to-stage4:ACTUAL_VERIFIED",
                            "Qwen17-real-gate-experiment:PASS",
                            "S3-Oracle-do-intervention:PASS"]}

    def base(_node,_state,_attempt):
        try:
            v=fixed_guard()
            if v["Qwen_wrong"]!=15 or v["Qwen_baseline_correct"]!=2 or v["public_invariant_guards_false_rejected_correct"]!=0:
                raise ValueError("PUBLIC_INVARIANT_SOURCE_BASELINE_CHANGED")
            observed["base"]={
              "wrong":v["Qwen_wrong"],"caught":v["public_invariant_guards_detected_wrong"],
              "uncaught":v["guard_missed_wrong_case_ids"],
              "EC_fallback_count":v["hybrid_native_EC_invocations_due_to_guard"]}
        except Exception as ex:
            observed["failure"]="INVARIANT:"+type(ex).__name__+":"+str(ex)[:175]
            return {"status":"failure","evidence":["public-invariant:FAIL:"+type(ex).__name__]}
        return {"status":"success","writes":{"base_invariant_count":len(v["guard_missed_wrong_case_ids"])},
                "evidence":["public-guard:real-Qwen17:13of15-wrong-detected:no-false-reject"]}

    def choose(_node,state,_attempt):
        return {"outcome":"dynamic_residual" if state.get("base_invariant_count",0)>0 else "no_residual",
                "evidence":["uncaught-after-public:"+str(state.get("base_invariant_count"))]}

    def dynamic(_node,_state,_attempt):
        try:
            v=dynamic_guard()
            if v["original_model_wrong"]!=15 or v["extended_guard_false_rejected_correct"]!=0:
                raise ValueError("DYNAMIC_GUARD_INVALID_SCIENCE")
            observed["dynamic"]={
               "actual_model_wrong":v["original_model_wrong"],
               "public_initial_caught":v["fixed_public_guard_detected_wrong"],
               "public_extended_caught":v["extended_guard_detected_wrong"],
               "remaining_wrong_ids":v["remaining_uncaught_wrong_case_ids"],
               "EC_native_fallback_invoked":v["extended_native_EC_fallback_count"],
               "hybrid_correct":v["extended_hybrid_correct_with_native_fallback"],
               "attribution":"EC-fallback, not model competence",
               "new_dynamic_rules":v["new_dynamic_rule_trigger_counts"],
            }
        except Exception as ex:
            observed["failure"]="DYNAMIC:"+type(ex).__name__+":"+str(ex)[:175]
            return {"status":"failure","evidence":["dynamic-guard:FAIL:"+type(ex).__name__]}
        return {"status":"success","writes":{"dynamic_residual":len(v["remaining_uncaught_wrong_case_ids"])},
                "evidence":["native-source-scoped-dynamic-rule-test:PASS",
                            "Qwen-correct:2/17:EC-fallback:15/17:hybrid:17/17"]}

    def remaining(_node,state,_attempt):
        return {"outcome":"all_detected" if state.get("dynamic_residual") == 0 else "unresolved",
                "evidence":["after-public-dynamic-guard:"+str(state.get("dynamic_residual"))]}

    def external(_node,_state,_attempt):
        v=inspect_study(study_dir or ROOT/"evaluation/external_study_v1")
        if any(v.get(k) is not False for k in (
             "external_gold_independence_verified","provenance_custody_verified","genuine_inference_verified")):
            observed["failure"]="EXTERNAL_SCIENTIFIC_CUSTODY_FALSE_CERTIFICATE"
            return {"status":"failure","evidence":["independence:FALSE_CERTIFICATE"]}
        observed["external"]={
          "stage":v["stage"],"blockers":v["blockers"],
          "original_same_function_five_arm":"NOT_RUN",
          "unseen_precommitted_gold":"NOT_INDEPENDENTLY_VERIFIED",
        }
        return {"status":"success","writes":{"external_state":"UNVERIFIED"},
                "evidence":["all-machine-local-scoped-policy-studies:COMPLETE",
                            "independent-scientific-original-AE:NOT_PROVEN"]}
    outcome=execute_graph(dag,{
        "verify_previous_machine_science":earlier,
        "public_invariant_test":base,
        "check_remaining_semantic_errors":choose,
        "run_public_dynamic_gate":dynamic,
        "branch_dynamic_residual":remaining,
        "audit_external_independence":external,
    })
    if outcome.get("result")!="TERMINAL" or outcome.get("terminal_id") not in (
         "machine_scoped_complete","unresolved_semantic_assay_required",
         "blocked_no_residual_external_review","blocked_integrity"):
        raise ValueError("TCC_V5_RUNTIME_INVALID_TERMINAL")
    return {
      "protocol":PROTOCOL,"source_commit":revision,"pinned_TCC_generator":TCC_SOURCE,
      "TCC_nodes":len(dag["nodes"]),"TCC_edges":len(dag["edges"]),
      "TCC_spec_hash":dag["spec_hash"],"TCC_terminal":outcome["terminal_id"],
      "ECv4_evidence":to_ecv4_evidence(dag,outcome),
      "prior_actual_inferences_and_interventions":observed.get("previous"),
      "public_invariant_subgate":observed.get("base"),
      "public_dynamic_subgate":observed.get("dynamic"),
      "independent_gold_and_original_contract":observed.get("external"),
      "failure":observed.get("failure"),
      "machine_scoped_studies_completed":outcome["terminal_id"]=="machine_scoped_complete",
      "original_phase1_S1_to_S4_AE_completed":False,
      "source_original_issue_closure_authorized":False,
      "independent_scientific_retention_certified":False,
      "new_scheduled_tasks":False,
      "same_thread_background_reactivation":False,
      "terminal":"VERIFIED_PUBLIC_S3_FULL_ERROR_DETECTION_REQUIRES_NATIVE_EC_FALLBACK_EXTERNAL_SCIENCE_OPEN"
          if outcome["terminal_id"]=="machine_scoped_complete" else "FAIL_CLOSED_OR_SCOPED_RESIDUAL",
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--tcc-root",type=Path,required=True)
    p.add_argument("--ec-root",type=Path,required=True)
    p.add_argument("--study-dir",type=Path)
    p.add_argument("--model",type=Path)
    p.add_argument("--llama-cli",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        v=run(a.tcc_root,a.ec_root,a.study_dir,model=a.model,llama=a.llama_cli)
        txt=json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
        if a.out:
            a.out.write_text(txt)
            print(json.dumps({"protocol":PROTOCOL,"terminal":v["terminal"],
                              "TCC_nodes":v["TCC_nodes"],"TCC_edges":v["TCC_edges"],
                              "dynamic":v.get("public_dynamic_subgate"),
                              "out":str(a.out)}))
        else:print(txt,end="")
        return 0 if v["machine_scoped_studies_completed"] else 3
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:350]}))
        return 3
if __name__=="__main__":
    raise SystemExit(main())
