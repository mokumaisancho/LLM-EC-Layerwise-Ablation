#!/usr/bin/env python3
"""Issue #1 real compiler-driven TCC v10: only ORIGINAL Phase1 S1-S4 18 AC.

Runs all machine-feasible gates in one call. Does not convert auxiliary
13-AC / 120-document optional research into an original MVP prerequisite.
The immutable original ECv4.4 is factually non-isomorphic for S3/S4; only a
versioned, separately qualified successor can ever unlock original A-E.
"""
from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.audit_issue1_original_phase1_scope_v1 import run as original_scope
from tools.issue1_phase1_ae_gate_v1 import run as audit_AE
from tools.run_issue57_tcc_generator_gate import TCC_SOURCE,context_for,node
from tools.run_issue1_root_ac_orchestrator_v6 import git_head,git_blob
from tools.run_issue1_root_ac_w4b_tcc_v8 import sources_pin as experimental_pin

PROTOCOL="ISSUE1_ORIGINAL_PHASE1_TCC_V10"
AC18=[f"AC-{i:02d}" for i in (*range(1,10),*range(11,18),19,20)]
SOURCE_FILES=[
  "ACCEPTANCE_CRITERIA.md",
  "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json",
  "results/ec_native_adapter_qualification.json",
  "results/phase1_s4_identifiability_audit_2026-10-03.json",
  "tools/audit_issue1_original_phase1_scope_v1.py",
  "tools/issue1_phase1_ae_gate_v1.py",
  "tools/run_issue1_original_phase1_tcc_v10.py",
]

def must(ok,message):
    if not ok:raise ValueError(message)

def code_seals():
    result={}
    for name in SOURCE_FILES:
        p=ROOT/name
        sha=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD:"+name],
            capture_output=True,text=True,timeout=15)
        must(p.is_file() and not p.is_symlink() and sha.returncode==0 and
             sha.stdout.strip()==git_blob(p.read_bytes()),"G0_UNTRACKED_OR_CHANGED_SOURCE:"+name)
        result[name]=sha.stdout.strip()
    return result

def immutable_input_seals(paths):
    out={}
    for path in paths:
        must(path.is_file() and not path.is_symlink(),"G4_INPUT_MISSING_OR_SYMLINK")
        out[str(path.resolve())]=hashlib.sha256(path.read_bytes()).hexdigest()
    return out

def manifest():
    return {
      "schema":"tcc.spec.v3","tcc_id":"ISSUE1-ORIGINAL-S1-S4-AC18-V10",
      "goal":"Run original Phase1 AC dependency/source, native qualification, optional A-E raw replay and fixed 0.20 localization; never self-upgrade optional proof13 into the root.",
      "acceptance":[
        "Pinned original 20 AC and mandatory 18 AC unchanged, post-MVP AC10/AC18 optional",
        "Frozen native ECv4.4 mismatches S3 admissible set and S4 closure: preserve negative witness 8/10, not EC accuracy",
        "A/B/C/D and four independent Oracle interventions require actual matched source, not typed author fixture",
        "Source, model input, gold, native source and TCC code seals before/after",
        "Fail closed on false native authority, input mismatch, leaked Oracle, wrong or duplicate case, result-overturning failures",
        "Only actual qualified original A-E + all 18 AC may close; optional 13 proof AC are not a Phase1 requirement",
      ],
      "state_keys":["sources","ac","native","successor","ae","score"],
      "immutable_state_keys":[],
      "entry_nodes":["freeze_original_source"],
      "nodes":[
        node("freeze_original_source","action",writes=("sources",),failure="blocked_integrity"),
        node("verify_original_AC20_MVP18","action",
             depends=("freeze_original_source",),writes=("ac",),failure="blocked_integrity"),
        node("probe_original_native_S3_S4","action",
             depends=("verify_original_AC20_MVP18",),writes=("native",),failure="blocked_integrity"),
        node("check_versioned_native_successor","action",
             depends=("probe_original_native_S3_S4",),writes=("successor",),failure="blocked_integrity"),
        node("replay_matched_AE_evidence_if_supplied","action",
             depends=("check_versioned_native_successor",),writes=("ae",),failure="blocked_integrity"),
        node("evaluate_original_layer_gains_and_AC_exit","action",
             depends=("replay_matched_AE_evidence_if_supplied",),writes=("score",),failure="blocked_integrity"),
        node("strict_original_phase1_exit","gate",
             depends=("evaluate_original_layer_gains_and_AC_exit",),
             reads=("sources","ac","native","successor","ae","score"),
             branches={"real_original_18_AC_PASS":"root_science_verified",
                       "native_source_incompatible":"blocked_native",
                       "whole_AE_unmeasured":"blocked_AE"}),
        node("root_science_verified","terminal",terminal="SUCCESS"),
        node("blocked_native","terminal",terminal="BLOCKED"),
        node("blocked_AE","terminal",terminal="BLOCKED"),
        node("blocked_integrity","terminal",terminal="BLOCKED"),
      ],
    }

def run(tcc_root:Path, native_successor:Path|None=None,
        arms:Path|None=None,gold:Path|None=None):
    must(git_head(tcc_root)==TCC_SOURCE,"G0_TCC_COMPILER_CHANGED")
    must((arms is None)==(gold is None),"G6_HALF_PROVIDED_AE_EVIDENCE")
    if str(tcc_root) not in sys.path:sys.path.insert(0,str(tcc_root))
    from tcc.core_v3 import validate_spec,normalize_spec,compile_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph,to_ecv4_evidence
    local_commit=git_head(ROOT)
    spec=manifest()
    ctx=context_for(spec,local_commit)
    ctx.update(selected_issue_id="ISSUE-1",actionable_issue_ids=["ISSUE-1"],
               blocked_issue_ids=[],snapshot_id="ISSUE1-V10:"+local_commit[:12],
               source_fingerprint="sha256:"+hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest())
    generated=generate_tcc_from_context(ctx)
    must(generated.get("result")=="tcc.spec.v3" and
         not validate_spec(generated["spec"]) and
         generated["spec"]==normalize_spec(spec),"G1_COMPILER_REWROTE_TCC")
    graph=compile_spec(generated["spec"])
    pre=code_seals()
    inputs=immutable_input_seals([p for p in (arms,gold) if p is not None])
    record={"errors":[],"work":{}}
    def seal():
        must(code_seals()==pre,"G7_SOURCE_CHANGED_DURING_EXPERIMENT")
        must(immutable_input_seals([p for p in (arms,gold) if p is not None])==inputs,
             "G7_RAW_OR_GOLD_CHANGED_DURING_EXPERIMENT")
        if native_successor is not None and "successor_source_git_blobs" in record:
            must(experimental_pin(native_successor)==record["successor_source_git_blobs"],
                 "G3_G7_NATIVE_SUCCESSOR_SOURCE_CHANGED_DURING_EXPERIMENT")
    def done(k):
        return {"status":"success","writes":{k:True},"evidence":[k.upper()+"_SOURCE_BOUND"]}
    def source(_n,_s,_a):
        try:
            record["original"]=original_scope(ROOT)
            seal()
            record["work"]["source"]="VERIFIED"
            return done("sources")
        except Exception as ex:
            record["errors"].append("SOURCE:"+str(ex)[:180])
            return {"status":"failure","evidence":["G0_ORIGINAL_SOURCE_INVALID"]}
    def ac(_n,_s,_a):
        try:
            x=record["original"]
            must(x["original_mvp_AC_total"]==18 and x["original_mvp_AC_pass"]==2 and
                 x["original_mvp_complete"] is False and
                 len(x["original_AC20_status"])==20,"G11_FALSE_ORIGINAL_AC_PROMOTION")
            record["work"]["ac"]="2_OF_18_CURRENTLY_PROVEN"
            seal()
            return done("ac")
        except Exception as ex:
            record["errors"].append("AC:"+str(ex)[:180])
            return {"status":"failure","evidence":["G11_ORIGINAL_AC_INVALID"]}
    def old_native(_n,_s,_a):
        try:
            x=record["original"]
            must(x["original_pinned_EC_compatible"] is False and
                 x["S4_signature_ceiling"]["correct"]==8 and
                 x["S4_signature_ceiling"]["total"]==10,
                 "G3_FALSE_ORIGINAL_NATIVE_INTERFACE_PASS")
            record["work"]["old_native"]="SOURCE_QUALIFIED_INCOMPATIBLE"
            seal()
            return done("native")
        except Exception as ex:
            record["errors"].append("NATIVE:"+str(ex)[:180])
            return {"status":"failure","evidence":["G3_NATIVE_SOURCE_RELABELED"]}
    def successor(_n,_s,_a):
        try:
            if native_successor is not None:
                result=experimental_pin(native_successor)
                record["successor_source_git_blobs"]=result
                record["work"]["successor"]="EXPERIMENTAL_TYPED_SOURCE_NOT_INDEPENDENT_SEMANTICS"
            else:
                record["work"]["successor"]="NO_VERSIONED_SOURCE_SUPPLIED"
            # Neither a pinned source nor 936 typed-state tests prove that
            # unrestricted semantic admissibility and S4 obligations are right.
            record["scientifically_qualified_native_successor"]=False
            seal()
            return done("successor")
        except Exception as ex:
            record["errors"].append("SUCCESSOR:"+str(ex)[:180])
            return {"status":"failure","evidence":["G3_EXPERIMENTAL_NATIVE_SOURCE_UNPINNED"]}
    def ae(_n,_s,_a):
        try:
            if arms is None:
                record["work"]["ae"]="RAW_AE_NOT_PROVIDED"
            else:
                record["raw_recomputed"]=audit_AE(arms,gold)
                must(record["raw_recomputed"]["original_AC18_pass_automatically"] is False,
                     "G11_FALSE_AE_CAUSAL_QUALIFICATION")
                record["work"]["ae"]="STRUCTURAL_RAW_RECOMPUTED_CAUSAL_PROVENANCE_NOT_VERIFIED"
            seal()
            return done("ae")
        except Exception as ex:
            record["errors"].append("AE:"+str(ex)[:180])
            return {"status":"failure","evidence":["G4_G5_G6_G7_G10_AE_RAW_INVALID"]}
    def score(_n,_s,_a):
        try:
            # A/E per-layer Oracle gains may be shown when genuine raw exists;
            # no data-manifest can bypass the live native-functional mismatch.
            record["work"]["score"]="FROZEN_MATERIALITY_0P20_ORIGINAL_ROOT_OPEN"
            must(record["original"]["original_mvp_AC_pass"]==2 and
                 record["scientifically_qualified_native_successor"] is False,
                 "G11_FALSE_ROOT_AC_AUTHORITY")
            seal()
            return done("score")
        except Exception as ex:
            record["errors"].append("SCORE:"+str(ex)[:180])
            return {"status":"failure","evidence":["G11_ORIGINAL_EXIT_UNQUALIFIED"]}
    def decide(_n,state,_a):
        if not all(state.get(key) is True for key in
                   ("sources","ac","native","successor","ae","score")):
            return {"outcome":"whole_AE_unmeasured","evidence":["DEPENDENCY_NOT_PROVEN"]}
        return {"outcome":"native_source_incompatible",
                "evidence":["PINNED_ECV44_S3_SINGLETON_S4_INFORMATION_DEFICIT",
                            "NO_EXPERIMENTAL_TYPED_SOURCE_UPGRADE_TO_ORIGINAL_AC"]}
    graph_output=execute_graph(graph,{
        "freeze_original_source":source,
        "verify_original_AC20_MVP18":ac,
        "probe_original_native_S3_S4":old_native,
        "check_versioned_native_successor":successor,
        "replay_matched_AE_evidence_if_supplied":ae,
        "evaluate_original_layer_gains_and_AC_exit":score,
        "strict_original_phase1_exit":decide,
    })
    must(graph_output.get("result")=="TERMINAL" and
         graph_output["terminal_id"] in
         ("root_science_verified","blocked_native","blocked_AE","blocked_integrity"),
         "G1_TCC_TERMINAL_UNKNOWN")
    must(graph_output["terminal_id"]!="root_science_verified","G11_FALSE_ROOT_18_AC_COMPLETION")
    return {
       "protocol":PROTOCOL,"TCC_compiler":TCC_SOURCE,"TCC_nodes":len(graph["nodes"]),
       "TCC_edges":len(graph["edges"]),"TCC_terminal":graph_output["terminal_id"],
       "ECv4_handoff":to_ecv4_evidence(graph,graph_output),
       "original_root_pass":2,"original_root_required":18,
       "original_source_git_blobs":pre,"work_state":record["work"],
       "original_native_witness":record.get("original",{}).get("S4_signature_ceiling"),
       "successor_source_git_blobs":record.get("successor_source_git_blobs"),
       "raw_AE_structural_replay":record.get("raw_recomputed"),
       "scientifically_qualified_native_successor":record.get("scientifically_qualified_native_successor",False),
       "no_13_AC_or_120_documents_as_original_MVP_gates":True,
       "source_and_input_seals_stable":pre==code_seals() and
            inputs==immutable_input_seals([p for p in (arms,gold) if p is not None]),
       "errors":record["errors"],"original_science_complete":False,
       "terminal":"SOURCE_PROVEN_ORIGINAL_NATIVE_INCOMPATIBLE_VERSIONED_S3_S4_REQUIRED"
           if graph_output["terminal_id"]=="blocked_native" else "EVIDENCE_OR_INTEGRITY_BLOCKED",
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--tcc-root",type=Path,required=True)
    parser.add_argument("--native-successor",type=Path)
    parser.add_argument("--arms",type=Path)
    parser.add_argument("--gold",type=Path)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    try:
        result=run(args.tcc_root,args.native_successor,args.arms,args.gold)
        data=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
        if args.out:
            must(not args.out.is_symlink(),"OUTPUT_SYMLINK")
            args.out.write_text(data,encoding="utf-8")
            print(json.dumps({"TCC":result["TCC_terminal"],
                              "original_AC":str(result["original_root_pass"])+"/18",
                              "nodes":result["TCC_nodes"],"edges":result["TCC_edges"]}))
        else:print(data,end="")
        return 2 if not result["errors"] else 3
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"INTEGRITY_FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:250]}))
        return 3
if __name__=="__main__":
    raise SystemExit(main())
