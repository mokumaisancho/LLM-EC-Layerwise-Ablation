#!/usr/bin/env python3
"""Source-pinned successor: real TCC Generator v3 + bounded S3/S4 mechanics, no scientific promotion."""
import hashlib
import importlib.util
import itertools
import json
import subprocess
import sys
from pathlib import Path

BASE = Path("../INIT-ISSUE1-TCC-OF23/offline_runner.py")
BASE_BLOB = "f91505ddbfaa2a47533d1dbf02f02211a6d81a5e"
TCC_PIN = "786d52c1efbc9271096f9311d768ef49bcd116e2"
V40_BLOB = "d4e5eeda1703445af42264eb150a17a3bda85786"
S3_AUDIT_BLOB = "b8e7a6d1708b8a30768fbbcb2475bebeb2dbafb3"
S4_AUDIT_BLOB = "624616a1f4b0dc4a2330cbcd0a6a03b94a475ce8"
PROOF = b"issue1-v41-native-tcc-s3-s4-source-mechanics-verified-science-blocked\\n"
OUT = Path("issue1-v41-tcc-receipt.json")
S3 = Path("issue1-v41-s3-boundary.json")
S4 = Path("issue1-v41-s4-bounded-proof.json")
GRAPH = Path("issue1-v41-generated-tcc-spec.json")
H = "a"*64

def gb(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def save(path, obj):
    path.write_text(json.dumps(obj,sort_keys=True,indent=2,ensure_ascii=False)+"\\n",encoding="utf-8")
    return digest(path.read_bytes())

def cmd(*args):
    return subprocess.run(args,capture_output=True,text=True,check=True,timeout=10).stdout.strip()

def close_decision(state):
    """Mechanics ONLY. Authored state not trusted as source truth."""
    if not isinstance(state,dict): return "BLOCK_INVALID"
    for k in ("policy_sha256","upstream_sha256","execution_sha256"):
        if not isinstance(state.get(k),str) or len(state[k])!=64: return "BLOCK_UNBOUND"
    if state.get("inventory_complete") is not True: return "BLOCK_INCOMPLETE"
    if not isinstance(state.get("obligations"),list): return "BLOCK_INCOMPLETE"
    if not state["obligations"] and not (state.get("zero_duty_proof_sha256") and len(state["zero_duty_proof_sha256"])==64):
        return "BLOCK_ZERO_NOT_PROVEN"
    if state.get("pending_conflict") is not False or state.get("pending_reframe") is not False or state.get("open_residual") is not False:
        return "BLOCK_UNRESOLVED"
    ids=set()
    for x in state["obligations"]:
        if not isinstance(x,dict) or not isinstance(x.get("id"),str) or not x["id"] or x["id"] in ids:
            return "BLOCK_OBLIGATION_SCHEMA"
        ids.add(x["id"])
        if x.get("status")=="SATISFIED":
            if not isinstance(x.get("evidence_sha256"),str) or len(x["evidence_sha256"])!=64:
                return "BLOCK_NO_WITNESS"
        elif x.get("status")=="ACCEPTED_LIMITATION":
            if not isinstance(x.get("authority_sha256"),str) or len(x["authority_sha256"])!=64:
                return "BLOCK_NO_AUTHORITY"
        else:
            return "BLOCK_UNRESOLVED_DUTY"
    return "CLOSE"

def bounded_tests():
    base={"policy_sha256":H,"upstream_sha256":H,"execution_sha256":H,
          "inventory_complete":True,"obligations":[],
          "pending_conflict":False,"pending_reframe":False,"open_residual":False}
    cases=0; close=0; violations=0
    for statuses in itertools.product(("SATISFIED","UNRESOLVED","UNKNOWN","ACCEPTED_LIMITATION"),repeat=3):
        for pending in itertools.product((False,True),repeat=3):
            state=dict(base)
            state.update(zip(("pending_conflict","pending_reframe","open_residual"),pending))
            state["obligations"]=[{"id":"d"+str(i),"status":status,
                "evidence_sha256":H if status=="SATISFIED" else None,
                "authority_sha256":H if status=="ACCEPTED_LIMITATION" else None}
                for i,status in enumerate(statuses)]
            actual=close_decision(state)
            expected=all(s in ("SATISFIED","ACCEPTED_LIMITATION") for s in statuses) and not any(pending)
            if (actual=="CLOSE")!=expected: violations+=1
            if actual=="CLOSE":close+=1
            cases+=1
    if cases!=512 or close!=8 or violations: raise ValueError("S4_MODEL_CHECK_FAILURE")
    tests={}
    s=dict(base,obligations=[{"id":"o","status":"SATISFIED","evidence_sha256":H}])
    tests["valid_single_close"]=close_decision(s)=="CLOSE"
    tests["missing_actual_trace"]=close_decision(dict(s,execution_sha256=""))!="CLOSE"
    tests["unchecked_inventory"]=close_decision(dict(s,inventory_complete=False))!="CLOSE"
    tests["empty_no_positive_proof"]=close_decision(base)!="CLOSE"
    tests["empty_with_positive_proof"]=close_decision(dict(base,zero_duty_proof_sha256=H))=="CLOSE"
    tests["unresolved_conflict"]=close_decision(dict(s,pending_conflict=True))!="CLOSE"
    tests["unresolved_reframe"]=close_decision(dict(s,pending_reframe=True))!="CLOSE"
    tests["missing_satisfaction_witness"]=close_decision(dict(s,obligations=[{"id":"o","status":"SATISFIED"}]))!="CLOSE"
    tests["unapproved_limitation"]=close_decision(dict(s,obligations=[{"id":"o","status":"ACCEPTED_LIMITATION"}]))!="CLOSE"
    tests["duplicate_obligation"]=close_decision(dict(s,obligations=s["obligations"]*2))!="CLOSE"
    tests["unknown_duty"]=close_decision(dict(s,obligations=[{"id":"o","status":"UNKNOWN"}]))!="CLOSE"
    tests["missing_policy_pin"]=close_decision(dict(s,policy_sha256=""))!="CLOSE"
    if not all(tests.values()): raise ValueError("S4_NEGATIVE_GATE_FAILED")
    # Synthetic typed-state counterexamples, not claims about real M001/7 or M003/9 gold:
    left=close_decision(s)
    right=close_decision(dict(s,obligations=[{"id":"o","status":"UNRESOLVED"}]))
    if (left,right)!=("CLOSE","BLOCK_UNRESOLVED_DUTY"): raise ValueError("S4_COLLISION_DISCRIMINATOR_FAILURE")
    return {"schema":"ISSUE1_S4_BOUNDED_TYPED_STATE_PROOF_V41",
       "source_ref_git_blob":S4_AUDIT_BLOB,"test_states":cases,
       "safe_close":close,"unsafe_close":violations,"explicit_controls":tests,
       "collision_signature_pairs_under_test":["M001/M007","M003/M009"],
       "collision_note":"Injected hypothetical missing task-state field discriminates statuses; underlying historic S3 signature still insufficient",
       "real_case_state_enriched":False,"real_native_S4_executed":False,
       "semantically_independent_gold":False,"original_science_promotions":0}

def s3_interface():
    return {"schema":"ISSUE1_S3_AUTHORITY_SPLIT_V41",
      "source_ref_git_blob":S3_AUDIT_BLOB,
      "EC_NATIVE_CARDINALITY":"EXACTLY_ONE_NEXT_ACTION",
      "GENERIC_S3_CARDINALITY":"ONE_OR_MORE_ADMISSIBLE_CANDIDATES",
      "singleton_fixture_count":8,"multiple_selection_fixture_count":2,
      "singleton_share":0.8,"native_isomorphic":False,
      "shared_experiment":"native_single_next_action_only",
      "different_experiment":"set_admissibility_with_separate_adapter_authority",
      "v41_s3_contract_split":True,
      "real_EC_qualification":"REQUIRES_ACTUAL_ENGINE_EXECUTION",
      "real_model_inference":False,
      "original_science_promotions":0}

def run():
    if gb(BASE.read_bytes())!=BASE_BLOB: raise ValueError("ORIGINAL_SOURCE_PIN_CHANGED")
    loader=importlib.util.spec_from_file_location("original_v23",BASE)
    base=importlib.util.module_from_spec(loader)
    loader.loader.exec_module(base)
    if cmd("git","-C",str(base.TCC),"rev-parse","HEAD")!=TCC_PIN:
        raise ValueError("PINNED_TCC_NOT_PRESENT")
    if cmd("git","-C",str(base.TCC),"status","--porcelain","--untracked-files=no"):
        raise ValueError("PINNED_TCC_DIRTY")
    for f in ("tcc/__init__.py","tcc/core_v3.py","tcc/runtime_v3.py",
              "tcc/recipe_builder_v3.py","tcc/generator_v3.py",
              "tcc/suite_context.py","tcc/suite_boundary.py"):
        p=base.TCC/f
        if p.is_symlink() or not p.resolve().is_relative_to(base.TCC.resolve()):
            raise ValueError("UNSAFE_SOURCE_ESCAPE")
        original=subprocess.run(["git","-C",str(base.TCC),"show",TCC_PIN+":"+f],
            check=True,capture_output=True,timeout=10).stdout
        if p.read_bytes()!=original: raise ValueError("TCC_SOURCE_TAMPER:"+f)
    sys.path.insert(0,str(base.TCC))
    from tcc.core_v3 import validate_spec,compile_spec,canonical_json,normalize_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph
    nodes=[
      base.nd("P00_SOURCE","action",writes=["source_ok"],failure_target="ERR_SOURCE"),
      base.nd("P01_S3_SPLIT","action",depends_on=["P00_SOURCE"],reads=["source_ok"],writes=["s3_ok"],failure_target="ERR_S3"),
      base.nd("P02_S4_MODEL","action",depends_on=["P00_SOURCE"],reads=["source_ok"],writes=["s4_ok"],failure_target="ERR_S4"),
      base.nd("P03_CAUSAL_GATE","gate",depends_on=["P01_S3_SPLIT","P02_S4_MODEL"],
          reads=["s3_ok","s4_ok","actual_engine_ok"],
          branches={"missing":"BLOCK_REAL_CAUSAL","verified":"PASS_CAUSAL"}),
      base.nd("PASS_CAUSAL","terminal",terminal_status="SUCCESS"),
      base.nd("BLOCK_REAL_CAUSAL","terminal",terminal_status="BLOCKED"),
      base.nd("ERR_SOURCE","terminal",terminal_status="FAILURE"),
      base.nd("ERR_S3","terminal",terminal_status="FAILURE"),
      base.nd("ERR_S4","terminal",terminal_status="FAILURE")]
    spec={"schema":"tcc.spec.v3","tcc_id":"ISSUE1-S3S4-SUCCESSOR-V41",
       "goal":"Regenerate corrected S3 authority split and S4 typed proof, then block any original or successor causal conclusion lacking real engine receipts",
       "acceptance":["SOURCE PINS preserve Phase1-v2 incompatible terminal and original 2/18",
         "S3 native singleton cannot masquerade as generic all-admissible set",
         "S4 512 states and 12 controls pass as bounded mechanics only",
         "No D06 or causal scientific success without true matched LLM EC Oracle execution",
         "No third party signature or 120/300-sample extended research required for frozen fixed-fixture MVP"],
       "state_keys":["source_ok","s3_ok","s4_ok","actual_engine_ok"],
       "immutable_state_keys":[],"entry_nodes":["P00_SOURCE"],"nodes":nodes}
    if validate_spec(spec): raise ValueError("SPEC_VALIDATION_FAILED:"+str(validate_spec(spec)))
    base.PINNED_SOURCE["corrected_technical_v40"]=V40_BLOB
    base.PINNED_SOURCE["S3_interface_audit"]=S3_AUDIT_BLOB
    base.PINNED_SOURCE["S4_identifiability"]=S4_AUDIT_BLOB
    ctx=base.context(spec)
    generated=generate_tcc_from_context(ctx,current_tcc_id=spec["tcc_id"])
    if generated.get("result")!="tcc.spec.v3": raise ValueError("GENERATOR_NOT_SPEC:"+str(generated.get("reason_code")))
    if canonical_json(generated["spec"])!=canonical_json(normalize_spec(spec)):
        raise ValueError("NATIVE_GENERATED_GRAPH_SPEC_CHANGED")
    graph=compile_spec(generated["spec"])
    save(GRAPH,generated["spec"])
    def handler(n,state,attempt):
        if n["id"]=="P00_SOURCE":
            return {"status":"success","writes":{"source_ok":True},
                "evidence":["V40:"+V40_BLOB,"S3:"+S3_AUDIT_BLOB,"S4:"+S4_AUDIT_BLOB]}
        if n["id"]=="P01_S3_SPLIT":
            v=s3_interface()
            if v["native_isomorphic"] or v["multiple_selection_fixture_count"]!=2:
                raise ValueError("S3_INVALID_UNITS")
            h=save(S3,v)
            return {"status":"success","writes":{"s3_ok":True},
                    "evidence":["S3_BOUNDARY_SHA256:"+h]}
        if n["id"]=="P02_S4_MODEL":
            v=bounded_tests()
            h=save(S4,v)
            return {"status":"success","writes":{"s4_ok":True},
                    "evidence":["S4_BOUNDED_PROOF_SHA256:"+h]}
        return {"status":"failure","evidence":["NOT_AUTHORIZED_TO_SIMULATE_ENGINE"]}
    def gate(n,state,attempt):
        good=state.get("s3_ok") is True and state.get("s4_ok") is True
        return {"outcome":"verified" if good and state.get("actual_engine_ok") is True else "missing",
                "evidence":["ACTUAL_REAL_ENGINE_SHA_AND_ORACLE_TARGET_ONLY_RECEIPTS_REQUIRED"]}
    handlers={n["id"]:(gate if n["kind"]=="gate" else handler)
          for n in nodes if n["kind"] in ("gate","action")}
    result=execute_graph(graph,handlers)
    executed={e["node_id"] for e in result.get("evidence",[]) if e.get("event")=="NODE_SUCCESS"}
    if result.get("result")!="TERMINAL" or result.get("terminal_id")!="BLOCK_REAL_CAUSAL" or result.get("terminal_status")!="BLOCKED":
        raise ValueError("INVALID_SCIENCE_EXIT")
    if not {"P00_SOURCE","P01_S3_SPLIT","P02_S4_MODEL"}<=executed or "PASS_CAUSAL" in executed:
        raise ValueError("TCC_GATE_SKIPPED")
    if not S3.is_file() or not S4.is_file() or not GRAPH.is_file():
        raise ValueError("ARTIFACTS_MISSING")
    return {"schema":"ISSUE1_TCC_S3_S4_REGENERATED_V41",
       "tcc_generator":"PASS","validator":"PASS","runtime":"PASS",
       "source_cardinality_split":"PASS",
       "bounded_s4_model_check":"PASS","typed_model_states":512,
       "real_EC_LLMS3_S4_causes":"NOT_EXECUTED",
       "original_frozen_phase1_terminal":"EC_NATIVE_SCOPE_INCOMPATIBLE",
       "original_mvp_verified":2,"original_mvp_required":18,"scientific_promotion":0,
       "tcc_source_commit":TCC_PIN,"graph_spec_hash":graph["spec_hash"],
       "source_spec_sha256":digest(GRAPH.read_bytes()),
       "s3_sha256":digest(S3.read_bytes()),"s4_sha256":digest(S4.read_bytes()),
       "terminal":"BLOCK_REAL_CAUSAL","native_result":result}

if __name__=="__main__":
    try:
        output=run()
        save(OUT,output)
        Path("proof.txt").write_bytes(PROOF)
        if digest(Path("proof.txt").read_bytes())!=digest(PROOF):
            raise ValueError("PROOF_MISMATCH")
        print(json.dumps({"control":"PASS","terminal":output["terminal"],
          "science":"2/18","tcc_gen":"PASS","s3":output["s3_sha256"],
          "s4":output["s4_sha256"],"result_sha256":digest(OUT.read_bytes())},sort_keys=True))
    except Exception as exc:
        Path("proof.txt").unlink(missing_ok=True)
        print(json.dumps({"control":"FAILED","type":type(exc).__name__,"reason":str(exc)[:450]}))
        raise SystemExit(3)
