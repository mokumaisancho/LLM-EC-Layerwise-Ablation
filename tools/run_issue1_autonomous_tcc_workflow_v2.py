#!/usr/bin/env python3
"""Issue #1: self-directed second TCC stage, beyond the original P2 barrier.

Runs actual machine-resolvable SCIENTIFIC *diagnostics* (public S4 interface
sufficiency, pinned native EC 17, matched same-case local Qwen 17) instead
of stopping immediately at original Phase1 incompatible P2. Outputs explicit
scope and blockers; never closes the original A-E or independent #57 study.
No timers, background jobs, schedulers, chat UI, or user prompts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from tools.run_issue57_tcc_generator_gate import TCC_SOURCE, context_for, node
from tools.run_issue1_autonomous_tcc_workflow import execute as execute_prior
from tools.run_issue1_s4_interface_information_diagnostic_v1 import run as run_s4

PROTOCOL="ISSUE1_AUTONOMOUS_CONTINUATION_TCC_STAGE2_V1"
DEFAULT_MODEL_EVIDENCE=ROOT/"results/issue1_qwen_next_action_v2_mac_actual_2026-10-10.json"

def sha(value)->str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
                                     separators=(",",":")).encode()).hexdigest()

def get_head(repo:Path)->str:
    p=subprocess.run(["git","-C",str(repo),"rev-parse","HEAD"],
                     text=True,capture_output=True,timeout=15)
    if p.returncode:raise RuntimeError("GIT_SOURCE_PIN_UNAVAILABLE")
    return p.stdout.strip()

def spec()->dict:
    return {
      "schema":"tcc.spec.v3",
      "tcc_id":"ISSUE1-AUTONOMOUS-BEYOND-P2-S3S4-QWEN-REAL-V1",
      "goal":"After original Phase1 P2 incompatibility, perform independent available bounded experiments without repeated user prompts",
      "acceptance":[
        "Original AC-01..20 and frozen V1/V2 remain untouched; explicitly block fictional A-E result",
        "Actually rerun original TCC, SUITE, ECv4 and qualify scoped successor",
        "Actually run retrospective S4 public-info intervention with negative controls; do not call EC accuracy",
        "Actually rerun 17 native EC source-pinned governed next actions when source is available",
        "Use genuine pinned Qwen raw same-case output if source-pinned runtime available, or stable previously sealed report",
        "Missing runtime must not hide independent machine-resolvable steps or count as completed science",
        "All outcomes recorded in generated TCC ECv4 handoff and source hashes; no automatic closure",
      ],
      "state_keys":["origin_gate","s4_diagnostic","ec17","llm17"],
      "immutable_state_keys":[],
      "entry_nodes":["frozen_origin"],
      "nodes":[
        node("frozen_origin","action",writes=("origin_gate",),failure="blocked_integrity"),
        node("s4_public_info","action",depends=("frozen_origin",),
             writes=("s4_diagnostic",),failure="blocked_integrity"),
        node("ec_native17","action",depends=("s4_public_info",),
             writes=("ec17",),failure="blocked_integrity"),
        node("llm_pinned17","action",depends=("ec_native17",),
             writes=("llm17",),failure="blocked_integrity"),
        node("assess_machine_scope","gate",depends=("llm_pinned17",),
             reads=("origin_gate","s4_diagnostic","ec17","llm17"),
             branches={"all_available":"scoped_machine_evidence_qualified",
                       "additional_input_missing":"blocked_external_science"}),
        node("scoped_machine_evidence_qualified","terminal",terminal="SUCCESS"),
        node("blocked_external_science","terminal",terminal="BLOCKED"),
        node("blocked_integrity","terminal",terminal="BLOCKED"),
      ],
    }

def checked_model_report(envelope:dict)->dict:
    data=envelope.get("run",envelope.get("result",envelope))
    if data.get("protocol")!="ISSUE1_NEXT_ACTION_QWEN_MAC_COMPAT_REAL_V3":
        raise ValueError("UNRECOGNIZED_LOCAL_LLM_REPORT")
    if data.get("qwen_model_sha256")!="1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370":
        raise ValueError("LOCAL_QWEN_MODEL_PIN_MISMATCH")
    if data.get("local_binary_sha256")!="023712cb97abef06769a544fe034a92cc57921bd60fd9fcd2c02e325839641c2":
        raise ValueError("LOCAL_BINARY_SHA_MISMATCH")
    if data.get("llm_actual_inference_count")!=17 or len(data.get("raw_inference",[]))!=17:
        raise ValueError("LOCAL_QWEN_REAL_INFERENCE_COVERAGE_INVALID")
    if len(data.get("llm",{}).get("rows",[]))!=17:
        raise ValueError("LOCAL_QWEN_CASE_ROWS_MISSING")
    if data.get("independent_gold") is not False or data.get("scientific_phase1_a_e_completed") is not False:
        raise ValueError("FALSE_CLAIM_OF_SCIENTIFIC_COMPLETION")
    return data

def run(tcc_root:Path,*,ec_root:Path|None=None,model:Path|None=None,
        llama:Path|None=None,report_file:Path|None=None,seconds:int=90)->dict:
    expected=get_head(ROOT)
    if get_head(tcc_root)!=TCC_SOURCE:raise ValueError("TCC_GENERATOR_PIN_MISMATCH")
    if str(tcc_root) not in sys.path:sys.path.insert(0,str(tcc_root))
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.core_v3 import compile_spec,validate_spec,normalize_spec
    from tcc.runtime_v3 import execute_graph,to_ecv4_evidence
    contract=spec();ctx=context_for(contract,expected)
    ctx["selected_issue_id"]="ISSUE-1";ctx["actionable_issue_ids"]=["ISSUE-1"]
    ctx["blocked_issue_ids"]=[]
    ctx["snapshot_id"]="ISSUE1-STAGE2:"+expected[:16]
    ctx["source_fingerprint"]="sha256:"+sha({"spec":contract,"head":expected,"pin":TCC_SOURCE})
    generated=generate_tcc_from_context(ctx)
    if generated.get("result")!="tcc.spec.v3" or validate_spec(generated.get("spec")):
        raise ValueError("TCC_SPEC_GENERATION_FAILED:"+str(generated.get("errors",[])))
    if generated["spec"]!=normalize_spec(contract):
        raise ValueError("TCC_SEMANTIC_CONTRACT_CHANGED")
    graph=compile_spec(generated["spec"]);obs={}

    def frozen(_node,_state,_attempt):
        try:
            first=execute_prior(tcc_root,expected_source=expected)
            if first["stop_state"]!="SCOPED_SUCCESSOR_AUDITED_ORIGINAL_REQUIRES_NEW_VALID_STUDY":
                raise ValueError("ORIGIN_TCC_NOT_AUTHORIZED")
            if first["ecv4_closure_authorized"] or first["original_five_arm_complete"]:
                raise ValueError("FROZEN_ORIGINAL_UNJUSTIFIABLY_CLOSED")
            obs["first_stage"]={"terminal":first["tcc_terminal_id"],
                                "suite_ecv4":first["method_audit"],
                                "source":first["source_commit"]}
        except Exception as ex:
            obs["failure"]="origin:"+type(ex).__name__+":"+str(ex)[:170]
            return {"status":"failure","evidence":["original:FAIL:"+type(ex).__name__]}
        return {"status":"success","writes":{"origin_gate":"VERIFIED_BUT_ORIGINAL_P2_INCOMPATIBLE"},
                "evidence":["original-v2-TCC-replay:PASS:EC_NATIVE_SCOPE_INCOMPATIBLE",
                            "SUITE-ECv4:PASS"]}

    def s4_diagnostic(_node,_state,_attempt):
        try:
            s4=run_s4()
            if s4["enhanced_public_interface_known_fixture_accuracy"]!=1 or s4["original_structural_interface_majority_upper_bound"]!=.8:
                raise ValueError("S4_DIAGNOSTIC_COUNTERFACTUAL_FAILED")
            if s4["independent_study_certified"] or s4["native_ec_closure_measured"]:
                raise ValueError("SCOPED_S4_DIAGNOSTIC_FALSE_CERTIFICATION")
            obs["s4"]={"retrospective_count":s4["fixture_count"],
                       "old_majority_upper_bound":.8,"public_enriched_case_accuracy":1,
                       "strict_scope":"retrospective_fixture_information_not_ec_accuracy",
                       "source_hash":sha(s4)}
        except Exception as ex:
            obs["failure"]="s4:"+type(ex).__name__+":"+str(ex)[:170]
            return {"status":"failure","evidence":["S4:FAIL:"+type(ex).__name__]}
        return {"status":"success","writes":{"s4_diagnostic":"PASS_SCOPED_DIAGNOSTIC"},
                "evidence":["S4:known-10:structural-upper-bound8/10:public-features10/10:controls-PASS"]}

    def native(_node,_state,_attempt):
        if ec_root is None:
            obs["ec17"]={"status":"EC_PINNED_CHECKOUT_NOT_SUPPLIED"}
            return {"status":"success","writes":{"ec17":"UNAVAILABLE"},
                    "evidence":["native-EC17:source-checkout-missing"] }
        try:
            from tools.replay_issue1_ecv44_native_next_action_v2 import replay
            r=replay(ec_root)
            if r["terminal"]!="NATIVE_EC_17_CASE_REPLAY_MATCH" or r["ec_decision_correct"]!=17 or r["ec_reason_correct"]!=17:
                raise ValueError("EC_ACTUAL_REPLAY_DIVERGED")
            obs["ec17"]={"status":"REPLAY_MATCH","cases":17,
                         "source_commit":r["source_ec_commit"],"raw_evidence_hash":sha(r)}
        except Exception as ex:
            obs["failure"]="ec17:"+type(ex).__name__+":"+str(ex)[:170]
            return {"status":"failure","evidence":["native-EC17:FAIL:"+type(ex).__name__]}
        return {"status":"success","writes":{"ec17":"ACTUAL_REPLAY_MATCH"},
                "evidence":["native-EC17:real-rerun:17-decision-pass:17-reason-pass"]}

    def qwen(_node,_state,_attempt):
        try:
            report=report_file or DEFAULT_MODEL_EVIDENCE
            if report.is_file():
                data=checked_model_report(json.loads(report.read_text()))
                obs["llm17"]={"status":"REAL_PINNED_CASES_CACHED",
                              "cases":17,"correct":data["llm"]["decision_correct"],
                              "source_sha256":sha(data)}
            elif model is not None and llama is not None and ec_root is not None:
                from tools.run_issue1_llm_next_action_v2_local_mac import execute
                data=checked_model_report(execute(model,llama,ec_root,seconds))
                obs["llm17"]={"status":"REAL_PINNED_CASES_JUST_RUN",
                              "cases":17,"correct":data["llm"]["decision_correct"],
                              "source_sha256":sha(data)}
            else:
                obs["llm17"]={"status":"MODEL_EVIDENCE_OR_RUNTIME_UNAVAILABLE"}
                return {"status":"success","writes":{"llm17":"UNAVAILABLE"},
                        "evidence":["Qwen17:missing-verifiable-real-output"] }
        except Exception as ex:
            obs["failure"]="llm17:"+type(ex).__name__+":"+str(ex)[:170]
            return {"status":"failure","evidence":["Qwen17:FAIL:"+type(ex).__name__]}
        return {"status":"success","writes":{"llm17":"ACTUAL_REAL_OUTPUT_RECORDED"},
                "evidence":["Qwen17:17-real-case-inferences-pinned:no-gold-certificate"]}

    def final_gate(_node,state,_attempt):
        good=(state.get("origin_gate")=="VERIFIED_BUT_ORIGINAL_P2_INCOMPATIBLE"
              and state.get("s4_diagnostic")=="PASS_SCOPED_DIAGNOSTIC"
              and state.get("ec17")=="ACTUAL_REPLAY_MATCH"
              and state.get("llm17")=="ACTUAL_REAL_OUTPUT_RECORDED")
        return {"outcome":"all_available" if good else "additional_input_missing",
                "evidence":["scoped-machine-evidence:"+("COMPLETE" if good else "PARTIAL"),
                            "original-S1S4-five-arm:NOT_RUN","independent-original-LLM0:NOT_PROVEN"]}
    handlers={
       "frozen_origin":frozen,"s4_public_info":s4_diagnostic,
       "ec_native17":native,"llm_pinned17":qwen,"assess_machine_scope":final_gate,
    }
    output=execute_graph(graph,handlers)
    if output.get("result")!="TERMINAL" or output["terminal_id"] not in (
       "scoped_machine_evidence_qualified","blocked_external_science","blocked_integrity"):
        raise ValueError("TCC_RUNTIME_UNEXPECTED_TERMINAL")
    original_done=False
    return {
      "protocol":PROTOCOL,"research_commit":expected,"tcc_compiler_pin":TCC_SOURCE,
      "generated_node_count":len(graph["nodes"]),"generated_edge_count":len(graph["edges"]),
      "generated_spec_sha":graph["spec_hash"],"ecv4_handoff":to_ecv4_evidence(graph,output),
      "prior_tcc_verification":obs.get("first_stage"),"s4_public_information":obs.get("s4"),
      "native_ec_17":obs.get("ec17"),"real_qwen_17":obs.get("llm17"),
      "original_issue_1_five_arm_complete":original_done,
      "external_independent_gold_qualified":False,
      "original_phase1_ec_native_contract_repaired":False,
      "ecv4_issue_closure_authorized":False,
      "registered_task_or_schedule":False,"employed_background_ui":False,
      "subworkflow_machine_qualified":output["terminal_id"]=="scoped_machine_evidence_qualified",
      "error":obs.get("failure"),
      "stop_state":"MACHINE_SCOPED_EVIDENCE_COMPLETE_ORIGINAL_SCIENCE_STILL_BLOCKED" if output["terminal_id"]=="scoped_machine_evidence_qualified"
       else "EXTERNAL_INPUT_REQUIRED" if output["terminal_id"]=="blocked_external_science" else "FAIL_CLOSED_INTEGRITY",
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--tcc-root",type=Path,required=True)
    ap.add_argument("--ec-root",type=Path)
    ap.add_argument("--model",type=Path)
    ap.add_argument("--llama-cli",type=Path)
    ap.add_argument("--report-file",type=Path)
    ap.add_argument("--seconds",type=int,default=90)
    a=ap.parse_args()
    try:
        r=run(a.tcc_root,ec_root=a.ec_root,model=a.model,llama=a.llama_cli,report_file=a.report_file,seconds=a.seconds)
        print(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2))
        return 0 if r["subworkflow_machine_qualified"] else 2
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"stop_state":"FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:300]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
