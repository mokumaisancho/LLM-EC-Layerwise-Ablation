#!/usr/bin/env python3
"""Issue #1 TCC v9: one invocation for all currently machine-executable AC tasks.

Re-evaluates original strict root via v8, then autonomously runs independent
metamorphic typed-source diagnostics, adversarial abstention and the #57
external gold-blind readiness gate, and computes exact W4B/W4C/W5/MVP
dependencies. No self-attested credentials or scoped success can close #1.

Not a background daemon or mechanism to self-reopen a ChatGPT conversation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.run_issue57_tcc_generator_gate import TCC_SOURCE,context_for,node
from tools.run_issue1_root_ac_orchestrator_v6 import git_head,git_blob,immutable_evidence_seal
from tools.run_issue1_root_ac_w4b_tcc_v8 import (
    run as nested_v8,public_case,child_predict,digest,sources_pin
)
from tools.issue1_ac_dependency_planner_v9 import schedule,check_normative,NORMATIVE
from tools.preflight_issue57_study_assets import inspect_study
from tools.verify_issue1_s4_bounded_safety_v1 import run as verify_bounded_s4
from tools.issue1_independent_proof_13ac_gate_v1 import inspect as inspect_proof_package
from tools.issue1_proof13_portable_preflight_v1 import run as run_portable_proof, sha256 as sha_file

PROTOCOL="ISSUE1_ROOT_AC_FIXED_POINT_TCC_V9"
DATA_COUNT=48
READ_ONLY_INPUTS=[
  "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json",
  "docs/ISSUE1_W4B_W4C_TYPED_EVIDENCE_CONTRACT_V1.json",
  "docs/ISSUE1_W4B_W4C_INDEPENDENT_PROOF_AC_V1.json",
]
CODE_SOURCES=[
  "tools/run_issue1_root_ac_continuation_tcc_v9.py",
  "tools/issue1_ac_dependency_planner_v9.py",
  "tools/run_issue1_root_ac_w4b_tcc_v8.py",
  "tools/preflight_issue57_study_assets.py",
  "tools/verify_issue1_s4_bounded_safety_v1.py",
  "tools/issue1_independent_proof_13ac_gate_v1.py",
  "tools/issue1_proof13_portable_preflight_v1.py",
]
def must(ok,why):
    if not ok:raise ValueError(why)

def tracked_code_seal():
    proofs={}
    for path in CODE_SOURCES:
        p=ROOT/path
        raw=p.read_bytes()
        git=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD:"+path],
                 text=True,capture_output=True,timeout=15)
        must(git.returncode==0 and not p.is_symlink() and
             git_blob(raw)==git.stdout.strip(),"G0_G7_UNCOMMITTED_SCIENCE_CODE:"+path)
        proofs[path]=git.stdout.strip()
    return proofs

def frozen_input_seal():
    proofs={}
    for path in READ_ONLY_INPUTS:
        p=ROOT/path
        git=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD:"+path],
                 text=True,capture_output=True,timeout=15)
        must(git.returncode==0 and not p.is_symlink() and
             git_blob(p.read_bytes())==git.stdout.strip(),"G7_FROZEN_CONTRACT_DRIFT:"+path)
        proofs[path]=git.stdout.strip()
    return proofs

def verify_dynamic_typed(native:Path,count=DATA_COUNT):
    """Separate verification cohort; none of the original historical gold is opened.

    This is known-rule, generated structured data, NOT unseen semantic gold.
    All 48 cases and strict invalid source controls are verified at runtime.
    """
    pinned=sources_pin(native)
    rows=[]
    with tempfile.TemporaryDirectory(prefix="issue1-tcc9-") as td:
        p=Path(td)/"public.json"
        for n in range(200,200+count):
            public=public_case(n)
            p.write_text(json.dumps(public,sort_keys=True),encoding="utf-8")
            tested=child_predict(native,p)
            facts=public["typed_document"]["facts"]
            label=[
                bool(facts[f"fact_{n}_a"]),
                not facts[f"fact_{n}_b"],
                bool(facts[f"fact_{n}_c"]) and not facts[f"fact_{n}_a"]
            ]
            ids=[x["candidate_id"] for x in public["public_s2"]["candidates"]]
            expected=[cid for cid,accepted in zip(ids,label) if accepted]
            must(tested["input_sha256"]==digest(public) and
                 tested["native_selected"]==expected,
                 "G5_TYPED_S3_UNKNOWN_CASE_PREDICTION_MISMATCH:"+str(n))
            must(tested["untrusted_completeness_rejected"] and
                 tested["natural_semantics_qualified"] is False and
                 tested["independent_inventory_qualified"] is False,
                 "G6_G11_FALSE_NATIVE_S4_CLOSURE_OR_CERTIFICATE:"+str(n))
            rows.append({
               "case_index":n,
               "public_SHA256":tested["input_sha256"],
               "selected":len(tested["native_selected"]),
               "S4_unverified_closure_refused":True,
               "is_independent_natural_language_eval":False
            })
        damaged=public_case(999)
        damaged["typed_document"]["source_sha256"]="0"*64
        p.write_text(json.dumps(damaged,sort_keys=True),encoding="utf-8")
        try:
            child_predict(native,p)
        except Exception as err:
            must("TYPED_DOCUMENT_SHA_MISMATCH" in str(err),
                 "G7_INVALID_SHA_NOT_PROPERLY_REJECTED")
        else:raise ValueError("G7_TAMPERED_DOCUMENT_WAS_ACCEPTED")
        missing=public_case(998)
        candidate=missing["public_s2"]["candidates"][0]["candidate_id"]
        missing["typed_document"]["candidate_requirements"][candidate]=["fact:unknown_external"]
        body={k:v for k,v in missing["typed_document"].items() if k!="source_sha256"}
        missing["typed_document"]["source_sha256"]=digest(body)
        p.write_text(json.dumps(missing,sort_keys=True),encoding="utf-8")
        try:
            child_predict(native,p)
        except Exception as err:
            must("FACT_NOT_PROVEN_ABSTAIN" in str(err),
                 "G5_UNKNOWN_FACT_NOT_REJECTED")
        else:raise ValueError("G5_UNKNOWN_FACT_UNSAFELY_GUESSED")
    must(len(rows)==count and len({r["case_index"] for r in rows})==count,
         "G10_NONUNIQUE_OR_MISSING_TEST_COVERAGE")
    return {
      "case_count":count,"all_formal_typed_cases_passed":count,
      "S4_false_closure_prevented":count,
      "source_SHA_pin_count":len(pinned),
      "tampered_document_rejected":True,"unknown_fact_abstention_verified":True,
      "independent_natural_language_science_not_established":True,
      "casewise":rows,
    }

def manifest():
    return {
      "schema":"tcc.spec.v3","tcc_id":"ISSUE1-ROOT-AC-ONECALL-FIXEDPOINT-V9",
      "goal":"Run all machine-executable tasks to a verified AC dependency fixed point, never terminal scoped success as root closure; require independent scientific authority for W5",
      "acceptance":[
          "Original 20 AC and 18 MVP AC and frozen materiality independent of narrower 4/17/48 case studies",
          "Execute real nested v8 root science and pinned old/new EC source studies in same invocation",
          "Verify 48 separately generated public typed cases and adversarial hidden unknown source/SHA",
          "Prove bounded 936-state native S4 safety, five-condition MC/DC witnesses and kill 5 real source mutations without promoting full C03",
          "Audit original 13 preregistered W4B/W4C proof ACs; credit C03 only bounded mechanical subproof and emit true evidence requirements",
          "Never silently self-certify independent semantic admissibility or S4 inventory",
          "Optionally check newly supplied external blind study if present; never assert independent proof from files alone",
          "Compute and traverse original AC20 and W0-W7 prerequisite DAG and strict 18/18 exit",
          "Protect research code, both normative contracts, real frozen model evidence, native source and casewise hashes before after tests",
      ],
      "state_keys":["norm","v8","additional","s4formal","external","ac","proof"],
      "immutable_state_keys":[],
      "entry_nodes":["verify_original_normative_AC"],
      "nodes":[
          node("verify_original_normative_AC","action",writes=("norm",),failure="blocked_integrity"),
          node("execute_original_all_machine_branches","action",depends=("verify_original_normative_AC",),
               writes=("v8",),failure="blocked_integrity"),
          node("run_typed_metamorphic_negative_controls","action",
               depends=("execute_original_all_machine_branches",),writes=("additional",),
               failure="blocked_integrity"),
          node("verify_bounded_native_S4_formal_properties","action",
               depends=("run_typed_metamorphic_negative_controls",),writes=("s4formal",),
               failure="blocked_integrity"),
          node("check_external_study_if_present","action",
               depends=("verify_bounded_native_S4_formal_properties",),writes=("external",),
               failure="blocked_integrity"),
          node("recompute_AC_and_W4_W5_prerequisites","action",
               depends=("check_external_study_if_present",),writes=("ac",),failure="blocked_integrity"),
          node("audit_13_independent_proof_ACs","action",
               depends=("recompute_AC_and_W4_W5_prerequisites",),
               writes=("proof",),failure="blocked_integrity"),
          node("true_original_scientific_exit","gate",
               depends=("audit_13_independent_proof_ACs",),
               reads=("norm","v8","additional","s4formal","external","ac","proof"),
               branches={"actual_root_18AC_complete":"root_science_verified",
                         "independent_semantics_or_S4_missing":"blocked_external_science",
                         "original_full_AE_missing":"blocked_AE"}),
          node("root_science_verified","terminal",terminal="SUCCESS"),
          node("blocked_external_science","terminal",terminal="BLOCKED"),
          node("blocked_AE","terminal",terminal="BLOCKED"),
          node("blocked_integrity","terminal",terminal="BLOCKED"),
      ],
    }

def execute(tcc_root:Path,original_ec_root:Path,w4a_root:Path,w4b_root:Path,
            external_study:Path|None=None,
            proof_bundle_root:Path|None=None,
            proof_submission:Path|None=None)->dict:
    must(git_head(tcc_root)==TCC_SOURCE,"G0_TCC_GENERATOR_SOURCE_CHANGED")
    must(proof_submission is None or proof_bundle_root is not None,
         "P02_PROOF_SUBMISSION_WITHOUT_BUNDLE_ROOT")
    if str(tcc_root) not in sys.path:sys.path.insert(0,str(tcc_root))
    from tcc.core_v3 import validate_spec,normalize_spec,compile_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph,to_ecv4_evidence
    repo_commit=git_head(ROOT)
    contract=manifest()
    ctx=context_for(contract,repo_commit)
    ctx.update(selected_issue_id="ISSUE-1",actionable_issue_ids=["ISSUE-1"],
               blocked_issue_ids=[],snapshot_id="ISSUE1-TCC9:"+repo_commit[:12],
               source_fingerprint="sha256:"+digest({"commit":repo_commit,"manifest":contract}))
    built=generate_tcc_from_context(ctx)
    must(built.get("result")=="tcc.spec.v3" and
         not validate_spec(built["spec"]) and
         built["spec"]==normalize_spec(contract),"G1_TCC_GENERATED_SPEC_DRIFT")
    graph=compile_spec(built["spec"])
    before={
       "raw":immutable_evidence_seal(),
       "code":tracked_code_seal(),
       "norm":frozen_input_seal(),
       "native":sources_pin(w4b_root),
    }
    observations={"errors":[]}
    norm=json.loads(NORMATIVE.read_text())
    def check_seals():
        must(before["raw"]==immutable_evidence_seal(),"G4_RESULT_OVERTURNING_RAW_DRIFT")
        must(before["code"]==tracked_code_seal(),"G0_SCIENTIFIC_CODE_CHANGED_AFTER_TRIAL")
        must(before["norm"]==frozen_input_seal(),"G7_ORIGINAL_AC_THRESHOLD_CHANGED")
        must(before["native"]==sources_pin(w4b_root),"G0_NATIVE_SOURCE_CHANGED_AFTER_TRIAL")
    def v_normal(_n,_s,_a):
        try:
            ac=check_normative(norm)
            must(len(ac["ac20_order"])==20,"G1_AC_DAG_COVERAGE")
            observations["AC_source"]={"topological_AC20":ac["ac20_order"],
                                      "original_required":norm["mvp"]["required_ac"]}
        except Exception as exc:
            observations["errors"].append("NORM:"+str(exc)[:180])
            return {"status":"failure","evidence":["AC20_MVP18_NOT_VALID"]}
        return {"status":"success","writes":{"norm":True},
                "evidence":["ORIGINAL_AC20_MVP18_DEPENDENCIES_VALID"]}

    def run_old(_n,_s,_a):
        try:
            x=nested_v8(tcc_root,original_ec_root,w4a_root,w4b_root)
            must(x["TCC_terminal_id"]=="blocked_external_semantics" and
                 x["original_root_completed"] is False and
                 x["original_AC_MVP18_pass_count"]==2 and x["errors"]==[] and
                 x["evidence_pre_post_equal"] and x["native_source_pre_post_equal"] and
                 x["research_code_pre_post_equal"] and
                 x["preregistered_contract_pre_post_equal"],
                 "G11_ROOT_V8_AC_EVIDENCE_NOT_QUALIFIED")
            observations["v8"]=x
            check_seals()
        except Exception as exc:
            observations["errors"].append("V8:"+str(exc)[:180])
            return {"status":"failure","evidence":["NESTED_V8_MODEL_RAW_OR_SOURCE_DRIFT"]}
        return {"status":"success","writes":{"v8":True},
                "evidence":["REAL_NESTED_V8_ALL_MACHINE_BRANCHES_VERIFIED"]}

    def extra(_n,_s,_a):
        try:
            x=verify_dynamic_typed(w4b_root)
            observations["metamorphic"]=x
            check_seals()
        except Exception as exc:
            observations["errors"].append("DYNAMIC:"+str(exc)[:180])
            return {"status":"failure","evidence":["ADVERSARIAL_TYPED_SOURCE_OR_S4_GATE_FAILED"]}
        return {"status":"success","writes":{"additional":True},
                "evidence":["48_NONEXPOSED_STRUCTURED_METAMORPHIC_PASS",
                            "48_S4_UNVERIFIED_CLOSURES_DENIED",
                            "UNKNOWN_FACT_AND_DOCUMENT_HASH_FAIL_CLOSED"]}

    def s4formal(_n,_s,_a):
        try:
            result=verify_bounded_s4(w4b_root)
            bound=result["bounded_state_space"]
            mcdc=result["MC_DC_BOUNDED"]
            mutants=result["actual_native_source_mutation"]
            must(bound["states_checked"]==936 and
                 bound["reference_decision_exact_matches"]==936 and
                 bound["unattested_states_refused"]==468 and
                 bound["unsafe_close_within_typed_bounded_reference"]==0 and
                 mcdc["pair_count"]==5 and
                 mutants["killed"]==mutants["total"]==5 and
                 result["original_AC_C03_qualified"] is False and
                 result["independent_obligation_inventory_certified"] is False,
                 "C03_BOUNDED_FORMAL_PROOF_CANNOT_SUBSTITUTE_EXTERNAL_INVENTORY")
            observations["s4formal"]=result
            check_seals()
        except Exception as exc:
            observations["errors"].append("S4_FORMAL:"+str(exc)[:180])
            return {"status":"failure","evidence":["C03_BOUNDED_S4_COUNTEREXAMPLE_OR_PROVENANCE_FAIL"]}
        return {"status":"success","writes":{"s4formal":True},
                "evidence":["C03_936_BOUNDED_TYPED_STATES_PASS",
                            "C03_5_CONDITION_PAIRS_AND_5_MUTANTS_PASS",
                            "EXTERNAL_S4_INVENTORY_STILL_NOT_CERTIFIED"]}

    def study(_n,_s,_a):
        try:
            x=inspect_study(external_study)
            # Do not interpret a corpus/commitment or structural review as
            # independent judged gold or authenticated original model/V4.
            must(x["external_gold_independence_verified"] is False and
                 x["provenance_custody_verified"] is False and
                 x["genuine_inference_verified"] is False,
                 "G6_INDEPENDENT_PROVENANCE_FABRICATED")
            observations["external"]=x
            check_seals()
        except Exception as exc:
            observations["errors"].append("EXTERNAL:"+str(exc)[:180])
            return {"status":"failure","evidence":["EXTERNAL_STUDY_INTEGRITY_FAILURE"]}
        return {"status":"success","writes":{"external":True},
                "evidence":["GOLD_BLIND_EXTERNAL_PROVENANCE_PREFLIGHT_NOT_CERTIFIED"]}

    def audit(_n,_s,_a):
        try:
            must(observations["s4formal"]["original_AC_C03_qualified"] is False,
                 "G11_FALSE_C03_PROOF_PROMOTION")
            decision=schedule(observations["v8"],norm,observations["external"])
            must(decision["AC"]["original_mvp_pass_count"]==2 and
                 not decision["root_ac_complete"] and
                 decision["first_unmet_independence"]==[
                    "W4B_INDEPENDENT_SEMANTICS","W4C_INDEPENDENT_COMPLETENESS"],
                 "G11_FALSE_ROOT_AC_PROMOTION")
            observations["planner"]=decision
            check_seals()
        except Exception as exc:
            observations["errors"].append("AC:"+str(exc)[:180])
            return {"status":"failure","evidence":["ORIGINAL_18AC_DEPENDENCY_OR_SCORE_INVALID"]}
        return {"status":"success","writes":{"ac":True},
                "evidence":["ORIGINAL_18AC_PASS2_UNMET16_NO_SCOPED_UPGRADE",
                            "NEXT_CRITICAL_PATH_W4B_W4C_THEN_W5_ALL_AE"]}

    def audit_proof(_n,_s,_a):
        try:
            ledger=inspect_proof_package(observations["s4formal"])
            must(ledger["proof_AC_total"]==13 and
                 ledger["proof_package_mvp_required"]==11 and
                 ledger["proof_package_mvp_pass"]==0 and
                 ledger["status_by_AC"]["C03"]["state"]=="PARTIAL_BOUNDED_MECHANICS_ONLY" and
                 ledger["original_MVP_completed"] is False,
                 "G11_FALSE_INDEPENDENT_PROOF_AC_ACCEPTANCE")
            observations["proof_ledger"]=ledger
            # This portable stage runs with no Mac-specific runtime. A provided
            # external bundle is validated structurally, never certified as
            # independent third-party gold merely because its hashes match.
            prior_sha = sha_file(proof_submission) if proof_submission else None
            evidence = run_portable_proof(
                ROOT/"docs/ISSUE1_W4B_W4C_INDEPENDENT_PROOF_AC_V1.json",
                proof_bundle_root or ROOT, proof_submission)
            must(evidence["original_root_complete"] is False and
                 evidence["independent_proof_AC_pass"]==0 and
                 evidence["original_MVP_required"]==18 and
                 evidence["proof13_total"]==13,
                 "G11_PORTABLE_EVIDENCE_SELF_CERTIFICATION_FORBIDDEN")
            if proof_submission:
                must(sha_file(proof_submission)==prior_sha,
                     "G06_PROOF_SUBMISSION_CHANGED_DURING_VALIDATION")
            observations["proof_evidence_structural_gate"]=evidence
            check_seals()
        except Exception as exc:
            observations["errors"].append("PROOF13:"+str(exc)[:180])
            return {"status":"failure","evidence":["INDEPENDENT_GOLD_OR_PROOF13_SOURCE_NOT_QUALIFIED"]}
        return {"status":"success","writes":{"proof":True},
                "evidence":["PROOF_AC13_DAG_VALID_0OF11_INDEPENDENT_GATE_PASS",
                            "C03_PARTIAL_BOUNDED_MECHANICS_ONLY",
                            "ORIGINAL_AC18_STILL_2OF18"]}

    def final(_n,state,_attempt):
        if not all(state.get(x) is True for x in ("norm","v8","additional","s4formal","external","ac","proof")):
            return {"outcome":"original_full_AE_missing","evidence":["AC_DEPENDENCY_STATE_INCOMPLETE"]}
        plan=observations["planner"]
        if plan["AC"]["original_mvp_pass_count"]==18 and plan["original_phase1_AE_completed"]:
            return {"outcome":"actual_root_18AC_complete","evidence":["ROOT_FOUR_LAYER_AC_ALL_PASS"]}
        return {"outcome":"independent_semantics_or_S4_missing",
                "evidence":["W4B_W4C_SOURCE_AUTHORITY_REQUIRED_BEFORE_W5"]}

    runtime=execute_graph(graph,{
       "verify_original_normative_AC":v_normal,
       "execute_original_all_machine_branches":run_old,
       "run_typed_metamorphic_negative_controls":extra,
       "verify_bounded_native_S4_formal_properties":s4formal,
       "check_external_study_if_present":study,
       "recompute_AC_and_W4_W5_prerequisites":audit,
       "audit_13_independent_proof_ACs":audit_proof,
       "true_original_scientific_exit":final,
    })
    must(runtime.get("result")=="TERMINAL" and runtime["terminal_id"] in
         ("root_science_verified","blocked_external_science","blocked_AE","blocked_integrity"),
         "TCC9_INVALID_RUNTIME_TERMINAL")
    must(runtime["terminal_id"]!="root_science_verified","G11_FALSE_ORIGINAL_ROOT_EXIT")
    return {
       "protocol":PROTOCOL,"research_commit":repo_commit,"TCC_nodes":len(graph["nodes"]),
       "TCC_edges":len(graph["edges"]),"TCC_compiler":TCC_SOURCE,
       "TCC_terminal_id":runtime["terminal_id"],"ECv4_handoff":to_ecv4_evidence(graph,runtime),
       "original_required_AC":18,
       "original_AC_pass_count":observations.get("planner",{}).get("AC",{}).get("original_mvp_pass_count"),
       "dependency_ordered_AC_and_work":observations.get("planner"),
       "actual_metamorphic_typed_evidence":observations.get("metamorphic"),
       "C03_bounded_native_S4_formal_proof":observations.get("s4formal"),
       "W4B_W4C_independent_13AC_proof_ledger":observations.get("proof_ledger"),
       "W4B_W4C_portable_evidence_structural_preflight":observations.get("proof_evidence_structural_gate"),
       "external_blind_study_preflight":observations.get("external"),
       "all_seals_same":all([
          before["raw"]==immutable_evidence_seal(),
          before["code"]==tracked_code_seal(),
          before["norm"]==frozen_input_seal(),
          before["native"]==sources_pin(w4b_root)
       ]),
       "errors":observations["errors"],
       "original_issue_completed":False,
       "new_scheduled_tasks":False,
       "terminal":"ALL_MACHINE_BRANCHES_VERIFIED_EXTERNAL_INDEPENDENT_S3_S4_AND_FULL_AE_REQUIRED"
         if runtime["terminal_id"]=="blocked_external_science" else "INTEGRITY_OR_UNRUN_ORIGINAL_AE",
    }

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--tcc-root",required=True,type=Path)
    a.add_argument("--ec-root",required=True,type=Path)
    a.add_argument("--v7-native-root",required=True,type=Path)
    a.add_argument("--new-native-root",required=True,type=Path)
    a.add_argument("--external-study-dir",type=Path)
    a.add_argument("--proof-bundle-root",type=Path)
    a.add_argument("--proof-submission",type=Path)
    a.add_argument("--out",type=Path)
    v=a.parse_args()
    try:
        r=execute(v.tcc_root,v.ec_root,v.v7_native_root,v.new_native_root,
                  v.external_study_dir,v.proof_bundle_root,v.proof_submission)
        txt=json.dumps(r,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
        if v.out:
            must(not v.out.is_symlink(),"OUTPUT_SYMLINK_FORBIDDEN")
            v.out.write_text(txt,encoding="utf-8")
            print(json.dumps({"terminal":r["terminal"],"ac_pass":r["original_AC_pass_count"],
                              "additional_cases":(r.get("actual_metamorphic_typed_evidence") or {}).get("case_count"),
                              "tcc_nodes":r["TCC_nodes"],"tcc_edges":r["TCC_edges"]}))
        else:print(txt,end="")
        return 0 if r["original_issue_completed"] else (3 if r["errors"] else 2)
    except Exception as exc:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"INTEGRITY_FAIL_CLOSED",
                          "error":type(exc).__name__+":"+str(exc)[:250]}))
        return 3
if __name__=="__main__":
    raise SystemExit(main())
