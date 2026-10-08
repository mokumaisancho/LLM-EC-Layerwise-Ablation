#!/usr/bin/env python3
"""Issue58 scientific-evaluation method preflight; no synthetic scientific claim."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def pinned(name,count):
    d=json.loads((ROOT/"semantic_runtime"/name).read_text())["files"]
    return len(d)==count and all((ROOT/path).is_file() and blob(ROOT/path)==sha for path,sha in d.items())

def unit(module):
    p=subprocess.run([sys.executable,"-m","unittest","-v",module],
                     cwd=ROOT,capture_output=True,text=True,timeout=90)
    output=p.stdout+p.stderr
    count=re.search(r"\\bRan (\\d+) tests? in ",output)
    return {"pass":p.returncode==0 and count is not None,
            "test_count":int(count.group(1)) if count else None,
            "tail":output[-5000:]}

def main():
    tests={
        "blind_evaluator":unit("tests.test_quality_blind_v2"),
        "three_stage_cli":unit("tests.test_quality_blind_cli_v2"),
        "legacy_retention":unit("tests.test_capability_retention_v1"),
    }
    checks={
        "research_21_unchanged":pinned("research_pins.json",21),
        "product_11_unchanged":pinned("product_pins.json",11),
        "evaluation_only_no_product_import":not any(
            "evaluation.quality_blind_v2" in (ROOT/path).read_text(encoding="utf-8")
            for path in ("semantic_runtime/runtime.py","semantic_runtime/discovery.py",
                         "semantic_runtime/constrained_v5.py","semantic_runtime/execution_v4.py")),
        "no_historical_fixture_import_in_v2_evaluator":
            "tests.test_semantic_runtime_v5_grammar" not in
            (ROOT/"evaluation/quality_blind_v2.py").read_text(encoding="utf-8"),
        "no_ORACLE_read_in_v2_evaluator":
            "historical_labels_v1.json" not in
            (ROOT/"evaluation/quality_blind_v2.py").read_text(encoding="utf-8"),
    }
    passed=all(x["pass"] for x in tests.values()) and all(checks.values())
    print(json.dumps({
        "protocol":"ISSUE58_BLIND_EVALUATION_METHOD_PREFLIGHT_V1",
        "terminal":"ISSUE58_METHOD_CODE_PASS_REAL_FOUR_ARM_PENDING" if passed else "ISSUE58_METHOD_FAILURE",
        "pass":passed,
        "checks":checks,"tests":tests,
        "source_gold_independence_proven":False,
        "actual_llm_v1_v4_v5_comparison_performed":False,
        "external_provenance_required":True,
        "claim_limit":"Independent unseen data and genuine frozen raw LLM/V1/V4/V5 runs cannot be simulated by unit tests."
    },ensure_ascii=False,sort_keys=True,indent=2))
    return 0 if passed else 3

if __name__=="__main__":
    raise SystemExit(main())
