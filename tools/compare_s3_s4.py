#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def score(root: Path, results: Path):
    rows = []
    for fixture in sorted(p for p in root.iterdir() if p.is_dir()):
        hidden = load(fixture / "hidden" / "evaluation.json")
        result = load(results / (fixture.name + ".json"))
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
    n = max(1, len(rows))
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
    ap.add_argument("--llm", default="results/llm_s3_s4")
    args = ap.parse_args()
    root = Path(args.root)
    ec = score(root, Path(args.ec))
    llm = score(root, Path(args.llm))

    hash_mismatches = []
    for e, l in zip(ec["rows"], llm["rows"]):
        if e["fixture_id"] != l["fixture_id"] or e["candidate_set_hash"] != l["candidate_set_hash"] or e["semantic_state_hash"] != l["semantic_state_hash"]:
            hash_mismatches.append(e["fixture_id"])

    out = {
        "protocol": "FIXED_CANDIDATE_SELECTION_CONTROL_COMPARISON_V1",
        "controlled_upstream_hashes": not hash_mismatches,
        "hash_mismatches": hash_mismatches,
        "EC": {k: ec[k] for k in ("selection_accuracy", "reframe_accuracy", "closure_accuracy", "final_task_success")},
        "LLM": {k: llm[k] for k in ("selection_accuracy", "reframe_accuracy", "closure_accuracy", "final_task_success")},
    }
    out["delta_EC_minus_LLM"] = {k: out["EC"][k] - out["LLM"][k] for k in out["EC"]}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
