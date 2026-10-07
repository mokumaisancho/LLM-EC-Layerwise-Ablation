#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/"tools"


def fail(detail:str)->None:
    print(json.dumps({"terminal":"IMPLEMENTATION_PREFLIGHT_FAILED","detail":detail},indent=2))
    raise SystemExit(2)


def main()->int:
    if os.environ.get("PRODUCT_RUNTIME_EVIDENCE") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"evidence_product_semantic_runtime.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"product_runtime_evidence_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr: sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("PRODUCT_RUNTIME_REGRESSION") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"regress_product_runtime_v32_compat.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"product_runtime_regression_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr: sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("PRODUCT_RUNTIME_PREFLIGHT") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"preflight_product_semantic_runtime.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"product_runtime_preflight_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr: sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_V32_POSTRUN") == "1":
        runtime=ROOT/"results"/"s1c_v32_paired_actual_2026-10-08.json"
        audit=ROOT/"results"/"s1c_v32_postrun_audit_actual_2026-10-08.json"
        replay=ROOT/"results"/"s1c_v32_fixed_b2_replay_actual_2026-10-08.json"
        terminal=ROOT/"results"/"s1c_v32_terminal_actual_2026-10-08.json"
        a=subprocess.run([sys.executable,str(TOOLS/"audit_s1c_v32_independent.py"),str(runtime),"--output",str(audit)],cwd=ROOT,text=True,capture_output=True)
        sys.stdout.write(a.stdout)
        if a.stderr: sys.stderr.write(a.stderr)
        if a.returncode: return a.returncode
        r=subprocess.run([sys.executable,str(TOOLS/"replay_s1c_v32_fixed_b2.py"),str(runtime),str(audit),"--output",str(replay)],cwd=ROOT,text=True,capture_output=True)
        sys.stdout.write(r.stdout)
        if r.stderr: sys.stderr.write(r.stderr)
        if r.returncode: return r.returncode
        t=subprocess.run([sys.executable,str(TOOLS/"classify_s1c_v32_terminal.py"),str(audit),str(replay),"--output",str(terminal)],cwd=ROOT,text=True,capture_output=True)
        sys.stdout.write(t.stdout)
        if t.stderr: sys.stderr.write(t.stderr)
        return t.returncode
    if os.environ.get("S1C_V32_RUNNER_PREFLIGHT") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"preflight_s1c_v32_runner.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"s1c_v32_runner_preflight_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_V32_PAIRED") == "1":
        import base64, hashlib
        q=subprocess.run([sys.executable,str(TOOLS/"run_s1c_v32_paired_v1.py")],cwd=ROOT,text=True,capture_output=True)
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        evidence=ROOT/"s1c_v32_paired_runtime.json"
        if evidence.exists():
            raw=evidence.read_bytes()
            b64=base64.b64encode(raw).decode("ascii")
            chunk_size=3000
            chunks=[b64[i:i+chunk_size] for i in range(0,len(b64),chunk_size)]
            print("S1C_V32_EVIDENCE_MANIFEST="+json.dumps({"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"chunks":len(chunks)},separators=(",",":")))
            for i,chunk in enumerate(chunks,1):
                print(f"S1C_V32_EVIDENCE_CHUNK={i}/{len(chunks)}:{chunk}")
        else:
            print("S1C_V32_EVIDENCE_MISSING")
        return q.returncode
    if os.environ.get("S1C_V31_RUNNER_PREFLIGHT") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"preflight_s1c_v31_runner.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"s1c_v31_runner_preflight_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_V31_PAIRED") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"run_s1c_v31_paired_v1.py")],cwd=ROOT,text=True,capture_output=True)
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_V31_SCHEMA_SMOKE") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"smoke_s1c_v31_json_schema_runtime.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"s1c_v31_schema_smoke_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_V31_PREFLIGHT") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"preflight_s1c_v31.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"s1c_v31_preflight_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_V_V2_RUN") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"run_s1c_v_paired_v2.py")],cwd=ROOT,text=True,capture_output=True)
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_V_V2_RUNNER_PREFLIGHT") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"preflight_s1c_v_runner_v2.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"s1c_v_v2_runner_preflight_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_V_RUN") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"run_s1c_v_paired_v1.py")],cwd=ROOT,text=True,capture_output=True)
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_V_RUNNER_PREFLIGHT") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"preflight_s1c_v_runner.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"s1c_v_runner_preflight_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_V_PREFLIGHT") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"preflight_s1c_v.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"s1c_v_preflight_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_R_POSTRUN") == "1":
        runtime=ROOT/"results"/"function_boundary_s1c_r_paired_actual_2026-10-07.json"
        audit=ROOT/"results"/"function_boundary_s1c_r_postrun_audit_runtime.json"
        replay=ROOT/"results"/"function_boundary_s1c_r_fixed_b2_replay_runtime.json"
        a=subprocess.run([sys.executable,str(TOOLS/"audit_s1c_r_paired_v1.py"),str(runtime),"--output",str(audit)],cwd=ROOT,text=True,capture_output=True)
        sys.stdout.write(a.stdout)
        if a.stderr:
            sys.stderr.write(a.stderr)
        if a.returncode:
            return a.returncode
        r=subprocess.run([sys.executable,str(TOOLS/"replay_s1c_r_fixed_b2.py"),str(runtime),str(audit),"--output",str(replay)],cwd=ROOT,text=True,capture_output=True)
        sys.stdout.write(r.stdout)
        if r.stderr:
            sys.stderr.write(r.stderr)
        return r.returncode
    if os.environ.get("S1C_R_RUNNER_PREFLIGHT") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"preflight_s1c_r_runner.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"s1c_r_runner_preflight_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_R_PAIRED") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"run_s1c_r_paired_v1.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"s1c_r_paired_console.txt").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    if os.environ.get("S1C_R_PREFLIGHT") == "1":
        q=subprocess.run([sys.executable,str(TOOLS/"preflight_s1c_r.py")],cwd=ROOT,text=True,capture_output=True)
        (ROOT/"s1c_r_preflight_result.json").write_text(q.stdout,encoding="utf-8")
        sys.stdout.write(q.stdout)
        if q.stderr:
            sys.stderr.write(q.stderr)
        return q.returncode
    active=set()
    for pattern in ("*s2b2b1*.py","preflight_s2b2b1.py","preflight_s2b2_v3_static.py"):
        active.update(TOOLS.glob(pattern))
    required={TOOLS/"s2b2b1_schema_synth_core.py",TOOLS/"score_s2b2b1_schema_synth.py",TOOLS/"generate_s2b2b1_schema_synth_holdout.py",TOOLS/"preflight_s2b2b1.py"}
    if not required.issubset(active) or any(not p.exists() for p in required): fail("required active B1 file missing")
    compiled=[]
    for p in sorted(active):
        try: py_compile.compile(str(p),doraise=True)
        except Exception as e: fail(f"py_compile:{p.name}:{e}")
        compiled.append(p.name)
    smoke="import sys; sys.path.insert(0,'tools'); import s2b2b1_schema_synth_core, score_s2b2b1_schema_synth, generate_s2b2b1_schema_synth_holdout, preflight_s2b2b1; print('IMPORT_SMOKE_PASS')"
    p=subprocess.run([sys.executable,"-c",smoke],cwd=ROOT,text=True,capture_output=True)
    if p.returncode or "IMPORT_SMOKE_PASS" not in p.stdout: fail("import smoke:"+(p.stderr or p.stdout))
    q=subprocess.run([sys.executable,str(TOOLS/"preflight_s2b2b1.py")],cwd=ROOT,text=True,capture_output=True)
    if q.returncode: fail("scientific preflight:"+(q.stderr or q.stdout))
    try: scientific=json.loads(q.stdout)
    except Exception as e: fail(f"scientific preflight output parse:{e}")
    if scientific.get("terminal")!="B1_PREFLIGHT_PASS": fail("scientific terminal not PASS")
    out={"terminal":"V3_L00_IMPLEMENTATION_STATIC_VALID","protocol":"S2B2_MVP_TCC_V3","compiled":compiled,"import_smoke":"PASS","scientific_preflight":scientific,"model_acquisition_authorized":True}
    print(json.dumps(out,indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
