#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="fixtures/phase1_v2/generated")
    ap.add_argument("--results", default="results/ec_s3_s4")
    args = ap.parse_args()
    root, results = Path(args.root), Path(args.results)

    rows = []
    for fixture in sorted(p for p in root.iterdir() if p.is_dir()):
        hidden = load(fixture / "hidden" / "evaluation.json")
        result = load(results / (fixture.name + ".json"))
        expected = set(hidden["acceptable_candidate_ids"])
        selected = set(result["s3"]["selected_candidate_ids"])
        selection_exact = selected == expected
        reframe_correct = bool(result["s3"]["reframe_required"]) == bool(hidden["reframe_required"])
        closure_correct = result["s4"]["closure_class"] == hidden["closure_class"]
        rows.append({
            "fixture_id": fixture.name,
            "selection_exact": selection_exact,
            "reframe_correct": reframe_correct,
            "closure_correct": closure_correct,
            "final_task_success": selection_exact and reframe_correct and closure_correct,
            "ec_mode": result.get("ec_mode")
        })

    n = max(1, len(rows))
    summary = {
        "fixture_count": len(rows),
        "selection_accuracy": sum(r["selection_exact"] for r in rows) / n,
        "reframe_accuracy": sum(r["reframe_correct"] for r in rows) / n,
        "closure_accuracy": sum(r["closure_correct"] for r in rows) / n,
        "final_task_success": sum(r["final_task_success"] for r in rows) / n,
        "rows": rows,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
