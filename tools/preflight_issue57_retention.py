#!/usr/bin/env python3
"""#57 preflight: methodology is executable; non-degradation claim remains blocked."""
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

def pincheck(name,count):
    d=json.loads((ROOT/"semantic_runtime"/name).read_text())["files"]
    return len(d)==count and all((ROOT/k).is_file() and blob(ROOT/k)==v for k,v in d.items())

def cmd(*args):
    return subprocess.run([sys.executable,*args],cwd=ROOT,check=False,capture_output=True,text=True,timeout=90)

def main():
    unit=cmd("-m","unittest","-v","tests.test_capability_retention_v1")
    historic=cmd("tools/run_capability_retention_historical_v1.py")
    try:
        data=json.loads(historic.stdout)
        t=data["report"]["adjacent_transitions"]["V1_TO_V5"]
        record={
            "terminal":data["terminal"],
            "benchmark_sha256":data["report"]["input_benchmark_sha256"],
            "V1_metrics":data["report"]["arm_metrics"]["V1"],
            "V5_metrics":data["report"]["arm_metrics"]["V5"],
            "lost_wrong":t["correct_to_wrong"],
            "lost_abstain":t["correct_to_abstain"],
            "gained":t["incorrect_to_correct"],
            "critical_losses":t["critical_losses"],
            "tail_losses":t["tail_losses"],
            "full_blocker":data["full_comparison_blocker"],
            "LLM0":data["original_llm_same_input"],
            "labels_blob":data["frozen_gold_label_blob"],
        }
    except (KeyError,TypeError,ValueError):
        record={"terminal":"INVALID_DIAGNOSTIC_RUN","raw_tail":historic.stdout[-1500:],"stderr":historic.stderr[-1500:]}
    checks={
       "unit_tests_16":unit.returncode==0 and "Ran 16 tests" in unit.stderr and "OK" in unit.stderr,
       "diagnostic_runner":historic.returncode==0,
       "historical_only":record["terminal"]=="HISTORICAL_DIAGNOSTIC_COMPLETE_FULL_QUALITY_BLOCKED",
       "no_original_llm_imputed":record.get("LLM0")=="MISSING_NOT_INFERRED",
       "full_holdout_blocker":record.get("full_blocker")=="FULL_COMPARISON_REQUIRES_INDEPENDENT_BENCHMARK",
       "product_pin_11":pincheck("product_pins.json",11),
       "research_pin_21":pincheck("research_pins.json",21),
    }
    ok=all(checks.values())
    out={
       "protocol":"ISSUE57_RETENTION_GATE_PREFLIGHT_V1",
       "terminal":"CAPABILITY_RETENTION_GATE_IMPLEMENTED_QUALITY_UNPROVEN" if ok else "CAPABILITY_RETENTION_GATE_FAILURE",
       "gate_implemented":ok,
       "original_llm_comparison_complete":False,
       "independent_generalization_evaluation_complete":False,
       "checks":checks,
       "retrospective_diagnostic":record,
       "unit_test_failure_tail":"" if unit.returncode==0 else unit.stderr[-3000:],
       "diagnostic_failure_tail":"" if historic.returncode==0 else historic.stderr[-3000:]
    }
    print(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2))
    return 0 if ok else 3

if __name__=="__main__":
    raise SystemExit(main())
