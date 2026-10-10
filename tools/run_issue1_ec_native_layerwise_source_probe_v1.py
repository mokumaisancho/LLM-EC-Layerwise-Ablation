#!/usr/bin/env python3
"""Cross-repository source-qualified EC-native S3 multi-select/S4 closure probe.

Actual native *source* implementation is pinned to a new versioned EC source
commit; never relabel the old frozen ECv4.4 singleton API. An external public
admissibility attestor is simulated with explicit authored feature heuristics
for the 4 EXPOSED development cases only. This does not verify real-world
semantic truth, independence or the original four-layer root AC.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.run_issue1_root_ac_orchestrator_v6 import git_blob

PROTOCOL="ISSUE1_NATIVE_S3_SET_S4_CLOSURE_VERSIONED_SOURCE_PROBE_V1"
EC_COMMIT="24fe3a665b21ad90a79095eb8d5818dda5447d62"
EC_MODULE_BLOB="c12e4743c89221a9b81a2f2fa98c4df9d61d72b2"
EC_TEST_BLOB="3821477df059ccf0fc72deef59d852e09cce4ba9"
MODULE="01_repo/src/v4/ec_layerwise_admissible_set_closure_v1.py"
TESTS="01_repo/tests/test_ec_layerwise_admissible_set_closure_v1.py"
CASES=("M003","M007","M008","M009")

def pin(root:Path):
    check=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                         capture_output=True,text=True,timeout=10)
    if check.returncode or check.stdout.strip()!=EC_COMMIT:
        raise ValueError("SOURCE_EC_NATIVE_EXTENSION_GIT_COMMIT_MISMATCH")
    for name,sha in ((MODULE,EC_MODULE_BLOB),(TESTS,EC_TEST_BLOB)):
        path=root/name
        if not path.is_file() or path.is_symlink() or git_blob(path.read_bytes())!=sha:
            raise ValueError("SOURCE_EC_NATIVE_EXTENSION_BLOB_MISMATCH:"+name)

def load(root:Path):
    pin(root)
    p=root/MODULE
    spec=importlib.util.spec_from_file_location("ec_layerwise_v1_qualified",p)
    if spec is None or spec.loader is None:
        raise ValueError("NATIVE_SOURCE_IMPORT_FAILED")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def prepare(task:dict,s2:dict,source_commit:str)->dict:
    # public columns only; ORACLE answer, fixture ID, category and
    # authored acceptable-candidate IDs must NEVER be supplied to native EC.
    candidates=s2["candidates"]
    public={
        "candidates":[{
            "candidate_id":c["candidate_id"],
            "semantic_transition":c["semantic_transition"],
            "evidence_refs":c.get("evidence_refs",[]),
            "dependencies":c.get("dependencies",[]),
            "claims":c.get("claims",[]),
        } for c in candidates],
        "relation_groups":s2.get("relation_groups",[]),
        "semantic_ir_hash":s2["semantic_ir_hash"],
        "source_refs":["input/task.json"],
    }
    # NOTE: evidence presence is a structural development heuristic, not an
    # independently judged semantic-compatibility theorem.
    judgments={}
    for c in candidates:
        cited=bool(c.get("evidence_refs")) and bool(c.get("dependencies"))
        judgments[c["candidate_id"]]={
          "status":"ADMISSIBLE" if cited else "REJECTED",
          "reason":"PUBLIC_SOURCE_AND_DEPENDENCY_PRESENT" if cited else "MISSING_PUBLIC_SOURCE_BINDING",
          "evidence_ref":"input/task.json"}
    sha=hashlib.sha256(json.dumps(public,sort_keys=True,ensure_ascii=False,
                     separators=(",",":")).encode()).hexdigest()
    text_facts=task["context"]["facts"]
    # Explicit literal public unresolved required condition; otherwise this
    # exposed-cohort inventory is user/author attested, not independently proven.
    unresolved="required_condition=unresolved" in text_facts
    required={"required_condition":{"status":"UNRESOLVED" if unresolved else "SATISFIED",
              "evidence_ref":"input/task.json"}} if unresolved else {}
    return {
      "public_s2":public,
      "adjudications":judgments,
      "semantic_authority":{"upstream_sha256":sha,
                            "issuer":"EXPERIMENTAL_PUBLIC_EVIDENCE_HEURISTIC_NOT_INDEPENDENT",
                            "source_commit":source_commit},
      "required_conditions":required,
      "framing":{"reframe_required":False,"reframe_resolved":False},
      "condition_inventory_complete":True,
      "complete_inventory_authority":"DEVELOPMENT_AUTHOR_ASSUMPTION_NOT_INDEPENDENT",
    }

def predict_only(root:Path,src:Path)->dict:
    """Separate child receives ONLY allowlisted public source, not labels."""
    native=load(root)
    req=json.loads(src.read_text())
    keys={"public_s2","adjudications","semantic_authority","required_conditions",
          "framing","condition_inventory_complete","complete_inventory_authority"}
    if set(req)!=keys or req["complete_inventory_authority"]!="DEVELOPMENT_AUTHOR_ASSUMPTION_NOT_INDEPENDENT":
        raise ValueError("UNEXPECTED_PRIVILEGED_PREDICTOR_ENVELOPE")
    selected=native.select_admissible_set(req["public_s2"],
                        adjudications=req["adjudications"],
                        semantic_authority=req["semantic_authority"])
    closure=native.evaluate_closure(selected,
                        required_conditions=req["required_conditions"],
                        framing=req["framing"],
                        public_s2_sha256=selected["source_s2_sha256"],
                        condition_inventory_complete=req["condition_inventory_complete"])
    if selected["semantic_truth_independently_verified"] or closure["semantic_truth_independently_verified"]:
        raise ValueError("FALSE_INDEPENDENT_EC_NATIVE_QUALIFICATION")
    return {"protocol":PROTOCOL,"native_source":EC_COMMIT,
            "input_sha256":hashlib.sha256(json.dumps(req,sort_keys=True,
                   ensure_ascii=False,separators=(",",":")).encode()).hexdigest(),
            "S3":selected,"S4":closure}

def run(root:Path)->dict:
    pin(root)
    p=subprocess.run([sys.executable,"-B","-m","unittest","discover",
                      "-s",str(root/"01_repo/tests"),"-p",
                      "test_ec_layerwise*.py","-q"],
                     capture_output=True,text=True,timeout=30)
    if p.returncode or "Ran 14 tests" not in p.stderr or "OK" not in p.stderr:
        raise ValueError("PINNED_EC_NATIVE_14_NEGATIVE_TESTS_FAILED:"+p.stderr[-240:])
    if str(ROOT/"tools") not in sys.path:sys.path.insert(0,str(ROOT/"tools"))
    from generate_phase1_measurement_v2_canonical import SPECS,rebuild
    frozen=[s for s in SPECS if s["id"] in CASES]
    if [s["id"] for s in frozen]!=list(CASES):
        raise ValueError("AUTHOR_FIXED_SCOPED_CASE_ORDER_INVALID")
    rows=[]
    with tempfile.TemporaryDirectory(prefix="issue1-ec-native-public-") as tmp:
        for spec in frozen:
            task,_s1,s2,_s3,_s4,hidden,_manifest=rebuild(spec)
            # Parent holds hidden only for post-inference grading.
            public=prepare(task,s2,EC_COMMIT)
            path=Path(tmp)/"payload.json"
            path.write_text(json.dumps(public,ensure_ascii=False,sort_keys=True))
            completed=subprocess.run([
                sys.executable,"-B",str(Path(__file__).resolve()),"--predict-only",
                "--ec-root",str(root),"--payload",str(path)],
                capture_output=True,text=True,timeout=30)
            if completed.returncode:
                raise ValueError("PINNED_EC_NATIVE_CHILD_FAILED:"+completed.stderr[-240:])
            predicted=json.loads(completed.stdout)
            actual_ids=predicted["S3"]["selection"]["selected_candidate_ids"]
            actual_closure=predicted["S4"]["closure"]["class"]
            rows.append({
              "case_id":spec["id"],
              "public_input_sha256":predicted["input_sha256"],
              "native_source_git_commit":EC_COMMIT,
              "selected_count":len(actual_ids),
              "selected_candidate_ids":actual_ids,
              "closure_class":actual_closure,
              "selection_match_author_visible_fixture":actual_ids==hidden["acceptable_candidate_ids"],
              "closure_match_author_visible_fixture":actual_closure==hidden["closure_class"],
              "S3_semantic_independence_qualified":False,
              "S4_complete_obligation_inventory_independently_qualified":False,
            })
    if len(rows)!=4 or len({r["case_id"] for r in rows})!=4:
        raise ValueError("S3_S4_SCOPED_CASE_COVERAGE_INCOMPLETE")
    return {
      "protocol":PROTOCOL,
      "native_additive_source_git_commit":EC_COMMIT,
      "native_module_git_blob":EC_MODULE_BLOB,
      "native_negative_tests_passed":14,
      "four_author_exposed_fixtures":len(rows),
      "S3_selected_two_for_M003_and_M009":rows[0]["selected_count"]==2 and rows[3]["selected_count"]==2,
      "S4_competing_CONTINUE_equivalent_CLOSE_unresolved_CONTINUE":
          rows[0]["closure_class"]=="CONTINUE" and
          rows[1]["closure_class"]=="CONTINUE" and
          rows[3]["closure_class"]=="CLOSE",
      "casewise_S3_development_matches":sum(r["selection_match_author_visible_fixture"] for r in rows),
      "casewise_S4_development_matches":sum(r["closure_match_author_visible_fixture"] for r in rows),
      "genuine_native_selection_and_closure_code_exists":True,
      "native_module_actual_python_process_executed":True,
      "external_semantic_adjudicator_certified":False,
      "external_complete_inventory_certified":False,
      "original_frozen_ec_v44_adapter_qualified":False,
      "original_four_layer_AE_completed":False,
      "independent_unseen_gold":False,
      "rows":rows,
      "terminal":"W4_NATIVE_EXPERIMENTAL_SOURCE_COMPILED_AND_EXECUTED_SEMANTIC_AUTHORITY_STILL_UNQUALIFIED",
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--ec-root",required=True,type=Path)
    p.add_argument("--predict-only",action="store_true")
    p.add_argument("--payload",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        v=predict_only(a.ec_root,a.payload) if a.predict_only else run(a.ec_root)
        text=json.dumps(v,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            a.out.write_text(text)
            print(json.dumps({"terminal":v["terminal"],"source":v["native_additive_source_git_commit"],
                              "cases":v["four_author_exposed_fixtures"],"output":str(a.out)}))
        else:print(text,end="")
        return 0
    except Exception as e:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(e).__name__+":"+str(e)[:350]}),
              file=sys.stderr if a.predict_only else sys.stdout)
        return 3
if __name__=="__main__":
    raise SystemExit(main())
