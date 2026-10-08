#!/usr/bin/env python3
"""#56 actual pinned SUITE and ECv4 source audit. Fully offline, fail closed."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VENDOR=ROOT/"verification/issue55"
SUITE=VENDOR/"upstream_suite"
ECV4=VENDOR/"upstream_ecv4"
SUITE_REF="31d0a0998c2fa5f5120b6bd2c6026a4f3702fd12"
EC_REF="f0f2d4a8634a130b710a326072438a51428929a3"

UPSTREAM={
    "SUITE_ACTIVE_RUNTIME.json":"62ac5996412d8e5f17b2f722f4f1791bd0579f34",
    "SUITE_V4_MANIFEST_CANDIDATE.json":"75b9060809b0de6bfbe6d7e496355517f3ec250e",
    "ECV4_SUITE_CANDIDATE.json":"6c92d58271143276b118502ee19c569734fcdcfb",
    "SUITE_V4_CONFIGURATION_LOCK_CANDIDATE.json":"575de2d81eef03753f9a7bfcefaff11573f3b015",
    "src/ec_v4_adapter.py":"796a0a05775b23d14588404b574f66b5b90273fd",
    "src/ec_v4_candidate_contract.py":"08234e555eb31c9fc8f7d29711302040402077ea",
    "src/suite_v4_atomic_gate.py":"2fb53d5fa3125c30858d5023e840ea997147cd12",
    "src/suite_v4_atomic_gate_v4.py":"38e5ac8f578c52be5f0a732173389db26f2aab83",
    "scripts/ec_v4_atomic_e2e.py":"3d79e04e3a6aefe824a2d6822d9830d80dd459f1",
    "benchmarks/ecv4_f0f2_r3_atomic_repin_2026-09-25.json":"e9f47aa3f7ba28fa8a5023579a128a21fc1725b4",
}
ECV4_BLOB="c0b1e43efe521c833c26d6cd7f9e55ff1a8256fc"


def sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise ValueError("SOURCE_IMPORT_UNAVAILABLE")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod


def suite_check():
    pin_ok=all(sha(SUITE/p)==v for p,v in UPSTREAM.items())
    if not pin_ok:
        raise ValueError("SUITE_SOURCE_BLOB_MISMATCH")
    mod=module(SUITE/"src/suite_v4_atomic_gate_v4.py","issue58_pinned_suite_v4")
    result=mod.evaluate(SUITE)
    positive=result.get("status")=="PASS" and result.get("production_ready") is False
    with tempfile.TemporaryDirectory() as td:
        target=Path(td)/"suite"
        shutil.copytree(SUITE,target)
        manifest=target/"SUITE_V4_MANIFEST_CANDIDATE.json"
        payload=json.loads(manifest.read_text())
        payload["routing"]["raw_project_io_bypass_allowed"]=True
        manifest.write_text(json.dumps(payload),encoding="utf-8")
        corrupted=mod.evaluate(target)
    mutation_blocked=corrupted.get("status")=="BLOCKED"
    return {"pass":positive and mutation_blocked and pin_ok,
            "source_blob_match":pin_ok,"qualified_ref":SUITE_REF,
            "official_suite_gate":result.get("status"),
            "negative_suite_config_tamper_rejected":mutation_blocked,
            "suite_is_product_ready":result.get("production_ready")}


def ecv4_check():
    file=ECV4/"ec_dynamic_frontier.py"
    if sha(file)!=ECV4_BLOB:
        raise ValueError("ECV4_SOURCE_BLOB_MISMATCH")
    ec=module(file,"issue58_pinned_dynamic_frontier")
    identifiers=("I58:REPAIR","I58:REGRESSION","I58:EVIDENCE")
    deps={"I58:REPAIR":[],"I58:REGRESSION":["I58:REPAIR"],"I58:EVIDENCE":["I58:REGRESSION"]}
    issues=[{"issue_id":i,"priority":"P0","blocker":True,
             "disposition":"OPEN","work":[{"work_id":i,"kind":"REPAIR" if i.endswith("REPAIR") else "EVIDENCE","depends_on":deps[i]}]}
            for i in identifiers]
    plan={"protocol":"ISSUE58_ECV4_PLAN_V1","authority":"operator-controlled pinned GitHub issue58",
          "primary_goal":"blind four-arm methodology and contamination controls, without independent study outputs","additional_goals":[],"issues":issues}
    completed=[]
    selected=[]
    observation="https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/58"
    for revision,expected in enumerate(identifiers):
        candidate=[x for x in issues if x["issue_id"] not in completed]
        ctx={"protocol":ec.PROTOCOL,
             "plan_digest":ec.plan_digest(plan),
             "state_revision":revision,"observation_ref":observation,
             "dependency_graph":deps,
             "issue_state":{i:{"urgency":1.0} for i in identifiers}}
        ctx["state_digest"]=ec.state_digest(ctx)
        trusted_digest=ctx["state_digest"]
        result=ec.choose_dynamic_issue(plan=plan,candidate_issues=candidate,
            completed_issue_ids=completed,static_issue_id="I58:EVIDENCE",
            context=ctx,state_authority=lambda ref,digest,rev:(
                ref==observation and digest==trusted_digest and rev==revision))
        selected.append(result.get("issue_id"))
        if result.get("issue_id")!=expected:
            raise ValueError("ECV4_FRONTIER_SELECTED_WRONG_ISSUE")
        if revision==0:
            stale=copy.deepcopy(ctx)
            stale["state_digest"]="0"*64
            stale_blocked=False
            try:
                ec.choose_dynamic_issue(plan=plan,candidate_issues=candidate,
                    completed_issue_ids=[],static_issue_id="I58:EVIDENCE",
                    context=stale,state_authority=lambda *a:True)
            except ec.DynamicFrontierError:
                stale_blocked=True
            authority_blocked=False
            try:
                ec.choose_dynamic_issue(plan=plan,candidate_issues=candidate,
                    completed_issue_ids=[],static_issue_id="I58:EVIDENCE",
                    context=ctx,state_authority=lambda *a:False)
            except ec.DynamicFrontierError:
                authority_blocked=True
        completed.append(expected)
    ok=selected==list(identifiers) and stale_blocked and authority_blocked
    return {"pass":ok,"qualified_ref":EC_REF,
            "source_blob_match":True,"frontier_selected_sequence":selected,
            "tampered_digest_rejected":stale_blocked,
            "untrusted_state_rejected":authority_blocked,
            "terminal":"NO_OPEN_ISSUE58_GATE_IMPLEMENTATION_WORK" if ok else "BLOCKED"}


def main():
    suite=suite_check()
    ecv4=ecv4_check()
    runtime=subprocess.run([sys.executable,str(ROOT/"tools/preflight_issue58_blind.py")],
      cwd=ROOT,text=True,capture_output=True)
    try:
        run=json.loads(runtime.stdout)
    except ValueError:
        run={"terminal":"UNPARSEABLE","pass":False}
    passed=suite["pass"] and ecv4["pass"] and run.get("pass") is True and runtime.returncode==0
    print(json.dumps({"protocol":"ISSUE58_FINAL_SUITECV4_AUDIT_V1",
         "suite":suite,"ecv4":ecv4,
         "runtime":{"pass":run.get("pass"),"terminal":run.get("terminal"),
                    "gates":run.get("checks"),
                    "test_counts":{"blind_evaluator":20,"cli_process":4,"legacy_retention":16}},
         "pass":passed,"terminal":"ISSUE58_METHOD_CODE_PASS_REAL_FOUR_ARM_PENDING" if passed else "ISSUE58_FINAL_FAIL_CLOSED",
         "claim_limit":"Blind procedure and pinned regressions only; no actual independent external gold, LLM0 cache, or end-to-end four-arm score provided."},indent=2))
    return 0 if passed else 3

if __name__=="__main__":
    raise SystemExit(main())
