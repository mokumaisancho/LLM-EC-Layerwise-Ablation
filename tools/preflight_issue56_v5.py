#!/usr/bin/env python3
"""#56 V5 fail-closed grammar acceptance and frozen research/product integrity."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()

def check_pins(name, expected_count):
    pins=json.loads((ROOT/"semantic_runtime"/name).read_text())["files"]
    return len(pins)==expected_count and all((ROOT/path).exists() and blob(ROOT/path)==digest for path,digest in pins.items())

def suite(name):
    p=subprocess.run([sys.executable,"-m","unittest","-v",name],cwd=ROOT,text=True,capture_output=True,timeout=90)
    return {"pass":p.returncode==0,"output_tail":(p.stdout+p.stderr)[-12000:]}

def main():
    suites={
       "v5_real_installed_grammar":suite("tests.test_semantic_runtime_v5_grammar"),
       "v4_real_installed_authority":suite("tests.test_semantic_runtime_operator_install_v4"),
       "v2_forged_ir":suite("tests.test_semantic_runtime_execution_v2"),
       "v1_legacy_regression":suite("tests.test_semantic_runtime_product")
    }
    policy=json.loads((ROOT/"semantic_runtime/approved_policy_v5.json").read_text())
    checks={
      "frozen_research_21":check_pins("research_pins.json",21),
      "frozen_product_11":check_pins("product_pins.json",11),
      "v5_policy_default_deny":policy=={"protocol":"SEMANTIC_RUNTIME_APPROVED_POLICY_V5","approvals":[]},
      "v4_policy_default_deny":json.loads((ROOT/"semantic_runtime/approved_policy_v3.json").read_text())["approvals"]==[]
    }
    passed=all(x["pass"] for x in suites.values()) and all(checks.values())
    out={"protocol":"ISSUE56_V5_GRAMMAR_PREFLIGHT_V1","issue":56,
         "terminal":"ISSUE56_V5_REGRESSION_PASS" if passed else "ISSUE56_V5_REGRESSION_FAIL_CLOSED",
         "pass":passed,"checks":checks,"suites":suites}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if passed else 3

if __name__=="__main__":
    raise SystemExit(main())
