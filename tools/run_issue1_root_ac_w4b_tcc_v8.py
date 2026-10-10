#!/usr/bin/env python3
"""AC-driven TCC v8: real W4B/C typed-logic implementation and negative gates.

Runs pinned v7 root-AC science using its *original* source, then checks
new native typed authority revision + 24 source tests, runs independently
isolated public-input predictions on a generated typed corpus, checks that
uncertified S4 closure fails, and recomputes original 18-AC MVP dependencies.
No recursion into ChatGPT, no scheduled process, no development gold as heldout.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.run_issue57_tcc_generator_gate import TCC_SOURCE,context_for,node
from tools.run_issue1_root_ac_orchestrator_v6 import git_head,git_blob,immutable_evidence_seal
from tools.run_issue1_root_ac_w4_tcc_v7 import run as run_v7

PROTOCOL="ISSUE1_ROOT_AC_W4B_W4C_TYPED_TCC_V8"
SOURCE_COMMIT="ae4b02bca34147d549abda85fad9cdc793ca054f"
MODULE="01_repo/src/v4/ec_layerwise_typed_evidence_authority_v1.py"
MODULE_BLOB="a3efa53f81004a17127c83e195f4281bd3fb645a"
TESTS="01_repo/tests/test_ec_layerwise_typed_evidence_authority_v1.py"
TESTS_BLOB="2f19334a01f4fb2cdeeac85c77c2188d65bc28ca"
NATIVE_OLD="01_repo/src/v4/ec_layerwise_admissible_set_closure_v1.py"
NATIVE_OLD_BLOB="c12e4743c89221a9b81a2f2fa98c4df9d61d72b2"
CONTRACT=ROOT/"docs/ISSUE1_W4B_W4C_TYPED_EVIDENCE_CONTRACT_V1.json"

def need(value,msg):
    if not value:raise ValueError(msg)

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,
             separators=(",",":")).encode()).hexdigest()

def sources_pin(root:Path):
    need(git_head(root)==SOURCE_COMMIT,"W4B_NATIVE_GIT_COMMIT_MISMATCH")
    hashes={}
    for name,pinned in ((MODULE,MODULE_BLOB),(TESTS,TESTS_BLOB),
                        (NATIVE_OLD,NATIVE_OLD_BLOB)):
        p=root/name
        need(p.is_file() and not p.is_symlink() and git_blob(p.read_bytes())==pinned,
             "W4B_NATIVE_CODE_OR_TEST_TAMPER:"+name)
        hashes[name]=pinned
    return hashes

def researcher_source_seal():
    names=["tools/run_issue1_root_ac_orchestrator_v6.py",
           "tools/run_issue1_root_ac_w4_tcc_v7.py",
           "tools/run_issue1_root_ac_w4b_tcc_v8.py"]
    out={}
    for n in names:
        p=ROOT/n
        get=subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD:"+n],
               text=True,capture_output=True,timeout=10)
        need(get.returncode==0 and p.is_file() and not p.is_symlink() and
             git_blob(p.read_bytes())==get.stdout.strip(),
             "RESEARCH_SCIENTIFIC_CODE_TAMPER:"+n)
        out[n]=get.stdout.strip()
    return out

def public_case(i):
    # Programmatically construct new names and held-out *typed structures*;
    # not human-blinded new language semantics and not original Phase1 gold.
    names=[f"fresh_{i}_{j}" for j in range(3)]
    facts={f"fact_{i}_a":bool(i%2),f"fact_{i}_b":bool(i%3),
           f"fact_{i}_c":bool(i%5)}
    predicates={
       names[0]:[f"fact:fact_{i}_a"],
       names[1]:[f"not:fact:fact_{i}_b"],
       names[2]:[f"fact:fact_{i}_c",f"not:fact:fact_{i}_a"],
    }
    ob={"approval":"UNRESOLVED"} if i%4==0 else (
       {"approval":"SATISFIED"} if i%4==1 else {})
    relation="COMPETING" if i%2 else "EQUIVALENT"
    p={"candidates":[{
         "candidate_id":n,"semantic_transition":{"operation":"DEVELOPMENT_TYPED_ONLY"},
         "evidence_refs":["typed:input"],"dependencies":[],"claims":[]}
         for n in names],
       "relation_groups":[{"group_id":"relation",
             "relation_type":relation,"candidate_ids":names[:2]}],
       "semantic_ir_hash":digest({"case_shape":i,"names":names}),
       "source_refs":["typed:input"]}
    body={"schema":"EC_TYPED_SCOPE_V1",
          "source_id":"typed:input","facts":facts,
          "candidate_requirements":predicates,
          "required_obligations":ob,"inventory_closed":True}
    doc={**body,"source_sha256":digest(body)}
    return {"public_s2":p,"typed_document":doc}

def child_predict(native_root:Path,payload:Path)->dict:
    sources_pin(native_root)
    packet=json.loads(payload.read_text())
    need(set(packet)=={"public_s2","typed_document"},"PRIVILEGED_CHILD_PACKET_FIELDS")
    import importlib.util
    spec=importlib.util.spec_from_file_location("ec_native_typed_v1",native_root/MODULE)
    eng=importlib.util.module_from_spec(spec);spec.loader.exec_module(eng)
    old_spec=importlib.util.spec_from_file_location("ec_native_set_s4",native_root/NATIVE_OLD)
    native=importlib.util.module_from_spec(old_spec);old_spec.loader.exec_module(native)
    prod=eng.compile_public_typed_evidence(packet["public_s2"],
               packet["typed_document"],source_commit=SOURCE_COMMIT)
    select=native.select_admissible_set(packet["public_s2"],
               adjudications=prod["adjudications"],
               semantic_authority=prod["semantic_authority"])
    blocked=False
    try:
        native.evaluate_closure(select,required_conditions=prod["required_conditions"],
              framing={"reframe_required":False,"reframe_resolved":False},
              public_s2_sha256=select["source_s2_sha256"],
              condition_inventory_complete=prod["condition_inventory_complete"])
    except native.ECAdmissibilityError as exc:
        blocked="S4_COMPLETE_CONDITION_INVENTORY_ATTESTATION_REQUIRED" in str(exc)
    need(blocked,"FALSE_S4_CLOSE_FROM_SELF_ASSERTED_TYPED_SCOPE")
    return {
        "input_sha256":digest(packet),
        "typed_statuses":prod["adjudications"],
        "native_selected":select["selection"]["selected_candidate_ids"],
        "native_rejected":select["selection"]["rejected_candidate_ids"],
        "untrusted_completeness_rejected":blocked,
        "natural_semantics_qualified":prod["natural_language_semantic_authority_qualified"],
        "independent_inventory_qualified":prod["independent_obligation_inventory_qualified"],
        "source_claims_complete":prod["source_declares_inventory_closed"],
    }

def measure(native_root:Path)->dict:
    pinned=sources_pin(native_root)
    p=subprocess.run([sys.executable,"-B","-m","unittest","discover",
          "-s",str(native_root/"01_repo/tests"),"-p","test_ec_layerwise*.py","-q"],
          text=True,capture_output=True,timeout=50)
    need(p.returncode==0 and "Ran 24 tests" in p.stderr and "OK" in p.stderr,
         "W4B_C_NATIVE_24_TESTS_FAILED:"+p.stderr[-180:])
    rows=[]
    with tempfile.TemporaryDirectory(prefix="issue1-native-typed-") as scratch:
        for k in range(1,13):
            public=public_case(k)
            f=Path(scratch)/"public_only.json"
            f.write_text(json.dumps(public,sort_keys=True),encoding="utf-8")
            q=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),
                  "--child-only","--new-native-root",str(native_root),
                  "--public-payload",str(f)],text=True,capture_output=True,timeout=25)
            need(q.returncode==0,"W4_TYPED_CHILD_SUBPROCESS_FAILED:"+q.stderr[-250:])
            response=json.loads(q.stdout)
            need(response["input_sha256"]==digest(public),"W4_TYPED_CHILD_INPUT_SHA_CHANGED")
            x=public["typed_document"]["facts"]
            names=[z["candidate_id"] for z in public["public_s2"]["candidates"]]
            expected=[(x[f"fact_{k}_a"]),
                      (not x[f"fact_{k}_b"]),
                      (x[f"fact_{k}_c"] and not x[f"fact_{k}_a"])]
            allowed=[name for name,ok in zip(names,expected) if ok]
            need(response["native_selected"]==allowed,
                 "W4_TYPED_UNREGISTERED_S3_PREDICTION:"+str(k))
            need(response["untrusted_completeness_rejected"] and
                 response["natural_semantics_qualified"] is False and
                 response["independent_inventory_qualified"] is False,
                 "W4_TYPED_UNAUTHORIZED_CLOSURE_OR_CREDENTIAL")
            rows.append({"case_index":k,"input_sha256":response["input_sha256"],
                         "candidate_count":3,"expected_formal_selected_count":len(allowed),
                         "native_selected_count":len(response["native_selected"]),
                         "native_exact_formal_invariant_pass":True,
                         "native_S4_self_attestation_rejected":True})
        # Tamper gate: derivative packet missing a declared precondition must
        # not be "corrected" by looking up fixture-specific gold.
        bad=public_case(81)
        bad["typed_document"]["candidate_requirements"].pop(
            bad["public_s2"]["candidates"][0]["candidate_id"])
        base={k:v for k,v in bad["typed_document"].items() if k!="source_sha256"}
        bad["typed_document"]["source_sha256"]=digest(base)
        path=Path(scratch)/"negative_public.json"
        path.write_text(json.dumps(bad),encoding="utf-8")
        neg=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),
                "--child-only","--new-native-root",str(native_root),
                "--public-payload",str(path)],text=True,capture_output=True,timeout=20)
        need(neg.returncode!=0 and "CANDIDATE_REQUIREMENTS_COVERAGE_INCOMPLETE" in neg.stderr,
             "W4B_INCOMPLETE_TYPED_SOURCE_FAILED_TO_ABSTAIN")
    return {
       "new_native_commit":SOURCE_COMMIT,
       "native_git_blobs":pinned,
       "native_source_tests_passed":24,
       "public_new_typed_cases":12,
       "formal_invariant_cases_passed":sum(r["native_exact_formal_invariant_pass"] for r in rows),
       "S4_false_closure_preventions":sum(r["native_S4_self_attestation_rejected"] for r in rows),
       "undeclared_requirement_abstention_verified":True,
       "true_natural_language_semantic_adjudication":False,
       "independently_verified_complete_obligation_inventory":False,
       "original_A_E_all_layers_measured":False,
       "development_data_relabelled_unseen":False,
       "rows":rows
    }

def tcc_spec():
    return {
       "schema":"tcc.spec.v3","tcc_id":"ISSUE1-ROOT-AC-W4B-C-TYPED-PROOF-V8",
       "goal":"Autonomously execute all AC-dependent machine-feasible W4B/C typed source gates after pinned v7, then decide root exit strictly by original 18 AC and real 4-layer A-E",
       "acceptance":[
          "Replay real root original 18AC and frozen v7 source-typed W4A with pinned v7 EC commit",
          "Verify NEW 3 upstream module/test Git source blobs and run all 24 native negative tests",
          "Execute 12 fresh typed inputs in label-isolated native S3 child with independent formal expected values",
          "Prevent every unverified closed obligation inventory from native S4 CLOSE",
          "Invalid case, byte/commit/source change or fabricated independent gold must fail closed",
          "Analyze full W4A/B/C -> W5 all-layer A-E -> W6 true original 18/18 MVP dependencies",
          "No partial typed-logic success may promote semantic or original AC qualification"
       ],
       "state_keys":["v7_verified","native_pinned","typed_measured","root_dependencies"],
       "immutable_state_keys":[],
       "entry_nodes":["execute_root_original_v7"],
       "nodes":[
          node("execute_root_original_v7","action",writes=("v7_verified",),failure="blocked_integrity"),
          node("pin_new_native_source","action",depends=("execute_root_original_v7",),
               writes=("native_pinned",),failure="blocked_integrity"),
          node("execute_typed_public_semantics_and_no_false_closure","action",
               depends=("pin_new_native_source",),writes=("typed_measured",),
               failure="blocked_integrity"),
          node("audit_original_AC_MVP_and_dependencies","action",
               depends=("execute_typed_public_semantics_and_no_false_closure",),
               writes=("root_dependencies",),failure="blocked_integrity"),
          node("strict_original_exit","gate",depends=("audit_original_AC_MVP_and_dependencies",),
               reads=("v7_verified","native_pinned","typed_measured","root_dependencies"),
               branches={"root_verified":"verified_original_science",
                         "external_semantic_custody_missing":"blocked_external_semantics",
                         "original_AE_not_done":"blocked_original_AE"}),
          node("verified_original_science","terminal",terminal="SUCCESS"),
          node("blocked_external_semantics","terminal",terminal="BLOCKED"),
          node("blocked_original_AE","terminal",terminal="BLOCKED"),
          node("blocked_integrity","terminal",terminal="BLOCKED"),
       ]
    }

def run(tcc_root:Path,ec_old_v44:Path,native_v7:Path,native_v8:Path)->dict:
    need(git_head(tcc_root)==TCC_SOURCE,"TCC_SOURCE_NOT_FROZEN")
    need(CONTRACT.is_file() and json.loads(CONTRACT.read_text())["status"]=="SPEC_FROZEN_BEFORE_EXPERIMENT",
         "TYPED_EXPERIMENT_PREREGISTRATION_MISSING")
    sources_pin(native_v8)
    if str(tcc_root) not in sys.path:sys.path.insert(0,str(tcc_root))
    from tcc.core_v3 import validate_spec,normalize_spec,compile_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph,to_ecv4_evidence
    head=git_head(ROOT)
    spec=tcc_spec()
    ctx=context_for(spec,head)
    ctx.update(selected_issue_id="ISSUE-1",actionable_issue_ids=["ISSUE-1"],
               blocked_issue_ids=[],
               snapshot_id="ISSUE1-TCC8:"+head[:12],
               source_fingerprint="sha256:"+digest({"head":head,"spec":spec}))
    built=generate_tcc_from_context(ctx)
    need(built.get("result")=="tcc.spec.v3" and
         not validate_spec(built["spec"]) and
         built["spec"]==normalize_spec(spec),"TCC8_COMPILER_CONTRACT_DRIFT")
    graph=compile_spec(built["spec"])
    pre_raw=immutable_evidence_seal();pre_native=sources_pin(native_v8)
    pre_research=researcher_source_seal()
    pre_contract=hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    evidence={"errors":[]}

    def previous(_n,_state,_attempt):
        try:
            x=run_v7(tcc_root,ec_old_v44,native_v7)
            need(x["TCC_terminal"]=="blocked_W4_semantic_authority" and
                 x["original_scientifically_complete"] is False and
                 x["W4_to_original_MVP_dependency_matrix"]["MVP_scientifically_passed"]==2 and
                 x["evidence_integrity_failures"]==[],"ROOT_V7_ORIGINAL_AC_DRIFT")
            evidence["v7"]={"terminal":x["terminal"],
                           "MVP_AC_pass":2,
                           "native_W4A_cases":x["new_W4_native_source_test"]["four_author_exposed_fixtures"]}
        except Exception as exc:
            evidence["errors"].append("ROOT:"+type(exc).__name__+":"+str(exc)[:180])
            return {"status":"failure","evidence":["ROOT_V7_FAIL_CLOSED"]}
        return {"status":"success","writes":{"v7_verified":True},
                "evidence":["ROOT_MVP_18_AC_VERIFIED_OPEN_2_PASS","W4A_14_TESTS_4_ACTUAL_DEV"]}

    def check_new(_n,_state,_attempt):
        try:
            x=sources_pin(native_v8)
            evidence["pin"]=x
        except Exception as exc:
            evidence["errors"].append("SOURCE:"+type(exc).__name__+":"+str(exc)[:180])
            return {"status":"failure","evidence":["NATIVE_SOURCE_FAIL_CLOSED"]}
        return {"status":"success","writes":{"native_pinned":True},
                "evidence":["W4B_W4C_REAL_SOURCE_SHA_PINNED"]}

    def execute(_n,_state,_attempt):
        try:
            x=measure(native_v8)
            need(x["native_source_tests_passed"]==24 and
                 x["formal_invariant_cases_passed"]==12 and
                 x["S4_false_closure_preventions"]==12 and
                 x["undeclared_requirement_abstention_verified"],
                 "SCOPED_SOURCE_MECHANIC_EVALUATION_FAILED")
            need(pre_raw==immutable_evidence_seal() and
                 pre_native==sources_pin(native_v8) and
                 pre_research==researcher_source_seal() and
                 pre_contract==hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
                 "SCIENCE_CODE_OR_RAW_CHANGED_DURING_TCC")
            evidence["typed"]=x
        except Exception as exc:
            evidence["errors"].append("MODEL:"+type(exc).__name__+":"+str(exc)[:180])
            return {"status":"failure","evidence":["TYPED_CAUSAL_MECHANIC_FAIL_CLOSED"]}
        return {"status":"success","writes":{"typed_measured":True},
                "evidence":["NATIVE_TYPED_24_TESTS_PASS_12_FORMAL_PUBLIC_CASES_PASS",
                            "S4_FALSE_CLOSURE_12_OF_12_REJECTED"]}

    def audit(_n,_state,_attempt):
        try:
            typed=evidence["typed"]
            need(not typed["true_natural_language_semantic_adjudication"] and
                 not typed["independently_verified_complete_obligation_inventory"] and
                 not typed["original_A_E_all_layers_measured"],
                 "FALSE_INDEPENDENT_SCIENTIFIC_CREDENTIAL")
            nodes={
              "ORIGINAL_AC18":{"parents":[],"state":"2_OF_18_ORIGINAL_MVP_PASS"},
              "W4A_NATIVE_SET_AND_CLOSURE":{"parents":["ORIGINAL_AC18"],"state":"SCOPED_PASS_14"},
              "W4B_TYPED_LOGIC":{"parents":["W4A_NATIVE_SET_AND_CLOSURE"],"state":"BOUNDED_TYPED_PASS_24_PLUS_12"},
              "W4C_TYPED_INVENTORY_FAIL_CLOSED":{"parents":["W4B_TYPED_LOGIC"],"state":"UNTRUSTED_SELF_CLOSURE_REJECTED_12"},
              "W4B_INDEPENDENT_NATURAL_SEMANTICS":{"parents":["W4B_TYPED_LOGIC"],"state":"NOT_PROVEN"},
              "W4C_INDEPENDENT_EXHAUSTIVE_OBLIGATION_PROOF":{"parents":["W4C_TYPED_INVENTORY_FAIL_CLOSED"],"state":"NOT_PROVEN"},
              "W5_FOUR_LAYER_MATCHED_A_E":{"parents":["W4B_INDEPENDENT_NATURAL_SEMANTICS","W4C_INDEPENDENT_EXHAUSTIVE_OBLIGATION_PROOF"],"state":"BLOCKED_DEPENDENCIES"},
              "W6_ORIGINAL_18AC_MVP":{"parents":["W5_FOUR_LAYER_MATCHED_A_E"],"state":"NOT_CLOSED"},
            }
            visited=set()
            for name,v in nodes.items():
                need(set(v["parents"]).issubset(visited),"W4B_C_W5_AC_DAG_ORDER_INVALID")
                visited.add(name)
            evidence["dependencies"]=nodes
            need(pre_raw==immutable_evidence_seal() and
                 pre_native==sources_pin(native_v8) and
                 pre_research==researcher_source_seal() and
                 pre_contract==hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
                 "POST_SCORE_SOURCE_OR_DATA_TAMPER")
        except Exception as exc:
            evidence["errors"].append("AC:"+type(exc).__name__+":"+str(exc)[:180])
            return {"status":"failure","evidence":["AC18_FINAL_SCORE_FAIL_CLOSED"]}
        return {"status":"success","writes":{"root_dependencies":True},
                "evidence":["W4B_TYPED_DONE_W4C_FAILCLOSE_DONE",
                            "INDEPENDENT_SEMANTIC_AND_INVENTORY_W5_REQUIRED",
                            "NO_ORIGINAL_18AC_ROOT_COMPLETION"]}

    def decide(_n,state,_attempt):
        if not all(state.get(z) is True for z in ("v7_verified","native_pinned","typed_measured","root_dependencies")):
            return {"outcome":"original_AE_not_done","evidence":["NOT_ALL_GATES_VERIFIED"]}
        # No local authored document can prove independent semantic correctness,
        # and there are no actual whole-layer A-E interventions in this successor.
        return {"outcome":"external_semantic_custody_missing",
                "evidence":["W4B_LANGUAGE_SEMANTICS_AND_W4C_COMPLETENESS_INDEPENDENCE_MISSING"]}
    out=execute_graph(graph,{
         "execute_root_original_v7":previous,
         "pin_new_native_source":check_new,
         "execute_typed_public_semantics_and_no_false_closure":execute,
         "audit_original_AC_MVP_and_dependencies":audit,
         "strict_original_exit":decide,
    })
    need(out.get("result")=="TERMINAL" and out["terminal_id"] in (
         "verified_original_science","blocked_external_semantics",
         "blocked_original_AE","blocked_integrity"),"TCC8_INVALID_TERMINAL")
    need(out["terminal_id"]!="verified_original_science",
         "ROOT_MVP_FALSE_VERIFICATION")
    return {
      "protocol":PROTOCOL,"source_commit":head,"TCC_compiler_commit":TCC_SOURCE,
      "TCC_nodes":len(graph["nodes"]),"TCC_edges":len(graph["edges"]),
      "TCC_terminal_id":out["terminal_id"],
      "ECv4_handoff":to_ecv4_evidence(graph,out),
      "original_AC_MVP18_pass_count":2,
      "original_AC_MVP18_total":18,
      "verified_original":evidence.get("v7"),
      "new_actual_native_typed_public_evidence":evidence.get("typed"),
      "source_bound_W4B_W4C_W5_W6_dependency_DAG":evidence.get("dependencies"),
      "errors":evidence["errors"],
      "evidence_pre_post_equal":pre_raw==immutable_evidence_seal(),
      "native_source_pre_post_equal":pre_native==sources_pin(native_v8),
      "research_code_pre_post_equal":pre_research==researcher_source_seal(),
      "preregistered_contract_pre_post_equal":pre_contract==hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
      "independent_semantics_proven":False,
      "independent_complete_S4_inventory_proven":False,
      "original_four_layer_AE_run":False,
      "original_root_completed":False,
      "new_scheduled_tasks":False,
      "terminal":"VERIFIED_W4_TYPED_MECHANICS_EXTERNAL_NATURAL_SEMANTICS_AND_S4_COMPLETENESS_STILL_OPEN"
          if out["terminal_id"]=="blocked_external_semantics" else "INTEGRITY_OR_ORIGINAL_AE_BLOCK",
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--tcc-root",type=Path)
    ap.add_argument("--ec-root",type=Path)
    ap.add_argument("--v7-native-root",type=Path)
    ap.add_argument("--new-native-root",type=Path,required=True)
    ap.add_argument("--child-only",action="store_true")
    ap.add_argument("--public-payload",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    try:
        r=child_predict(a.new_native_root,a.public_payload) if a.child_only else run(
             a.tcc_root,a.ec_root,a.v7_native_root,a.new_native_root)
        text=json.dumps(r,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
        if a.out:
            a.out.write_text(text,encoding="utf-8")
            print(json.dumps({"terminal":r["terminal"],"AC_pass":r["original_AC_MVP18_pass_count"],
                              "tests":r["new_actual_native_typed_public_evidence"]["native_source_tests_passed"],
                              "typed_cases":r["new_actual_native_typed_public_evidence"]["public_new_typed_cases"]}))
        else:print(text,end="")
        return 0 if a.child_only or r["original_root_completed"] else 2
    except Exception as exc:
        print(json.dumps({"terminal":"INTEGRITY_FAIL_CLOSED",
                          "error":type(exc).__name__+":"+str(exc)[:300]}),
              file=sys.stderr if a.child_only else sys.stdout)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
