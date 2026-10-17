#!/usr/bin/env python3
"""Real source-pinned native TCC v3 D04/D05 parallel intake. No inference or gold creation."""
import hashlib, importlib.util, json, subprocess, sys
from pathlib import Path

SOURCE = Path("../INIT-ISSUE1-TCC-OF23/offline_runner.py")
TCC_PIN = "786d52c1efbc9271096f9311d768ef49bcd116e2"
PUBLISHER_PACKET_BLOB = "5bbab248b0d5ef74f92a7117898eb4acb1aa4c2a"
BASE_BLOB = "f91505ddbfaa2a47533d1dbf02f02211a6d81a5e"
PROOF = b"issue1-tcc-v27-d04-d05-evidence-intake-blocked-external\n"
REPORT = Path("d04-d05-native-runtime-receipt.json")
D04 = Path("d04-independent-gold-request.json")
D05 = Path("d05-independent-policy-review-request.json")
SEVEN = {
 "airline/0": ["Agent should refuse to proceed with the cancellation."],
 "airline/10": ["Check that Agent does not offer to change cabin for only some of the flights in a reservation."],
 "airline/26": ["Agent does not offer the refund because reservation doesn't meet policy criteria."],
 "airline/28": ["Agent does not cancel flight.", "Agent does not offer any refund."],
 "airline/31": ["Agent doesn't book any flight."],
 "airline/34": ["Agent should not make any changes."],
 "airline/46": ["Agent does not cancel insurance or offer a refund."]
}
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def git(*args):
    return subprocess.run(["git",*args],check=True,text=True,capture_output=True,timeout=10).stdout.strip()
def write(path,value):
    path.write_text(json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+"\n")
    return sha(path.read_bytes())
def run():
    if blob(SOURCE.read_bytes()) != BASE_BLOB:
        raise ValueError("PINNED_PREDECESSOR_MISMATCH")
    spec=importlib.util.spec_from_file_location("issue1_v23",SOURCE)
    base=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    if git("-C",str(base.TCC),"rev-parse","HEAD")!=TCC_PIN:
        raise ValueError("PINNED_TCC_HEAD_MISMATCH")
    if git("-C",str(base.TCC),"status","--porcelain","--untracked-files=no"):
        raise ValueError("PINNED_TCC_DIRTY")
    for path in ("tcc/__init__.py","tcc/core_v3.py","tcc/runtime_v3.py",
                 "tcc/recipe_builder_v3.py","tcc/generator_v3.py",
                 "tcc/suite_context.py","tcc/suite_boundary.py"):
        actual=(base.TCC/path)
        if actual.is_symlink() or not actual.resolve().is_relative_to(base.TCC.resolve()):
            raise ValueError("PINNED_TCC_SOURCE_ESCAPE")
        original=subprocess.run(["git","-C",str(base.TCC),"show",TCC_PIN+":"+path],
             check=True,capture_output=True,timeout=10).stdout
        if actual.read_bytes()!=original:
            raise ValueError("PINNED_TCC_SOURCE_TAMPER:"+path)
    base.PINNED_SOURCE["full_publisher_review_packet"]=PUBLISHER_PACKET_BLOB
    sys.path.insert(0,str(base.TCC))
    from tcc.core_v3 import validate_spec,compile_spec,normalize_spec,canonical_json
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph
    s=base.spec()
    s["tcc_id"]="ISSUE1-D04-D05-PARALLEL-INTAKE-V27"
    s["goal"]="Create source-pinned independent S3/S4 adjudication requests via real native TCC generator without claiming gold exists"
    for node in s["nodes"]:
        if node["id"]=="D05_S4": node["depends_on"]=["D00_PINS"]
        if node["id"]=="INDEPENDENCE": node["depends_on"]=["D04_S3","D05_S4"]
    if validate_spec(s): raise ValueError("NEW_SPEC_INVALID:"+str(validate_spec(s)))
    generated=generate_tcc_from_context(base.context(s),current_tcc_id=s["tcc_id"])
    if generated.get("result")!="tcc.spec.v3":
        raise ValueError("NATIVE_GENERATOR_FAILED:"+str(generated.get("reason_code")))
    if canonical_json(generated["spec"])!=canonical_json(normalize_spec(s)):
        raise ValueError("NATIVE_GENERATED_SPEC_DRIFT")
    graph=compile_spec(generated["spec"])
    def handler(node,state,attempt):
        name=node["id"]
        if name=="D00_PINS":
            return {"status":"success","writes":{"source_ok":True},
                    "evidence":["pinned-host-TCC","publisher-task-blob-a18c17a1619ab1b78370ac0bc5f0e4df46cff5b9","packet-"+PUBLISHER_PACKET_BLOB]}
        if name=="D04_S3":
            h=write(D04,{"schema":"ISSUE1_D04_INDEPENDENT_HOLDOUT_REQUEST_V27",
                "parent_issue":59,"source_of_truth":"NOT_YET_QUALIFIED",
                "required":["genuinely unseen case inputs with provenance and creation date",
                    "heldout frozen before evaluated models and EC see inputs",
                    "all-admissible candidate decisions and source-grounded rationales",
                    "S1/S2 per-case SHA binding","third-party assessor and custody attestation",
                    "no gold in predictor runtime","competing/equivalent counterfactual controls"],
                "independent_gold_rows":None,"third_party_attestation":None,
                "scientific_ac_promotion":0,"status":"BLOCKED_EXTERNAL"})
            return {"status":"success","writes":{"d04_ok":False},
                    "evidence":["D04_SOURCE_BOUND_INTAKE_SHA256:"+h]}
        if name=="D05_S4":
            if len(SEVEN)!=7: raise ValueError("RISK_CASE_COUNT_DRIFT")
            h=write(D05,{"schema":"ISSUE1_D05_POLICY_ADJUDICATION_REQUEST_V27",
                "parent_issue":60,"full_publisher_review_packet_git_blob":PUBLISHER_PACKET_BLOB,
                "publisher_commit":"864350a8971a8f8ee9e7b8472e2edc380a806b0c",
                "publisher_policy_blob":"8098be7db3f47de943fad39d1e057ede6cc6cd04",
                "cases":[{"case_id":case,"original_assertions":assertions,
                    "all_policy_lines_inspected":False,
                    "applicable_mandatory_clauses":None,
                    "complete_residuals":None,"independent_assessor":None,
                    "empty_set_proof":None,"NL_ASSERTION_in_scoring":False,
                    "real_agent_scored":False,"authoritative_close":False}
                    for case,assertions in sorted(SEVEN.items())],
                "followup_after_seven":"remaining 51 NL cases, then 106 with no published NL assertions",
                "full_policy_lines_in_git_packet":167,"source_policy_read_required":True,
                "scientific_ac_promotion":0,"status":"BLOCKED_EXTERNAL"})
            return {"status":"success","writes":{"d05_ok":False},
                    "evidence":["D05_SEVEN_CASE_REVIEW_QUEUE_SHA256:"+h]}
        return {"status":"failure","evidence":["DOWNSTREAM_SCIENCE_UNAUTHORIZED"]}
    def gate(node,state,attempt):
        return {"outcome":"qualified" if state.get("d04_ok") is True and state.get("d05_ok") is True else "blocked",
                "evidence":["independent-semantic-and-obligation-authority-failclosed"]}
    handlers={n["id"]:(gate if n["kind"]=="gate" else handler)
              for n in s["nodes"] if n["kind"] in ("action","gate")}
    result=execute_graph(graph,handlers)
    visited=[e["node_id"] for e in result.get("evidence",[]) if e.get("event")=="NODE_SUCCESS"]
    if result.get("result")!="TERMINAL" or result.get("terminal_id")!="BLOCK_EXTERNAL" or result.get("ecv4_closure")!="NOT_DECIDED":
        raise ValueError("UNEXPECTED_SCIENTIFIC_TERMINAL")
    if not {"D00_PINS","D04_S3","D05_S4"}<=set(visited) or any(x in visited for x in ["D06_REAL","D07_REAL","D08_REAL","D09_REAL"]):
        raise ValueError("INCORRECT_CRITICAL_PATH_EXECUTION")
    if not D04.exists() or not D05.exists(): raise ValueError("MISSING_CRITICAL_PATH_ARTIFACT")
    return {"native_tcc_generator":"PASS","native_tcc_validator":"PASS",
        "native_tcc_runtime":"PASS","executed_nodes":visited,
        "D04_independent_gold":"BLOCKED_EXTERNAL","D05_complete_policy_obligations":"BLOCKED_EXTERNAL",
        "D04_request_sha256":sha(D04.read_bytes()),"D05_request_sha256":sha(D05.read_bytes()),
        "original_mvp_proven":2,"original_mvp_required":18,"original_science_ac_promoted":0,
        "TCC_upstream":TCC_PIN,"publisher_packet_blob":PUBLISHER_PACKET_BLOB,
        "graph_spec_hash":graph["spec_hash"],"terminal":"BLOCK_EXTERNAL",
        "runtime":result}
if __name__=="__main__":
    try:
        evidence=run()
        write(REPORT,evidence)
        Path("proof.txt").write_bytes(PROOF)
        if sha(Path("proof.txt").read_bytes()) != sha(PROOF): raise ValueError("PROOF_DRIFT")
        print(json.dumps({"control":"PASS","science":"BLOCKED_EXTERNAL",
            "report_sha256":sha(REPORT.read_bytes()),"D04_sha256":evidence["D04_request_sha256"],
            "D05_sha256":evidence["D05_request_sha256"]},sort_keys=True))
    except Exception as e:
        Path("proof.txt").unlink(missing_ok=True)
        print(json.dumps({"control":"FAILED","exception_type":type(e).__name__,"error":str(e)[:500]}))
        raise SystemExit(3)
