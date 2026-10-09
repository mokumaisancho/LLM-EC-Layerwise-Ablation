#!/usr/bin/env python3
"""Self-directed, single-invocation origin #1 workflow with real TCC v3 gates.

This is not ChatGPT message recursion and creates NO task, daemon, cron entry,
calendar event or watcher. It advances all machine-resolvable dependencies
without user prompts and returns an honest terminal with ECv4 evidence.
Externally required independent evaluation never self-certifies itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools.audit_issue1_original_exit_and_scoped_successor import verify
from tools.run_issue57_tcc_generator_gate import TCC_SOURCE, context_for, node


def canonical_sha(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,
                                     separators=(",",":")).encode()).hexdigest()


def spec() -> dict:
    return {
        "schema": "tcc.spec.v3",
        "tcc_id": "ORIGIN-ISSUE1-SELF-ADVANCING-TRUTHFUL-EXIT-V1",
        "goal": "Complete machine-executable original-issue verification and scoped successor; fail closed at genuine external evidence and incompatible semantics",
        "acceptance": [
            "Root #1 five-arm S1-S4 objectives remain immutable; #57 independent four-arm conservation is separate",
            "Original Phase1 TCC V2 actually rerun without unauthorized repair, all source hashes audited",
            "Native EC singleton S3 and underidentified S4 not falsely compared against generic frozen Phase1",
            "Route incompatible frozen branch automatically to real scoped S1C successor audit without user prompts",
            "Check optional external blind-study public/seal artifacts without reading private gold or certifying custodian",
            "No timestamp schedule, no task registration, no user UI activity, no automatic issue closure",
            "Emit one explicit terminal, ECv4-handoff evidence, source hash and genuinely unresolved requirements",
        ],
        "state_keys": ["origin_verified","original_terminal","scoped_verified","external_structural_ready"],
        "immutable_state_keys": [],
        "entry_nodes":["verify_frozen_origin"],
        "nodes":[
            node("verify_frozen_origin","action", writes=("origin_verified","original_terminal"),
                 failure="blocked_integrity"),
            node("route_original_scope","gate", depends=("verify_frozen_origin",),
                 reads=("origin_verified","original_terminal"),
                 branches={"frozen_incompatible":"verify_scoped_successor",
                           "unanticipated_change":"blocked_integrity"}),
            node("verify_scoped_successor","action",writes=("scoped_verified",),
                 failure="blocked_integrity"),
            node("check_blind_study","action",depends=("verify_scoped_successor",),
                 writes=("external_structural_ready",), failure="blocked_integrity"),
            node("route_external_evidence","gate",depends=("check_blind_study",),
                 reads=("scoped_verified","external_structural_ready"),
                 branches={"missing":"scoped_verified_external_missing",
                           "requires_review":"scoped_verified_external_review"}),
            node("scoped_verified_external_missing","terminal",terminal="BLOCKED"),
            node("scoped_verified_external_review","terminal",terminal="BLOCKED"),
            node("blocked_integrity","terminal",terminal="BLOCKED"),
        ],
    }


def source_sha() -> str:
    result=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD"],
                          capture_output=True,text=True,timeout=15)
    if result.returncode:
        raise RuntimeError("GIT_SOURCE_HEAD_UNAVAILABLE")
    return result.stdout.strip()


def execute(tcc_root: Path, *, study_dir: Path | None = None,
            expected_source: str | None = None, verifier=verify,
            study_inspector=None) -> dict:
    if expected_source is not None and source_sha()!=expected_source:
        raise ValueError("RESEARCH_HEAD_DRIFT")
    head=source_sha()
    tcc_head=subprocess.run(["git","-C",str(tcc_root),"rev-parse","HEAD"],
                            capture_output=True,text=True,timeout=15)
    if tcc_head.returncode or tcc_head.stdout.strip()!=TCC_SOURCE:
        raise ValueError("READONLY_TCC_COMPILER_PIN_MISMATCH")
    if str(tcc_root) not in sys.path:
        sys.path.insert(0,str(tcc_root))
    from tcc.recipe_builder_v3 import build_recipe_from_context, generate_tcc_from_context
    from tcc.core_v3 import compile_spec, normalize_spec, validate_spec
    from tcc.runtime_v3 import execute_graph, to_ecv4_evidence
    from tools.preflight_issue57_study_assets import inspect_study
    contract=spec()
    ctx=context_for(contract,head)
    ctx["selected_issue_id"]="ISSUE-1"
    ctx["actionable_issue_ids"]=["ISSUE-1"]
    ctx["blocked_issue_ids"]=[]
    ctx["snapshot_id"]="ISSUE1-AUTONOMOUS-WORKFLOW:"+head[:16]
    ctx["source_fingerprint"]="sha256:"+canonical_sha({
        "spec":contract,"repo_head":head,"tcc_compiler":TCC_SOURCE,
        "root_issue":1,"related_issues":[57,58]})
    recipe=build_recipe_from_context(ctx)
    generated=generate_tcc_from_context(ctx)
    if recipe.get("result")!="suite.tcc-generation-recipe.v4":
        raise RuntimeError("TCC_RECIPE_INVALID:"+str(recipe.get("reason_code")))
    if generated.get("result")!="tcc.spec.v3":
        raise RuntimeError("TCC_SPEC_GENERATION_INVALID:"+str(generated.get("reason_code")))
    if validate_spec(generated["spec"]) or generated["spec"]!=normalize_spec(contract):
        raise RuntimeError("TCC_GENERATOR_SEMANTIC_DRIFT")
    graph=compile_spec(generated["spec"])
    observed:dict={}
    def origin_handler(_node,_state,_attempt):
        try:
            result=verifier(ROOT,actual_replay=True)
            if result["frozen_tcc_replay"]["terminal"]!="EC_NATIVE_SCOPE_INCOMPATIBLE":
                raise ValueError("UNEXPECTED_FROZEN_ORIGINAL_TERMINAL")
            if result["original_exit_pass"] is not False:
                raise ValueError("ORIGINAL_AC_FALSELY_SATISFIED")
            observed["origin"]=result
        except Exception as ex:
            observed["error"]="ORIGIN:"+type(ex).__name__+":"+str(ex)[:160]
            return {"status":"failure","evidence":["origin:FAIL:"+type(ex).__name__]}
        return {"status":"success",
                "writes":{"origin_verified":True,"original_terminal":result["frozen_tcc_replay"]["terminal"]},
                "evidence":["original:real-TCC-replay:rc4:EC_NATIVE_SCOPE_INCOMPATIBLE",
                            "original:finite-bound:8/10:not-EC-accuracy"]}
    def scope_gate(_node,state,_attempt):
        observed["branch_decision"]="incompatible" if state.get("original_terminal")=="EC_NATIVE_SCOPE_INCOMPATIBLE" else "unexpected"
        return {"outcome":"frozen_incompatible" if observed["branch_decision"]=="incompatible"
                and state.get("origin_verified") is True else "unanticipated_change",
                "evidence":["route:"+observed["branch_decision"]]}
    def successor_handler(_node,_state,_attempt):
        try:
            r=observed["origin"]
            if r["completed_scoped_successor"]["scoped_study_status"]!="COMPLETE_FOR_CURRENT_MVP_BOUNDARY":
                raise ValueError("SCOPED_SUCCESSOR_UNVERIFIED")
            if not r["s4"]["not_ec_accuracy"] or r["s4"]["structural_upper_bound"]!=0.8:
                raise ValueError("INTERFACE_IDENTIFIABILITY_DRIFT")
            observed["successor"]={"source":r["completed_scoped_successor"]["source_report"],
                                   "status":"COMPLETE_FOR_CURRENT_MVP_BOUNDARY"}
        except Exception as ex:
            observed["error"]="SUCCESSOR:"+type(ex).__name__+":"+str(ex)[:160]
            return {"status":"failure","evidence":["successor:FAIL:"+type(ex).__name__]}
        return {"status":"success","writes":{"scoped_verified":True},
                "evidence":["successor:verified-limited-finite-typed-boundary",
                            "successor:raw-Qwen-actual-output-hash-pinned",
                            "no-false-original-AC-closure"]}
    def study_handler(_node,_state,_attempt):
        try:
            inspector=study_inspector or inspect_study
            readiness=inspector(study_dir)
            if not isinstance(readiness,dict) or readiness.get("external_gold_independence_verified") is not False:
                raise ValueError("INDEPENDENCE_NOT_MACHINE_CERTIFIABLE")
            if readiness.get("provenance_custody_verified") is not False or readiness.get("genuine_inference_verified") is not False:
                raise ValueError("EXTERNAL_ATTESTATION_NOT_ALLOWED")
            observed["study_readiness"]=readiness
        except Exception as ex:
            observed["error"]="STUDY:"+type(ex).__name__+":"+str(ex)[:160]
            return {"status":"failure","evidence":["external-study:FAIL:"+type(ex).__name__]}
        return {"status":"success",
                "writes":{"external_structural_ready":readiness.get("machine_structural_complete") is True},
                "evidence":["external-study:machine-structure:"
                            +("PASS_UNREVIEWED" if readiness.get("machine_structural_complete") else "MISSING"),
                            "external-study:independence-custody-actual-inference:UNVERIFIED"]}
    def external_gate(_node,state,_attempt):
        if state.get("scoped_verified") is not True:
            raise RuntimeError("SCOPED_SUCCESSOR_GATE_NOT_PASSED")
        return {"outcome":"requires_review" if state.get("external_structural_ready") is True else "missing",
                "evidence":["scientific-independence:NOT_PROVEN","original-five-arm:NOT_RUN"]}
    result=execute_graph(graph,{
        "verify_frozen_origin":origin_handler,
        "route_original_scope":scope_gate,
        "verify_scoped_successor":successor_handler,
        "check_blind_study":study_handler,
        "route_external_evidence":external_gate,
    })
    if result.get("result")!="TERMINAL" or result.get("terminal_status")!="BLOCKED":
        raise RuntimeError("UNEXPECTED_CLOSURE_OR_EXECUTION:"+str(result.get("result")))
    if result["terminal_id"] not in {
        "scoped_verified_external_missing","scoped_verified_external_review","blocked_integrity"}:
        raise RuntimeError("UNRECOGNIZED_TERMINAL")
    handoff=to_ecv4_evidence(graph,result)
    terminal=result["terminal_id"]
    return {
        "protocol":"ISSUE1_SINGLE_TURN_AUTONOMOUS_TCC_EXECUTOR_V1",
        "original_issue":1,
        "related_issues":[57,58],
        "source_commit":head,
        "tcc_compiler_pin":TCC_SOURCE,
        "tcc_recipe":"suite.tcc-generation-recipe.v4",
        "tcc_generated_spec_sha":graph["spec_hash"],
        "tcc_node_count":len(graph["nodes"]),
        "tcc_edge_count":len(graph["edges"]),
        "machine_steps_without_intermediate_user_prompts":True,
        "creates_automations":False,
        "starts_background_process":False,
        "actual_frozen_tcc_replay":observed.get("origin",{}).get("frozen_tcc_replay"),
        "scoped_successor":observed.get("successor"),
        "external_public_study_readiness":observed.get("study_readiness"),
        "next_execution_branch":"NEED_VERSIONED_COMPARABLE_EC_NATIVE_S1_S4_CONTRACT_AND_INDEPENDENT_REVIEW",
        "tcc_terminal_id":terminal,
        "tcc_status":result["terminal_status"],
        "ecv4_handoff":handoff,
        "original_five_arm_complete":False,
        "scientific_preservation_certified":False,
        "ecv4_closure_authorized":False,
        "reason":observed.get("error") if terminal=="blocked_integrity"
                 else "Original frozen EC S3/S4 interfaces incompatible; narrower successor audited. Independent external evidence cannot be self-generated or certified.",
        "stop_state":"FAIL_CLOSED_INTEGRITY" if terminal=="blocked_integrity"
                     else "SCOPED_SUCCESSOR_AUDITED_ORIGINAL_REQUIRES_NEW_VALID_STUDY",
    }


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--tcc-root",type=Path,required=True)
    p.add_argument("--study-dir",type=Path)
    p.add_argument("--source-commit")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        outcome=execute(a.tcc_root,study_dir=a.study_dir,expected_source=a.source_commit)
        rendered=json.dumps(outcome,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
        if a.out:
            a.out.parent.mkdir(parents=True,exist_ok=True)
            tmp=a.out.with_suffix(a.out.suffix+".tmp")
            if tmp.is_symlink():
                raise ValueError("TEMP_EVIDENCE_SYMLINK_NOT_ALLOWED")
            tmp.write_text(rendered,encoding="utf-8")
            os.replace(tmp,a.out)
            print(json.dumps({"protocol":outcome["protocol"],"stop_state":outcome["stop_state"],
                              "output_path":str(a.out),"tcc_terminal_id":outcome["tcc_terminal_id"],
                              "output_sha256":hashlib.sha256(rendered.encode()).hexdigest()},
                             ensure_ascii=False,sort_keys=True))
        else:
            print(rendered,end="")
        return 0 if outcome["stop_state"].startswith("SCOPED_SUCCESSOR_AUDITED") else 3
    except Exception as ex:
        print(json.dumps({"protocol":"ISSUE1_SINGLE_TURN_AUTONOMOUS_TCC_EXECUTOR_V1",
                          "stop_state":"FAIL_CLOSED","error":type(ex).__name__+":"+str(ex)[:350]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
