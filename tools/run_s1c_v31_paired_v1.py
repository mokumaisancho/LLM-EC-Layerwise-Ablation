#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import tarfile
import time
import urllib.request
from typing import Any

from generate_s1c_v31_corpus import build_corpus
from validate_s1c_v31_corpus import validate_corpus
from score_s1c_v31_denotational import aggregate, validate_prediction
from s1c_v31_deterministic_baseline import predict as deterministic_predict
from s1c_v31_json_schema import schema_for

ROOT=pathlib.Path(__file__).resolve().parents[1]
TOOLS=ROOT/"tools"
WORK=pathlib.Path("/tmp/s1c-v31-paired-v1")
OUT=ROOT/"s1c_v31_paired_runtime.json"

PROTOCOL="FUNCTION_BOUNDARY_S1C_V31_PAIRED_V1"
TCC="S1C_SEMANTIC_SPACE_TCC_V1"
ISSUE=51
MATERIALITY=0.20

EXPECTED_BLOBS={
 "docs/S1C_V31_DENOTATIONAL_DISCOVERY_CONTRACT_2026-10-07.json":"f77a112f90620e64c48fb824a65ca7a995b04212",
 "tools/s1c_v31_public_hypotheses.py":"fe7b7b9a6203624e93ffdce1d542404fd250e63d",
 "tools/generate_s1c_v31_corpus.py":"a324ddd9ad9fbeb4e7cbb0b4a684a65a153d3a4b",
 "tools/validate_s1c_v31_corpus.py":"65746d0224b527f02f9caa20595a2fdf0690fb2c",
 "tools/score_s1c_v31_denotational.py":"f2df24b1994bc8da2b66b6280b41aba37d02d10e",
 "tools/s1c_v31_deterministic_baseline.py":"b5bf066dd2dd55a2cdcf076b09f5183c441b9866",
 "tools/s1c_v31_json_schema.py":"e97276494ecd21b62a3ad23c5e37cb7cdaa2c68d",
 "tools/preflight_s1c_v31.py":"0475ec4c7c576fc8a50c62b06f0a4cbd8b975b10",
 "results/s1c_v31_schema_smoke_actual_2026-10-08.json":"5d26feba4dcd0a23935f3ab85e81cf7465ac7202",
 "tools/audit_s1c_v31_independent.py":"b7b116d9705213facd5dbc7348e65717600d1ae9",
 "tools/replay_s1c_v31_fixed_b2.py":"da0fc48d530dd19f06f81f3aec7d8ec680dd2cb9",
 "tools/classify_s1c_v31_terminal.py":"6c71fdd9b90003f17dc0d3eca10c54bcfc14fc2b",
}

LLAMA_TAG="b11146"
LLAMA_FILE="llama-b11146-bin-ubuntu-x64.tar.gz"
LLAMA_URL=f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}"
LLAMA_SHA="c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410"
MODEL_REPO="bartowski/Qwen2.5-1.5B-Instruct-GGUF"
MODEL_FILE="Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
MODEL_URL=f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}"
MODEL_SHA="1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370"
MODEL_SIZE=986048768


def canon(x:Any)->str:return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha_obj(x:Any)->str:return hashlib.sha256(canon(x).encode()).hexdigest()

def blob_sha(path:pathlib.Path)->str:
    raw=path.read_bytes();h=hashlib.sha1();h.update(f"blob {len(raw)}\0".encode());h.update(raw);return h.hexdigest()

def sha256_file(path:pathlib.Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def verify_sources()->dict[str,str]:
    out={}
    for rel,expected in EXPECTED_BLOBS.items():
        p=ROOT/rel
        if not p.exists():raise RuntimeError("FROZEN_SOURCE_MISSING:"+rel)
        got=blob_sha(p);out[rel]=got
        if got!=expected:raise RuntimeError(f"FROZEN_SOURCE_DRIFT:{rel}:{got}:{expected}")
    return out

def run_preflight()->dict[str,Any]:
    p=subprocess.run(["python3",str(TOOLS/"preflight_s1c_v31.py")],cwd=ROOT,text=True,capture_output=True)
    if p.returncode:raise RuntimeError("V31_PREFLIGHT_FAILED:"+(p.stderr or p.stdout))
    out=json.loads(p.stdout)
    if out.get("terminal")!="S1C_V31_PREFLIGHT_PASS" or out.get("pass") is not True:raise RuntimeError("V31_PREFLIGHT_NOT_PASS")
    return out

def verify_smoke()->dict[str,Any]:
    p=ROOT/"results"/"s1c_v31_schema_smoke_actual_2026-10-08.json"
    x=json.loads(p.read_text())
    if x.get("terminal")!="S1C_V31_SYNTHETIC_JSON_SCHEMA_RUNTIME_SMOKE_PASS" or x.get("pass") is not True or x.get("paired_model_inference_authorized") is not True:
        raise RuntimeError("V31_SCHEMA_SMOKE_NOT_PASS")
    if x.get("scientific_measurement_performed") is not False:raise RuntimeError("V31_SCHEMA_SMOKE_SCIENTIFIC_CONTAMINATION")
    return x

def download(url:str,dest:pathlib.Path,ua:str)->None:
    req=urllib.request.Request(url,headers={"User-Agent":ua})
    with urllib.request.urlopen(req,timeout=240) as r,dest.open("wb") as out:
        while True:
            chunk=r.read(1024*1024)
            if not chunk:break
            out.write(chunk)

def acquire_runtime()->pathlib.Path:
    arc=WORK/LLAMA_FILE;download(LLAMA_URL,arc,"s1c-v31-paired-v1/1")
    if sha256_file(arc)!=LLAMA_SHA:raise RuntimeError("LLAMA_SHA_MISMATCH")
    target=WORK/"llama";target.mkdir(parents=True,exist_ok=True)
    with tarfile.open(arc,"r:gz") as tf:tf.extractall(target,filter="data")
    hits=list(target.rglob("llama-server"))
    if not hits:raise RuntimeError("LLAMA_SERVER_NOT_FOUND")
    hits[0].chmod(0o755);return hits[0]

def post_json(url:str,payload:dict[str,Any],timeout:int=600)->dict[str,Any]:
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)

def invalid_result(reason:str,raw_rows:list[dict[str,Any]],source_blobs:dict[str,str],corpus:dict[str,Any],oracle:dict[str,Any])->int:
    out={"schema_version":"FUNCTION_BOUNDARY_S1C_V31_INVALID_V1","protocol":PROTOCOL,"tcc":TCC,"issue":ISSUE,
         "terminal":"V31_ASSAY_EXECUTION_INVALID","reason":reason,"source_blob_pins":source_blobs,
         "corpus_digest":corpus.get("dataset_digest"),"oracle_terminal":oracle.get("terminal"),"raw_qwen_rows":raw_rows,
         "scientific_metrics_authorized":False,"successor_required":True}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("S1C_V31_INVALID="+json.dumps({"reason":reason,"result_sha256":sha256_file(OUT),"completed_qwen_tasks":len(raw_rows)},separators=(",",":")),flush=True)
    return 3

def qwen_predict(tasks:list[dict[str,Any]],server_url:str,source_blobs:dict[str,str],corpus:dict[str,Any],oracle:dict[str,Any]):
    system=(
      "Discover reusable semantic slots from the four visible training examples. "
      "The public behavior hypothesis is symmetric for both arms: each of three binary coordinates independently uses KEEP, SET0, SET1, or FLIP. "
      "Use the partial before/after observations to infer which training examples share one behavior; do not invent or assume hidden slot names. "
      "For every discovered slot, predict the after-state for every visible evaluation probe input Q03,Q05,Q06,Q07. "
      "Then use the raw-language relation between training member texts and heldout texts to assign each non-ambiguous heldout example to a discovered local slot. "
      "Preserve visible entity IDs, argument order, polarity, and modality. "
      "Use AMBIGUOUS only for genuinely unresolved heldout language. "
      "Every training example must appear in exactly one discovered slot and every heldout example must be assigned or abstained exactly once. "
      "Return only one JSON object satisfying the supplied schema."
    )
    preds={};raw_rows=[]
    for task in tasks:
        visible=task["visible"];tid=str(task["task_id"])
        prompt="<|im_start|>system\n"+system+"<|im_end|>\n<|im_start|>user\n"+canon(visible)+"<|im_end|>\n<|im_start|>assistant\n"
        response=post_json(server_url+"/completion",{"prompt":prompt,"n_predict":2200,"temperature":0,"json_schema":schema_for(task),"cache_prompt":False})
        raw=str(response.get("content","")).strip();parsed=None
        try:
            x=json.loads(raw)
            if isinstance(x,dict):parsed=x
        except Exception:parsed=None
        row={"task_id":tid,"visible_sha256":sha_obj(visible),"raw_sha256":hashlib.sha256(raw.encode()).hexdigest(),"raw":raw,"prediction":parsed}
        raw_rows.append(row)
        print("S1C_V31_TASK="+json.dumps({"task_id":tid,"raw_sha256":row["raw_sha256"],"parsed":parsed is not None,"raw_chars":len(raw)},separators=(",",":")),flush=True)
        if parsed is None:return None,raw_rows,invalid_result("MALFORMED_JSON_OUTPUT:"+tid,raw_rows,source_blobs,corpus,oracle)
        shape=validate_prediction(task,parsed)
        if shape.get("valid") is not True:return None,raw_rows,invalid_result("SCHEMA_SEMANTIC_SHAPE_INVALID:"+tid+":"+str(shape.get("reason")),raw_rows,source_blobs,corpus,oracle)
        preds[tid]=parsed
    return preds,raw_rows,0

def main()->int:
    WORK.mkdir(parents=True,exist_ok=True)
    source_blobs=verify_sources();preflight=run_preflight();smoke=verify_smoke()
    corpus=build_corpus();tasks=corpus["tasks"];oracle=validate_corpus(corpus)
    if oracle.get("pass") is not True:raise RuntimeError("ORACLE_VALIDATION_NOT_PASS")
    deterministic_predictions={str(t["task_id"]):deterministic_predict({"visible":t["visible"]}) for t in tasks}
    deterministic=aggregate(tasks,deterministic_predictions,oracle["references"])
    if deterministic.get("pass") is not True:raise RuntimeError("DETERMINISTIC_SCORE_FAIL")
    print("S1C_V31_STATE=ALL_PREINFERENCE_GATES_PASS_MODEL_ACQUISITION_AUTHORIZED",flush=True)

    server_bin=acquire_runtime();model=WORK/MODEL_FILE;download(MODEL_URL,model,"s1c-v31-paired-v1/1")
    if model.stat().st_size!=MODEL_SIZE:raise RuntimeError("MODEL_SIZE_MISMATCH")
    if sha256_file(model)!=MODEL_SHA:raise RuntimeError("MODEL_SHA_MISMATCH")
    log_path=WORK/"llama.log";log=log_path.open("w")
    server=subprocess.Popen([str(server_bin),"-m",str(model),"-c","8192","-b","64","-ub","64","--threads","1","--no-warmup","--host","127.0.0.1","--port","18086"],stdout=log,stderr=subprocess.STDOUT,text=True)
    try:
        ready=False
        for _ in range(240):
            if server.poll() is not None:break
            try:
                with urllib.request.urlopen("http://127.0.0.1:18086/health",timeout=2) as r:
                    if r.status==200:ready=True;break
            except Exception:pass
            time.sleep(1)
        if not ready:
            log.flush();raise RuntimeError("LLAMA_NOT_READY:"+log_path.read_text(errors="replace")[-3000:])
        qpred,raw_rows,invalid=qwen_predict(tasks,"http://127.0.0.1:18086",source_blobs,corpus,oracle)
        if invalid:return invalid
        assert qpred is not None
        qwen=aggregate(tasks,qpred,oracle["references"])
        if qwen.get("pass") is not True:return invalid_result("QWEN_SCORE_FAIL_CLOSED",raw_rows,source_blobs,corpus,oracle)
        deltas={k:float(qwen["primary"][k])-float(deterministic["primary"][k]) for k in deterministic["primary"]}
        out={"schema_version":"FUNCTION_BOUNDARY_S1C_V31_PAIRED_ACTUAL_V1","protocol":PROTOCOL,"tcc":TCC,"issue":ISSUE,
             "terminal":"V31_PAIRED_METRICS_READY_AUDIT_REQUIRED","source_blob_pins":source_blobs,
             "preflight_terminal":preflight["terminal"],"schema_smoke_terminal":smoke["terminal"],
             "corpus":corpus,"oracle_validation":oracle,"deterministic_predictions":deterministic_predictions,
             "model":{"repository":MODEL_REPO,"file":MODEL_FILE,"size_bytes":MODEL_SIZE,"sha256":MODEL_SHA},
             "runtime":{"llama_cpp_tag":LLAMA_TAG,"llama_cpp_asset_sha256":LLAMA_SHA,"temperature":0,"context_tokens":8192,
                        "constraint":"json_schema","github_actions_used":False,"google_drive_used":False,"qwen3_4b_used":False},
             "arms":{"deterministic":deterministic,"qwen25_1p5b":qwen},"raw_qwen_rows":raw_rows,
             "primary_deltas_qwen_minus_deterministic":deltas,"materiality_abs":MATERIALITY,
             "final_branch_authorized":False,
             "required_next_gates":["S1C_V31_INDEPENDENT_POSTRUN_AUDIT","S1C_V31_FIXED_B2_CAUSAL_REPLAY","S1C_V31_TERMINAL_CLASSIFIER"],
             "claim_limit":"Finite public 64-function coordinate-wise transition hypothesis class only; no unrestricted ontology invention or open-ended world-knowledge claim."}
        OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("S1C_V31_TERMINAL="+json.dumps({"terminal":out["terminal"],"result_sha256":sha256_file(OUT),"deterministic_primary":deterministic["primary"],"qwen_primary":qwen["primary"],"deltas":deltas},separators=(",",":")),flush=True)
        return 0
    finally:
        if server.poll() is None:server.terminate()
        log.close()

if __name__=="__main__":raise SystemExit(main())
