#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/"tools"
PROTOCOL="S1C_V32_RUNNER_PREFLIGHT_V1"

EXPECTED={
 "docs/S1C_V32_MEASUREMENT_SEPARATION_CONTRACT_2026-10-08.json":"416633b311428146948989ad76d50fa9651bace9",
 "tools/score_s1c_v32_denotational.py":"2a1bd54341e44b0896d57f1d7cccdec17e42db34",
 "tools/audit_s1c_v32_independent.py":"dc08d4980ef1c52c4a842c7e337c5471838e2c80",
 "tools/replay_s1c_v32_fixed_b2.py":"89d0af86d15b5090a887bd0b9b35d90e65c69261",
 "tools/classify_s1c_v32_terminal.py":"f6c3134080a91da01ea000b82f3fa9c09fe0874e",
 "tools/run_s1c_v32_paired_v1.py":"7880e0f3182ae3446a5ebad3720c38f49945b662",
 "tools/run_s1c_v31_paired_v1.py":"99e3b30259246a2b3c81ce79dcdacfdfafca4b92",
}

def blob(path:Path)->str:
    import hashlib
    raw=path.read_bytes();h=hashlib.sha1();h.update(f"blob {len(raw)}\0".encode());h.update(raw);return h.hexdigest()

def fail(reason,detail=None):
    print(json.dumps({"protocol":PROTOCOL,"pass":False,"terminal":"S1C_V32_RUNNER_PREFLIGHT_FAIL_CLOSED","reason":reason,"detail":detail},indent=2));return 3

def system_block(src:str)->str:
    start=src.index("    system=(")
    end=src.index("    preds={};raw_rows=[]",start)
    return src[start:end]

def main()->int:
    for rel,expected in EXPECTED.items():
        p=ROOT/rel
        if not p.exists():return fail("SOURCE_MISSING",rel)
        got=blob(p)
        if got!=expected:return fail("SOURCE_DRIFT",{"path":rel,"actual":got,"expected":expected})
        if p.suffix==".py":
            try:py_compile.compile(str(p),doraise=True)
            except Exception as exc:return fail("PY_COMPILE_FAILED",{"path":rel,"error":repr(exc)})

    p=subprocess.run([sys.executable,str(TOOLS/"preflight_s1c_v31.py")],cwd=ROOT,text=True,capture_output=True)
    if p.returncode:return fail("V31_SCIENTIFIC_PREFLIGHT_FAILED",p.stderr or p.stdout)
    pre=json.loads(p.stdout)
    if pre.get("terminal")!="S1C_V31_PREFLIGHT_PASS":return fail("V31_SCIENTIFIC_PREFLIGHT_NOT_PASS")

    smoke=json.loads((ROOT/"results"/"s1c_v31_schema_smoke_actual_2026-10-08.json").read_text())
    if smoke.get("terminal")!="S1C_V31_SYNTHETIC_JSON_SCHEMA_RUNTIME_SMOKE_PASS" or smoke.get("paired_model_inference_authorized") is not True:
        return fail("SCHEMA_RUNTIME_SMOKE_NOT_PASS")

    sys.path.insert(0,str(TOOLS))
    try:
        import run_s1c_v31_paired_v1 as v31
        import run_s1c_v32_paired_v1 as v32
        import generate_s1c_v31_corpus as generator
        import validate_s1c_v31_corpus as oracle
        import s1c_v31_deterministic_baseline as baseline
        import score_s1c_v32_denotational as scorer
    except Exception as exc:return fail("IMPORT_FAILED",repr(exc))

    s31=inspect.getsource(v31.qwen_predict);s32=inspect.getsource(v32.qwen_predict)
    try:b31=system_block(s31);b32=system_block(s32)
    except Exception as exc:return fail("SYSTEM_PROMPT_EXTRACTION_FAILED",repr(exc))
    if b31!=b32:return fail("V32_PROMPT_DRIFT_FROM_V31")
    for forbidden in ("canon(oracle)","REFERENCE[","TASK_SPECS","training_gold","slot_references","target_code"):
        if forbidden in b32:return fail("V32_PROMPT_HIDDEN_REFERENCE_ACCESS",forbidden)

    corpus=generator.build_corpus();ov=oracle.validate_corpus(corpus)
    if ov.get("pass") is not True:return fail("ORACLE_VALIDATION_NOT_PASS",ov.get("failures"))
    preds={str(t["task_id"]):baseline.predict({"visible":t["visible"]}) for t in corpus["tasks"]}
    score=scorer.aggregate(corpus["tasks"],preds,ov["references"])
    if score.get("pass") is not True:return fail("V32_BASELINE_SCORE_FAIL",score)
    expected_primary={
      "semantic_output_validity_rate":1.0,
      "training_partition_adjusted_rand_index":1.0,
      "unseen_probe_behavior_accuracy":1.0,
      "heldout_denotational_assignment_accuracy":0.9583333333333334,
      "exact_discovery_and_grounding_rate":0.875,
    }
    if score.get("primary")!=expected_primary:return fail("V32_BASELINE_PRIMARY_DRIFT",{"actual":score.get("primary"),"expected":expected_primary})
    if score.get("semantic_invalid_tasks")!=[]:return fail("DETERMINISTIC_BASELINE_SEMANTIC_INVALID",score.get("semantic_invalid_tasks"))

    out={"protocol":PROTOCOL,"pass":True,"terminal":"S1C_V32_RUNNER_PREFLIGHT_PASS","source_blob_pins":EXPECTED,
         "v31_scientific_preflight_terminal":pre["terminal"],"schema_smoke_terminal":smoke["terminal"],
         "qwen_prompt_byte_identical_to_v31":True,"qwen_prompt_visible_only_gate":"PASS",
         "baseline_primary":score["primary"],"baseline_secondary":score["secondary"],
         "model_inference_executed":False,"paired_model_inference_authorized":True,
         "scientific_change_scope":"measurement boundary only; dataset/prompt/model/public hypothesis unchanged"}
    print(json.dumps(out,indent=2));return 0

if __name__=="__main__":raise SystemExit(main())
