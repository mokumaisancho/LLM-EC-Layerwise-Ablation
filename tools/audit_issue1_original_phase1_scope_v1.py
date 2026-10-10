#!/usr/bin/env python3
"""Original Phase1 scope/identifiability admission. Not an AC-completion scorer.

An optional 13-AC independent proof package cannot silently become a required
gate for the immutable Issue #1 Phase1 MVP. Frozen ECv4.4 S3/S4 incompatibility
is a first-class result, NOT a generic 'missing 120 documents' blocker.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

PROTOCOL="ISSUE1_ORIGINAL_PHASE1_SCOPE_ADMISSION_V1"
SOURCE_BLOBS={
    "ACCEPTANCE_CRITERIA.md":"40e4d41914fb17ee5c7deb0cfd32276a41c9a1fc",
    "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json":"08407bec73278aeda8ddd2d4d6efc810dadf46f9",
    "results/ec_native_adapter_qualification.json":"8693c5be282b1e8407a0c1358e18eab2ad78905c",
    "results/phase1_s4_identifiability_audit_2026-10-03.json":"624616a1f4b0dc4a2330cbcd0a6a03b94a475ce8",
}
EC_PIN="d5ec423968f1c9242c590e5e77ccfd92d1f59eb2"
MVP=[f"AC-{n:02d}" for n in (*range(1,10),*range(11,18),19,20)]
AC20={f"AC-{n:02d}" for n in range(1,21)}


def gate(ok,reason):
    if not ok: raise ValueError(reason)


def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest()


def topological(contract):
    deps=contract["ac_dependencies"]
    gate(set(deps)==AC20,"AC20_ADDED_OR_REMOVED")
    order=[]
    while len(order)<20:
        next_ready=[]
        for ident in sorted(AC20-set(order)):
            refs=deps[ident]
            gate(len(refs)==len(set(refs)),"DUPLICATE_AC_EDGE")
            for parent in refs:
                gate(parent in AC20 or parent in contract["issue_dependencies"]
                     or (ident=="AC-18" and parent=="AC-10_IF_NEEDED"),
                     "UNKNOWN_AC_OR_ISSUE_PARENT:"+parent)
            if all(p in order for p in refs if p in AC20):
                next_ready.append(ident)
        gate(bool(next_ready),"AC_DEPENDENCY_CYCLE")
        order.extend(next_ready)
    return order


def audit(norm,adapter,s4):
    gate(norm["protocol"]=="PHASE1_MVP_TCC_V1","PHASE1_PROTOCOL_CHANGED")
    gate(norm["mvp"]["required_ac"]==MVP and
         set(norm["mvp"]["post_mvp_ac"])==AC20-set(MVP) and
         norm["frozen_thresholds"]["oracle_substitution_gain_material_abs"]==0.2,
         "ORIGINAL_MVP_OR_0P20_MATERIALITY_CHANGED")
    gate(norm["canonical_inputs"]["ec_commit"]==EC_PIN and
         adapter["ec_source"]["commit"]==EC_PIN and
         adapter["protocol"]=="PHASE1_EC_NATIVE_ADAPTER_V1" and
         adapter["oracle_blind"] is True,"FROZEN_NATIVE_PROVENANCE_CHANGED")
    gate(norm["mvp"]["scope"]=={
         "S1":["LLM","ORACLE"],"S2":["LLM","ORACLE"],
         "S3":["LLM","ECV4_4_NATIVE_VIA_QUALIFIED_ADAPTER","ORACLE"],
         "S4":["LLM","ECV4_4_NATIVE_VIA_QUALIFIED_ADAPTER","ORACLE"]},
         "ORIGINAL_LAYER_SCOPE_CHANGED")
    order=topological(norm)
    a=adapter["subfunction_authority"]
    gate(adapter["status"]=="INCOMPATIBLE" and
         a["s3_selection"]["authority"]=="EC_NATIVE_NOT_APPLICABLE" and
         a["s4_closure"]["authority"]=="EC_NATIVE_NOT_APPLICABLE" and
         a["s3_selection"]["reportable"] is False and
         a["s4_closure"]["reportable"] is False,
         "FORGED_EC_NATIVE_SAME_FUNCTION_QUALIFICATION")
    gate(set(a["s3_selection"]["counterexamples"])=={"M003","M009"},
         "S3_MULTISELECTION_COUNTEREXAMPLE_CHANGED")
    gate(s4["identifiability"]["metric_type"]=="INTERFACE_IDENTIFIABILITY_BOUND_NOT_EC_ACCURACY",
         "INTERFACE_BOUND_LAUNDERED_AS_ACCURACY")
    covered=set()
    top=0
    for group in s4["collision_groups"]:
        values=group["closure_labels"]
        gate(set(values)=={"CLOSE","CONTINUE"},"CLOSURE_LABELS_CHANGED")
        cases=[c for group_cases in values.values() for c in group_cases]
        gate(not set(cases)&covered,"DUPLICATE_CLOSURE_SCORING")
        covered.update(cases)
        top+=max(map(len,values.values()))
    for item in s4["separately_identifiable"]:
        ident=item["fixture_id"]
        gate(ident not in covered,"DUPLICATE_CLOSURE_SCORING")
        covered.add(ident)
        top+=1
    gate(len(covered)==s4["fixture_count"]==10 and top==8 and
         s4["identifiability"]["best_possible_majority_correct"]==8 and
         a["s4_closure"]["structural_upper_bound"]==0.8,
         "ORIGINAL_S4_IDENTIFIABILITY_EVIDENCE_CHANGED")
    pass_ids={"AC-19","AC-20"}
    verdict={name:("PASS" if name in pass_ids else "NOT_PROVEN") for name in order}
    for name in pass_ids:
        gate(all(verdict[p]=="PASS" for p in norm["ac_dependencies"][name] if p in AC20),
             "ORIGINAL_AC_WITH_FAILED_PARENT")
    return {
      "protocol":PROTOCOL,
      "original_issue":1,
      "scope":"ORIGINAL_PHASE1_S1_TO_S4_ONLY",
      "original_mvp_AC_total":len(MVP),
      "original_mvp_AC_pass":sum(verdict[k]=="PASS" for k in MVP),
      "original_AC20_topological_order":order,
      "original_AC20_status":verdict,
      "original_mvp_complete":False,
      "genuine_A_B_C_D_E_four_layer_evidence":False,
      "native_S3_multi_selection_counterexamples":["M003","M009"],
      "S4_signature_ceiling":{"correct":top,"total":len(covered),
            "bound_only_not_EC_accuracy":True},
      "original_pinned_EC_compatible":False,
      "actual_blocker":"FROZEN_NATIVE_S3_S4_SAME_FUNCTION_INCOMPATIBLE",
      "next_valid_action":"VERSIONED_S3_S4_EC_SUCCESSOR_THEN_REAL_MATCHED_A_TO_E",
      "critical_path":["QUALIFY_VERSIONED_S3_S4_NATIVE_INTERFACE",
                       "RUN_ACTUAL_ALL_LAYER_A_TO_E_INTERVENTIONS",
                       "VERIFY_ALL_18_ORIGINAL_AC"],
      "post_MVP":["AC-10","AC-18"],
      "optional_studies_not_frozen_root_gates":[
          "13_ADDITIONAL_PROOF_AC","120_EXTERNALLY_SOURCED_HOLDOUT_DOCUMENTS",
          "C1_TO_C6_GLOBAL_INTERNAL_MECHANISM_STUDY"],
      "terminal":"FROZEN_ORIGINAL_NATIVE_INCOMPATIBLE_VERSIONED_SUCCESSOR_REQUIRED",
    }


def run(root):
    contents={}
    for name,want in SOURCE_BLOBS.items():
        path=root/name
        gate(path.is_file() and not path.is_symlink(),"MISSING_FROZEN_SOURCE:"+name)
        raw=path.read_bytes()
        gate(blob(raw)==want,"FROZEN_GIT_BLOB_MISMATCH:"+name)
        contents[name]=raw
    gate(b"AC-01." in contents["ACCEPTANCE_CRITERIA.md"] and
         b"AC-20." in contents["ACCEPTANCE_CRITERIA.md"],
         "FROZEN_AC_MARKDOWN_INVALID")
    json_path=lambda name: json.loads(contents[name].decode("utf-8"))
    return audit(json_path("docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json"),
                 json_path("results/ec_native_adapter_qualification.json"),
                 json_path("results/phase1_s4_identifiability_audit_2026-10-03.json"))


def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--root",required=True,type=Path)
    arg.add_argument("--out",type=Path)
    v=arg.parse_args()
    try:
        report=run(v.root)
        result=json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\\n"
        if v.out:
            gate(not v.out.is_symlink(),"OUTPUT_SYMLINK")
            v.out.write_text(result,encoding="utf-8")
        else:print(result,end="")
        return 2
    except Exception as e:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"INTEGRITY_FAIL_CLOSED",
                          "error":type(e).__name__+":"+str(e)[:240]}),file=sys.stderr)
        return 3
if __name__=="__main__":
    raise SystemExit(main())
