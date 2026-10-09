#!/usr/bin/env python3
"""Third-stage origin #1 self-directed TCC: controlled S4 LLM information test.

Completes all currently executable machine-verified branches (frozen origin,
EC17, genuine Qwen17, actual S4 two-arm Qwen20, error-mechanism audit,
external-study preflight). No self-sent ChatGPT messages or schedule.
Never claims original five-arm S1-S4 causal localization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.run_issue57_tcc_generator_gate import TCC_SOURCE,context_for,node
from tools.run_issue1_autonomous_tcc_workflow_v2 import run as prior_run
from tools.run_issue1_s4_public_info_paired_llm_v1 import (
    PROTOCOL as S4_PROTOCOL, CONTRACT as S4_CONTRACT, FIELDS,
    blob_sha,arm_projection,read_contract,canonical_hash,public_projection,
)

PROTOCOL="ISSUE1_AUTONOMOUS_CAUSAL_INFORMATION_STAGE3_TCC_V1"
REPORT=ROOT/"results/issue1_s4_qwen20_paired_info_ablation_actual_2026-10-10.json"


def spec():
    return {
      "schema":"tcc.spec.v3",
      "tcc_id":"ISSUE1-AUTONOMOUS-AFTER-S4-REAL-20-V1",
      "goal":"Verify real 20 paired Qwen calls, automatically interpret observed effect and identify next scientific blocking work, with original S1-S4 not falsely closed",
      "acceptance":[
       "Replay real frozen origin/EC17/Qwen17/SUITE/ECv4 chain with source pins",
       "Prove 10 paired S4 public cases and exact pre-registered two-arm factor",
       "Recompute scores from raw labels, never trust report aggregates",
       "Gate any gold/hash/prompt/execution contamination before causal diagnosis",
       "Classify observed S4 information gain by frozen materiality criterion without post-hoc prompt tuning",
       "Use result-based conditional branch: benefit or no-effect, then check independent study provenance",
       "Record real next barrier and do not auto-close root issue without complete original A-E",
      ],
      "state_keys":["earlier_verified","paired_verified","material_effect","diagnosis","external_readiness"],
      "immutable_state_keys":[],
      "entry_nodes":["verify_origin_and_s2"],
      "nodes":[
        node("verify_origin_and_s2","action",writes=("earlier_verified",),failure="blocked_integrity"),
        node("verify_s4_paired_real_inference","action",depends=("verify_origin_and_s2",),
             writes=("paired_verified","material_effect"),failure="blocked_integrity"),
        node("branch_on_real_information_effect","gate",depends=("verify_s4_paired_real_inference",),
             reads=("paired_verified","material_effect"),
             branches={"no_material_effect":"diagnose_model_information_use",
                       "material_effect":"diagnose_representation_gain",
                       "invalid":"blocked_integrity"}),
        node("diagnose_model_information_use","action",writes=("diagnosis",),failure="blocked_integrity"),
        node("diagnose_representation_gain","action",failure="blocked_integrity"),
        node("blocked_external_review","terminal",terminal="BLOCKED",
             depends=("diagnose_representation_gain",)),
        node("check_external_scientific_gate","action",depends=("diagnose_model_information_use",),
             writes=("external_readiness",),failure="blocked_integrity"),
        node("accept_scoped_machine_terminal","terminal",terminal="SUCCESS",
             depends=("check_external_scientific_gate",)),
        node("blocked_integrity","terminal",terminal="BLOCKED"),
      ],
    }


def audit_report(envelope:dict)->dict:
    if str(ROOT/"tools") not in sys.path:
        sys.path.insert(0,str(ROOT/"tools"))
    from tools.generate_phase1_measurement_v2_canonical import SPECS,rebuild
    from tools.run_issue1_s4_interface_information_diagnostic_v1 import (
        baseline_signature,canonical_hash as original_hash,predict,
    )
    if set(envelope)!={"protocol","source_commit_at_run","pre_registered_contract_blob_sha1","source_verification","result"}:
        raise ValueError("PAIRED_EVIDENCE_ENVELOPE_SCHEMA_DRIFT")
    v=envelope["result"]
    frozen=json.loads(S4_CONTRACT.read_text())
    if frozen["status"]!="FROZEN_BEFORE_MODEL_RUN" or frozen["protocol"]!=S4_PROTOCOL:
        raise ValueError("PREREGISTERED_STUDY_CONTRACT_INVALID")
    if v["preregistered_contract_git_blob_sha1"]!=blob_sha(S4_CONTRACT) or envelope["pre_registered_contract_blob_sha1"]!=blob_sha(S4_CONTRACT):
        raise ValueError("PREREGISTRATION_SOURCE_BLOB_DRIFT")
    if v["protocol"]!=S4_PROTOCOL or v["actual_inferences"]!=20 or v["cases"]!=10:
        raise ValueError("REAL_PAIRED_INFERENCE_COVERAGE_REQUIRED")
    if v["original_phase1_oracle_A_to_E_completed"] or v["EC_native_closure_compared"] or v["independent_holdout"]:
        raise ValueError("SCOPED_RESEARCH_FALSE_ORIGINAL_COMPLETION")
    if len(v["case_results"])!=10:
        raise ValueError("MISSING_PAIRED_RESULTS")
    correct={"STRUCTURAL":0,"ENRICHED":0,"DETERMINISTIC":0}
    paired_changed=[]
    for spec, row in zip(SPECS,v["case_results"]):
        task,_s1,s2,s3,_s4,hidden,_manifest=rebuild(spec)
        if row["case_id"]!=spec["id"] or row["reference"]!=hidden["closure_class"]:
            raise ValueError("CASE_OR_GOLD_DRIFT")
        public=public_projection(task,s2,s3)
        if row["full_public_features_sha256"]!=canonical_hash(public) or row["shared_fixed_structural_signature_sha256"]!=baseline_signature(public):
            raise ValueError("PUBLIC_CASE_HASH_DRIFT")
        for arm,key in (("STRUCTURAL","structure"),("ENRICHED","enriched")):
            raw=row[key]
            if raw.get("arm")!=arm or raw.get("protocol")!="S4_PUBLIC_ARM_RAW_INFERENCE_V1":
                raise ValueError("ARM_ID_OR_PROTOCOL_MISMATCH")
            if raw["input_sha256"]!=canonical_hash(arm_projection(public,arm)):
                raise ValueError("ACTUAL_MODEL_INPUT_NOT_FIXED_TO_ARM")
            if raw.get("model_oracle_access") is not False:
                raise ValueError("ORACLE_ACCESS_SELF_ATTESTATION_INVALID")
            if not all(len(raw[k])==64 for k in ("prompt_sha256","stdout_sha256","stderr_sha256")):
                raise ValueError("MISSING_RAW_MODEL_PROVENANCE_HASH")
            if raw["parsed_prediction"]!=(
                 raw["raw_response"] if raw["raw_response"] in ("CLOSE","CONTINUE") else "FORMAT_ERROR"):
                raise ValueError("RAW_PARSE_OR_PREDICTION_TAMPERED")
            expected=raw["parsed_prediction"]==hidden["closure_class"]
            if row[("structure" if arm=="STRUCTURAL" else "enriched")+"_correct"]!=expected:
                raise ValueError("REPORTED_SCORE_NOT_RAW_RECOMPUTATION")
            correct[arm]+=int(expected)
        deterministic=predict(public)["closure_class"]==hidden["closure_class"]
        if row["public_deterministic_correct"]!=deterministic:
            raise ValueError("DETERMINISTIC_BASELINE_RAW_SCORE_DRIFT")
        correct["DETERMINISTIC"]+=int(deterministic)
        if row["structure"]["parsed_prediction"]!=row["enriched"]["parsed_prediction"]:
            paired_changed.append(spec["id"])
    if (v["structural_correct"],v["enriched_correct"],v["enhanced_deterministic_typed_policy_correct"])!=(
        correct["STRUCTURAL"],correct["ENRICHED"],correct["DETERMINISTIC"]):
        raise ValueError("AGGREGATE_RESULTS_NOT_RECOMPUTED")
    gain=(correct["ENRICHED"]-correct["STRUCTURAL"])/10
    if abs(gain-v["paired_enriched_minus_structural_accuracy"])>1e-10:
        raise ValueError("MATERIAL_EFFECT_NOT_REPRODUCED")
    threshold=frozen["comparison"]["materiality_abs"]
    decision="STRUCTURED_UPSTREAM_INFORMATION_MATERIAL_ON_EXPOSED_FIXTURES_ONLY" if gain>=threshold else "NO_MATERIAL_INFORMATION_EFFECT_DETECTED_ON_EXPOSED_FIXTURES"
    if v["decision"]!=decision:
        raise ValueError("PREREGISTERED_DECISION_NOT_REPRODUCED")
    return {
      "cases":10,"calls":20,"structural_correct":correct["STRUCTURAL"],
      "enriched_correct":correct["ENRICHED"],"typed_public_correct":correct["DETERMINISTIC"],
      "actual_qwen_changed_decisions":paired_changed,
      "paired_enriched_minus_structural":gain,"materiality_threshold":threshold,
      "branch":"material_effect" if gain>=threshold else "no_material_effect",
      "provenance_scope":"source-hash-matched real raw model outputs on historical exposed fixtures, not independent unseen or original native S4",
    }


def run(tcc_root:Path,ec_root:Path|None,*,study_dir:Path|None=None,
        report:Path=REPORT,model:Path|None=None,llama:Path|None=None,
        seconds:int=65)->dict:
    import subprocess
    if not tcc_root.is_dir():raise ValueError("PINNED_TCC_MISSING")
    head=subprocess.run(["git","-C",str(tcc_root),"rev-parse","HEAD"],
                        capture_output=True,text=True,timeout=12)
    if head.returncode or head.stdout.strip()!=TCC_SOURCE:
        raise ValueError("TCC_COMPILER_GIT_HEAD_CHANGED")
    if str(tcc_root) not in sys.path:sys.path.insert(0,str(tcc_root))
    from tcc.core_v3 import compile_spec,normalize_spec,validate_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph,to_ecv4_evidence
    from tools.preflight_issue57_study_assets import inspect_study
    research=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD"],
                            capture_output=True,text=True,timeout=12)
    if research.returncode:raise ValueError("RESEARCH_GIT_SOURCE_UNAVAILABLE")
    head=research.stdout.strip()
    manifest=spec()
    ctx=context_for(manifest,head)
    ctx.update({"selected_issue_id":"ISSUE-1","actionable_issue_ids":["ISSUE-1"],
                "blocked_issue_ids":[],"snapshot_id":"ISSUE1-STAGE3-"+head[:12],
                "source_fingerprint":"sha256:"+hashlib.sha256(
                    json.dumps({"source":head,"spec":manifest},sort_keys=True).encode()).hexdigest()})
    built=generate_tcc_from_context(ctx)
    if built.get("result")!="tcc.spec.v3" or validate_spec(built["spec"]):
        raise ValueError("TCC_GENERATION_SEMANTIC_FAILURE")
    if built["spec"]!=normalize_spec(manifest):
        raise ValueError("TCC_GENERATOR_SILENT_SEMANTIC_CHANGE")
    graph=compile_spec(built["spec"])
    state={}
    def origin(_node,_state,_attempt):
        try:
            from tools.run_issue1_autonomous_tcc_workflow_v2 import run as previous
            previous_report=previous(tcc_root,ec_root=ec_root)
            if not previous_report["subworkflow_machine_qualified"]:
                raise ValueError("EARLIER_SCIENCE_EVIDENCE_NOT_QUALIFIED")
            if previous_report["ecv4_issue_closure_authorized"] or previous_report["original_issue_1_five_arm_complete"]:
                raise ValueError("FORGED_ORIGINAL_EXIT")
            state["upstream"]={"native_EC17":previous_report["native_ec_17"]["status"],
                               "Qwen17":previous_report["real_qwen_17"]["status"],
                               "original_phase1":"EC_NATIVE_SCOPE_INCOMPATIBLE"}
        except Exception as exc:
            state["error"]="ORIGIN:"+type(exc).__name__+":"+str(exc)[:160]
            return {"status":"failure","evidence":["origin:FAIL:"+type(exc).__name__]}
        return {"status":"success","writes":{"earlier_verified":True},
                "evidence":["upstream:real-frozen-TCC-native-EC17-Qwen17-SUITE-ECv4-VERIFIED"]}
    def paired(_node,_state,_attempt):
        try:
            if report.is_symlink():
                raise ValueError("MODEL_REPORT_SYMLINK_PROHIBITED")
            if not report.is_file():
                if model is None or llama is None:
                    raise ValueError("REAL_20_MODEL_RAW_REPORT_MISSING_AND_NO_PINNED_EXECUTION_ASSETS")
                from tools.run_issue1_s4_public_info_paired_llm_v1 import run as run_live_model
                import os,tempfile
                raw=run_live_model(model,llama,seconds)
                envelope_live={
                    "protocol":"ISSUE1_S4_QWEN20_ACTUAL_PAIRED_OUTPUT_SEAL_20261010_V1",
                    "source_commit_at_run":head,
                    "pre_registered_contract_blob_sha1":raw["preregistered_contract_git_blob_sha1"],
                    "source_verification":{
                      "model_actual_calls":20,"paired_frozen_cases":10,
                      "original_A_E_completed":False,"independent_gold":False,
                    },
                    "result":raw,
                }
                report.parent.mkdir(parents=True,exist_ok=True)
                tmp_path=None
                try:
                    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=report.parent,
                         prefix=".issue1_s4_pending_",suffix=".json",delete=False) as staging:
                        tmp_path=Path(staging.name)
                        json.dump(envelope_live,staging,ensure_ascii=False,sort_keys=True,indent=2)
                        staging.write("\n")
                        staging.flush()
                        os.fsync(staging.fileno())
                    # Atomic create only; never overwrite a competing evidence record.
                    os.link(tmp_path,report)
                finally:
                    if tmp_path is not None:
                        tmp_path.unlink(missing_ok=True)
            envelope=json.loads(report.read_text())
            result=audit_report(envelope)
            state["S4"]=result
        except Exception as exc:
            state["error"]="PAIRED:"+type(exc).__name__+":"+str(exc)[:160]
            return {"status":"failure","evidence":["S4-real-paired:FAIL:"+type(exc).__name__]}
        return {"status":"success",
                "writes":{"paired_verified":True,"material_effect":result["branch"]},
                "evidence":["S4-real-model-paired20:PASS",
                            "actual-info-treatment:"+result["branch"]]}
    def effect_gate(_node,live,_attempt):
        value=live.get("material_effect")
        return {"outcome":value if live.get("paired_verified") is True and
                value in ("material_effect","no_material_effect") else "invalid",
                "evidence":["frozen-materiality-threshold:"+str(state["S4"]["materiality_threshold"]) if "S4" in state else "NOT_VERIFIED"]}
    def no_gain(_node,_state,_attempt):
        result=state["S4"]
        # Non-overclaiming diagnosis: input addition was not sufficient for
        # this fixed small model/prompt; does NOT prove permanent incapacity.
        state["inference"]={"mechanism":"ADDED_PUBLIC_INFORMATION_NOT_USED_IN_FIXED_QWEN_ASSAY",
              "model_pairwise_label_changes":result["actual_qwen_changed_decisions"],
              "next_scientific_target":"NEW_UNSEEN_SEMANTIC_GROUNDING_ASSAY_WITH_INDEPENDENT_GOLD_AND_FIXED_INTERFACE",
              "wrong_cases_need_not_imply_universal_incapacity":True}
        return {"status":"success","writes":{"diagnosis":"NO_MATERIAL_GAIN_EXPOSED"},
                "evidence":["no-gain:next-science-semantic-grounding-not-relabel-answers"]}
    def gain(_node,_state,_attempt):
        state["inference"]={"mechanism":"PUBLIC_UPSTREAM_INFORMATION_MATTERS_FOR_THIS_FIXED_QWEN_ASSAY",
              "model_pairwise_label_changes":state["S4"]["actual_qwen_changed_decisions"],
              "next_scientific_target":"INDEPENDENT_HOLDOUT_MATCHED_S4_PLUS_S1_S2_S3_CAUSAL_INTERVENTIONS"}
        return {"status":"success",
                "evidence":["gain:scoped-feature-effect-only:independent-review-required"]}
    def independent(_node,_state,_attempt):
        readiness=inspect_study(study_dir)
        if any(readiness.get(k) is not False for k in (
             "external_gold_independence_verified","provenance_custody_verified",
             "genuine_inference_verified")):
            state["error"]="EXTERNAL_STUDY_FALSE_CERTIFICATION"
            return {"status":"failure","evidence":["independent-study:FALSE_CLAIM"]}
        state["independence"]={"stage":readiness["stage"],
                               "blockers":readiness["blockers"],
                               "provenance_certified":False}
        return {"status":"success","writes":{"external_readiness":"EXTERNAL_INDEPENDENCE_NOT_VERIFIED"},
                "evidence":["independent-scientific-gold:NOT_VERIFIED",
                            "original-full-five-arm:NOT_RUN"]}
    # Prior action-specific handlers dynamically add the common independent
    # gate as downstream through a TCC dependency, without manual user prompts.
    handlers={"verify_origin_and_s2":origin,
              "verify_s4_paired_real_inference":paired,
              "branch_on_real_information_effect":effect_gate,
              "diagnose_model_information_use":no_gain,
              "diagnose_representation_gain":gain,
              "check_external_scientific_gate":independent}
    result=execute_graph(graph,handlers)
    if result.get("result")!="TERMINAL":
        raise ValueError("TCC_FAILED_TO_TERMINATE")
    if result.get("terminal_status") not in ("BLOCKED","SUCCESS"):
        raise ValueError("UNEXPECTED_TCC_TERMINAL")
    return {
       "protocol":PROTOCOL,
       "repo_source_commit":head,
       "TCC_compiler_sha":TCC_SOURCE,
       "graph_nodes":len(graph["nodes"]),"graph_edges":len(graph["edges"]),
       "graph_spec_sha":graph["spec_hash"],
       "tcc_terminal_id":result["terminal_id"],
       "tcc_terminal_status":result["terminal_status"],
       "ecv4_evidence":to_ecv4_evidence(graph,result),
       "prior_actual_machine_studies":state.get("upstream"),
       "new_actual_llm_info_intervention":state.get("S4"),
       "mechanistic_interpretation":state.get("inference"),
       "independent_gold_gate":state.get("independence"),
       "failure":state.get("error"),
       "new_scheduled_tasks":False,
       "background_self_prompt_loop":False,
       "full_original_s1_s4_A_E_completed":False,
       "scientific_capability_preservation_certified":False,
       "ecv4_original_issue_closure_authorized":False,
       "terminal":"ALL_AVAILABLE_SCOPED_EXPERIMENTS_AUDITED_ORIGINAL_FULL_STUDY_STILL_OPEN"
            if result["terminal_id"]=="accept_scoped_machine_terminal"
            else "FAIL_CLOSED_STUDY_AUDIT",
    }


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--tcc-root",type=Path,required=True)
    ap.add_argument("--ec-root",type=Path)
    ap.add_argument("--study-dir",type=Path)
    ap.add_argument("--report",type=Path,default=REPORT)
    ap.add_argument("--model",type=Path)
    ap.add_argument("--llama-cli",type=Path)
    ap.add_argument("--seconds",type=int,default=65)
    a=ap.parse_args()
    try:
        data=run(a.tcc_root,a.ec_root,study_dir=a.study_dir,report=a.report,
                 model=a.model,llama=a.llama_cli,seconds=a.seconds)
        print(json.dumps(data,sort_keys=True,ensure_ascii=False,indent=2))
        return 0 if data["terminal"]=="ALL_AVAILABLE_SCOPED_EXPERIMENTS_AUDITED_ORIGINAL_FULL_STUDY_STILL_OPEN" else 3
    except Exception as exc:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(exc).__name__+":"+str(exc)[:310]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
