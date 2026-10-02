#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    contract = json.loads(read(CONTRACT))
    blockers: list[dict] = []
    passed: list[str] = []

    workflows = ROOT / ".github" / "workflows"
    if workflows.exists() and any(workflows.iterdir()):
        blockers.append({"id": "AC-20", "reason": "GITHUB_ACTIONS_PRESENT", "path": str(workflows.relative_to(ROOT))})
    else:
        passed.append("AC-20_NO_ACTIONS")

    qualification = ROOT / "results/phase1_v2_qualification_2026-10-03.json"
    if not qualification.exists():
        blockers.append({"id": "FOUNDATION", "reason": "QUALIFICATION_RESULT_MISSING"})
    else:
        q = json.loads(read(qualification))
        q_text = json.dumps(q, sort_keys=True)
        expected_digest = contract["canonical_inputs"]["phase1_v2_dataset_sha256"]
        if expected_digest not in q_text:
            blockers.append({"id": "FOUNDATION", "reason": "CANONICAL_DATASET_DIGEST_NOT_PROVEN", "expected": expected_digest})
        else:
            passed.append("FOUNDATION_QUALIFICATION_EVIDENCE")

    ec_runner = ROOT / "tools/run_ec_s3_s4.py"
    if not ec_runner.exists():
        blockers.append({"id": "ISSUE-20", "reason": "EC_RUNNER_MISSING"})
    else:
        text = read(ec_runner)
        required_markers = ["EC_V4_4_COMMIT", "EC_V4_4_RESIDUAL_DETECTOR_V1", "ec_provenance"]
        missing = [m for m in required_markers if m not in text]
        if missing or "FALLBACK_NO_EC_PATH" in text:
            blockers.append({
                "id": "ISSUE-20",
                "reason": "ACTUAL_ECV4_FAIL_CLOSED_BINDING_NOT_IMPLEMENTED",
                "missing_markers": missing,
                "silent_fallback_present": "FALLBACK_NO_EC_PATH" in text,
            })
        else:
            passed.append("ISSUE-20_ECV4_BINDING")

    llm_s34 = ROOT / "tools/run_llm_s3_s4_cache.py"
    if not llm_s34.exists():
        blockers.append({"id": "ISSUE-12", "reason": "LLM_S3_S4_RUNNER_MISSING"})
    else:
        text = read(llm_s34)
        required_markers = ["format_contract_ok", "schema_constrained", "raw_output_sha256"]
        missing = [m for m in required_markers if m not in text]
        if missing:
            blockers.append({"id": "ISSUE-12", "reason": "FORMAT_SEMANTIC_SEPARATION_INCOMPLETE", "missing_markers": missing})
        else:
            passed.append("ISSUE-12_FORMAT_SEMANTIC_SPLIT")

    issue22_files = [
        ROOT / "tools/run_llm_s1_s2_cache.py",
        ROOT / "tools/run_phase1_oracle_substitution.py",
        ROOT / "tools/score_phase1_mvp.py",
    ]
    missing_files = [str(p.relative_to(ROOT)) for p in issue22_files if not p.exists()]
    if missing_files:
        blockers.append({"id": "ISSUE-22", "reason": "S1_S2_ORACLE_GAIN_IMPLEMENTATION_MISSING", "missing_files": missing_files})
    else:
        passed.append("ISSUE-22_A_B_E_IMPLEMENTATION")

    threshold = contract.get("frozen_thresholds", {})
    threshold_required = [
        "oracle_substitution_gain_material_abs",
        "llm_vs_ec_joint_layer_difference_material_abs",
        "dominant_tie_max_difference",
        "capacity_collapse",
    ]
    threshold_missing = [k for k in threshold_required if k not in threshold]
    if threshold_missing:
        blockers.append({"id": "ISSUE-21", "reason": "THRESHOLD_CONTRACT_INCOMPLETE", "missing": threshold_missing})
    else:
        passed.append("ISSUE-21_THRESHOLDS_FROZEN")

    result = {
        "protocol": contract["protocol"],
        "contract_sha256": sha256(CONTRACT),
        "status": "PASS" if not blockers else "BLOCKED",
        "terminal_state": "P1_FOUNDATION_GATE" if not blockers else "INVALID_TEST_CONTRACT",
        "passed": passed,
        "blockers": blockers,
        "next_state_if_pass": "P1_FOUNDATION_GATE",
        "manual_midrun_repair_allowed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
