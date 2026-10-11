#!/usr/bin/env python3
"""Single-call bounded original Phase1 + versioned-successor science executor.

Returns an *actual* disposition, reuses both original-model capacity results,
and never confuses an authored finite-policy receipt with independent gold.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from tools.run_issue1_finite_exit_preflight_v14 import (
    ROOT, BLOBS, blob, gate, run as original_feasibility,
)

CONTRACT="ISSUE1_FAST_COMPLETE_DEPENDENCY_RUN_V15"
ONEP5="results/phase1_qwen25_1p5b_reframe_actual_2026-10-03.json"
ONEP5_BLOB="33b557c448d9f5ed6f5218cfd76b0f91675f9479"
EC_REPO="mokumaisancho/GPT-EC-Closure-Engine"
EC_COMMIT="3f435ad4365d846d96264458540efb4848ce3541"
EXIT_STATES={"ROOT_SCIENCE_VERIFIED","ROOT_FROZEN_PROTOCOL_INFEASIBLE",
             "SUCCESSOR_EXTERNAL_AUTHORITY_NOT_EVALUABLE",
             "SUCCESSOR_CAPACITY_LIMIT","SUCCESSOR_INVALID_CAUSAL_RUN",
             "SUCCESSOR_AMBIGUOUS","SUCCESSOR_NO_MATERIAL_LAYER",
             "SUCCESSOR_LOCALIZED","INTEGRITY_FAIL_CLOSED"}
PATHS=("F0_original_native_feasibility_and_successor_ec",
       "F1_external_independent_S3_S4_authority",
       "F2_0p5b_and_1p5b_actual_assay_reuse",
       "F3_matched_four_layer_target_only_AE",
       "F4_blind_scoring_AC18_decision")
INTEGRITY=(
    "FROZEN_AC_OR_THRESHOLD_CHANGED","EC_VERSION_DISGUISED_AS_ECV4_4",
    "UNKNOWN_S3_OR_S4_SOURCE_CUSTODY","GOLD_AVAILABLE_TO_PREDICTOR",
    "HELDOUT_REUSED_FOR_TUNING","NON_TARGET_E_ORACLE_INJECTION",
    "FALSE_ECV4_COMPATIBILITY","UNQUALIFIED_AE_AS_ROOT_SCIENCE",
    "CHANGED_MODEL_OUTPUT_RAW_OR_HASH","DUPLICATED_OR_MISSING_CASE_OR_ARM",
    "SCORES_INFERRED_FROM_END_TO_END_ONLY",
)

def sha(path: Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()

def git_pinned_source(root:Path, name:str):
    f=root/name
    p=subprocess.run(["git","-C",str(root),"rev-parse","HEAD:"+name],
         text=True,capture_output=True,timeout=12)
    gate(f.is_file() and not f.is_symlink() and p.returncode==0 and
         p.stdout.strip()==blob(f),"G0_VERSIONED_SOURCE_UNTRACKED_OR_EDITED:"+name)

def load_1p5(root:Path):
    f=root/ONEP5
    gate(f.is_file() and not f.is_symlink() and blob(f)==ONEP5_BLOB,
         "G0_HISTORICAL_1P5B_SOURCE_CHANGED")
    d=json.loads(f.read_text())
    e=json.loads((root/"results/phase1_qwen25_0p5b_reframe_actual_2026-10-03.json").read_text())
    gate(d["assay"]==e["assay"]=="PHASE1_V2_S3_REFRAME_FIXED_STATE_V1" and
         d["dataset_digest"]==e["dataset_digest"] and
         d["result"]["fixture_count"]==e["result"]["fixture_count"]==10 and
         e["result"]["correct"]==1 and d["result"]["correct"]==9 and
         d["result"]["accuracy"]==0.9 and
         d["result"]["capacity_collapse_rule_fired"] is False and
         d["result"]["capacity_limit_after_1p5b"] is False and
         d["result"]["output_contract_valid"] is True and
         d["model"]["sha256"]=="1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370" and
         d["ecv4_4_reframe_comparison"]["ec_accuracy"]==0.9,
         "G12_FROZEN_1P5B_RESULTS_NOT_MATCHING")
    return d

def run(root:Path=ROOT,ec_root:Path|None=None,
        independent_provenance:Path|None=None):
    source_files=[*BLOBS,ONEP5]
    before={x:blob(root/x) for x in source_files}
    git_pinned_source(root,"tools/run_issue1_fast_integrated_v15.py")
    git_pinned_source(root,"tests/test_issue1_fast_integrated_v15.py")
    f0=original_feasibility(root)
    gate(f0["terminal"]=="INFEASIBLE_UNDER_FROZEN_ECV4_4_INTERFACE" and
         f0["scientific_root_AC_pass"]==2 and
         f0["source_seals_stable"],"G11_FROZEN_FEASIBILITY_NOT_VALID")
    successor_ec={
        "repository":EC_REPO,"commit":EC_COMMIT,
        "implemented":"VERSIONED_FINITE_POLICY_S3_S4",
        "original_ECv4_4_same_function":False,
        "natural_semantic_qualification":False,
        "independent_S4_completeness":False,
        "can_close_original_frozen_AC":False}
    if ec_root is not None:
        cmd=subprocess.run(["git","-C",str(ec_root),"rev-parse","HEAD"],
                           capture_output=True,text=True,timeout=12)
        gate(cmd.returncode==0 and cmd.stdout.strip()==EC_COMMIT,
             "G0_SUCCESSOR_NATIVE_SOURCE_COMMIT_MISMATCH")
        successor_ec["ec_checkout_verified"]=True
    else:
        successor_ec["ec_checkout_verified"]=False
    f1={
        "status":"NOT_EVALUABLE_INDEPENDENT_SEMANTIC_AND_OBLIGATION_AUTHORITY",
        "S3_independent_source_custody":False,
        "S4_independently_complete_real_task_inventory":False,
        "model_gold_separation_authenticated":False,
        "genuine_unseen_heldout_authenticated":False,
        "source":"No independently authenticated protocol + expert/adjudicator "
                 "source custodian in the supplied frozen research inputs",
    }
    # Supplying a JSON path cannot itself certify a third party or blind gold:
    # a real independent custodian's authentication must be verified out of band.
    if independent_provenance is not None:
        gate(independent_provenance.is_file() and
             not independent_provenance.is_symlink(),
             "G6_EXTERNAL_DOCUMENT_INVALID")
        f1["provided_source_sha256"]=sha(independent_provenance)
        f1["status"]="UNVERIFIED_DOCUMENT_PRESENT_EXTERNAL_CUSTODY_REQUIRED"
    recorded=load_1p5(root)
    f2={
        "status":"COMPLETED_USING_PRIOR_REAL_EXPERIMENT_NOT_NEW_INFERENCE",
        "run_again":False,"0p5b_correct":"1/10",
        "1p5b_correct":"9/10","1p5b_model_sha256":recorded["model"]["sha256"],
        "paired_assay":recorded["assay"],
        "absolute_improvement":recorded["capacity_comparison"]["absolute_improvement"],
        "1p5b_capacity_collapse":False,
        "ecv4_4_S3_reframe_accuracy_diagnostic":recorded[
                "ecv4_4_reframe_comparison"]["ec_accuracy"],
        "1p5b_llm_S3_reframe_accuracy_diagnostic":recorded[
                "ecv4_4_reframe_comparison"]["llm_1p5b_accuracy"],
        "not_full_S3_selection_or_S4_causal_study":True,
        "further_4b_escalation":False,
    }
    f3={"status":"NOT_EXECUTED_UNQUALIFIED_INPUTS",
        "reason":["NO_INDEPENDENT_GOLD_S3","NO_COMPLETE_S4_AUTHORITY",
                  "NO_TRUSTED_LLM_EC_ORACLE_RUNTIME_ATTESTATION"],
        "required_arms":["A","B","C","D","E_S1","E_S2","E_S3","E_S4"],
        "original_four_layers":["S1","S2","S3","S4"],
        "target_only_runtime_verified":False}
    f4={"status":"NOT_RUN_NO_INDEPENDENT_AE",
        "observed_effect":None,"dominant_layer":None,
        "frozen_materiality_abs":0.2,
        "scoring_qualified":False}
    after={x:blob(root/x) for x in source_files}
    gate(before==after,"G7_FROZEN_MODEL_EVIDENCE_MUTATED_MIDRUN")
    git_pinned_source(root,"tools/run_issue1_fast_integrated_v15.py")
    git_pinned_source(root,"tests/test_issue1_fast_integrated_v15.py")
    root_result={
        "protocol":CONTRACT,
        "original_scope":"FROZEN_ECV4_4_NATIVE",
        "original_ac_pass":2,"original_mvp_AC":18,
        "original_science_complete":False,
        "original_protocol_terminal":"ROOT_FROZEN_PROTOCOL_INFEASIBLE",
        "separate_versioned_successor_terminal":
                 "SUCCESSOR_EXTERNAL_AUTHORITY_NOT_EVALUABLE",
        "onecall_stages":list(PATHS),
        "stage_evidence":{
            PATHS[0]:{"original_frozen_feasibility":"STRUCTURALLY_INFEASIBLE",
                      "frozen_S3_counterexamples":["M003","M009"],
                      "frozen_S4_signature_accuracy_ceiling_not_empirical":"8/10",
                      "successor_native":successor_ec},
            PATHS[1]:f1,PATHS[2]:f2,PATHS[3]:f3,PATHS[4]:f4},
        "actual_progress":{
            "preexisting_1p5b_capacity": "FOUND_COMPLETED_NOT_RERUN",
            "repeated_model_reinference":False,
            "repeat_old_455_regression":False,
            "successor_natural_semantics_verified":False,
            "full_AE_executed":False},
        "closure_decision":{
            "research_under_original_frozen_ECv4_4":
                 "INFEASIBLE: UNREPRESENTABLE_FULL_SET_S3_AND_S4",
            "research_under_versioned_successor":
                 "NOT_EVALUABLE: INDEPENDENT_REAL_TASK_S3_S4_GOLD_UNAVAILABLE",
            "not_scientific_18AC_success":True,
            "no_further_same_input_automatic_TCC_RERUN":True,
            "reopen_condition":"NEW_INDEPENDENT_EXPERT_SOURCE_CUSTODIED_S3_AND_S4_GOLD_AND_TRUSTED_RUNTIME"},
        "all_AC_and_MVP_fixed":True,
        "evidence_replay_fingerprint":hashlib.sha256(
             json.dumps({"original_source_pins":before,"successor":EC_COMMIT},
                        sort_keys=True).encode()).hexdigest(),
        "error_overturning_gates":list(INTEGRITY),
        "all_source_hashes_preserved":True,
        "unsafe_autonomous_implementation":False,
        "errors":[],
    }
    gate(root_result["original_ac_pass"]==2 and
         not root_result["original_science_complete"] and
         root_result["stage_evidence"][PATHS[2]]["1p5b_correct"]=="9/10" and
         root_result["stage_evidence"][PATHS[3]]["status"].startswith("NOT_EXECUTED"),
         "G11_FALSE_PREMATURE_CAUSAL_CLOSURE")
    return root_result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--ec-root",type=Path)
    parser.add_argument("--independent-provenance",type=Path)
    parser.add_argument("--out",type=Path)
    a=parser.parse_args()
    try:
        d=run(ROOT,a.ec_root,a.independent_provenance)
        if a.out:
            gate(not a.out.is_symlink(),"G7_OUTPUT_SYMLINK_FORBIDDEN")
            a.out.write_text(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
        print(json.dumps({"original":d["original_protocol_terminal"],
                          "successor":d["separate_versioned_successor_terminal"],
                          "reused_1p5b":"9/10",
                          "original_AC":"2/18",
                          "new_inference":False}))
        return 2
    except Exception as exc:
        print(json.dumps({"terminal":"INTEGRITY_FAIL_CLOSED",
                          "error":type(exc).__name__+":"+str(exc)[:240]}))
        return 3
if __name__=="__main__":
    raise SystemExit(main())
