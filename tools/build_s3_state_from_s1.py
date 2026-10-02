#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PROTOCOL = "PHASE1_S1_TO_S3_STATE_ADAPTER_V1"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(obj: dict[str, Any]) -> str:
    value = dict(obj)
    value.pop("content_hash", None)
    blob = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def build_state(task: dict, s1: dict) -> dict:
    if "oracle_constraints" in task or "oracle_constraints" in s1:
        raise ValueError("ORACLE_FIELD_FORBIDDEN_IN_AB_ADAPTER_INPUT")
    if task.get("fixture_id") != s1.get("fixture_id"):
        raise ValueError("FIXTURE_ID_MISMATCH")
    if s1.get("schema_version") != "S1_DOMAIN_SEMANTIC_IR_V1":
        raise ValueError("S1_SCHEMA_INVALID")
    s1_hash = s1.get("content_hash")
    if not isinstance(s1_hash, str) or not s1_hash:
        raise ValueError("S1_HASH_REQUIRED")
    if canonical_hash(s1) != s1_hash:
        raise ValueError("S1_HASH_MISMATCH")

    variables: dict[str, dict] = {}
    for raw in s1.get("entities") or []:
        if not isinstance(raw, dict):
            continue
        entity_id = norm(raw.get("id"))
        entity_type = norm(raw.get("type")).upper()
        if not entity_id or entity_type == "GOAL":
            continue
        attrs = raw.get("attributes") if isinstance(raw.get("attributes"), dict) else {}
        semantic_key = norm(attrs.get("semantic_key") or raw.get("value") or entity_id)
        evidence_refs = attrs.get("evidence_refs") if isinstance(attrs.get("evidence_refs"), list) else s1.get("source_refs", [])
        variables[entity_id] = {
            "semantic_key": semantic_key,
            "entity_type": entity_type or "ENTITY",
            "evidence_refs": [norm(x) for x in evidence_refs if norm(x)],
            "actionable": bool(attrs.get("actionable", True)),
            "source_s1_entity_id": entity_id,
        }

    goal_ids = {norm(g.get("id")) for g in s1.get("goals") or [] if isinstance(g, dict) and norm(g.get("id"))}
    success_conditions = [
        norm(g.get("description") or g.get("id"))
        for g in s1.get("goals") or []
        if isinstance(g, dict) and norm(g.get("description") or g.get("id"))
    ]
    if not success_conditions:
        protected = task.get("protected_intent") if isinstance(task.get("protected_intent"), dict) else {}
        success_conditions = [norm(protected.get("goal"))] if norm(protected.get("goal")) else ["complete stated task"]

    goal_coverage = {condition: [] for condition in success_conditions}
    linked: set[str] = set()
    for rel in s1.get("relations") or []:
        if not isinstance(rel, dict):
            continue
        source, target = norm(rel.get("source")), norm(rel.get("target"))
        if source in variables and target in goal_ids:
            linked.add(source)
        if target in variables and source in goal_ids:
            linked.add(target)
    coverage_ids = sorted(linked) if linked else sorted(k for k, v in variables.items() if v.get("actionable"))
    for condition in goal_coverage:
        goal_coverage[condition] = coverage_ids

    protected_invariants = []
    for c in s1.get("constraints") or []:
        if isinstance(c, dict):
            text = norm(c.get("value") or c.get("description") or c.get("id"))
            if text:
                protected_invariants.append(text)
    if not protected_invariants:
        protected_invariants = ["preserve stated domain rules", "preserve protected intent"]

    observations = []
    for idx, ambiguity in enumerate(s1.get("ambiguities") or []):
        if not isinstance(ambiguity, dict):
            continue
        text = norm(ambiguity.get("description") or ambiguity.get("value") or ambiguity.get("id"))
        if text:
            observations.append({
                "observation_id": norm(ambiguity.get("id")) or f"ambiguity-{idx+1}",
                "semantic_key": text,
                "evidence_ref": f"s1:{s1_hash}",
            })

    state = {
        "schema_version": "S3_SEMANTIC_STATE_V1",
        "adapter_protocol": PROTOCOL,
        "fixture_id": s1["fixture_id"],
        "fixture_generation": s1.get("fixture_generation"),
        "artifact_id": str(s1["fixture_id"]) + "-S3-STATE-FROM-S1",
        "content_hash": "",
        "source_refs": [f"s1:{s1_hash}", "input/task.json"],
        "source_s1_hash": s1_hash,
        "oracle_blind": True,
        "intent": {
            "original_intent": norm((task.get("protected_intent") or {}).get("goal")) or success_conditions[0],
            "success_conditions": success_conditions,
            "protected_invariants": protected_invariants,
            "prohibited_substitutions": ["replace evidence with linguistic plausibility"],
        },
        "framing": {
            "framing_revision_id": 0,
            "variables": variables,
            "edges": [],
            "goal_coverage": goal_coverage,
            "violated_invariants": [],
            "substitutions": [],
        },
        "observations": observations,
    }
    state["content_hash"] = canonical_hash(state)
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-root", default="fixtures/phase1_v2/generated")
    ap.add_argument("--s1-dir", required=True)
    ap.add_argument("--out", default="results/ab_common_s3_state")
    args = ap.parse_args()

    task_root, s1_dir, out = Path(args.task_root), Path(args.s1_dir), Path(args.out)
    count = 0
    for task_dir in sorted(p for p in task_root.iterdir() if p.is_dir()):
        fid = task_dir.name
        task = load(task_dir / "input" / "task.json")
        s1 = load(s1_dir / f"{fid}.json")
        state = build_state(task, s1)
        target = out / f"{fid}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        count += 1
    print(json.dumps({"protocol": PROTOCOL, "status": "PASS", "count": count, "oracle_blind": True}, indent=2))


if __name__ == "__main__":
    main()
