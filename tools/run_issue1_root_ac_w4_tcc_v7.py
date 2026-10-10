#!/usr/bin/env python3
"""Issue #1 TCC v7: real native EC W4 source implementation, AC-driven continuation.

One real TCC call verifies the immutable root 20 AC/18-MVP via v6, then
runs a *new actual EC repo source module* with isolated public-only test
cases and 14 native negative tests, then determines independent attestor
and S4 obligation-custody dependencies. No scoped success -> root closure.
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
from tools.run_issue1_root_ac_orchestrator_v6 import (
    run as run_root_ac_v6,git_head,git_blob,immutable_evidence_seal
)
from tools.run_issue1_ec_native_layerwise_source_probe_v1 import (
    run as run_native_probe,pin as pin_native_source,EC_COMMIT,EC_MODULE_BLOB,
    PROTOCOL as NATIVE_PROTOCOL,MODULE as NATIVE_MODULE,TESTS as NATIVE_TESTS
)

PROTOCOL="ISSUE1_ROOT_W4_EC_NATIVE_AC_TCC_V7"
CFG=ROOT/"docs/ISSUE1_ROOT_AC_W4_NATIVE_IMPLEMENTATION_TCC_V7.json"
CFG_BLOB="411f71aed1a971dfd6c73d1af5d994e48db48348"

def demand(ok:bool,reason:str):
    if not ok:raise ValueError(reason)

def sha(o)->str:
    return hashlib.sha256(json.dumps(o,sort_keys=True,ensure_ascii=False,
                                     separators=(",",":")).encode()).hexdigest()

def qualification_plan(v6:dict,native:dict,config:dict)->dict:
    source_good=(native["native_additive_source_git_commit"]==EC_COMMIT and
                 native["native_module_git_blob"]==EC_MODULE_BLOB and
                 native["native_negative_tests_passed"]==14 and
                 native["casewise_S3_development_matches"]==4 and
                 native["casewise_S4_development_matches"]==4 and
                 native["native_module_actual_python_process_executed"] is True)
    demand(source_good,"W4_NATIVE_ENGINE_SOURCE_NOT_ACTUALLY_VERIFIED")
    ac=v6["MVP_18_required_AC_status"]
    demand(ac["required_count"]==18 and ac["required_pass_count"]==2 and
           ac["mvp_pass"]==["AC-19","AC-20"],"ROOT_AC_MATRIX_NOT_REPRODUCED")
    demand(v6["terminal"]=="NATIVE_SOURCE_CAPABILITY_GAP" and
           v6["original_issue_1_completed"] is False and
           v6["blocking_integrity_errors"]==[],"ROOT_AC_V6_NOT_SCIENTIFICALLY_VERIFIED")
    demand(native["external_semantic_adjudicator_certified"] is False and
           native["external_complete_inventory_certified"] is False and
           native["original_four_layer_AE_completed"] is False and
           native["independent_unseen_gold"] is False,
           "UNVERIFIED_SEMANTIC_TRUTH_OR_INVENTORY_FALSIFIED")
    matrix={
      "W0_TO_W3_ORIGINAL_SOURCE_AND_SCOPED_RUN":{
        "depends_on":[],"status":"DONE_BY_REAL_V6",
        "source":"original frozen V2 + v5 actual EC/Qwen/scoped evidence"},
      "W4A_NATIVE_CANDIDATE_SET_AND_CLOSURE_ENGINE":{
        "depends_on":["W0_TO_W3_ORIGINAL_SOURCE_AND_SCOPED_RUN"],
        "status":"IMPLEMENTED_EXPERIMENTAL_VERIFIED",
        "source":EC_COMMIT},
      "W4B_INDEPENDENT_SEMANTIC_ADJUDICATOR":{
        "depends_on":["W4A_NATIVE_CANDIDATE_SET_AND_CLOSURE_ENGINE"],
        "status":"BLOCKED_AUTHENTICATED_SEMANTIC_REASON_AUTHORITY_NOT_PRESENT",
        "must_supply":"independent original-language->candidate admissibility provenance, no development gold"},
      "W4C_COMPLETE_S4_OBLIGATION_PROOF":{
        "depends_on":["W4A_NATIVE_CANDIDATE_SET_AND_CLOSURE_ENGINE"],
        "status":"BLOCKED_COMPLETENESS_INVENTORY_NOT_INDEPENDENTLY_PROVEN",
        "must_supply":"attested mandatory condition inventory incl absence claims; no implicit empty inventory"},
      "W5_ORIGINAL_S1_S4_A_B_C_D_E":{
        "depends_on":["W4B_INDEPENDENT_SEMANTIC_ADJUDICATOR",
                      "W4C_COMPLETE_S4_OBLIGATION_PROOF"],
        "status":"NOT_RUN_DEPENDENCY_BLOCKED",
        "must_supply":"all four layer real model+native EC same-function interventions; frozen original cannot be reclassified"},
      "W6_ROOT_18AC_MVP_AND_CAUSAL_LOCALIZATION":{
        "depends_on":["W5_ORIGINAL_S1_S4_A_B_C_D_E"],
        "status":"NOT_RUN_UNTIL_18_AC_PASS_AND_CONTROLLED_A_E"},
      "W7_UNSEEN_LLM0_V4_INDEPENDENT_HOLDOUT":{
        "depends_on":["W6_ROOT_18AC_MVP_AND_CAUSAL_LOCALIZATION"],
        "status":"BLOCKED_EXTERNAL_INDEPENDENT_EVIDENCE",
        "must_supply":"heldout gold custody, genuine original LLM0 + authorized V4"},
    }
    # Validate the schedule (dependency graph) is acyclic and grounded.
    seen=set()
    for name,job in matrix.items():
        demand(set(job["depends_on"]).issubset(seen),
               "W4_W5_CYCLIC_OR_FUTURE_DEPENDENCY:"+name)
        seen.add(name)
    return {
      "original_AC_total":20,"MVP_required":18,"MVP_scientifically_passed":2,
      "original_AC_pass_only":ac["mvp_pass"],
      "all_4_layer_oracle_A_to_E_run":False,
      "native_source_experimental_engine_implemented":True,
      "independent_semantic_adjudicator_qualified":False,
      "complete_S4_obligation_inventory_independently_qualified":False,
      "work_dependencies":matrix,
      "next_executable_task":"W4B independently authenticated semantic inference authority + W4C complete S4 inventory; then W5 genuine A-E",
      "original_issue_mvp_complete":False,
    }

def spec()->dict:
    return {
      "schema":"tcc.spec.v3",
      "tcc_id":"ISSUE1-ORIGINAL-AC-W4-ACTUAL-NATIVE-SOURCE-V7",
      "goal":"Do not stop at W4 source specification. Verify new EC native S3/S4 source and test on public inputs, then AC-dependency gate true untested semantic provenance.",
      "acceptance":[
        "re-execute original frozen Phase1 AC-driven 12-node v6 including 18 normative MVP gates and full stage1–5",
        "verify newly implemented EC additive multi-selection and obligation closure source from separate newer Git commit (preserve frozen v4.4)",
        "run 14 native negative tests, four actual public-input isolated-child S3/S4 casewise probes",
        "no Oracle/reference label/fixture ID supplied to predictor; independent semantic authority must never be invented",
        "pre/post scientific source code and frozen raw hashes must remain stable",
        "produce W4A/W4B/W4C/W5/W6/W7 causal prerequisite graph and next work",
        "close original only with authentic 18/18 AC and four-layer A-E; never allow W4 partial as completion",
      ],
      "state_keys":["root_ac_v6","new_native_ec_source","semantic_custody"],
      "immutable_state_keys":[],
      "entry_nodes":["execute_root_original_v6"],
      "nodes":[
        node("execute_root_original_v6","action",writes=("root_ac_v6",),failure="blocked_integrity"),
        node("run_new_source_native_s3s4","action",depends=("execute_root_original_v6",),
             writes=("new_native_ec_source",),failure="blocked_integrity"),
        node("audit_w4_and_root_AC_dependencies","action",depends=("run_new_source_native_s3s4",),
             writes=("semantic_custody",),failure="blocked_integrity"),
        node("scientific_root_completion_gate","gate",
             depends=("audit_w4_and_root_AC_dependencies",),
             reads=("root_ac_v6","new_native_ec_source","semantic_custody"),
             branches={"all_18_and_AE":"root_science_verified",
                       "semantic_custody_missing":"blocked_W4_semantic_authority",
                       "full_AE_not_run":"blocked_W5_original_study"}),
        node("root_science_verified","terminal",terminal="SUCCESS"),
        node("blocked_W4_semantic_authority","terminal",terminal="BLOCKED"),
        node("blocked_W5_original_study","terminal",terminal="BLOCKED"),
        node("blocked_integrity","terminal",terminal="BLOCKED"),
      ]
    }

def run(tcc_root:Path,ec_v44_root:Path,new_native_root:Path)->dict:
    demand(git_head(tcc_root)==TCC_SOURCE,"TCC_COMPILER_GIT_COMMIT_CHANGED")
    demand(CFG.is_file() and not CFG.is_symlink() and git_blob(CFG.read_bytes())==CFG_BLOB,
           "VERSIONED_W4_DEPENDENCY_CONTRACT_CHANGED")
    config=json.loads(CFG.read_text())
    demand(config["schema"]=="issue1.root-ac-w4-source.tcc.v7" and
           config["original_required_ac_unchanged"]==18 and
           config["native_new_source_commit"]==EC_COMMIT and
           config["native_module_git_blob"]==EC_MODULE_BLOB,
           "ROOT_AC_OR_EC_NATIVE_SOURCE_RELABELED")
    if str(tcc_root) not in sys.path:sys.path.insert(0,str(tcc_root))
    from tcc.core_v3 import compile_spec,normalize_spec,validate_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph,to_ecv4_evidence
    source=git_head(ROOT)
    manifest=spec()
    ctx=context_for(manifest,source)
    ctx.update(selected_issue_id="ISSUE-1",actionable_issue_ids=["ISSUE-1"],
               blocked_issue_ids=[],
               snapshot_id="ISSUE1-TCC-W4V7-"+source[:12],
               source_fingerprint="sha256:"+sha({"source":source,"contract":manifest,
                                                 "w4":config}))
    built=generate_tcc_from_context(ctx)
    demand(built.get("result")=="tcc.spec.v3" and
           not validate_spec(built.get("spec")) and
           built["spec"]==normalize_spec(manifest),
           "GENERATED_TCC_SEMANTICS_CHANGED")
    graph=compile_spec(built["spec"])
    evidence={"errors":[]}
    raw_pre=immutable_evidence_seal()
    src_paths=[
       "tools/run_issue1_root_ac_orchestrator_v6.py",
       "tools/run_issue1_ec_native_layerwise_source_probe_v1.py",
       "tools/run_issue1_root_ac_w4_tcc_v7.py",
    ]
    def code_seal():
        checks={}
        for rel in src_paths:
            path=ROOT/rel
            expect=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD:"+rel],
                  text=True,capture_output=True,timeout=12)
            demand(expect.returncode==0 and
                   git_blob(path.read_bytes())==expect.stdout.strip(),
                   "W4_SCIENTIFIC_CODE_UNCOMMITTED_OR_CHANGED:"+rel)
            checks[rel]=expect.stdout.strip()
        return checks
    code_pre=code_seal()
    pin_native_source(new_native_root)
    new_native_sources_before={
        p:git_blob((new_native_root/p).read_bytes()) for p in (NATIVE_MODULE,NATIVE_TESTS)
    }
    config_pre=hashlib.sha256(CFG.read_bytes()).hexdigest()

    def origin(_node,_state,_attempt):
        try:
            r=run_root_ac_v6(tcc_root,ec_v44_root)
            demand(r["terminal"]=="NATIVE_SOURCE_CAPABILITY_GAP" and
                   r["original_issue_1_completed"] is False and
                   r["blocking_integrity_errors"]==[],
                   "ROOT_AC_V6_FROZEN_ORIGINAL_NOT_VERIFIED")
            evidence["old_root"]={
                "terminal":r["terminal"],
                "passed_AC":r["MVP_18_required_AC_status"]["mvp_pass"],
                "AC_unmet":r["MVP_18_required_AC_status"]["mvp_unmet"],
                "source_code_seal_count":len(r["scientific_source_code_git_blob_pins"])}
            evidence["_v6"]=r
        except Exception as exc:
            evidence["errors"].append("ROOT:"+type(exc).__name__+":"+str(exc)[:140])
            return {"status":"failure","evidence":["ROOT_AC:FAIL_CLOSED"]}
        return {"status":"success","writes":{"root_ac_v6":True},
                "evidence":["original-root-v6:real-18AC-source-and-data-gates:PASS:2of18-not-root-complete"]}

    def native(_node,_state,_attempt):
        try:
            out=run_native_probe(new_native_root)
            demand(out["protocol"]==NATIVE_PROTOCOL and
                   out["native_additive_source_git_commit"]==EC_COMMIT and
                   out["native_negative_tests_passed"]==14 and
                   out["casewise_S3_development_matches"]==4 and
                   out["casewise_S4_development_matches"]==4 and
                   out["original_four_layer_AE_completed"] is False,
                   "EXPERIMENTAL_NATIVE_SOURCE_INCONSISTENT")
            evidence["new_native"]=out
        except Exception as exc:
            evidence["errors"].append("NATIVE:"+type(exc).__name__+":"+str(exc)[:140])
            return {"status":"failure","evidence":["NEW_NATIVE:FAIL_CLOSED"]}
        return {"status":"success","writes":{"new_native_ec_source":True},
                "evidence":["new-real-EC-native-commit:"+EC_COMMIT[:12]+":14-tests:4-exposed-cases-PASS"]}

    def ac_check(_node,_state,_attempt):
        try:
            new=evidence["new_native"]
            v6=evidence["_v6"]
            matrix=qualification_plan(v6,new,config)
            # Source code, data and plan must remain immutable through
            # actual EC integration and prior nested TCC execution.
            demand(raw_pre==immutable_evidence_seal(),
                   "W4_RESULT_OVERTURNING_RAW_EVIDENCE_CHANGED")
            demand(code_pre==code_seal(),
                   "W4_RESULT_OVERTURNING_SCIENTIFIC_CODE_CHANGED")
            pin_native_source(new_native_root)
            demand(new_native_sources_before=={
                p:git_blob((new_native_root/p).read_bytes()) for p in
                (NATIVE_MODULE,NATIVE_TESTS)},
                "W4_RESULT_OVERTURNING_NATIVE_ENGINE_CODE_CHANGED")
            demand(config_pre==hashlib.sha256(CFG.read_bytes()).hexdigest(),
                   "W4_RESULT_OVERTURNING_MVP_CONTRACT_CHANGED")
            evidence["matrix"]=matrix
        except Exception as exc:
            evidence["errors"].append("AC_DEP:"+type(exc).__name__+":"+str(exc)[:140])
            return {"status":"failure","evidence":["W4_MVP_DEPENDENCIES:FAIL_CLOSED"]}
        return {"status":"success",
                "writes":{"semantic_custody":"NOT_INDEPENDENT"},
                "evidence":["W4A:REAL_NATIVE_IMPLEMENTATION_VERIFIED",
                            "W4B+W4C:INDEPENDENT_PROVENANCE_UNQUALIFIED",
                            "W5:FULL_ORIGINAL_AE_NOT_RUN",
                            "ROOT_AC_MVP:2OF18"]}

    def exit_gate(_node,state,_attempt):
        if not (state.get("root_ac_v6") and state.get("new_native_ec_source") and
                state.get("semantic_custody")):
            return {"outcome":"full_AE_not_run",
                    "evidence":["PREREQUISITE_STATE_MISSING_FAIL_CLOSED"]}
        m=evidence["matrix"]
        if (m["original_issue_mvp_complete"] and m["MVP_scientifically_passed"]==18 and
            m["all_4_layer_oracle_A_to_E_run"] and
            m["independent_semantic_adjudicator_qualified"] and
            m["complete_S4_obligation_inventory_independently_qualified"]):
            return {"outcome":"all_18_and_AE","evidence":["ORIGINAL_TRUE_SCIENTIFIC_EXIT"]}
        if (not m["independent_semantic_adjudicator_qualified"] or
            not m["complete_S4_obligation_inventory_independently_qualified"]):
            return {"outcome":"semantic_custody_missing",
                    "evidence":["EC_SOURCE_WRITTEN_BUT_SEMANTIC_PROOF_NOT_INDEPENDENT"]}
        return {"outcome":"full_AE_not_run",
                "evidence":["FOUR_LAYER_CAUSAL_A_E_STILL_UNEXECUTED"]}

    out=execute_graph(graph,{
        "execute_root_original_v6":origin,
        "run_new_source_native_s3s4":native,
        "audit_w4_and_root_AC_dependencies":ac_check,
        "scientific_root_completion_gate":exit_gate,
    })
    demand(out.get("result")=="TERMINAL" and out.get("terminal_id") in (
        "root_science_verified","blocked_W4_semantic_authority",
        "blocked_W5_original_study","blocked_integrity"),"TCC7_RUNTIME_BAD_TERMINAL")
    verified=(out["terminal_id"]=="root_science_verified" and
              evidence.get("matrix",{}).get("MVP_scientifically_passed")==18 and
              evidence["matrix"]["all_4_layer_oracle_A_to_E_run"])
    demand(out["terminal_id"]!="root_science_verified" or verified,
           "G11_FALSIFIED_ROOT_SUCCESS")
    evidence.pop("_v6",None)
    return {
      "protocol":PROTOCOL,"TCC_source":TCC_SOURCE,"research_commit":source,
      "original_issue_ac_total":20,"original_MVP_required_AC":18,
      "TCC_nodes":len(graph["nodes"]),"TCC_edges":len(graph["edges"]),
      "TCC_spec_hash":graph["spec_hash"],"TCC_terminal":out["terminal_id"],
      "ECv4_evidence":to_ecv4_evidence(graph,out),
      "prior_original_AC_results":evidence.get("old_root"),
      "new_W4_native_source_test":evidence.get("new_native"),
      "W4_to_original_MVP_dependency_matrix":evidence.get("matrix"),
      "evidence_integrity_failures":evidence["errors"],
      "scientific_code_git_blobs":code_pre,
      "new_native_source_pre_post_same":(
          new_native_sources_before=={
            p:git_blob((new_native_root/p).read_bytes()) for p in
            (NATIVE_MODULE,NATIVE_TESTS)}),
      "new_native_git_source_blobs":new_native_sources_before,
      "source_code_pre_post_same":code_pre==code_seal(),
      "raw_evidence_pre_post_same":raw_pre==immutable_evidence_seal(),
      "original_scientifically_complete":bool(verified),
      "scheduled_tasks_created":False,
      "external_semantics_credentialed":False,
      "terminal":"ROOT_MVP_SCIENTIFICALLY_VERIFIED" if verified else
                 ("W4_NATIVE_EXECUTED_INDEPENDENT_SEMANTIC_AUTHORITY_REQUIRED"
                  if out["terminal_id"]=="blocked_W4_semantic_authority"
                  else "INTEGRITY_OR_FULL_AE_BLOCKED"),
    }

def main()->int:
    a=argparse.ArgumentParser()
    a.add_argument("--tcc-root",required=True,type=Path)
    a.add_argument("--ec-root",required=True,type=Path)
    a.add_argument("--new-native-root",required=True,type=Path)
    a.add_argument("--out",type=Path)
    v=a.parse_args()
    try:
        result=run(v.tcc_root,v.ec_root,v.new_native_root)
        data=json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
        if v.out:
            demand(not v.out.is_symlink(),"OUTPUT_SYMLINK_FORBIDDEN")
            v.out.write_text(data)
            print(json.dumps({"protocol":PROTOCOL,"terminal":result["terminal"],
                 "TCC_nodes":result["TCC_nodes"],"TCC_edges":result["TCC_edges"],
                 "root_MVP_pass":result.get("W4_to_original_MVP_dependency_matrix",{}).get("MVP_scientifically_passed"),
                 "new_EC_source_verified":result.get("new_W4_native_source_test",{}).get("genuine_native_selection_and_closure_code_exists",False),
                 "out":str(v.out)}))
        else:print(data,end="")
        return 0 if result["original_scientifically_complete"] else (
            2 if result["TCC_terminal"]=="blocked_W4_semantic_authority" else 3)
    except Exception as exc:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"INTEGRITY_FAIL_CLOSED",
                          "error":type(exc).__name__+":"+str(exc)[:360]}))
        return 3
if __name__=="__main__":
    raise SystemExit(main())
