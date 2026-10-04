#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from s2b2a_composition_core import canonical_candidate_set, compose

PROTOCOL = "FUNCTION_BOUNDARY_S2B2A_COMPOSITION_HOLDOUT_V1"


def _sig(candidate: dict) -> str:
    return json.dumps(candidate, sort_keys=True, separators=(",", ":"))


def validate_fixture(fixture: dict) -> None:
    visible = fixture["visible"]
    gold = canonical_candidate_set(fixture["oracle"]["candidates"])
    existing = canonical_candidate_set(visible.get("existing_candidates", []))
    primitive_classes = {p["action_class"] for p in visible["primitive_actions"]}

    if set(map(_sig, gold)) & set(map(_sig, existing)):
        raise ValueError(f"{fixture['id']}: gold candidate instance leaked into existing_candidates")
    if any(c["action_class"] not in primitive_classes for c in gold):
        raise ValueError(f"{fixture['id']}: Stage A gold action class missing from primitive ontology")
    forbidden_top = {"gold", "oracle", "category", "family"} & set(visible)
    if forbidden_top:
        raise ValueError(f"{fixture['id']}: hidden fields exposed in visible: {sorted(forbidden_top)}")


def score(fixtures: list[dict]) -> dict:
    tp = emitted = gold_total = exact = 0
    invalid = fail_open = 0
    per_fixture = {}
    fam = defaultdict(lambda: {"tp":0,"emitted":0,"gold":0,"fixtures":0,"exact":0,"fail_open":0})

    for fixture in fixtures:
        validate_fixture(fixture)
        pred = canonical_candidate_set(compose(fixture["visible"]))
        gold = canonical_candidate_set(fixture["oracle"]["candidates"])
        pred_s, gold_s = set(map(_sig, pred)), set(map(_sig, gold))
        hit = len(pred_s & gold_s)
        fixture_fail_open = len(pred_s - gold_s)

        tp += hit
        emitted += len(pred_s)
        gold_total += len(gold_s)
        exact += int(pred_s == gold_s)
        fail_open += fixture_fail_open

        family = fixture["family"]
        f = fam[family]
        f["tp"] += hit; f["emitted"] += len(pred_s); f["gold"] += len(gold_s); f["fixtures"] += 1
        f["exact"] += int(pred_s == gold_s); f["fail_open"] += fixture_fail_open

        per_fixture[fixture["id"]] = {
            "family": family,
            "predicted": pred,
            "gold": gold,
            "tp": hit,
            "emitted": len(pred_s),
            "gold_count": len(gold_s),
            "exact": pred_s == gold_s,
            "fail_open": fixture_fail_open,
        }

    recall = tp / gold_total if gold_total else 1.0
    precision = tp / emitted if emitted else 0.0
    f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
    family_metrics = {}
    for name, v in sorted(fam.items()):
        r = v["tp"] / v["gold"] if v["gold"] else 1.0
        p = v["tp"] / v["emitted"] if v["emitted"] else 0.0
        family_metrics[name] = {
            **v,
            "recall": r,
            "precision": p,
            "f1": 2*r*p/(r+p) if r+p else 0.0,
            "exact_set_rate": v["exact"] / v["fixtures"] if v["fixtures"] else 0.0,
        }

    return {
        "candidate_recall": recall,
        "candidate_precision": precision,
        "f1": f1,
        "exact_set_rate": exact / len(fixtures) if fixtures else 0.0,
        "true_positive_total": tp,
        "emitted_total": emitted,
        "gold_total": gold_total,
        "invalid_output_count": invalid,
        "forbidden_fail_open_count": fail_open,
        "family_metrics": family_metrics,
        "per_fixture": per_fixture,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture_json", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    raw = args.fixture_json.read_bytes()
    data = json.loads(raw)
    if data.get("protocol") != PROTOCOL:
        raise SystemExit("wrong protocol")
    fixtures = data["fixtures"]
    metrics = score(fixtures)

    out = {
        "schema_version": "FUNCTION_BOUNDARY_S2B2A_COMPOSITION_ACTUAL_V1",
        "protocol": PROTOCOL,
        "issue": 43,
        "stage": "A_COMPOSITION_FROM_KNOWN_PRIMITIVES",
        "source_holdout_digest": data["holdout_digest"],
        "source_file_sha256": hashlib.sha256(raw).hexdigest(),
        "fixture_count": len(fixtures),
        "deterministic_core_commit": "c83632855cc775b8502e6a1ded18a3f3b022f19a",
        "metrics": metrics,
        "claim_limit": "This measures symbolic candidate-instance construction from an already supplied primitive ontology; it does not measure invention of a missing action class/operator.",
        "github_actions_used": False,
        "google_drive_used": False,
        "qwen3_4b_used": False
    }
    args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
