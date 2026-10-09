#!/usr/bin/env python3
"""Re-run historical frozen 17-case Qwen next-action lane on macOS using llama-cli.

Reuses EXACT historical 2026-10-03 prompt and GBNF function from its restored
Git blob; adapts llama-server POST to local llama-cli invocation. This runtime
is NOT identical to original b11146 Ubuntu server. Development/exposed only.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
PROTOCOL="ISSUE1_NEXT_ACTION_QWEN_MAC_COMPAT_REAL_V3"
MODEL_SHA="1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370"
MODEL_BYTES=986048768
LLAMA_SHA="023712cb97abef06769a544fe034a92cc57921bd60fd9fcd2c02e325839641c2"
HISTORICAL_BLOB="486863d076f49a9378a538e97739464849a044b1"
ARCHIVED=ROOT/"verification/issue1_next_action_v2/archived_original_runner_2026_10_03.py"
REPLAY=ROOT/"results/issue1_ecv44_native_next_action_v2_local_replay_2026-10-10.json"

def sha_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load_historical():
    if not ARCHIVED.is_file() or git_blob(ARCHIVED.read_bytes())!=HISTORICAL_BLOB:
        raise ValueError("HISTORICAL_RUNNER_SOURCE_BLOB_CHANGED")
    spec=importlib.util.spec_from_file_location("archived_issue1_runner_for_prompt_only",ARCHIVED)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod

def verify(model:Path,llama:Path)->Path:
    if model.is_symlink() or not model.is_file() or model.stat().st_size!=MODEL_BYTES:
        raise ValueError("FROZEN_QWEN_MODEL_MISSING_OR_WRONG_SIZE")
    if sha_file(model)!=MODEL_SHA:
        raise ValueError("FROZEN_QWEN_MODEL_SHA_MISMATCH")
    binary=llama.resolve(strict=True)
    if not binary.is_file() or sha_file(binary)!=LLAMA_SHA:
        raise ValueError("PINNED_MAC_LLAMA_CPP_BINARY_MISMATCH")
    return binary

def run_one_local(binary:Path,model:Path,prompt:str,grammar:str,seconds:int)->dict:
    command=[
        str(binary),"--single-turn","--no-warmup","-m",str(model),
        "-p",prompt,"-n","64","-c","2048","-t","4","-ngl","0",
        "--temp","0","--seed","0","-no-cnv","--simple-io",
        "--no-display-prompt","--log-disable","--grammar",grammar,
    ]
    proc=subprocess.run(command,stdin=subprocess.DEVNULL,
                        capture_output=True,text=True,timeout=seconds)
    raw=proc.stdout
    if proc.returncode:
        raise RuntimeError("PINNED_NATIVE_INFERENCE_FAILED:"+str(proc.returncode)+":"+proc.stderr[-280:])
    position=raw.rfind("\n\n> ")
    if position<0:
        raise RuntimeError("RESPONSE_INPUT_MARKER_MISSING:"+hashlib.sha256(raw.encode()).hexdigest())
    start=raw.find("\n\n",position+4)
    if start<0:
        raise RuntimeError("RESPONSE_BOUNDARY_MISSING:"+hashlib.sha256(raw.encode()).hexdigest())
    body=re.split(r"\n+\[ Prompt: ",raw[start+2:],maxsplit=1)[0].strip()
    if not body or len(body)>4096:
        raise RuntimeError("RESPONSE_EMPTY_OR_OVERSIZED")
    return {"raw_response":body,
            "stdout_sha256":hashlib.sha256(raw.encode()).hexdigest(),
            "stderr_sha256":hashlib.sha256(proc.stderr.encode()).hexdigest()}

def execute(model:Path,llama:Path,ec_root:Path,per_case_seconds:int=90)->dict:
    from tools.replay_issue1_ecv44_native_next_action_v2 import verify as verify_native
    verify_native(ec_root,ROOT/"fixtures/function_boundary_next_action_v1.json",ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json")
    binary=verify(model,llama)
    archived=load_historical()
    fixture=ROOT/"fixtures/function_boundary_next_action_v1.json"
    contract=ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json"
    if git_blob(fixture.read_bytes())!=archived.FIXTURE_BLOB:
        raise ValueError("FROZEN_FIXTURE_MISMATCH_WITH_HISTORICAL_PROMPT")
    frozen=json.loads(fixture.read_text())
    policy=json.loads(contract.read_text())
    ec=json.loads(REPLAY.read_text())["result"]
    if ec["ec_decision_correct"]!=17 or ec["ec_reason_correct"]!=17:
        raise ValueError("LOCAL_NATIVE_EC_REFERENCE_NOT_VERIFIED")
    ec_rows=[]
    for f,er in zip(frozen["fixtures"],ec["rows"]):
        if f["id"]!=er["case_id"] or not er["decision_correct"] or not er["reason_correct"]:
            raise ValueError("EC_COMPARISON_CASE_ORDER_OR_SUCCESS_INVALID")
        ec_rows.append({"dynamic_context":None})
        if er["native_dynamic_sha256"]:
            # Derive exactly the original dynamic context from the model-visible
            # dynamic_spec, not from oracle/gold. Never forge the hidden state.
            import sys as _sys
            # Provenance of dynamic state is checked against pinned EC source above.
            # Dynamic context itself must be recomputed by pinned native tool
            # in a separate run, not inferred from a digest. Use the original
            # source's explicit documented reconstruction formula:
            s=f["dynamic_spec"];base=f["plan"];done=f.get("completed_work_ids") or [];blocked=f.get("blocked_work") or {}
            src=ec_root/"01_repo/src"
            if not (src/"v4/ec_dynamic_frontier.py").exists():
                raise ValueError("PINNED_NATIVE_DYNAMIC_SOURCE_UNAVAILABLE")
            if str(src/"v4") not in _sys.path:_sys.path[:0]=[str(src/"v4"),str(src)]
            from ec_dynamic_frontier import PROTOCOL as dyn_protocol,plan_digest,state_digest
            ctx={"protocol":dyn_protocol,"plan_digest":plan_digest(base),
                 "state_revision":s["state_revision"],"dependency_graph":s["dependency_graph"],
                 "issue_state":s["issue_state"],"completed_work_ids":sorted(done),
                 "blocked_work":blocked,"observation_ref":f"auth:{s['state_revision']}"}
            ctx["state_digest"]=state_digest(ctx)
            observed=hashlib.sha256(json.dumps(ctx,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
            if observed!=er["native_dynamic_sha256"]:
                raise ValueError("NATIVE_DYNAMIC_CONTEXT_HASH_MISMATCH")
            ec_rows[-1]["dynamic_context"]=ctx

    invocations=[]
    def local_completion(_url,payload,timeout=180):
        result=run_one_local(binary,model,payload["prompt"],payload["grammar"],per_case_seconds)
        invocations.append({"prompt_sha256":hashlib.sha256(payload["prompt"].encode()).hexdigest(),
                            "grammar_sha256":hashlib.sha256(payload["grammar"].encode()).hexdigest(),
                            **result})
        return {"content":result["raw_response"]}
    archived.post_json=local_completion
    with contextlib.redirect_stdout(sys.stderr):
        rows=archived.run_llm("LOCAL_PINNED_LLAMA_CPP_CLI",frozen,policy,ec_rows)
    if len(rows)!=17 or len(invocations)!=17:
        raise RuntimeError("EXPECTED_17_ACTUAL_INFERENCES")
    aggregate=archived.summary(rows)
    return {
        "protocol":PROTOCOL,"reference_scope":"17 pre-existing exposed V2 cases",
        "qwen_model_sha256":MODEL_SHA,"local_binary_sha256":LLAMA_SHA,
        "historical_runner_git_blob_sha1":HISTORICAL_BLOB,
        "historical_llama_server_tag":"b11146",
        "this_local_runtime":"llama-cli Mac tag newer, not the historical Ubuntu llama-server",
        "decode":{"temperature":0,"seed":0,"gpu_layers":0,"threads":4,"max_tokens":64,"context":2048},
        "prompt_and_grammar_logic":"bytewise from archived original V2 runner",
        "ec_actual_replay":17,"llm_actual_inference_count":len(invocations),
        "llm":aggregate,"raw_inference":invocations,
        "ec_minus_llm_decision_accuracy":1.0-aggregate["decision_accuracy"],
        "independent_gold":False,"original_llm0_identity_established":False,
        "scientific_phase1_a_e_completed":False,
        "historical_original_server_output_reproduced":False,
        "terminal":"SCOPED_REAL_LOCAL_MAC_QWEN_17_DIAGNOSTIC_COMPLETE",
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--llama-cli",type=Path,required=True)
    p.add_argument("--seconds",type=int,default=90)
    p.add_argument("--ec-root",type=Path,required=True)
    a=p.parse_args()
    try:
        d=execute(a.model,a.llama_cli,a.ec_root,a.seconds)
        print(json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:400]}))
        return 3
if __name__=="__main__":
    raise SystemExit(main())
