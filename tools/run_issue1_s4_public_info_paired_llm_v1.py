#!/usr/bin/env python3
"""Frozen-before-inference, paired 10-case public S4 information ablation.

The predictor subprocess receives ONLY a seven-field public projection. The
parent holds the labels and scores AFTER both arms have been sealed.
This is a causal *input information* intervention over exposed dev cases,
not a true oracle-only-layer substitution or native EC S4 performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from tools.run_issue1_s4_interface_information_diagnostic_v1 import (
    public_projection, predict, baseline_signature, canonical_hash,
)

CONTRACT=ROOT/"docs/ISSUE1_S4_PUBLIC_INFORMATION_CONTROLLED_MODEL_ABLATION_V1.json"
PROTOCOL="ISSUE1_S4_PUBLIC_INFORMATION_CONTROLLED_MODEL_ABLATION_V1"
FIELDS={"protocol","selected_count","rejected_count","reframe_required",
        "trigger_residual_types","relation_groups","required_condition_state"}
GRAMMAR='root ::= "CLOSE" | "CONTINUE"'
INSTRUCTIONS=(
    "Decide whether a governed task may CLOSE or should CONTINUE based on "
    "the public upstream machine-readable information. "
    "Output strictly CLOSE or CONTINUE, nothing else. "
    "The rules are: any explicitly UNRESOLVED required condition means CONTINUE. "
    "Two selected competing admissible options mean CONTINUE until a choice is "
    "made; two semantically equivalent options need not prevent CLOSE. "
    "If the public representation lacks evidence that a blocking condition "
    "exists, do not invent one; CLOSE is permissible. "
    "An earlier reframing residual alone does not prevent closure when the "
    "reframe was already applied. Use only these supplied public fields. "
)

def file_sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda:f.read(4*1024*1024),b""):h.update(data)
    return h.hexdigest()

def blob_sha(path:Path)->str:
    value=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(value)).encode()+b"\0"+value).hexdigest()

def read_contract(model:Path,llama:Path)->dict:
    from tools.run_issue1_s4_interface_information_diagnostic_v1 import ROOT as SOURCE_ROOT
    c=json.loads(CONTRACT.read_text())
    if c["protocol"]!=PROTOCOL or c["status"]!="FROZEN_BEFORE_MODEL_RUN":
        raise ValueError("PREREGISTERED_CONTRACT_INVALID")
    pins=c["dataset"]["generator_blobs"]
    for f,digest in pins.items():
        if blob_sha(ROOT/f)!=digest:
            raise ValueError("DATA_GENERATOR_SOURCE_PIN_CHANGED:"+f)
    if blob_sha(ROOT/"tools/run_issue1_s4_interface_information_diagnostic_v1.py")!=c["dataset"]["existing_sanitizer_source_blob"]:
        raise ValueError("PUBLIC_SANITIZER_PIN_CHANGED")
    m=c["model"]
    if model.is_symlink() or model.stat().st_size!=m["size_bytes"] or file_sha(model)!=m["sha256"]:
        raise ValueError("MODEL_BYTES_SHA_MISMATCH")
    binary=llama.resolve(strict=True)
    if file_sha(binary)!=m["engine_binary_sha256"]:
        raise ValueError("MODEL_ENGINE_BINARY_SHA_MISMATCH")
    if m["gbnf"]!=GRAMMAR or (m["temperature"],m["seed"],m["max_new_tokens"])!=(0,0,20):
        raise ValueError("DECODE_CONTRACT_CHANGED")
    return c

def strict_public(obj:dict):
    if not isinstance(obj,dict) or set(obj)!=FIELDS:
        raise ValueError("UNSAFE_OR_INCOMPLETE_PREDICTOR_INPUT")
    if obj["protocol"]!="ISSUE1_S4_INTERFACE_INFORMATION_SUCCESSOR_DIAGNOSTIC_V1":
        raise ValueError("UNRECOGNIZED_PUBLIC_PROTOCOL")
    if obj["required_condition_state"] not in ("UNRESOLVED","NOT_EXPLICITLY_UNRESOLVED"):
        raise ValueError("INVALID_PUBLIC_PENDING_STATE")
    if not isinstance(obj["relation_groups"],list):
        raise ValueError("INVALID_RELATION_GROUPS")
    for g in obj["relation_groups"]:
        if set(g)!={"relation_type","selected_member_count"} or g["relation_type"] not in ("COMPETING","EQUIVALENT"):
            raise ValueError("INVALID_RELATION_TYPE")

def arm_projection(public:dict,arm:str)->dict:
    strict_public(public)
    if arm=="ENRICHED":
        return dict(public)
    if arm=="STRUCTURAL":
        return {k:v for k,v in public.items()
                if k not in ("relation_groups","required_condition_state")}
    raise ValueError("UNKNOWN_TREATMENT")

def predict_only(model:Path,binary:Path,source:Path,seconds:int)->dict:
    data=json.loads(source.read_text())
    if not isinstance(data,dict) or set(data)!={"arm","public"}:
        raise ValueError("PREDICTOR_ENVELOPE_NOT_ALLOWLISTED")
    arm=data["arm"]
    if arm not in ("ENRICHED","STRUCTURAL"):
        raise ValueError("UNKNOWN_ARM")
    projected=data["public"]
    if arm=="ENRICHED":
        strict_public(projected)
    else:
        if set(projected)!=(FIELDS-{"relation_groups","required_condition_state"}):
            raise ValueError("STRUCTURAL_ALLOWLIST_REQUIRED")
    prompt=(INSTRUCTIONS+"\nPublic upstream artifact:\n"
            +json.dumps(projected,ensure_ascii=False,sort_keys=True,separators=(",",":"))
            +"\nDecision:")
    cmd=[str(binary),"--single-turn","--no-warmup","-m",str(model),
         "-p",prompt,"-n","20","-t","4","-ngl","0","--temp","0",
         "--seed","0","-no-cnv","--simple-io","--no-display-prompt",
         "--log-disable","--grammar",GRAMMAR]
    p=subprocess.run(cmd,text=True,capture_output=True,stdin=subprocess.DEVNULL,
                     timeout=seconds)
    if p.returncode:
        raise RuntimeError("LLAMA_PROCESS_ERROR:"+str(p.returncode)+":"+p.stderr[-180:])
    mark=p.stdout.rfind("\n\n> ")
    if mark<0:raise ValueError("MODEL_RESPONSE_MARKER_MISSING")
    boundary=p.stdout.find("\n\n",mark+4)
    if boundary<0:raise ValueError("MODEL_RESPONSE_BOUNDARY_MISSING")
    raw=re.split(r"\n+\[ Prompt: ",p.stdout[boundary+2:],maxsplit=1)[0].strip()
    return {
        "protocol":"S4_PUBLIC_ARM_RAW_INFERENCE_V1",
        "arm":arm,"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),
        "input_sha256":canonical_hash(projected),
        "raw_response":raw,
        "parsed_prediction":raw if raw in ("CLOSE","CONTINUE") else "FORMAT_ERROR",
        "stdout_sha256":hashlib.sha256(p.stdout.encode()).hexdigest(),
        "stderr_sha256":hashlib.sha256(p.stderr.encode()).hexdigest(),
        "model_oracle_access":False,
    }

def run(model:Path,llama:Path,seconds:int)->dict:
    c=read_contract(model,llama)
    if str(ROOT/"tools") not in sys.path:
        sys.path.insert(0,str(ROOT/"tools"))
    from tools.generate_phase1_measurement_v2_canonical import SPECS,rebuild
    if [r["id"] for r in SPECS]!=c["dataset"]["cases"]:
        raise ValueError("FROZEN_CASE_ORDER_CHANGED")
    results=[]
    for spec in SPECS:
        task,_s1,s2,s3,_s4,hidden,_manifest=rebuild(spec)
        public=public_projection(task,s2,s3)
        for forbidden in c["comparison"]["deny_gold_fields"]:
            if forbidden in public:
                raise ValueError("ORACLE_FIELD_WAS_PROJECTED:"+forbidden)
        arm_raw={}
        with tempfile.TemporaryDirectory(prefix="s4-public-inference-") as d:
            for arm in ("STRUCTURAL","ENRICHED"):
                payload={"arm":arm,"public":arm_projection(public,arm)}
                path=Path(d)/"input.json"
                path.write_text(json.dumps(payload,sort_keys=True,ensure_ascii=False))
                cmd=[sys.executable,"-I",str(Path(__file__).resolve()),
                     "--predict-only","--model",str(model),"--llama-cli",str(llama),
                     "--input",str(path),"--seconds",str(seconds)]
                p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                 timeout=seconds+20,cwd=ROOT)
                if p.returncode:
                    raise RuntimeError("CHILD_INFERENCE_FAILED:"+arm+":"+p.stderr[-250:])
                actual=json.loads(p.stdout)
                if actual["input_sha256"]!=canonical_hash(payload["public"]) or actual["arm"]!=arm:
                    raise ValueError("PREDICTION_DIFFERENT_INPUT")
                arm_raw[arm]=actual
        truth=hidden["closure_class"]
        results.append({
            "case_id":spec["id"],
            "shared_fixed_structural_signature_sha256":baseline_signature(public),
            "full_public_features_sha256":canonical_hash(public),
            "structure":arm_raw["STRUCTURAL"],
            "enriched":arm_raw["ENRICHED"],
            "reference":truth,
            "structure_correct":arm_raw["STRUCTURAL"]["parsed_prediction"]==truth,
            "enriched_correct":arm_raw["ENRICHED"]["parsed_prediction"]==truth,
            "public_deterministic_correct":predict(public)["closure_class"]==truth,
        })
        print("S4_PAIRED_CASE_COMPLETED:"+str(len(results))+"/"+str(len(SPECS)),file=sys.stderr,flush=True)
    x=sum(r["structure_correct"] for r in results)
    y=sum(r["enriched_correct"] for r in results)
    z=sum(r["public_deterministic_correct"] for r in results)
    gain=(y-x)/len(results)
    return {
      "protocol":PROTOCOL,
      "preregistered_contract_git_blob_sha1":blob_sha(CONTRACT),
      "preregistration":c,
      "actual_inferences":len(results)*2,
      "cases":len(results),
      "structural_correct":x,
      "enriched_correct":y,
      "enhanced_deterministic_typed_policy_correct":z,
      "paired_enriched_minus_structural_accuracy":gain,
      "materiality_threshold":c["comparison"]["materiality_abs"],
      "decision":"STRUCTURED_UPSTREAM_INFORMATION_MATERIAL_ON_EXPOSED_FIXTURES_ONLY"
          if gain>=c["comparison"]["materiality_abs"] else
          "NO_MATERIAL_INFORMATION_EFFECT_DETECTED_ON_EXPOSED_FIXTURES",
      "case_results":results,
      "source_pins_proven":True,"no_input_gold_leak":True,
      "same_model_same_prompt_same_decode_except_public_treatment":True,
      "independent_holdout":False,"EC_native_closure_compared":False,
      "original_phase1_oracle_A_to_E_completed":False,
      "scientific_original_issue_completed":False,
      "terminal":"S4_TWO_ARM_ACTUAL_QWEN_PUBLIC_INFORMATION_INTERVENTION_COMPLETE",
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--llama-cli",type=Path,required=True)
    p.add_argument("--seconds",type=int,default=65)
    p.add_argument("--predict-only",action="store_true")
    p.add_argument("--input",type=Path)
    a=p.parse_args()
    try:
        result=predict_only(a.model,a.llama_cli,a.input,a.seconds) if a.predict_only else run(a.model,a.llama_cli,a.seconds)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except Exception as ex:
        print(json.dumps({"protocol":PROTOCOL,"terminal":"FAIL_CLOSED",
                          "error":type(ex).__name__+":"+str(ex)[:280]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
