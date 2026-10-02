#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def score(root: Path, results: Path, implementation: str):
    rows = []
    for fixture in sorted(p for p in root.iterdir() if p.is_dir()):
        hidden = load(fixture / "hidden" / "evaluation.json")
        result = load(results / (fixture.name + ".json"))

        if implementation == "LLM":
            if not result.get("format_contract_ok") or not result.get("semantic_metrics_eligible"):
                raise RuntimeError(f"LLM_RESULT_NOT_REPORTABLE:{fixture.name}")
            if result.get("measurement_mode") != "schema_constrained":
                raise RuntimeError(f"LLM_NOT_SCHEMA_CONSTRAINED:{fixture.name}")
        elif implementation == "EC":
            provenance = result.get("ec_provenance") or {}
            if result.get("ec_mode") != "ECV4_4_REPORTABLE" or not provenance.get("reportable"):
                raise RuntimeError(f"EC_RESULT_NOT_REPORTABLE:{fixture.name}")

        if not isinstance(result.get("s3"), dict) or not isinstance(result.get("s4"), dict):
            raise RuntimeError(f"LAYER_RESULT_MISSING:{fixture.name}")

        expected = set(hidden["acceptable_candidate_ids"])
        selected = set(result["s3"]["selected_candidate_ids"])
        rows.append({
            "fixture_id": fixture.name,
            "selection": selected == expected,
            "reframe": bool(result["s3"]["reframe_required"]) == bool(hidden["reframe_required"]),
            "closure": result["s4"]["closure_class"] == hidden["closure_class"],
            "candidate_set_hash": result["upstream"]["candidate_set_hash"],
            "semantic_state_hash": result["upstream"]["semantic_state_hash"],
        })
    if not rows:
        raise RuntimeError("NO_RESULTS")
    n = len(rows)
    return {
        "selection_accuracy": sum(x["selection"] for x in rows) / n,
        "reframe_accuracy": sum(x["reframe"] for x in rows) / n,
        "closure_accuracy": sum(x["closure"] for x in rows) / n,
        "final_task_success": sum(x["selection"] and x["reframe"] and x["closure"] for x in rows) / n,
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="fixtures/phase1_v2/generated")
    ap.add_argument("--ec", default="results/ec_s3_s4")
    ap.add_argument("--llm", default="results/llm_s3_s4/schema_constrained")
    args = ap.parse_args()
    root = Path(args.root)
    ec = score(root, Path(args.ec), "EC")
    llm = score(root, Path(args.llm), "LLM")

    hash_mismatches = []
    for e, l in zip(ec["rows"], llm["rows"]):
        if (
            e["fixture_id"] != l["fixture_id"]
            or e["candidate_set_hash"] != l["candidate_set_hash"]
            or e["semantic_state_hash"] != l["semantic_state_hash"]
        ):
            hash_mismatches.append(e["fixture_id"])
    if hash_mismatches:
        raise RuntimeError("UPSTREAM_HASH_MISMATCH:" + ",".join(hash_mismatches))

    out = {
        "protocol": "FIXED_CANDIDATE_SELECTION_CONTROL_COMPARISON_V2",
        "controlled_upstream_hashes": True,
        "hash_mismatches": [],
        "EC": {k: ec[k] for k in ("selection_accuracy", "reframe_accuracy", "closure_accuracy", "final_task_success")},
        "LLM": {k: llm[k] for k in ("selection_accuracy", "reframe_accuracy", "closure_accuracy", "final_task_success")},
    }
    out["delta_EC_minus_LLM"] = {k: out["EC"][k] - out["LLM"][k] for k in out["EC"]}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
