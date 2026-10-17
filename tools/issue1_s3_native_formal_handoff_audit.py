#!/usr/bin/env python3
"""Source-bound P01->EC v2 *qualification audit*, not a semantic predictor."""
import argparse
import hashlib
import json
import re
from pathlib import Path

EC_V2_BLOB = "7da0cd8d876505cafdd5a9811132427e2f441a14"
ATOM = re.compile(r"^[A-Za-z][A-Za-z0-9_]*=[A-Za-z][A-Za-z0-9_]*$")
CAUSES = [
    "NATIVE_EC_FORMAL_BOOLEAN_FACTS_ABSENT",
    "FORMAL_OPERATION_RULES_ABSENT_NATURAL_LANGUAGE_ONLY",
    "INDEPENDENT_POLICY_SEMANTIC_AUTHORITY_NOT_ATTESTED",
    "INDEPENDENT_RELATION_SEMANTICS_NOT_ATTESTED",
    "INDEPENDENT_OBLIGATION_COMPLETENESS_NOT_ATTESTED",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_observed_literal_facts(raw):
    if not isinstance(raw, list) or not raw:
        raise ValueError("EMPTY_OR_UNTYPED_SOURCE_FACTS")
    out, attributes = {}, {}
    for literal in raw:
        if not isinstance(literal, str) or not ATOM.fullmatch(literal):
            raise ValueError("FREE_TEXT_REQUIRES_SEMANTIC_INTERPRETATION")
        key, value = literal.split("=", 1)
        if key in attributes and attributes[key] != value:
            raise ValueError("CONFLICTING_OBSERVED_SOURCE_VALUES")
        if literal in out:
            raise ValueError("DUPLICATE_FACT_UNSUPPORTED")
        attributes[key], out[literal] = value, True
    return out


def audit_one(root, fixture_id):
    if not re.fullmatch(r"M\d{3}", fixture_id):
        raise ValueError("INVALID_FIXTURE_ID")
    pub = root / "replay" / fixture_id / "s3_predictor_visible_v42.json"
    task_path = root / "generated" / fixture_id / "input/task.json"
    manifest_path = root / "generated" / fixture_id / "fixture_manifest.json"
    visible, task, manifest = [json.loads(p.read_text()) for p in (pub, task_path, manifest_path)]
    if visible.get("schema") != "S3_SEMANTIC_PREDICTOR_INPUT_GOLD_BLIND_V43":
        raise ValueError("PREDICTOR_SCHEMA_DRIFT")
    if task.get("schema_version") != "TASK_INPUT_V1":
        raise ValueError("TASK_SCHEMA_DRIFT")
    if task.get("fixture_id") != fixture_id or manifest.get("fixture_id") != fixture_id:
        raise ValueError("CROSS_FIXTURE_BINDING_DRIFT")
    if visible.get("task") != {"prompt": task["prompt"], "facts": task["context"]["facts"],
                               "domain_rules": task["context"]["domain_rules"]}:
        raise ValueError("PUBLIC_TASK_CUSTODY_DRIFT")
    candidates = visible.get("candidates")
    if not isinstance(candidates, list) or len(candidates) < 2:
        raise ValueError("PUBLIC_CANDIDATES_MISSING")
    ids = [c.get("candidate_id", "") for c in candidates]
    if not all(re.fullmatch(r"c_[a-f0-9]{32}", i) for i in ids):
        raise ValueError("CANDIDATE_PUBLIC_PROTOCOL_DRIFT")
    if len(set(ids)) != len(ids):
        raise ValueError("PUBLIC_DUPLICATE_IDS")
    if any(not isinstance(c.get("semantic_operation"), str) for c in candidates):
        raise ValueError("CANDIDATE_SEMANTICS_MISSING")
    if any(x in json.dumps(visible) for x in ('"oracle_constraints"', '"acceptable_candidate_ids"',
                                               '"fixture_id"', '"reference_label"', '"relation_groups"')):
        raise ValueError("PRIVATE_GOLD_OR_RELATION_EXPOSED")
    atomic = normalize_observed_literal_facts(visible["task"]["facts"])
    formal_candidate = {"schema": "EC_FORMAL_FACTS_V2", "facts": atomic,
                        "source_ref": "sha256:" + digest(task_path)}
    return {"fixture_id": fixture_id, "source_task_sha256": digest(task_path),
            "predictor_input_sha256": digest(pub), "visible_candidates": len(ids),
            "strict_positive_fact_literals_normalized": len(atomic),
            "EC_formal_fact_object_candidate": formal_candidate,
            "formal_facts_structurally_constructible": True,
            "native_EC_v2_input_ready": False, "adjudication": "ABSTAIN_NOT_QUALIFIED",
            "causes": CAUSES}


def audit_all(root):
    names = sorted(x.name for x in (root / "generated").glob("M???") if x.is_dir())
    if names != [f"M{i:03d}" for i in range(1, 11)]:
        raise ValueError("REJECT_FIXTURE_SET_CHANGED")
    rows = [audit_one(root, n) for n in names]
    return {"schema": "ISSUE1_S3_NATIVE_FORMAL_HANDOFF_AUDIT_V1",
            "contract": {"original_native_EC_v2_git_blob": EC_V2_BLOB,
                         "native_protocol": "EC_SOURCE_POLICY_S3_S4_V2",
                         "predictor_protocol": "S3_SEMANTIC_PREDICTOR_INPUT_GOLD_BLIND_V43"},
            "real_source_input_cases": len(rows), "native_formal_handoff_qualified": 0,
            "cases_rejected_without_label_leakage": len(rows),
            "source_positive_atomic_literals_structurally_normalized": sum(r["strict_positive_fact_literals_normalized"] for r in rows),
            "fact_structural_conversion_possible_cases": len(rows),
            "reason_counts": {c: len(rows) for c in CAUSES}, "cases": rows,
            "scope": "Only source-preserving positive atom normalization. No semantic policy translation, independent relation/closure authority, EC execution or actual model inference.",
            "original_science_AC_promoted": 0}


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--root", type=Path, required=True)
    a.add_argument("--output", type=Path)
    arg = a.parse_args()
    report = audit_all(arg.root)
    raw = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if arg.output:
        arg.output.write_text(raw)
    print(json.dumps({"cases": 10, "positive_atomic_facts": 25,
                      "native_ready": report["native_formal_handoff_qualified"],
                      "abstain": report["cases_rejected_without_label_leakage"]}))
