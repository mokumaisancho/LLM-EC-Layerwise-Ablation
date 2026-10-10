#!/usr/bin/env python3
"""Original Issue #1 deterministic AC+work dependency auditor.

Never treats a scoped test result, GitHub issue state, self-attested review,
or extra JSON keys as scientific acceptance. This module only constructs
a dependency-consistent evidence ledger for a bounded TCC invocation.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NORMATIVE=ROOT/"docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json"
PROTOCOL="ISSUE1_ROOT_AC_DEPENDENCY_PLANNER_V9"
REQUIRED=set(f"AC-{i:02d}" for i in (*range(1,10),*range(11,18),19,20))
ALL={f"AC-{i:02d}" for i in range(1,21)}

# Distinguish implemented local mechanics from qualified scientific capability.
# Work items may be satisfied only by registered evidence validators.
WORK={
 "ROOT_FROZEN_AC_SOURCE":{"deps":[],"ac":["AC-19","AC-20"],"validator":"original_v8"},
 "W4A_NATIVE_SET_CLOSURE":{"deps":["ROOT_FROZEN_AC_SOURCE"],"ac":["AC-03","AC-11"],"validator":"original_v8"},
 "W4B_TYPED_SOURCE_RULES":{"deps":["W4A_NATIVE_SET_CLOSURE"],"ac":["AC-03","AC-14"],"validator":"original_v8"},
 "W4C_PREVENT_FALSE_CLOSE":{"deps":["W4B_TYPED_SOURCE_RULES"],"ac":["AC-11","AC-12"],"validator":"original_v8"},
 "W4B_INDEPENDENT_SEMANTICS":{"deps":["W4B_TYPED_SOURCE_RULES"],"ac":["AC-03","AC-05","AC-17"],"validator":"independent_provenance"},
 "W4C_INDEPENDENT_COMPLETENESS":{"deps":["W4C_PREVENT_FALSE_CLOSE"],"ac":["AC-11","AC-12","AC-17"],"validator":"independent_provenance"},
 "W5_ORIGINAL_A_TO_E":{"deps":["W4B_INDEPENDENT_SEMANTICS","W4C_INDEPENDENT_COMPLETENESS"],"ac":["AC-05","AC-06","AC-16","AC-17"],"validator":"four_layer_actual"},
 "W6_ORIGINAL_ROOT_MVP":{"deps":["W5_ORIGINAL_A_TO_E"],"ac":sorted(REQUIRED),"validator":"all_18_strict"},
 "W7_EXTERNAL_CAPABILITY_RETENTION":{"deps":["W6_ORIGINAL_ROOT_MVP"],"ac":["AC-10","AC-18"],"validator":"external_llm0_gold_v4"},
}
LOCAL_DONE={"ROOT_FROZEN_AC_SOURCE","W4A_NATIVE_SET_CLOSURE",
            "W4B_TYPED_SOURCE_RULES","W4C_PREVENT_FALSE_CLOSE"}
INDEPENDENT={"W4B_INDEPENDENT_SEMANTICS","W4C_INDEPENDENT_COMPLETENESS"}
TERMINAL_BLOCKERS={
 "W4B_INDEPENDENT_SEMANTICS":"No independently source-authenticated natural-language candidate admissibility and reasons; typed input is not independent evidence.",
 "W4C_INDEPENDENT_COMPLETENESS":"No independently authenticated proof of the exhaustive required S4 obligation inventory and negative absence claims.",
 "W5_ORIGINAL_A_TO_E":"Genuine same-function original S1-S4 A/B/C/D/E source-measured experiments not performed.",
 "W6_ORIGINAL_ROOT_MVP":"Original 18/18 AC source-qualified and genuine four-layer one-variable Oracle attribution not satisfied.",
 "W7_EXTERNAL_CAPABILITY_RETENTION":"Independent unseen gold custody, original LLM0 identity and owner-authorized V4 not qualified.",
}

def sha(obj)->str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,
       separators=(",",":")).encode()).hexdigest()

def check_normative(norm:dict)->dict:
    if norm["protocol"]!="PHASE1_MVP_TCC_V1" or set(norm["mvp"]["required_ac"])!=REQUIRED or set(norm["mvp"]["post_mvp_ac"])!=ALL-REQUIRED:
        raise ValueError("FROZEN_ORIGINAL_MVP_AC20_CHANGED")
    if len(norm["mvp"]["required_ac"])!=18 or norm["frozen_thresholds"]["oracle_substitution_gain_material_abs"]!=0.2:
        raise ValueError("FROZEN_MATERIALITY_OR_AC_COUNT_CHANGED")
    dependencies=norm["ac_dependencies"]
    if set(dependencies)!=ALL:raise ValueError("G1_UNKNOWN_OR_MISSING_AC_ID")
    edges={}
    for ac,parents in dependencies.items():
        if len(set(parents))!=len(parents):raise ValueError("G1_DUPLICATE_AC_DEPENDENCY:"+ac)
        parsed=[]
        for p in parents:
            if p.startswith("AC-") and p!="AC-10_IF_NEEDED":
                if p not in ALL:raise ValueError("G1_UNKNOWN_AC_DEPENDENCY:"+p)
                parsed.append(p)
            elif p=="AC-10_IF_NEEDED":
                if ac!="AC-18":raise ValueError("G1_UNAUTHORIZED_OPTIONAL_EDGE")
            elif p.startswith("ISSUE-"):
                if p not in norm["issue_dependencies"]:raise ValueError("G1_UNKNOWN_ISSUE_DEPENDENCY:"+p)
            else:raise ValueError("G1_MALFORMED_PARENT")
        edges[ac]=parsed
    remaining=set(ALL);order=[]
    while remaining:
        ready=sorted(k for k in remaining if set(edges[k]).issubset(order))
        if not ready:raise ValueError("G1_AC_CYCLE")
        order.extend(ready);remaining-=set(ready)
    return {"ac20_order":order,"ac20_edges":edges}

def work_order()->list[str]:
    visited=set()
    for name,v in WORK.items():
        if not set(v["deps"]).issubset(visited):raise ValueError("G1_WORK_CYCLE_OR_UNKNOWN_PARENT:"+name)
        if not set(v["ac"]).issubset(ALL):raise ValueError("G1_UNKNOWN_WORK_AC")
        visited.add(name)
    return list(WORK)

def inspect_ac_proof(v8:dict,norm:dict)->dict:
    # Dynamic acceptance verdicts are never accepted based on a string in a
    # user-uploaded json. A registered original v8 validator is the only
    # local source of already qualified AC-19/AC-20.
    if v8.get("protocol")!="ISSUE1_ROOT_AC_W4B_W4C_TYPED_TCC_V8":
        raise ValueError("AC_PROOF_ORIGINAL_SOURCE_INVALID")
    if (v8.get("TCC_terminal_id")!="blocked_external_semantics" or
        v8.get("original_AC_MVP18_pass_count")!=2 or
        v8.get("original_AC_MVP18_total")!=18 or
        v8.get("original_root_completed") is not False):
        raise ValueError("G11_FALSE_SCIENTIFIC_AC_PASS")
    if v8.get("errors")!=[]:raise ValueError("G11_NESTED_VALIDATION_ERRORS")
    for k in ("evidence_pre_post_equal","native_source_pre_post_equal",
              "research_code_pre_post_equal","preregistered_contract_pre_post_equal"):
        if v8.get(k) is not True:raise ValueError("G0_SOURCE_SEAL_FAILED:"+k)
    typed=v8.get("new_actual_native_typed_public_evidence",{})
    if (typed.get("native_source_tests_passed")!=24 or
        typed.get("public_new_typed_cases")!=12 or
        typed.get("formal_invariant_cases_passed")!=12 or
        typed.get("S4_false_closure_preventions")!=12 or
        typed.get("true_natural_language_semantic_adjudication") is not False or
        typed.get("independently_verified_complete_obligation_inventory") is not False or
        typed.get("original_A_E_all_layers_measured") is not False):
        raise ValueError("G9_SCOPED_NATIVE_SEMANTIC_RESULT_OVERTURNED")
    if v8.get("independent_semantics_proven") is not False or v8.get("independent_complete_S4_inventory_proven") is not False:
        raise ValueError("G11_SELF_ATTESTED_INDEPENDENCE_RELABELED")
    dag=check_normative(norm)
    pass_ac={"AC-19","AC-20"}
    results={}
    for ac in dag["ac20_order"]:
        parents=dag["ac20_edges"][ac]
        passed=ac in pass_ac and all(results[parent]["status"]=="PASS" for parent in parents)
        if ac in pass_ac and not passed:raise ValueError("G2_AC_PASSED_WITH_UNMET_DEPENDENCY")
        results[ac]={
            "status":"PASS" if passed else "NOT_PROVEN",
            "proof":"original v8 re-execution source-sealed" if passed else "no registered scientific original-layer validator",
            "AC_dependencies":parents,
            "unmet_AC_dependencies":[p for p in parents if results[p]["status"]!="PASS"],
        }
    return {
        "original_mvp_required_ac":norm["mvp"]["required_ac"],
        "original_mvp_pass_count":sum(results[x]["status"]=="PASS" for x in REQUIRED),
        "original_mvp_unmet":[x for x in norm["mvp"]["required_ac"] if results[x]["status"]!="PASS"],
        "ac20":results,
        "original_mvp_complete":False
    }

def schedule(v8:dict, norm:dict, external_preflight:dict|None=None)->dict:
    ac=inspect_ac_proof(v8,norm)
    seen=work_order()
    statuses={}
    for k in seen:
        deps=WORK[k]["deps"]
        if k in LOCAL_DONE:
            # check all local verified dependencies were covered by the real
            # immutable TCC v8; local PASS does not imply AC scientific PASS.
            if any(statuses[dep]["state"]!="LOCAL_SCOPED_VERIFIED" for dep in deps):
                raise ValueError("G2_LOCAL_SCOPED_DEPENDENCY_INVALID")
            status="LOCAL_SCOPED_VERIFIED"
            reason="Source-bound typed formal evidence, not independent semantics"
        elif k in INDEPENDENT:
            status="EXTERNAL_EVIDENCE_UNQUALIFIED"
            reason=TERMINAL_BLOCKERS[k]
        else:
            status="BLOCKED_DEPENDENCY"
            reason=TERMINAL_BLOCKERS[k]
        statuses[k]={"state":status,"depends_on":deps,
                     "unmet_work_dependencies":[d for d in deps if statuses[d]["state"]!="LOCAL_SCOPED_VERIFIED"],
                     "required_AC":WORK[k]["ac"],"reason":reason}
    preflight=external_preflight or {
      "stage":"NOT_CHECKED","machine_structural_complete":False,
      "external_gold_independence_verified":False,
      "provenance_custody_verified":False,"genuine_inference_verified":False,
      "blockers":["EXTERNAL_STUDY_DIR_MISSING"]}
    # Gold-blind tool can establish readiness only, never a valid independent
    # original LLM0/V4 or final scientific acceptance even if all files exist.
    for forbidden in ("external_gold_independence_verified",
                      "provenance_custody_verified","genuine_inference_verified"):
        if preflight.get(forbidden) is not False:
            raise ValueError("G6_EXTERNAL_REVIEW_SELF_ASSERTED:"+forbidden)
    return {
      "protocol":PROTOCOL,"AC":ac,
      "MVP_definition":"18 original mandatory AC and genuine S1-S4 A/B/C/D/E source-pinned individual Oracle causal study",
      "W0_W7_dependency_state":statuses,
      "work_order":seen,
      "first_unmet_independence":["W4B_INDEPENDENT_SEMANTICS","W4C_INDEPENDENT_COMPLETENESS"],
      "external_study_preflight":preflight,
      "root_ac_complete":False,
      "original_phase1_AE_completed":False,
      "stop_classification":"IRREDUCIBLE_INDEPENDENT_SEMANTIC_AUTHORITY_AND_S4_COMPLETENESS_REQUIRED",
      "no_completion_from_scoped_semantic_evidence":True,
    }
