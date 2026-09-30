#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def select_candidates(candidate_set: dict) -> tuple[list[str], list[str], list[dict]]:
    selected, rejected, reasons = [], [], []
    for candidate in candidate_set.get("candidates", []):
        cid = candidate.get("candidate_id")
        evidence = [x for x in candidate.get("evidence_refs", []) if str(x).strip()]
        dependencies = [x for x in candidate.get("dependencies", []) if str(x).strip()]
        # Deterministic evidence admission: unsupported candidates do not enter the selected frontier.
        admitted = bool(evidence and dependencies)
        if admitted:
            selected.append(cid)
            reasons.append({"candidate_id": cid, "decision": "SELECT", "rule": "EVIDENCE_AND_DEPENDENCY_PRESENT"})
        else:
            rejected.append(cid)
            reasons.append({"candidate_id": cid, "decision": "REJECT", "rule": "EVIDENCE_OR_DEPENDENCY_MISSING"})
    return selected, rejected, reasons


def fallback_residuals(state: dict) -> list[dict]:
    variables = state["framing"]["variables"]
    explained = {
        str(obs)
        for variable in variables.values()
        for obs in variable.get("explains", [])
    }
    out = []
    for observation in state.get("observations", []):
        oid = observation.get("observation_id")
        if oid and oid not in explained:
            out.append({"type": "UNEXPLAINED_OBSERVATION", "subject": oid})
    return out


def ec_residuals(state: dict):
    ec_root = os.environ.get("EC_V4_4_PYTHONPATH")
    if ec_root:
        sys.path.insert(0, ec_root)
        try:
            mod = importlib.import_module("v4.ec_residual_detector")
            result = mod.detect_residuals(state["intent"], state["framing"], observations=state.get("observations", []))
            return result.get("residuals", []), result.get("protocol"), "ECV4_4"
        except Exception as exc:
            return fallback_residuals(state), None, "FALLBACK:" + type(exc).__name__
    return fallback_residuals(state), None, "FALLBACK_NO_EC_PATH"


def closure_decision(candidate_set: dict, selected: list[str], state: dict, residuals: list[dict]):
    ops = {
        c.get("candidate_id"): (c.get("semantic_transition") or {}).get("operation")
        for c in candidate_set.get("candidates", [])
    }
    selected_ops = [ops.get(cid) for cid in selected]
    if len(selected) > 1:
        return "CONTINUE", [{"type": "MULTIPLE_ADMISSIBLE_BRANCHES"}]
    if any("unresolved" in str(v.get("semantic_key", "")).lower() for v in state["framing"]["variables"].values()):
        return "CONTINUE", [{"type": "REQUIRED_CONDITION_UNRESOLVED"}]
    # A selected framing-expansion operation is allowed to resolve an unexplained-observation residual.
    if residuals and any(str(op).startswith(("ADD_", "REFRAME_")) for op in selected_ops if op):
        return "CLOSE", []
    if residuals:
        return "CONTINUE", residuals
    return "CLOSE", []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="fixtures/phase1_v2/generated")
    ap.add_argument("--out", default="results/ec_s3_s4")
    args = ap.parse_args()
    root, out_root = Path(args.root), Path(args.out)
    rows = []
    for fixture in sorted(p for p in root.iterdir() if p.is_dir()):
        s2 = load_json(fixture / "oracle" / "s2_candidate_set.json")
        state = load_json(fixture / "upstream" / "s3_semantic_state.json")
        selected, rejected, reasons = select_candidates(s2)
        residuals, protocol, mode = ec_residuals(state)
        reframe = bool(residuals)
        closure, closure_residuals = closure_decision(s2, selected, state, residuals)
        result = {
            "fixture_id": fixture.name,
            "implementation": "EC",
            "ec_mode": mode,
            "ec_protocol": protocol,
            "upstream": {
                "candidate_set_hash": s2.get("content_hash"),
                "semantic_state_hash": state.get("content_hash")
            },
            "s3": {
                "selected_candidate_ids": selected,
                "rejected_candidate_ids": rejected,
                "decision_reasons": reasons,
                "residuals": residuals,
                "reframe_required": reframe
            },
            "s4": {
                "closure_class": closure,
                "residuals": closure_residuals
            }
        }
        out = out_root / (fixture.name + ".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows.append(result)
    print(json.dumps({"run": "EC_S3_S4", "fixture_count": len(rows), "result_count": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
