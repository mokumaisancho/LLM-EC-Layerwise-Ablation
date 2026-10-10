#!/usr/bin/env python3
"""Independent structural replay of original Phase1 A/B/C/D/E and E per layer.

This validates upstream identity and recomputes observed gains. It does not
authenticate which engine actually ran, provenance of gold, or scientific AC.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path

PROTOCOL="ISSUE1_PHASE1_AE_RAW_V1"
LAYERS=("S1","S2","S3","S4")
ARMS=("A","B","C","D","E_S1","E_S2","E_S3","E_S4")
MATERIALITY=0.20

def must(ok,label):
    if not ok:raise ValueError(label)

def h(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def verify(raw:dict,hidden:dict)->dict:
    must(isinstance(raw,dict) and raw.get("protocol")==PROTOCOL,"G0_PROTOCOL")
    must(isinstance(hidden,dict) and hidden.get("protocol")=="ISSUE1_PHASE1_GOLD_V1","G0_GOLD_PROTOCOL")
    must(raw.get("fixture_commit")==hidden.get("fixture_commit") and
         isinstance(raw.get("fixture_commit"),str) and len(raw["fixture_commit"])==40,"G4_FIXTURE_COMMIT_MISMATCH")
    must(raw.get("materiality")==hidden.get("materiality")==MATERIALITY,"G7_MATERIALITY_DRIFT")
    must(isinstance(raw.get("cases"),list) and raw["cases"],"G10_NO_CASES")
    must(isinstance(hidden.get("cases"),list),"G6_GOLD_CASES_NOT_LIST")
    gold={}
    for row in hidden["cases"]:
        must(set(row)=={"case_id","oracle_layers","label","family"},"G6_GOLD_SCHEMA")
        cid=row["case_id"]
        must(isinstance(cid,str) and cid and cid not in gold,"G10_DUPLICATE_GOLD_ID")
        must(set(row["oracle_layers"])==set(LAYERS),"G5_GOLD_LAYERS")
        must(type(row["label"]) is bool,"G6_GOLD_LABEL_INVALID")
        gold[cid]=row
    must(len(gold)==len(raw["cases"]),"G10_GOLD_COVERAGE")
    observed={a:[] for a in ARMS}
    casewise=[]
    seen=set()
    for row in raw["cases"]:
        must(set(row)=={"case_id","input_sha256","arms"},"G4_CASE_SCHEMA")
        cid=row["case_id"]
        must(cid in gold and cid not in seen,"G10_DUPLICATE_OR_UNKNOWN_CASE")
        seen.add(cid)
        must(isinstance(row["input_sha256"],str) and len(row["input_sha256"])==64,"G4_INPUT_HASH_MISSING")
        must(isinstance(row["arms"],list) and len(row["arms"])==len(ARMS),"G5_MISSING_ARM")
        measured={}
        for item in row["arms"]:
            must(set(item)=={"arm","layers","upstream","implementation","input_sha256","final_success"},"G4_ARM_SCHEMA")
            arm=item["arm"]
            must(arm in ARMS and arm not in measured,"G10_DUPLICATE_OR_UNKNOWN_ARM")
            must(set(item["layers"])==set(LAYERS) and set(item["upstream"])==set(LAYERS),"G5_LAYER_COVERAGE")
            must(item["input_sha256"]==row["input_sha256"],"G4_ARM_INPUT_MUTATED")
            must(item["implementation"] in ("LLM","NATIVE_EC","ORACLE_INTERVENTION"),"G9_UNQUALIFIED_ENGINE_NAME")
            must(type(item["final_success"]) is bool,"G6_RESULT_TYPE")
            measured[arm]=item
        must(set(measured)==set(ARMS),"G5_MISSING_ARM")
        for layer in ("S1","S2"):
            must(measured["A"]["layers"][layer]==measured["B"]["layers"][layer],"G4_A_B_UPSTREAM_REGENERATED")
            must(measured["C"]["layers"][layer]==measured["D"]["layers"][layer],"G4_C_D_UPSTREAM_REGENERATED")
        must(measured["A"]["implementation"]=="LLM" and measured["B"]["implementation"]=="NATIVE_EC" and
             measured["C"]["implementation"]=="LLM" and measured["D"]["implementation"]=="NATIVE_EC",
             "G9_FALSE_ENGINE_ARM")
        for i,layer in enumerate(LAYERS):
            e=measured["E_"+layer]
            must(e["implementation"]=="ORACLE_INTERVENTION","G5_E_NOT_ORACLE")
            for prior in LAYERS[:i]:
                must(e["layers"][prior]==measured["A"]["layers"][prior],
                     "G4_ORACLE_CHANGED_UPSTREAM:"+cid+":"+layer)
            must(e["layers"][layer]==gold[cid]["oracle_layers"][layer],
                 "G5_INTERVENTION_ORACLE_MISMATCH:"+cid+":"+layer)
        for arm,item in measured.items():
            for i,layer in enumerate(LAYERS):
                expected=row["input_sha256"] if i==0 else h(item["layers"][LAYERS[i-1]])
                must(item["upstream"][layer]==expected,
                     "G4_BROKEN_LAYER_HASH_CHAIN:"+cid+":"+arm+":"+layer)
            observed[arm].append(item["final_success"])
        casewise.append({"case_id":cid,"input_sha256":row["input_sha256"],
                         "success":{a:measured[a]["final_success"] for a in ARMS},
                         "family":gold[cid]["family"]})
    must(seen==set(gold),"G10_GOLD_SET_DISAGREEMENT")
    metrics={arm:sum(vals)/len(vals) for arm,vals in observed.items()}
    gains={layer:metrics["E_"+layer]-metrics["A"] for layer in LAYERS}
    return {"protocol":"ISSUE1_PHASE1_AE_RAW_AUDIT_V1","cases":len(casewise),
            "arms":list(ARMS),"metrics":metrics,"oracle_gains":gains,
            "materiality_threshold":MATERIALITY,
            "material_layers":[k for k,v in gains.items() if v>=MATERIALITY],
            "casewise":casewise,"all_arm_and_hash_gates_passed":True,
            "native_source_independently_qualified":False,
            "LLM_output_cryptographically_authenticated":False,
            "independent_gold_custody_authenticated":False,
            "original_AC18_pass_automatically":False}

def run(arms_path:Path,gold_path:Path)->dict:
    must(arms_path.is_file() and gold_path.is_file() and
         arms_path.resolve()!=gold_path.resolve(),"G6_SEPARATE_GOLD_AND_ARMS_REQUIRED")
    before=(hashlib.sha256(arms_path.read_bytes()).hexdigest(),
            hashlib.sha256(gold_path.read_bytes()).hexdigest())
    result=verify(json.loads(arms_path.read_text()),json.loads(gold_path.read_text()))
    after=(hashlib.sha256(arms_path.read_bytes()).hexdigest(),
           hashlib.sha256(gold_path.read_bytes()).hexdigest())
    must(before==after,"G7_INPUT_MODIFIED_DURING_SCORE")
    result["input_seals"]={"arms_sha256":before[0],"gold_sha256":before[1]}
    return result
