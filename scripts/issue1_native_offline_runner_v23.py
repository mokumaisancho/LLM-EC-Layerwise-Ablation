#!/usr/bin/env python3
"""Offline Issue #1 native TCC v3 control experiment. No GitHub API, no model calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PIN = "786d52c1efbc9271096f9311d768ef49bcd116e2"
TCC = Path.home() / "Library/Application Support/InitiativeDispatcher/tcc-compiler"
PROOF = b"issue1-offline-native-tcc-blocked-external-2026-10-14\n"
OUT = Path("native-control-result.json")
MARK = Path("proof.txt")
PINNED_SOURCE = {
    "original_ac": "40e4d41914fb17ee5c7deb0cfd32276a41c9a1fc",
    "original_protocol": "08407bec73278aeda8ddd2d4d6efc810dadf46f9",
    "issue1_tracker": "56bd5ac25d47e1dd9e8ea9da6193679656b661f5",
    "publisher_diagnostic": "a78df93af631f07b284dc3c8c74594f6989fbb6b",
}
FIELDS = ("id","kind","depends_on","reads","writes","branches","failure_target",
          "destructive","rollback","idempotent","max_attempts","retry_guard",
          "terminal_status","join_gate","join_inputs","compensation_actions",
          "rollback_order","compensated_target","loop_max_iterations",
          "loop_exhausted_target")

def nd(id, kind, **patch):
    a = dict(id=id,kind=kind,depends_on=[],reads=[],writes=[],branches={},
             failure_target=None,destructive=False,rollback=None,idempotent=True,
             max_attempts=1,retry_guard=None,terminal_status=None,join_gate=None,
             join_inputs={},compensation_actions=[],rollback_order=[],
             compensated_target=None,loop_max_iterations=None,loop_exhausted_target=None)
    a.update(patch)
    return a

def spec():
    nodes = [
        nd("D00_PINS","action",writes=["source_ok"],failure_target="ERR_D00"),
        nd("D04_S3","action",depends_on=["D00_PINS"],reads=["source_ok"],
           writes=["d04_ok"],failure_target="ERR_D04"),
        nd("D05_S4","action",depends_on=["D04_S3"],reads=["source_ok"],
           writes=["d05_ok"],failure_target="ERR_D05"),
        nd("INDEPENDENCE","gate",depends_on=["D05_S4"],reads=["d04_ok","d05_ok"],
           branches={"blocked":"BLOCK_EXTERNAL","qualified":"D06_REAL"}),
        nd("D06_REAL","action",writes=["d06_ok"],failure_target="ERR_D06"),
        nd("D07_REAL","action",depends_on=["D06_REAL"],reads=["d06_ok"],
           writes=["d07_ok"],failure_target="ERR_D07"),
        nd("D08_REAL","action",depends_on=["D07_REAL"],reads=["d07_ok"],
           writes=["d08_ok"],failure_target="ERR_D08"),
        nd("D09_REAL","action",depends_on=["D08_REAL"],reads=["d08_ok"],
           writes=["science_success"],failure_target="ERR_D09"),
        nd("PASS_ROOT","terminal",depends_on=["D09_REAL"],terminal_status="SUCCESS"),
        nd("BLOCK_EXTERNAL","terminal",terminal_status="BLOCKED"),
    ] + [nd("ERR_"+x,"terminal",terminal_status="FAILURE") for x in
         ("D00","D04","D05","D06","D07","D08","D09")]
    return {"schema":"tcc.spec.v3","tcc_id":"ISSUE1-OFFLINE-CTRL-V22",
            "goal":"One real native TCC Generator/Runtime exercise without promoting original science",
            "acceptance":["18 original MVP AC remain fixed; science 2/18",
                          "do not enter D06-D09 without independent S3+S4 attestation",
                          "finite BLOCKED_EXTERNAL and real native TCC execution"],
            "state_keys":["source_ok","d04_ok","d05_ok","d06_ok","d07_ok","d08_ok","science_success"],
            "immutable_state_keys":[],"entry_nodes":["D00_PINS"],"nodes":nodes}

def sha(x):
    return "sha256:"+hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),
                                             ensure_ascii=False).encode()).hexdigest()

def context(spec):
    fields = ["tcc_id","goal","acceptance","state_keys","immutable_state_keys","entry_nodes"]
    pairs = [("/"+k,spec[k]) for k in fields]
    for n in spec["nodes"]:
        tag=n["id"].replace("~","~0").replace("/","~1")
        pairs.extend((f"/nodes/{tag}/{k}",n[k]) for k in FIELDS)
    facts=[{"fact_id":"fixed:"+hashlib.sha256(p.encode()).hexdigest()[:20],
            "path":p,"value":v,"evidence_refs":["ev:offline-pinned-previously-audited"]}
           for p,v in pairs]
    f=sha({"spec":spec,"pinned_source":PINNED_SOURCE})
    return {"schema":"suite.tcc-context.v0","snapshot_id":"ISSUE1-OFFLINE-V22",
            "source_fingerprint":f,"base_source_fingerprint":f,
            "annotation_basis_fingerprint":f,"selected_issue_id":"ISSUE-1",
            "actionable_issue_ids":["ISSUE-1"],"blocked_issue_ids":[],
            "discovered_issues":[],"blocked_nodes":[],
            "evidence_refs":["ev:offline-pinned-previously-audited"],
            "ordering_rule":None,"ordering_rule_refs":[],"ordering_scope_issue_ids":[],
            "cross_issue_effects":[],"resource_conflicts":[],"resource_policy":None,
            "resource_policy_refs":[],"acceptance_couplings":[],
            "normalization_complete":True,"scope_expanded":False,
            "evidence_sufficient":True,"undeclared_judgment":False,
            "decision_needed":"control-only, no ECv4 scientific authority",
            "negative_assertion_refs":{k:["ev:offline-pinned-previously-audited"]
                for k in ["cross_issue_effects","resource_conflicts","acceptance_couplings",
                          "scope_expanded","undeclared_judgment"]},
            "semantic_facts":facts}

def cmd(*args):
    return subprocess.run(args,capture_output=True,text=True,check=True,timeout=10).stdout.strip()

def go():
    if not TCC.is_dir() or cmd("git","-C",str(TCC),"rev-parse","HEAD")!=PIN:
        raise ValueError("PINNED_TCC_HOST_CHECKOUT_MISSING_OR_DRIFT")
    if cmd("git","-C",str(TCC),"status","--porcelain","--untracked-files=no"):
        raise ValueError("TCC_TRACKED_WORKTREE_DIRTY")
    for path in ("tcc/__init__.py","tcc/core_v3.py","tcc/runtime_v3.py",
                 "tcc/recipe_builder_v3.py","tcc/generator_v3.py",
                 "tcc/suite_context.py","tcc/suite_boundary.py"):
        local=(TCC/path)
        if local.is_symlink() or not local.resolve().is_relative_to(TCC.resolve()):
            raise ValueError("TCC_SOURCE_ESCAPE")
        expected=subprocess.run(["git","-C",str(TCC),"show",PIN+":"+path],
                                capture_output=True,check=True,timeout=10).stdout
        if local.read_bytes()!=expected:
            raise ValueError("TCC_UPSTREAM_SOURCE_TAMPER:"+path)
    sys.path.insert(0,str(TCC))
    from tcc.core_v3 import validate_spec,compile_spec,canonical_json,normalize_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph
    s=spec()
    errors=validate_spec(s)
    if errors: raise ValueError("NATIVE_VALIDATOR:"+",".join(errors))
    gen=generate_tcc_from_context(context(s),current_tcc_id=s["tcc_id"])
    if gen.get("result")!="tcc.spec.v3": raise ValueError("NATIVE_GENERATOR:"+str(gen.get("reason_code")))
    if canonical_json(gen["spec"])!=canonical_json(normalize_spec(s)):
        raise ValueError("GENERATED_SPEC_DRIFT")
    graph=compile_spec(gen["spec"])
    def handler(node,state,attempt):
        if node["id"]=="D00_PINS":
            return {"status":"success","writes":{"source_ok":True},
                    "evidence":["offline-source-pins-from-prior-connector-audit"]}
        if node["id"]=="D04_S3":
            return {"status":"success","writes":{"d04_ok":False},
                    "evidence":["no-independent-S3-heldout-gold"]}
        if node["id"]=="D05_S4":
            return {"status":"success","writes":{"d05_ok":False},
                    "evidence":["no-independent-exhaustive-S4-policy-obligations"]}
        return {"status":"failure","evidence":["REAL_CAUSAL_EXECUTOR_NOT_BOUND"]}
    def gate(node,state,attempt):
        return {"outcome":"qualified" if state.get("d04_ok") is True and state.get("d05_ok") is True
                else "blocked","evidence":["fail-closed-independent-authority"]}
    handlers={n["id"]:(gate if n["kind"]=="gate" else handler)
              for n in s["nodes"] if n["kind"] in ("gate","action")}
    actual=execute_graph(graph,handlers)
    if (actual.get("result")!="TERMINAL" or actual.get("terminal_id")!="BLOCK_EXTERNAL"
        or actual.get("terminal_status")!="BLOCKED" or actual.get("ecv4_closure")!="NOT_DECIDED"
        or any(x.get("node_id","").startswith(("D06","D07","D08","D09"))
               for x in actual.get("evidence",[]))):
        raise ValueError("NATIVE_RUNTIME_SCIENCE_GATE_INVALID")
    return {"control":"PASS","scientific":"BLOCKED_EXTERNAL","scientific_ac_passed":2,
            "scientific_ac_required":18,"scientific_ac_promoted":0,
            "evidence_basis":"historical GitHub verified pins, NOT fresh unseen gold",
            "pinned_evidence":PINNED_SOURCE,"tcc_pin":PIN,"actual_generator":"tcc.spec.v3",
            "actual_runtime":actual,"graph_spec_hash":graph["spec_hash"]}

if __name__=="__main__":
    try:
        report=go()
        OUT.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
        MARK.write_bytes(PROOF)
        assert hashlib.sha256(MARK.read_bytes()).digest()==hashlib.sha256(PROOF).digest()
        print(json.dumps({"control":"PASS","scientific":"BLOCKED_EXTERNAL",
                          "result_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
                          "proof_sha256":hashlib.sha256(PROOF).hexdigest()}))
    except Exception as exc:
        MARK.unlink(missing_ok=True)
        OUT.write_text(json.dumps({"control":"BLOCKED","error_type":type(exc).__name__,
             "error":str(exc)[:500],"scientific":"OPEN","scientific_ac_passed":2},
             sort_keys=True)+"\n")
        print(json.dumps({"control":"BLOCKED","error_type":type(exc).__name__,
                          "error":str(exc)[:500]}))
        raise SystemExit(3)
