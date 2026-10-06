#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROTOCOL = "S1C_V_TERMINAL_CLASSIFIER_V1"
MATERIALITY = 0.20
PRIMARY_KEYS = (
    "training_partition_pairwise_accuracy",
    "heldout_denotational_assignment_accuracy",
    "exact_discovery_and_grounding_rate",
)


def fail(reason: str, detail: Any = None) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "pass": False,
        "terminal": "S1C_V_TERMINAL_FAIL_CLOSED",
        "reason": reason,
        "detail": detail,
        "boundary_update_authorized": False,
    }


def classify(audit: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
    if audit.get("terminal") != "S1C_V_POSTRUN_AUDIT_PASS" or audit.get("pass") is not True:
        return fail("POSTRUN_AUDIT_NOT_PASS")
    if replay.get("terminal") != "S1C_V_FIXED_B2_CAUSAL_REPLAY_PASS" or replay.get("pass") is not True:
        return fail("CAUSAL_REPLAY_NOT_PASS")
    if audit.get("result_overturning_gate_failures") != 0:
        return fail("RESULT_OVERTURNING_GATE_FAILURES_NONZERO")

    det = audit["deterministic"]["primary"]
    qwen = audit["qwen25_1p5b"]["primary"]
    deltas = {k: float(qwen[k]) - float(det[k]) for k in PRIMARY_KEYS}
    deltas["fixed_b2_downstream_success"] = float(replay["qwen25_1p5b_downstream_success"]) - float(replay["deterministic_downstream_success"])

    qwen_material = {k: v for k, v in deltas.items() if v >= MATERIALITY}
    deterministic_material = {k: v for k, v in deltas.items() if v <= -MATERIALITY}

    if qwen_material and deterministic_material:
        return fail("CONFLICTING_MATERIAL_DIRECTIONS", {
            "deltas_qwen_minus_deterministic": deltas,
            "qwen_material": qwen_material,
            "deterministic_material": deterministic_material,
        })

    if qwen_material:
        terminal = "V_LLM_MATERIAL_ADVANTAGE"
        interpretation = "LLM retains a material advantage in at least one predeclared semantic-space discovery/grounding or downstream causal metric."
    elif deterministic_material:
        terminal = "V_DETERMINISTIC_MATERIAL_ADVANTAGE"
        interpretation = "Deterministic external machinery has a material advantage in at least one predeclared semantic-space discovery/grounding or downstream causal metric, with no material metric favoring Qwen."
    else:
        terminal = "V_NO_MATERIAL_SEPARATION"
        interpretation = "No predeclared semantic-space discovery/grounding or downstream causal metric separates the two arms by the materiality threshold."

    return {
        "protocol": PROTOCOL,
        "pass": True,
        "terminal": terminal,
        "materiality_abs": MATERIALITY,
        "deltas_qwen_minus_deterministic": deltas,
        "qwen_material_metrics": qwen_material,
        "deterministic_material_metrics": deterministic_material,
        "interpretation": interpretation,
        "boundary_update_authorized": True,
        "single_boundary_update_required": True,
        "claim_limit": "Only the frozen MVP-V denotational supervision regime is classified. Open-ended world knowledge and unrestricted ontology invention remain outside scope.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("audit_json", type=Path)
    ap.add_argument("replay_json", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    audit = json.loads(args.audit_json.read_text(encoding="utf-8"))
    replay = json.loads(args.replay_json.read_text(encoding="utf-8"))
    result = classify(audit, replay)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result.get("pass") else 3


if __name__ == "__main__":
    raise SystemExit(main())
