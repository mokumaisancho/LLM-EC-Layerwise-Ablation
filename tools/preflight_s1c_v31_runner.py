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
PROTOCOL="S1C_V31_RUNNER_PREFLIGHT_V1"

EXPECTED={
 "tools/run_s1c_v31_paired_v1.py":"99e3b30259246a2b3c81ce79dcdacfdfafca4b92",
 "tools/audit_s1c_v31_independent.py":"b7b116d9705213facd5dbc7348e65717600d1ae9",
 "tools/replay_s1c_v31_fixed_b2.py":"da0fc48d530dd19f06f81f3aec7d8ec680dd2cb9",
 "tools/classify_s1c_v31_terminal.py":"6c71fdd9b90003f17dc0d3eca10c54bcfc14fc2b",
}

def blob(path:Path)->str:
    import hashlib
    raw=path.read_bytes();h=hashlib.sha1();h.update(f"blob {len(raw)}\0".encode());h.update(raw);return h.hexdigest()

def fail(reason,detail=None):
    print(json.dumps({"protocol":PROTOCOL,"pass":False,"terminal":"S1C_V31_RUNNER_PREFLIGHT_FAIL_CLOSED","reason":reason,"detail":detail},indent=2));return 3

def main()->int:
    for rel,expected in EXPECTED.items():
        p=ROOT/rel
        if not p.exists():return fail("SOURCE_MISSING",rel)
        got=blob(p)
        if got!=expected:return fail("SOURCE_DRIFT",{"path":rel,"actual":got,"expected":expected})
        try:py_compile.compile(str(p),doraise=True)
        except Exception as exc:return fail("PY_COMPILE_FAILED",{"path":rel,"error":repr(exc)})

    p=subprocess.run([sys.executable,str(TOOLS/"preflight_s1c_v31.py")],cwd=ROOT,text=True,capture_output=True)
    if p.returncode:return fail("SCIENTIFIC_PREFLIGHT_FAILED",p.stderr or p.stdout)
    pre=json.loads(p.stdout)
    if pre.get("terminal")!="S1C_V31_PREFLIGHT_PASS":return fail("SCIENTIFIC_PREFLIGHT_NOT_PASS")

    smoke=json.loads((ROOT/"results"/"s1c_v31_schema_smoke_actual_2026-10-08.json").read_text())
    if smoke.get("terminal")!="S1C_V31_SYNTHETIC_JSON_SCHEMA_RUNTIME_SMOKE_PASS" or smoke.get("paired_model_inference_authorized") is not True:
        return fail("SCHEMA_RUNTIME_SMOKE_NOT_PASS")

    sys.path.insert(0,str(TOOLS))
    try:
        import run_s1c_v31_paired_v1 as runner
        import generate_s1c_v31_corpus as generator
        import s1c_v31_json_schema as schema
    except Exception as exc:return fail("IMPORT_FAILED",repr(exc))

    src=inspect.getsource(runner.qwen_predict)
    required=("canon(visible)","json_schema")
    if any(x not in src for x in required):return fail("PROMPT_VISIBLE_BINDING_MISSING",required)
    forbidden=("canon(oracle)","REFERENCE[","TASK_SPECS","training_gold","slot_references","target_code")
    bad=[x for x in forbidden if x in src]
    if bad:return fail("QWEN_PROMPT_HIDDEN_REFERENCE_ACCESS",bad)

    corpus=generator.build_corpus()
    if corpus.get("task_count")!=8:return fail("TASK_COUNT")
    schema_rows=[]
    for task in corpus["tasks"]:
        row=schema.static_contract_check(task);schema_rows.append({"task_id":task["task_id"],"pass":row["pass"]})
        if row.get("pass") is not True:return fail("SCHEMA_STATIC_FAIL",{"task_id":task["task_id"],"failures":row["failures"]})

    out={"protocol":PROTOCOL,"pass":True,"terminal":"S1C_V31_RUNNER_PREFLIGHT_PASS","source_blob_pins":EXPECTED,
         "scientific_preflight_terminal":pre["terminal"],"schema_smoke_terminal":smoke["terminal"],
         "qwen_prompt_visible_only_gate":"PASS","schema_rows":schema_rows,"model_inference_executed":False,
         "paired_model_inference_authorized":True}
    print(json.dumps(out,indent=2));return 0

if __name__=="__main__":raise SystemExit(main())
