#!/usr/bin/env python3
"""Independent native-tokenizer preflight for historical Qwen next-action prompts.

Reconstruct the byte-exact historical 17 prompts and compute true pinned-model
token lengths; determine whether original 2048-token context truncated system
or plan information. Uses no model inference, no hidden gold in prompts.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.run_issue1_llm_next_action_v2_local_mac import (
    load_historical,MODEL_SHA,MODEL_BYTES,sha_file,
)
from tools.replay_issue1_ecv44_native_next_action_v2 import (
    verify,modules,native_predict,public_fields,
)

PROTOCOL="ISSUE1_NEXT_ACTION_QWEN_17_PROMPT_TOKEN_CONTEXT_AUDIT_V1"
CONTEXT_TOKENS=2048
MAX_GENERATION=64

def audit(model:Path,tokenizer:Path,ec_root:Path)->dict:
    if model.is_symlink() or not model.is_file() or model.stat().st_size!=MODEL_BYTES or sha_file(model)!=MODEL_SHA:
        raise ValueError("ORIGINAL_MODEL_PIN_INVALID")
    if not tokenizer.is_file():raise ValueError("NATIVE_TOKENIZER_UNAVAILABLE")
    fixture=ROOT/"fixtures/function_boundary_next_action_v1.json"
    frozen=json.loads(fixture.read_text())
    policy=json.loads((ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json").read_text())
    baseline=json.loads((ROOT/"results/issue1_qwen_next_action_v2_mac_actual_2026-10-10.json").read_text())["run"]
    src=verify(ec_root,fixture,ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json")
    ena,df=modules(src)
    dyn=[]
    for case in frozen["fixtures"]:
        _y,ctx=native_predict(ena,df,public_fields(case))
        dyn.append({"dynamic_context":ctx})
    archived=load_historical()
    original_raw=[]
    def capture(_server,payload,timeout=180):
        original_raw.append({"prompt":payload["prompt"],"gbnf":payload["grammar"]})
        return {"content":'{"status":"REFRAME","work_id":"NONE","reason_code":"ISSUE_DEFINITION_REFRAME"}'}
    archived.post_json=capture
    with contextlib.redirect_stdout(io.StringIO()):
        archived.run_llm("NO_REAL_INFERENCE_CAPTURE_ONLY",frozen,policy,dyn)
    if len(original_raw)!=17:
        raise ValueError("PROMPT_RECONSTRUCTION_CASE_COVERAGE_MISMATCH")
    rows=[]
    with tempfile.TemporaryDirectory(prefix="issue1-token-") as d:
        for i,(c,raw) in enumerate(zip(frozen["fixtures"],original_raw)):
            actual=baseline["raw_inference"][i]
            if hashlib.sha256(raw["prompt"].encode()).hexdigest()!=actual["prompt_sha256"]:
                raise ValueError("ACTUAL_HISTORICAL_PROMPT_HASH_MISMATCH:"+c["id"])
            if hashlib.sha256(raw["gbnf"].encode()).hexdigest()!=actual["grammar_sha256"]:
                raise ValueError("ACTUAL_HISTORICAL_GBNF_HASH_MISMATCH:"+c["id"])
            path=Path(d)/(str(i).zfill(3)+".txt")
            path.write_text(raw["prompt"],encoding="utf-8")
            p=subprocess.run([str(tokenizer),"--model",str(model),
                              "--file",str(path),"--show-count","--log-disable"],
                              text=True,capture_output=True,timeout=30,stdin=subprocess.DEVNULL)
            if p.returncode:
                raise ValueError("NATIVE_TOKENIZER_FAILED:"+str(p.returncode)+":"+p.stderr[-130:])
            found=re.search(r"Total number of tokens:\s*(\d+)",p.stdout)
            if not found:
                raise ValueError("TOKENIZER_TOTAL_COUNT_MISSING:"+c["id"])
            n=int(found.group(1))
            rows.append({
             "case_id":c["id"],"prompt_sha256":actual["prompt_sha256"],
             "grammar_sha256":actual["grammar_sha256"],
             "prompt_utf8_bytes":len(raw["prompt"].encode()),"qwen_token_count":n,
             "generation_budget":MAX_GENERATION,
             "context_tokens":CONTEXT_TOKENS,
             "total_tokens_prompt_plus_budget":n+MAX_GENERATION,
             "exceeds_declared_context":n+MAX_GENERATION>CONTEXT_TOKENS,
             "would_truncate_prompt_at_2048":n>CONTEXT_TOKENS,
             "raw_model_correct":baseline["llm"]["rows"][i]["decision_correct"],
            })
    return {
     "protocol":PROTOCOL,"frozen_model_sha256":MODEL_SHA,
     "actual_historical_prompt_sha_verified":True,
     "actual_historical_grammar_sha_verified":True,
     "frozen_context":CONTEXT_TOKENS,"max_generation":MAX_GENERATION,
     "exact_paired_case_count":len(rows),
     "min_tokens":min(r["qwen_token_count"] for r in rows),
     "max_tokens":max(r["qwen_token_count"] for r in rows),
     "prompt_context_exceeded_count":sum(r["would_truncate_prompt_at_2048"] for r in rows),
     "context_budget_exceeded_count":sum(r["exceeds_declared_context"] for r in rows),
     "rows":rows,"new_model_inferences":0,
     "independent_holdout":False,"original_full_A_E_completed":False,
     "interpretation":"Tokenizer exact counts only; this is a confound audit, not proof of model semantic competence.",
     "terminal":"PINNED_MODEL_TOKEN_CONTEXT_AUDIT_COMPLETE",
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",required=True,type=Path)
    ap.add_argument("--tokenizer",required=True,type=Path)
    ap.add_argument("--ec-root",required=True,type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    try:
        result=audit(a.model,a.tokenizer,a.ec_root)
        text=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
        if a.out:
            a.out.write_text(text)
            print(json.dumps({"terminal":result["terminal"],
                   "min_tokens":result["min_tokens"],"max_tokens":result["max_tokens"],
                   "prompt_truncated":result["prompt_context_exceeded_count"],
                   "budget_exceeded":result["context_budget_exceeded_count"],"out":str(a.out)}))
        else:print(text,end="")
        return 0
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:380]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
