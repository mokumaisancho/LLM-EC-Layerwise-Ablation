#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from generate_phase1_measurement_v2 import SPECS, build, canonical_hash, write_json, GENERATION


def apply_candidate_relations(fid, s2):
    by_id = {c["candidate_id"]: c for c in s2["candidates"]}
    if fid == "M003":
        by_id["v1"]["semantic_transition"] = {"operation": "INVESTIGATE_ROUTE_A"}
        by_id["v2"]["semantic_transition"] = {"operation": "INVESTIGATE_ROUTE_B"}
        s2["relation_groups"] = [{
            "group_id": "g-competing",
            "relation_type": "COMPETING",
            "candidate_ids": ["v1", "v2"]
        }]
        s2["oracle_constraints"]["required_candidate_semantics"] = [
            "INVESTIGATE_ROUTE_A", "INVESTIGATE_ROUTE_B", "BYPASS_CONTROL"
        ]
    elif fid == "M009":
        by_id["v1"]["semantic_transition"] = {"operation": "ACTION_A"}
        by_id["v2"]["semantic_transition"] = {"operation": "ACTION_B"}
        s2["relation_groups"] = [{
            "group_id": "g-equivalent",
            "relation_type": "EQUIVALENT",
            "candidate_ids": ["v1", "v2"]
        }]
        s2["oracle_constraints"]["required_candidate_semantics"] = [
            "ACTION_A", "ACTION_B", "REJECT_EQUIVALENT_FOR_WORDING"
        ]
    else:
        s2["relation_groups"] = []
    return s2


def rebuild(spec):
    task, s1, s2, s3, s4, hidden, manifest = build(spec)
    s2 = apply_candidate_relations(spec["id"], s2)
    s2["content_hash"] = canonical_hash(s2)

    s3["candidate_set_hash"] = s2["content_hash"]
    s3["content_hash"] = canonical_hash(s3)

    s4["selected_state_hash"] = s3["content_hash"]
    s4["content_hash"] = canonical_hash(s4)

    manifest["hashes"]["s2_oracle"] = s2["content_hash"]
    manifest["hashes"]["s3_oracle"] = s3["content_hash"]
    manifest["hashes"]["s4_oracle"] = s4["content_hash"]
    return task, s1, s2, s3, s4, hidden, manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="fixtures/phase1_v2/generated")
    args = ap.parse_args()
    root = Path(args.out)
    rows = []
    for spec in SPECS:
        task, s1, s2, s3, s4, hidden, manifest = rebuild(spec)
        d = root / spec["id"]
        for rel, obj in [
            ("input/task.json", task),
            ("oracle/s1_domain_semantic_ir.json", s1),
            ("oracle/s2_candidate_set.json", s2),
            ("oracle/s3_selected_reframed_state.json", s3),
            ("oracle/s4_closure_execution_result.json", s4),
            ("hidden/evaluation.json", hidden),
            ("fixture_manifest.json", manifest),
        ]:
            write_json(d / rel, obj)
        rows.append({
            "fixture_id": spec["id"],
            "category": hidden["category"],
            "s2_hash": s2["content_hash"],
            "s3_hash": s3["content_hash"],
            "s4_hash": s4["content_hash"],
        })
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(json.dumps({
        "fixture_generation": GENERATION,
        "fixture_count": len(rows),
        "canonical_relation_contract": "S2_RELATION_GROUPS_V1",
        "dataset_digest": digest,
    }, indent=2))


if __name__ == "__main__":
    main()
