#!/usr/bin/env python3
"""Finite scientific exit preflight. Stops unverifiable Phase1 rerun loops.

Not an 18AC scientific scorer, not a substitute for independent gold.
The ORIGINAL frozen v1 contract and ECv4.4 sources cannot represent the
required full S3 set and disambiguated S4 closure on the pinned witnesses.
Runs only frozen-source, provenance and capacity-branch verification; does
not invoke expensive nested v10/v11/v12/v13 tests again.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BLOBS={
    "ACCEPTANCE_CRITERIA.md":"40e4d41914fb17ee5c7deb0cfd32276a41c9a1fc",
    "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json":"08407bec73278aeda8ddd2d4d6efc810dadf46f9",
    "results/ec_native_adapter_qualification.json":"8693c5be282b1e8407a0c1358e18eab2ad78905c",
    "results/phase1_s4_identifiability_audit_2026-10-03.json":"624616a1f4b0dc4a2330cbcd0a6a03b94a475ce8",
    "results/phase1_qwen25_0p5b_reframe_actual_2026-10-03.json":"8b6e8ab07c4604a1c07ed106d864aaf07dccc8e2",
    "docs/ISSUE1_ORIGINAL_PHASE1_AC18_ONECALL_PLAN_V13_2026-10-11.json":"5c4fda72c73ea9d2211f571027984421882a829e",
}
LOCAL_SOURCE_FILES=(
    "tools/run_issue1_finite_exit_preflight_v14.py",
    "tests/test_issue1_finite_exit_preflight_v14.py",
    "docs/ISSUE1_FINITE_TERMINATION_PLAN_V14_2026-10-11.md",
)
MVP=[f"AC-{i:02d}" for i in (*range(1,10),*range(11,18),19,20)]
POST=["AC-10","AC-18"]
TERMINAL_ORIGINAL="INFEASIBLE_UNDER_FROZEN_ECV4_4_INTERFACE"
NO_PROGRESS="SAME_EVIDENCE_FINGERPRINT_NO_RERUN"
PHASES=("F0_frozen_source_feasibility","F1_independent_authority_admission",
        "F2_model_capacity_one_followup","F3_matched_AE_one_run",
        "F4_recompute_metrics_and_original_AC")
CAPS={"same_fingerprint_reruns":0,"versioned_protocol_revisions":1,
      "independent_authority_pilot":1,"model_1p5b_capacity_escalation":1,
      "qualified_matched_AE_full_runs":1,"primary_metric_and_AC_scoring":1}
def gate(check, name):
    if not check: raise ValueError(name)

def blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def local_source_pins(root):
    result={}
    for name in LOCAL_SOURCE_FILES:
        f=root/name
        p=subprocess.run(["git","-C",str(root),"rev-parse","HEAD:"+name],
                         text=True,capture_output=True,timeout=12)
        gate(f.is_file() and not f.is_symlink() and
             p.returncode==0 and p.stdout.strip()==blob(f),
             "G0_LOCAL_EXECUTION_SOURCE_DRIFT:"+name)
        result[name]=p.stdout.strip()
    return result

def pinned(root):
    data={}
    for name,wanted in BLOBS.items():
        p=root/name
        gate(p.is_file() and not p.is_symlink() and blob(p)==wanted,
             "G0_FROZEN_EVIDENCE_DRIFT:"+name)
        data[name]=json.loads(p.read_text()) if name.endswith(".json") else p.read_text()
    return data

def run(root=ROOT):
    before={name:blob(root/name) for name in BLOBS}
    own_before=local_source_pins(root) if (root/".git").exists() else None
    data=pinned(root)
    norm=data["docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json"]
    adapter=data["results/ec_native_adapter_qualification.json"]
    bound=data["results/phase1_s4_identifiability_audit_2026-10-03.json"]
    model=data["results/phase1_qwen25_0p5b_reframe_actual_2026-10-03.json"]
    p13=data["docs/ISSUE1_ORIGINAL_PHASE1_AC18_ONECALL_PLAN_V13_2026-10-11.json"]
    gate(norm["mvp"]["required_ac"]==MVP and norm["mvp"]["post_mvp_ac"]==POST
         and norm["frozen_thresholds"]["oracle_substitution_gain_material_abs"]==0.20,
         "G1_AC_SCOPE_OR_MATERIALITY_DRIFT")
    gate(p13["original_mvp_required"]==MVP and
         p13["frozen_contract_git_blob"]==BLOBS[
             "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json"],
         "G1_V13_PLAN_NOT_NORMATIVE")
    a=adapter["subfunction_authority"]
    gate(adapter["status"]=="INCOMPATIBLE" and
         adapter["ec_source"]["commit"]==norm["canonical_inputs"]["ec_commit"] and
         not a["s3_selection"]["reportable"] and
         not a["s4_closure"]["reportable"] and
         a["s3_selection"]["authority"]=="EC_NATIVE_NOT_APPLICABLE" and
         a["s4_closure"]["authority"]=="EC_NATIVE_NOT_APPLICABLE" and
         set(a["s3_selection"]["counterexamples"])=={"M003","M009"},
         "G3_FROZEN_NATIVE_COMPATIBILITY_EVIDENCE_CHANGED")
    gate(bound["fixture_count"]==10 and
         bound["identifiability"]["best_possible_majority_correct"]==8 and
         bound["identifiability"]["metric_type"]==
            "INTERFACE_IDENTIFIABILITY_BOUND_NOT_EC_ACCURACY",
         "G3_S4_IDENTIFIABILITY_WITNESSES_CHANGED")
    gate(model["dataset_digest"]==norm["canonical_inputs"]["phase1_v2_dataset_sha256"] and
         model["model"]["sha256"]==norm["canonical_inputs"]["qwen2_5_0_5b"]["sha256"] and
         model["model"]["size_bytes"]==norm["canonical_inputs"]["qwen2_5_0_5b"]["size_bytes"] and
         model["result"]["fixture_count"]==10 and
         model["result"]["correct"]==1 and
         model["result"]["capacity_collapse_rule_fired"] is True and
         model["result"]["prediction_distribution"]=={"YES":10,"NO":0},
         "G12_FROZEN_REAL_0P5B_RESULT_CORRUPTED")
    after={name:blob(root/name) for name in BLOBS}
    gate(before==after,"G7_FROZEN_SOURCE_CHANGED_DURING_PREFLIGHT")
    if own_before is not None:
        gate(local_source_pins(root)==own_before,
             "G7_LOCAL_EXECUTION_CODE_CHANGED_DURING_PREFLIGHT")
    fingerprint=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest()
    return {
        "protocol":"ISSUE1_FINITE_CAUSAL_RESEARCH_EXIT_PREFLIGHT_V14",
        "original_issue":1,"root_contract":"ORIGINAL_FROZEN_EC_V4_4",
        "terminal":TERMINAL_ORIGINAL,
        "scientific_root_AC_pass":2,"scientific_root_AC_required":18,
        "scientific_root_AC_completed":False,
        "original_frozen_native_EC_status":"INCOMPATIBLE",
        "S3":{ "status":"STRUCTURALLY_UNREPRESENTABLE_BY_FROZEN_EC",
               "native_reportable":False,"witnesses":["M003","M009"] },
        "S4":{ "status":"STRUCTURALLY_UNDERIDENTIFIED_BY_FROZEN_INTERFACE",
               "native_reportable":False,"identifiability_bound":"8/10",
               "not_empirical_accuracy":True },
        "known_llm_evidence":{
            "status":"ACTUAL_0P5B_MEASURED_CAPACITY_COLLAPSE",
            "accuracy":"1/10","all_yes":True,"model_sha256":model["model"]["sha256"],
            "per_frozen_protocol_next":"EXACTLY_ONE_1P5B_ASSAY",
            "asset_only_recheck_unnecessary":True},
        "analysis_loop_control":{
            "evidence_fingerprint":fingerprint,
            "same_fingerprint_rerun":NO_PROGRESS,
            "identical_input_retries_remaining":0,
            "no_new_tcc_version_for_same_blocker":True,
            "once_only_successor_stage_caps":CAPS},
        "successor_not_original":{
            "requires_explicit_versioned_protocol_change":True,
            "frozen_EC_can_not_be_renamed_as_successor_native":True,
            "phases":list(PHASES),
            "decision_rules":{
              "F0":"if old frozen ECV4.4 selected => terminal INFEASIBLE; versioned qualified successor => F1",
              "F1":"if independently identified source-custodied S3/S4 AND frozen heldout split proven => F2; else terminal NOT_EVALUABLE_EXTERNAL_AUTHORITY",
              "F2":"reuse actual 0.5B result, run exactly one allowed 1.5B same-assay branch; if collapses then terminal CAPACITY_LIMIT; else F3",
              "F3":"one version-locked genuine model/native/Oracle A/B/C/D + E_S1..S4; if bad receipt, absent arm, answer leakage, non-target change => terminal INVALID_CAUSAL_RUN; else F4",
              "F4":"independently recompute all required metrics on sealed raw/gold, compare gain at frozen 0.20 and AC18; terminal VERIFIED, NO_MATERIAL_DIFFERENCE, AMBIGUOUS, or INVALID_EVIDENCE",
            },
            "no_unbounded_refinement_or_hidden_retune":True,
            "scientific_AC_do_not_increase_on_feasibility_diagnostic":True},
        "gates":[
           "G0_SOURCES_GIT_SHA_PIN_BEFORE_AFTER",
           "G1_FROZEN_MVP18_AND_0P20",
           "G3_ECV4_4_S3_S4_STRUCTURAL_COUNTEREXAMPLES",
           "G6_INDEPENDENT_GOLD_NEVER_AUTHOR_SELF_CERTIFIED",
           "G7_NO_POST_SCORE_MUTATION_OR_RESULT_PROMOTION",
           "G8_NO_REPEATED_EVIDENCE_FINGERPRINT",
           "G11_NEGATIVE_SCIENTIFIC_CONCLUSION_NOT_AC_PASS",
           "G12_0P5B_ACTUAL_MEASUREMENT_REUSED"],
        "sources_git_blobs":before,
        "source_seals_stable":True,"errors":[],
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    try:
        r=run()
        encoded=json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
        if args.out:
            gate(not args.out.is_symlink(),"G7_OUTPUT_SYMLINK")
            args.out.write_text(encoded)
        print(json.dumps({"terminal":r["terminal"],"AC":"2/18",
                          "actual_0p5b_reused":True,"source_stable":True}))
        return 2 # completed research feasibility assessment; not 18/18!
    except Exception as exc:
        print(json.dumps({"terminal":"INTEGRITY_FAIL_CLOSED",
                          "error":type(exc).__name__+":"+str(exc)[:240]}))
        return 3
if __name__=="__main__":
    raise SystemExit(main())
