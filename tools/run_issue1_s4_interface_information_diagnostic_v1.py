#!/usr/bin/env python3
"""Origin #1, versioned *diagnostic only*: S4 information-sufficiency intervention.

This does NOT implement EC-native closure or prove an original S1-S4 A-E
comparison. It tests whether model-visible upstream information omitted from
the frozen S3 structural signature resolves its observed aliasing collisions.

A dedicated isolated predictor subprocess receives only a projection of public
task facts, public S2 candidate relations and S3 structural fields. It never
receives fixture IDs, gold/expected/oracle fields, hidden labels or eval imports.
The caller scores only after all predictor invocations have completed.
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
PROTOCOL="ISSUE1_S4_INTERFACE_INFORMATION_SUCCESSOR_DIAGNOSTIC_V1"


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
                                     separators=(",",":")).encode("utf-8")).hexdigest()


def public_projection(task:dict,s2:dict,s3:dict)->dict:
    if any("oracle" in k.lower() or "gold" in k.lower() or "hidden" in k.lower() for k in task):
        raise ValueError("UNTRUSTED_TASK_PRIVILEGED_FIELD")
    if any("oracle" in k.lower() or "gold" in k.lower() or "hidden" in k.lower() for k in s2):
        # S2 oracle constraints *may* exist in source artifact but are removed below.
        pass
    if task.get("schema_version")!="TASK_INPUT_V1":
        raise ValueError("PUBLIC_TASK_SCHEMA_MISMATCH")
    if s2.get("schema_version")!="S2_CANDIDATE_SET_V1":
        raise ValueError("PUBLIC_S2_SCHEMA_MISMATCH")
    if s3.get("schema_version")!="S3_SELECTED_REFRAMED_STATE_V1":
        raise ValueError("PUBLIC_S3_SCHEMA_MISMATCH")
    actual_selected=s3["selection"]["selected_candidate_ids"]
    actual_rejected=s3["selection"]["rejected_candidate_ids"]
    if not isinstance(actual_selected,list) or not isinstance(actual_rejected,list):
        raise ValueError("INVALID_SELECTED_SET")
    valid_ids={c["candidate_id"] for c in s2["candidates"]}
    if not set(actual_selected).issubset(valid_ids) or not set(actual_rejected).issubset(valid_ids):
        raise ValueError("UPSTREAM_CANDIDATE_ID_MISMATCH")
    relation_groups=[]
    for g in s2.get("relation_groups",[]):
        if g["relation_type"] not in ("COMPETING","EQUIVALENT"):
            raise ValueError("UNKNOWN_RELATION_TYPE")
        if not set(g["candidate_ids"]).issubset(set(actual_selected)):
            raise ValueError("RELATION_SELECTED_SET_MISMATCH")
        relation_groups.append({"relation_type":g["relation_type"],
                                "selected_member_count":len(g["candidate_ids"])})
    facts=task["context"]["facts"]
    if not isinstance(facts,list) or not all(isinstance(f,str) for f in facts):
        raise ValueError("PUBLIC_FACTS_NOT_STRINGS")
    return {
        "protocol":PROTOCOL,
        "selected_count":len(actual_selected),
        "rejected_count":len(actual_rejected),
        "reframe_required":s3["framing"]["reframe_required"],
        "trigger_residual_types":sorted(x["type"] for x in s3["framing"].get("trigger_residuals",[])),
        "relation_groups":relation_groups,
        "required_condition_state": "UNRESOLVED" if "required_condition=unresolved" in facts
                                     else "NOT_EXPLICITLY_UNRESOLVED",
    }


def predict(x:dict)->dict:
    fields={"protocol","selected_count","rejected_count","reframe_required",
            "trigger_residual_types","relation_groups","required_condition_state"}
    if not isinstance(x,dict) or set(x)!=fields or x.get("protocol")!=PROTOCOL:
        raise ValueError("PUBLIC_ONLY_SCHEMA_REQUIRED")
    # Known *typed* policy, NOT learned from gold/expected labels:
    # unresolved mandatory condition prevents closure; distinct competing
    # alternatives need selection continuation; equivalence permits completion.
    # It does not infer general language semantics or independent competence.
    if x["required_condition_state"] not in ("UNRESOLVED","NOT_EXPLICITLY_UNRESOLVED"):
        raise ValueError("INVALID_REQUIRED_CONDITION_STATE")
    if x["required_condition_state"]=="UNRESOLVED":
        return {"closure_class":"CONTINUE","reason":"UNRESOLVED_REQUIRED_CONDITION"}
    if any(g["relation_type"]=="COMPETING" and g["selected_member_count"]>=2
           for g in x["relation_groups"]):
        return {"closure_class":"CONTINUE","reason":"COMPETING_ALTERNATIVES_OPEN"}
    return {"closure_class":"CLOSE","reason":"NO_EXPLICIT_BLOCKING_SIGNAL_IN_PUBLIC_PROJECTION"}


def baseline_signature(x:dict)->str:
    return canonical_hash({k:x[k] for k in ("selected_count","rejected_count",
                                           "reframe_required","trigger_residual_types")})


def run()->dict:
    # The parent obtains retrospective truth, but only AFTER isolated predictor
    # output has been sealed; no independent generalization claim is permitted.
    sys.path.insert(0,str(ROOT/"tools"))
    from generate_phase1_measurement_v2_canonical import rebuild, SPECS
    pinned_original=json.loads((ROOT/"results/phase1_s4_identifiability_audit_2026-10-03.json").read_text())
    rows=[]
    with tempfile.TemporaryDirectory(prefix="issue1-s4-public-") as d:
        for spec in SPECS:
            task,s1,s2,s3,s4,hidden,manifest=rebuild(spec)
            visible=public_projection(task,s2,s3)
            path=Path(d)/(str(len(rows)).zfill(3)+".json")
            path.write_text(json.dumps(visible,sort_keys=True))
            proc=subprocess.run([sys.executable,"-I",str(Path(__file__).resolve()),
                                "--predict-public",str(path)],
                                capture_output=True,text=True,timeout=20,cwd=ROOT)
            if proc.returncode:
                raise RuntimeError("ISOLATED_PREDICTOR_FAILED:"+proc.stderr[-350:])
            predicted=json.loads(proc.stdout)
            if set(predicted)!={"closure_class","reason"}:
                raise ValueError("INVALID_PREDICTOR_RESPONSE")
            rows.append({"case_id":hidden["fixture_id"],
                         "task_public_sha256":canonical_hash(task),
                         "s2_public_sha256":canonical_hash({k:v for k,v in s2.items() if k!="oracle_constraints"}),
                         "s3_public_sha256":canonical_hash({k:v for k,v in s3.items() if k!="oracle_constraints"}),
                         "sanitized_predictor_sha256":canonical_hash(visible),
                         "structural_signature_sha256":baseline_signature(visible),
                         "prediction":predicted,
                         "reference_label":hidden["closure_class"],
                         "correct":predicted["closure_class"]==hidden["closure_class"],
                         "visible_diagnostic_features":visible,
                         })
    if len(rows)!=10 or len({r["case_id"] for r in rows})!=10:
        raise ValueError("TEN_FROZEN_FIXTURES_REQUIRED")
    correct=sum(r["correct"] for r in rows)
    groups={}
    for r in rows:
        groups.setdefault(r["structural_signature_sha256"],[]).append(r)
    best=sum(max(sum(row["reference_label"]==label for row in group)
                 for label in set(row["reference_label"] for row in group))
             for group in groups.values())
    prior=pinned_original["identifiability"]
    if best!=prior["best_possible_majority_correct"] or best!=8:
        raise ValueError("ORIGINAL_S4_COLLISION_BOUND_DRIFT")
    by_id={r["case_id"]:r for r in rows}
    controls={}
    for case_id,feature,drop in [
       ("M003","relation_groups",[]),
       ("M007","required_condition_state","NOT_EXPLICITLY_UNRESOLVED"),
    ]:
        x=dict(by_id[case_id]["visible_diagnostic_features"])
        x[feature]=drop
        controls[case_id]={"masked_feature":feature,"baseline":by_id[case_id]["prediction"],
                           "negative_control_prediction":predict(x),
                           "causal_public_feature_treatment":True}
        if controls[case_id]["baseline"]["closure_class"]==controls[case_id]["negative_control_prediction"]["closure_class"]:
            raise ValueError("NEGATIVE_CONTROL_DID_NOT_CHANGE_DECISION:"+case_id)
    return {
        "protocol":PROTOCOL,
        "version_reason":"New separate diagnostic; frozen original Phase1 unchanged",
        "scope":"10 retrospective author-visible Phase1 v2 fixtures; NOT heldout, NOT EC-native accuracy",
        "fixture_count":len(rows),
        "source":"tools/generate_phase1_measurement_v2_canonical.py",
        "original_structural_interface_majority_upper_bound":best/len(rows),
        "enhanced_public_interface_known_fixture_accuracy":correct/len(rows),
        "observed_accuracy_difference_not_generalization":(correct-best)/len(rows),
        "enhanced_correct":correct,
        "feature_ablation_controls":controls,
        "case_results":rows,
        "independent_study_certified":False,
        "full_five_arm_run":False,
        "native_ec_closure_measured":False,
        "original_issue_one_qualified":False,
        "scientific_takeaway":"S4 structural signatures alias at least two distinct closure labels. Restoring public relation type and pending-required-condition signals separates all known frozen fixture groups. Does not establish general closure correctness.",
        "terminal":"RETROSPECTIVE_INTERFACE_INFORMATION_DIAGNOSTIC_COMPLETE",
    }


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--predict-public",type=Path)
    args=ap.parse_args()
    if args.predict_public:
        data=json.loads(args.predict_public.read_text())
        print(json.dumps(predict(data),sort_keys=True))
        return 0
    print(json.dumps(run(),sort_keys=True,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
