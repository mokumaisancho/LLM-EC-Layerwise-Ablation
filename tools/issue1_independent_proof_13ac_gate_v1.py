#!/usr/bin/env python3
"""Independent W4B/W4C proof-package 13 AC evidence ledger.

One immutable scientific plan, actual pinned *partial* C03 mechanical proof.
This tool never authenticates external humans/gold or certifies original root.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"docs/ISSUE1_W4B_W4C_INDEPENDENT_PROOF_AC_V1.json"
PLAN_BLOB="c3a27b518ba42cc8bf41c91bacaf78baf5efcaef"
PROTOCOL="ISSUE1_W4B_W4C_PROOF_13AC_GATE_V1"
EXPECTED=("P01","P02","B01","B02","B03","B04","C01","C02",
          "C03","C04","C05","X01","X02")

def blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def require(ok:bool,label:str)->None:
    if not ok:raise ValueError(label)

def verify_plan(root:Path=ROOT)->dict:
    p=root/"docs/ISSUE1_W4B_W4C_INDEPENDENT_PROOF_AC_V1.json"
    require(p.is_file() and not p.is_symlink() and blob(p.read_bytes())==PLAN_BLOB,
            "P01_FROZEN_PROOF_CONTRACT_HASH_MISMATCH")
    doc=json.loads(p.read_text(encoding="utf-8"))
    require(doc["schema"]=="issue1-independent-proof.ac.v1" and
            doc["status"]=="SPECIFICATION_ONLY_NOT_EXECUTED" and
            doc["original_root_status_on_creation"]=="OPEN" and
            doc["independent_evidence_obtained_on_creation"] is False and
            doc["normative_contract"]["original_required_AC"]==18 and
            doc["normative_contract"]["original_total_AC"]==20 and
            doc["normative_contract"]["original_materiality_abs"]==.20 and
            doc["proof_package_mvp"]["AC_count"]==11,
            "P01_ORIGINAL_ACCEPTANCE_SCOPE_OR_EVIDENCE_STATUS_DRIFT")
    ac=doc["acceptance_criteria"]
    require([x["id"] for x in ac]==list(EXPECTED),"P01_AC_COUNT_OR_TOPOLOGICAL_ORDER_CHANGED")
    available=set()
    normative={f"AC-{i:02d}" for i in range(1,21)}
    for item in ac:
        require(set(item)=={"id","title","parent","depends","owner","evidence","pass","fail"},
                "P01_PROOF_AC_SCHEMA_CHANGED:"+item["id"])
        require(bool(item["evidence"]) and bool(item["pass"]) and bool(item["fail"]) and
                bool(item["owner"]) and set(item["parent"]).issubset(normative),
                "P01_INCOMPLETE_PROOF_ACCEPTANCE:"+item["id"])
        require(set(item["depends"]).issubset(available) and
                len(item["depends"])==len(set(item["depends"])),
                "P01_PROOF_DAG_CYCLE_OR_UNKNOWN:"+item["id"])
        available.add(item["id"])
    return doc

def score_frozen_c03(c03:dict)->dict:
    require(c03.get("protocol")=="ISSUE1_C03_BOUNDED_S4_MODEL_CHECK_V1" and
            c03.get("ec_native_source_commit")=="ae4b02bca34147d549abda85fad9cdc793ca054f" and
            c03.get("ec_native_source_git_blob")=="c12e4743c89221a9b81a2f2fa98c4df9d61d72b2",
            "C03_WRONG_NATIVE_S4_SOURCE")
    states=c03["bounded_state_space"]
    mcdc=c03["MC_DC_BOUNDED"]
    mutations=c03["actual_native_source_mutation"]
    require(states["states_checked"]==states["reference_decision_exact_matches"]==936 and
            states["unattested_states_refused"]==468 and
            states["unsafe_close_within_typed_bounded_reference"]==0 and
            mcdc["pair_count"]==5 and
            len(mcdc["independent_pairs"])==5 and
            mutations["killed"]==mutations["total"]==5 and
            all(v["killed"] is True for v in mutations["mutants"].values()),
            "C03_BOUNDED_MECHANICAL_GATES_FAILED")
    require(c03["original_AC_C03_qualified"] is False and
            c03["independent_obligation_inventory_certified"] is False and
            c03["independent_natural_language_semantics_certified"] is False,
            "C03_FALSE_INDEPENDENCE_OR_ROOT_AC_PROMOTION")
    return {
       "status":"BOUNDED_MECHANICS_VERIFIED_NOT_FULL_C03",
       "states":936,"MC_DC_pair_witnesses":5,"mutants_killed":5,
       "unsafe_close_within_bounded_reference":0,
       "missing":["C01 authoritative finite scope","C02 independent bidirectional source trace",
                  "C03 full requirements coverage validation"],
    }

def inspect(c03:dict, *,root:Path=ROOT)->dict:
    plan=verify_plan(root)
    formal=score_frozen_c03(c03)
    status={}
    ready=[]
    passed=[]
    for item in plan["acceptance_criteria"]:
        parents=item["depends"]
        all_preconditions_pass=all(status[p]["state"]=="PASS" for p in parents)
        if item["id"]=="C03":
            state="PARTIAL_BOUNDED_MECHANICS_ONLY"
            note="Actual native formal evidence exists, but C02 independent requirements completeness is unqualified"
        elif not parents:
            state="EVIDENCE_OR_AUTHORIZATION_MISSING"
            note="P01 original scope freeze and independent authorization unverified"
        elif not all_preconditions_pass:
            state="BLOCKED_ON_PRECEDING_PROOF_AC"
            note="One or more prerequisite proof AC are not independently proven"
        else:
            state="EVIDENCE_OR_AUTHORIZATION_MISSING"
            note="No independently authenticated source/custody record"
        require(state!="PASS","G11_SELF_GENERATED_PROOF_PACKAGE_PASS_FORBIDDEN")
        status[item["id"]]={
           "state":state,
           "depends_on":parents,
           "missing_prerequisite_AC":[p for p in parents if status[p]["state"]!="PASS"],
           "required_evidence":item["evidence"],
           "owner_role":item["owner"],
           "parent_original_AC":item["parent"],
           "failure_code":item["fail"],
           "reason":note,
        }
        if not parents:ready.append(item["id"])
    return {
        "protocol":PROTOCOL,
        "plan_git_blob":PLAN_BLOB,
        "proof_AC_total":len(status),
        "proof_package_mvp_required":11,
        "proof_package_mvp_pass":len(passed),
        "proof_package_mvp_complete":False,
        "original_MVP_AC_required":18,
        "original_MVP_completed":False,
        "AC_topological_order":list(status),
        "independent_evidence_ready_for_action":ready,
        "status_by_AC":status,
        "C03_actual_bounded_subproof":formal,
        "scientific_external_custody_verified":False,
        "remaining_proof_dependency_targets":["P01","P02","B01","C01",
                                            "B02","B03","B04","C02","C04","C05",
                                            "X01","X02"],
        "explicit_stop_reason":"AUTHORITATIVE_SCOPE_AND_EXTERNAL_INDEPENDENT_ANNOTATION_AND_S4_TRACE_NOT_PRESENT",
    }
