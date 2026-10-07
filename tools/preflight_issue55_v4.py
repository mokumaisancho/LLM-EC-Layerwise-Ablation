#!/usr/bin/env python3
"""#55 versioned acceptance. No V1/scientific asset mutation."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def run_test(name):
    x=subprocess.run([sys.executable,"-m","unittest","-v",name],cwd=ROOT,text=True,capture_output=True)
    return {"pass":x.returncode==0,"output":(x.stdout+x.stderr)[-12000:]}
def checks():
    research=json.loads((ROOT/"semantic_runtime/research_pins.json").read_text())["files"]
    product=json.loads((ROOT/"semantic_runtime/product_pins.json").read_text())["files"]
    return {
        "research_pins_21":len(research)==21 and all(blob(ROOT/p)==v for p,v in research.items()),
        "product_pins_11":len(product)==11 and all(blob(ROOT/p)==v for p,v in product.items()),
        "default_installed_policy_empty":json.loads((ROOT/"semantic_runtime/approved_policy_v3.json").read_text())["approvals"]==[],
        "manifest_research_sha":blob(ROOT/"semantic_runtime/research_pins.json")=="bdce80d5b6bfdc07a0d2ce799b099c0ed9ab22be",
        "manifest_product_sha":blob(ROOT/"semantic_runtime/product_pins.json")=="a87611cbc93638e262a07ec67afdcf8d936d740b",
    }
def main():
    suites={
        "v1":run_test("tests.test_semantic_runtime_product"),
        "v2":run_test("tests.test_semantic_runtime_execution_v2"),
        "v3":run_test("tests.test_semantic_runtime_operator_policy_v3"),
        "v4_real_installed":run_test("tests.test_semantic_runtime_operator_install_v4"),
    }
    gates=checks()
    passed=all(v["pass"] for v in suites.values()) and all(gates.values())
    out={"protocol":"SEMANTIC_RUNTIME_ISSUE55_V4_PREFLIGHT",
         "pass":passed,"terminal":"ISSUE55_V4_PRELIMINARY_PASS" if passed else "ISSUE55_V4_FAIL_CLOSED",
         "gates":gates,"suites":suites,"ecv4_final_audit_required":True}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if passed else 3
if __name__=="__main__":
    raise SystemExit(main())
