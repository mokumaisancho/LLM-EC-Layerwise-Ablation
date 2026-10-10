#!/usr/bin/env python3
"""Bounded exhaustive S4 closure property/mutation checker (Issue #1 C03).

This checks mechanical decision safety for the EXPLICITLY TYPED 0..2-obligation,
two-candidate/three-relation, three-reframe, two-inventory state domain. This
does NOT prove that the supplied obligations are complete, independently
authorized, or that natural-language semantics are correct.
"""
from __future__ import annotations
import hashlib
import importlib.util
import itertools
import json
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EC_COMMIT="ae4b02bca34147d549abda85fad9cdc793ca054f"
S4_MODULE="01_repo/src/v4/ec_layerwise_admissible_set_closure_v1.py"
S4_BLOB="c12e4743c89221a9b81a2f2fa98c4df9d61d72b2"
PROTOCOL="ISSUE1_C03_BOUNDED_S4_MODEL_CHECK_V1"
STATUSES=("SATISFIED","UNRESOLVED","ACCEPTED_LIMITATION")
RELATIONS=("NONE","COMPETING","EQUIVALENT")
FRAMES=((False,False),(True,False),(True,True))
PICKS=((),("A",),("B",),("A","B"))
PREDICATES=("inventory_attested","pending_reframe","unresolved_obligation",
            "competing_selected","at_least_one_selected")

def fail(msg):
    raise ValueError(msg)

def git_blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load_module(path:Path,alias:str):
    spec=importlib.util.spec_from_file_location(alias,path)
    if spec is None or spec.loader is None:fail("EC_SOURCE_MODULE_UNLOADABLE")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def pin(native:Path):
    v=subprocess.run(["git","-C",str(native),"rev-parse","HEAD"],text=True,
                     capture_output=True,timeout=10)
    if v.returncode or v.stdout.strip()!=EC_COMMIT:
        fail("C03_NATIVE_SOURCE_COMMIT_DRIFT")
    path=native/S4_MODULE
    if not path.is_file() or path.is_symlink() or git_blob(path.read_bytes())!=S4_BLOB:
        fail("C03_NATIVE_SOURCE_BLOB_CHANGED")
    return path

def case(picked:tuple[str,...],rel:str,conditions:tuple[str,...],
         frame:tuple[bool,bool],complete:bool):
    ids=("A","B")
    group=[] if rel=="NONE" else [
        {"group_id":"g","relation_type":rel,"candidate_ids":["A","B"]}]
    s2={
        "candidates":[{"candidate_id":c,"semantic_transition":{"type":"formal-only"},
                        "evidence_refs":["public"],"dependencies":[],"claims":[]}
                       for c in ids],
        "relation_groups":group,"semantic_ir_hash":"0"*64,
        "source_refs":["public"],
    }
    obligations={f"req_{i}":{"status":v,"evidence_ref":"public"}
                 for i,v in enumerate(conditions)}
    decisions={
        c:{"status":"ADMISSIBLE" if c in picked else "REJECTED",
           "reason":"FORMAL_INPUT_CONSTRAINT_ONLY","evidence_ref":"public"}
        for c in ids}
    return (s2,decisions,obligations,
            {"reframe_required":frame[0],"reframe_resolved":frame[1]},complete)

def predict(engine,data):
    s2,decisions,obligations,framing,complete=data
    bound=engine._hash(s2)
    selection=engine.select_admissible_set(
        s2,adjudications=decisions,
        semantic_authority={"upstream_sha256":bound,
                            "issuer":"BOUNDED_FORMAL_SIMULATION_NO_AUTHENTICATION",
                            "source_commit":EC_COMMIT})
    return engine.evaluate_closure(
        selection,required_conditions=obligations,framing=framing,
        public_s2_sha256=bound,condition_inventory_complete=complete)

def oracle(picked,rel,conditions,frame,complete):
    # Independent reference *Boolean* specification, not EC code imports.
    if not complete:return "REJECT_INVENTORY"
    pending=frame==(True,False)
    if pending:return "REFRAME"
    if any(value=="UNRESOLVED" for value in conditions):return "CONTINUE"
    if rel=="COMPETING" and len(picked)==2:return "CONTINUE"
    if not picked:return "BLOCKED"
    return "CLOSE"

def check(engine,data,expected):
    try:
        result=predict(engine,data)
    except engine.ECAdmissibilityError:
        return expected=="REJECT_INVENTORY"
    return result["closure"]["class"]==expected

def all_states():
    for picked in PICKS:
        for rel in RELATIONS:
            for num_obligations in range(3):
                for obligations in itertools.product(STATUSES,repeat=num_obligations):
                    for frame in FRAMES:
                        for complete in (False,True):
                            yield picked,rel,obligations,frame,complete

def witnesses():
    baseline=(("A","B"),"EQUIVALENT",("SATISFIED",),(False,False),True)
    return {
       "inventory_attested":(
           case(*baseline),
           case(baseline[0],baseline[1],baseline[2],baseline[3],False)),
       "pending_reframe":(
           case(*baseline),
           case(baseline[0],baseline[1],baseline[2],(True,False),True)),
       "unresolved_obligation":(
           case(*baseline),
           case(baseline[0],baseline[1],("UNRESOLVED",),baseline[3],True)),
       "competing_selected":(
           case(*baseline),
           case(baseline[0],"COMPETING",baseline[2],baseline[3],True)),
       "at_least_one_selected":(
           case(("A",),"NONE",(),(False,False),True),
           case((),"NONE",(),(False,False),True)),
    }

MUTANTS={
    "drop_inventory_gate":(
        "_require(condition_inventory_complete is True,",
        "_require(True,"),
    "drop_pending_reframe":(
        'if framing["reframe_required"] and not framing["reframe_resolved"]:',
        'if False and framing["reframe_required"] and not framing["reframe_resolved"]:'),
    "drop_unresolved_obligation":("elif unresolved:","elif False and unresolved:"),
    "drop_competing_selected":("elif competing:","elif False and competing:"),
    "drop_nonempty_selection":("elif not picked:","elif False and not picked:"),
}

def run(native:Path):
    source=pin(native)
    engine=load_module(source,"ec_s4_original_for_bounded_analysis")
    total=checked=refused=legitimate_close=unsafe_close=0
    failures=[]
    for picked,rel,conditions,frame,complete in all_states():
        total+=1
        expected=oracle(picked,rel,conditions,frame,complete)
        data=case(picked,rel,conditions,frame,complete)
        try:
            result=predict(engine,data)
        except engine.ECAdmissibilityError as exc:
            actual="REJECT_INVENTORY"
            if complete:failures.append((total,"unexpected rejection",str(exc)))
            refused+=1
        else:
            actual=result["closure"]["class"]
            if actual=="CLOSE":
                legitimate_close+=int(expected=="CLOSE")
                unsafe_close+=int(expected!="CLOSE")
            # Reject a refactoring that returns an unreviewed conclusion.
            if result["semantic_truth_independently_verified"] is not False:
                failures.append((total,"false independence status"))
        checked+=int(expected==actual)
        if expected!=actual:failures.append((total,expected,actual))
    if failures:fail("C03_STATE_COUNTEREXAMPLES:"+repr(failures[:3]))
    if total!=936 or refused!=468:
        fail("C03_INCOMPLETE_BOUNDED_STATE_SPACE")
    # Explicit MC/DC witnesses for the 5 independently influential gate
    # conditions. Two inputs differ in only the named predicate's condition.
    mcdc={}
    for name,(a,b) in witnesses().items():
        results=[]
        for data in (a,b):
            s2,decisions,obligations,framing,complete=data
            picked=tuple(k for k in ("A","B") if decisions[k]["status"]=="ADMISSIBLE")
            rel=s2["relation_groups"][0]["relation_type"] if s2["relation_groups"] else "NONE"
            expected=oracle(picked,rel,tuple(v["status"] for v in obligations.values()),
                            (framing["reframe_required"],framing["reframe_resolved"]),complete)
            if not check(engine,data,expected):fail("C03_MCDC_WITNESS_FAILED:"+name)
            results.append(expected)
        if results[0]==results[1] or results[0]!="CLOSE":
            fail("C03_MCDC_INDEPENDENCE_NOT_DEMONSTRATED:"+name)
        mcdc[name]=results
    # Source-level mutations in a temp file; never modify pinned native code.
    original=source.read_text()
    killed={}
    with tempfile.TemporaryDirectory(prefix="issue1-s4-native-mutants-") as tmp:
        for name,(before,after) in MUTANTS.items():
            if original.count(before)!=1:fail("C03_MUTANT_SOURCE_PATTERN_CHANGED:"+name)
            mutant=original.replace(before,after,1)
            path=Path(tmp)/(name+".py")
            path.write_text(mutant)
            altered=load_module(path,"ec_s4_mutant_"+name)
            witness=witnesses()[{
                "drop_inventory_gate":"inventory_attested",
                "drop_pending_reframe":"pending_reframe",
                "drop_unresolved_obligation":"unresolved_obligation",
                "drop_competing_selected":"competing_selected",
                "drop_nonempty_selection":"at_least_one_selected",
            }[name]][1]
            s2,decisions,obligations,framing,complete=witness
            picked=tuple(k for k in ("A","B") if decisions[k]["status"]=="ADMISSIBLE")
            rel=s2["relation_groups"][0]["relation_type"] if s2["relation_groups"] else "NONE"
            expected=oracle(picked,rel,tuple(v["status"] for v in obligations.values()),
                            (framing["reframe_required"],framing["reframe_resolved"]),complete)
            survived=check(altered,witness,expected)
            if survived:fail("C03_UNKILLED_MUTANT:"+name)
            killed[name]={"killed":True,"mutated_source_sha256":
                           hashlib.sha256(mutant.encode()).hexdigest()}
    return {
        "protocol":PROTOCOL,
        "ec_native_source_commit":EC_COMMIT,
        "ec_native_source_git_blob":S4_BLOB,
        "bounded_state_space":{"candidates":2,"relations":list(RELATIONS),
               "obligations_count_domain":[0,1,2],"obligation_statuses":list(STATUSES),
               "valid_framing_states":len(FRAMES),"inventory_attestation_states":2,
               "states_checked":total,"reference_decision_exact_matches":checked,
               "unattested_states_refused":refused,
               "unsafe_close_within_typed_bounded_reference":unsafe_close,
               "legitimate_typed_closures":legitimate_close},
        "MC_DC_BOUNDED":{"conditions":list(PREDICATES),"independent_pairs":mcdc,
                         "pair_count":len(mcdc)},
        "actual_native_source_mutation":{"mutants":killed,"killed":len(killed),
                                         "total":len(MUTANTS)},
        "original_AC_C03_qualified":False,
        "independent_obligation_inventory_certified":False,
        "independent_natural_language_semantics_certified":False,
        "finite_state_mechanics_verified":True,
        "qualification_limit":"PROVES_ONLY_EXPLICIT_TYPED_FINITE_DOMAIN_FOR_PINNED_NATIVE_DECISION",
    }

if __name__=="__main__":
    import argparse
    a=argparse.ArgumentParser()
    a.add_argument("--native-root",required=True,type=Path)
    a.add_argument("--out",type=Path)
    x=a.parse_args()
    v=run(x.native_root)
    out=json.dumps(v,sort_keys=True,indent=2)
    if x.out:x.out.write_text(out+"\n",encoding="utf-8")
    print(json.dumps({"states":v["bounded_state_space"]["states_checked"],
                      "matched":v["bounded_state_space"]["reference_decision_exact_matches"],
                      "MC_DC":v["MC_DC_BOUNDED"]["pair_count"],
                      "mutants_killed":v["actual_native_source_mutation"]["killed"],
                      "formal_only":True}))
