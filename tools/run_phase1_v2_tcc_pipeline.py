#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

TCC_SKILL_PATH = os.environ.get("TCC_SKILL_PATH", "../Skills/skills/tcc/scripts")
sys.path.insert(0, TCC_SKILL_PATH)
from tcc import ToolScript


def run_step(script: ToolScript, name: str, cmd: str, timeout: int = 60):
    output, rc = script.run(cmd, timeout=timeout)
    script.set(name, {"rc": rc, "output": output[-6000:] if output else ""})
    if rc != 0:
        script.add_error(f"{name} failed with rc={rc}")
        print(script.output())
        raise SystemExit(rc)
    return output


def main():
    script = ToolScript("phase1-v2-coarse-ablation-qualification")

    run_step(script, "generate_measurement", "python3 tools/generate_phase1_measurement_v2_canonical.py")
    run_step(script, "generate_s3_states", "python3 tools/generate_phase1_v2_s3_states.py")

    leak = run_step(script, "leakage_gate", "python3 tools/scan_phase1_v2_leakage_tcc.py")
    try:
        leak_doc = json.loads(leak)
        if leak_doc.get("results", {}).get("status") != "PASS":
            script.add_error("leakage gate did not PASS")
            print(script.output())
            raise SystemExit(2)
    except json.JSONDecodeError:
        script.add_error("leakage gate output was not valid TCC JSON")
        print(script.output())
        raise SystemExit(2)

    run_step(script, "ec_s3_s4", "python3 tools/run_ec_s3_s4.py")
    score = run_step(script, "score_ec_s3_s4", "python3 tools/score_ec_s3_s4.py")
    try:
        score_doc = json.loads(score)
        script.set("ec_qualification_summary", {
            "selection_accuracy": score_doc.get("selection_accuracy"),
            "reframe_accuracy": score_doc.get("reframe_accuracy"),
            "closure_accuracy": score_doc.get("closure_accuracy"),
            "final_task_success": score_doc.get("final_task_success"),
        })
    except json.JSONDecodeError:
        script.add_error("score output was not JSON")

    script.set("status", "PASS" if not script.errors else "BLOCKED")
    print(script.output())


if __name__ == "__main__":
    main()
