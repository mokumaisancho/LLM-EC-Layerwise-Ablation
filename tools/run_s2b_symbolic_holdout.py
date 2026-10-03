#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

PROTOCOL = "FUNCTION_BOUNDARY_S2B_SYMBOLIC_HOLDOUT_V1"
FAMILIES = (
    "INSUFFICIENT_TO_RESOLVE",
    "ADMISSIBLE_UNDER_CONSTRAINT",
    "BLOCKS_INFERENCE",
    "SUPERSEDES",
)

AMBIGUITY_CASES = [
    ("custodian", "depot_custodian", "contract_custodian"),
    ("maintainer", "package_maintainer", "service_maintainer"),
    ("agent", "broker_agent", "workflow_agent"),
    ("owner", "asset_owner", "queue_owner"),
]
ADMISSIBLE_CASES = [
    ("path_north", "path_east", "encryption_required"),
    ("deploy_blue", "deploy_green", "audit_required"),
    ("backup_local", "backup_remote", "retention_required"),
    ("review_dual", "review_human", "segregation_required"),
]
BLOCK_CASES = [
    ("lint_warning", "compile_failure"),
    ("cache_miss", "service_outage"),
    ("weather_alert", "road_closure"),
    ("latency_spike", "capacity_failure"),
]
SUPERSEDE_CASES = [
    ("config_v2", "config_v1"),
    ("schedule_friday", "schedule_thursday"),
    ("inventory_reserved", "inventory_available"),
    ("feature_disabled", "feature_enabled"),
]


def _seed_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16], 16)


def _assign_ids(rng: random.Random, specs: list[dict]) -> tuple[dict[str, dict], list[str]]:
    ids = [f"a{i}" for i in range(1, len(specs) + 1)]
    rng.shuffle(ids)
    candidates: dict[str, dict] = {}
    gold: list[str] = []
    for cid, spec in zip(ids, specs):
        candidates[cid] = {k: v for k, v in spec.items() if k != "gold"}
        if spec.get("gold"):
            gold.append(cid)
    return candidates, sorted(gold)


def _ambiguity_fixture(rng: random.Random, i: int, referent: str, left: str, right: str) -> dict:
    relation = {"operator": "INSUFFICIENT_TO_RESOLVE", "referent": referent, "options": [left, right]}
    specs = [
        {"text": f"request clarification for {referent}", "action_class": "REQUEST_CLARIFICATION", "target": referent, "forbidden": False, "gold": True},
        {"text": f"preserve {referent} as unresolved", "action_class": "PRESERVE_UNRESOLVED", "target": referent, "forbidden": False, "gold": True},
        {"text": f"bind {referent} immediately to {left}", "action_class": "BIND_IMMEDIATELY", "target": left, "forbidden": True},
        {"text": f"bind {referent} immediately to {right}", "action_class": "BIND_IMMEDIATELY", "target": right, "forbidden": True},
        {"text": f"ignore unresolved {referent}", "action_class": "IGNORE", "target": referent, "forbidden": True},
        {"text": "continue without clarification", "action_class": "CONTINUE_UNRESOLVED", "target": referent, "forbidden": True},
    ]
    candidates, gold = _assign_ids(rng, specs)
    return {"id": f"H1{i:02d}", "family": relation["operator"], "relation": relation, "candidates": candidates, "gold": gold}


def _admissible_fixture(rng: random.Random, i: int, left: str, right: str, constraint: str) -> dict:
    relation = {"operator": "ADMISSIBLE_UNDER_CONSTRAINT", "alternatives": [left, right], "constraint": constraint}
    specs = [
        {"text": f"retain {left} while preserving {constraint}", "action_class": "RETAIN_ALTERNATIVE", "target": left, "constraint_preserved": True, "forbidden": False, "gold": True},
        {"text": f"retain {right} while preserving {constraint}", "action_class": "RETAIN_ALTERNATIVE", "target": right, "constraint_preserved": True, "forbidden": False, "gold": True},
        {"text": f"use {left} while bypassing {constraint}", "action_class": "RETAIN_ALTERNATIVE", "target": left, "constraint_preserved": False, "forbidden": True},
        {"text": f"use {right} while bypassing {constraint}", "action_class": "RETAIN_ALTERNATIVE", "target": right, "constraint_preserved": False, "forbidden": True},
        {"text": f"remove {constraint}", "action_class": "REMOVE_CONSTRAINT", "target": constraint, "forbidden": True},
        {"text": "discard all admissible alternatives", "action_class": "DISCARD_ALL", "target": "all", "forbidden": True},
    ]
    candidates, gold = _assign_ids(rng, specs)
    return {"id": f"H2{i:02d}", "family": relation["operator"], "relation": relation, "candidates": candidates, "gold": gold}


def _block_fixture(rng: random.Random, i: int, trigger: str, proposition: str) -> dict:
    relation = {"operator": "BLOCKS_INFERENCE", "trigger": trigger, "proposition": proposition}
    specs = [
        {"text": f"keep {proposition} unconfirmed", "action_class": "PRESERVE_UNCONFIRMED", "target": proposition, "forbidden": False, "gold": True},
        {"text": f"retain {trigger} as a review signal rather than proof", "action_class": "RETAIN_REVIEW_SIGNAL", "target": trigger, "forbidden": False, "gold": True},
        {"text": f"confirm {proposition} from {trigger}", "action_class": "CONFIRM", "target": proposition, "forbidden": True},
        {"text": f"treat {trigger} as direct proof", "action_class": "DIRECT_PROOF", "target": trigger, "forbidden": True},
        {"text": f"ignore {trigger}", "action_class": "IGNORE", "target": trigger, "forbidden": True},
        {"text": f"escalate {proposition} as confirmed", "action_class": "ESCALATE_CONFIRMED", "target": proposition, "forbidden": True},
    ]
    candidates, gold = _assign_ids(rng, specs)
    return {"id": f"H3{i:02d}", "family": relation["operator"], "relation": relation, "candidates": candidates, "gold": gold}


def _supersede_fixture(rng: random.Random, i: int, new: str, old: str) -> dict:
    relation = {"operator": "SUPERSEDES", "new": new, "old": old}
    specs = [
        {"text": f"apply {new} as current", "action_class": "APPLY_CURRENT", "target": new, "forbidden": False, "gold": True},
        {"text": f"retain {old} as history", "action_class": "RETAIN_HISTORY", "target": old, "forbidden": False, "gold": True},
        {"text": f"apply {old} as current", "action_class": "APPLY_CURRENT", "target": old, "forbidden": True},
        {"text": f"treat {new} and {old} as equally current", "action_class": "EQUAL_CURRENT", "target": "both", "forbidden": True},
        {"text": "ignore freshness ordering", "action_class": "IGNORE_FRESHNESS", "target": "ordering", "forbidden": True},
        {"text": f"discard {new}", "action_class": "DISCARD_NEW", "target": new, "forbidden": True},
    ]
    candidates, gold = _assign_ids(rng, specs)
    return {"id": f"H4{i:02d}", "family": relation["operator"], "relation": relation, "candidates": candidates, "gold": gold}


def generate_holdout(seed: str) -> list[dict]:
    rng = random.Random(_seed_int(seed))
    fixtures: list[dict] = []
    for i, row in enumerate(AMBIGUITY_CASES, 1): fixtures.append(_ambiguity_fixture(rng, i, *row))
    for i, row in enumerate(ADMISSIBLE_CASES, 1): fixtures.append(_admissible_fixture(rng, i, *row))
    for i, row in enumerate(BLOCK_CASES, 1): fixtures.append(_block_fixture(rng, i, *row))
    for i, row in enumerate(SUPERSEDE_CASES, 1): fixtures.append(_supersede_fixture(rng, i, *row))
    rng.shuffle(fixtures)
    return fixtures


def predict(fixture: dict) -> list[str]:
    # Deliberately no access to fixture['gold'] or surface text.
    r = fixture["relation"]
    selected: list[str] = []
    for cid, c in fixture["candidates"].items():
        op = r["operator"]
        ok = False
        if op == "INSUFFICIENT_TO_RESOLVE":
            ok = c["target"] == r["referent"] and c["action_class"] in {"REQUEST_CLARIFICATION", "PRESERVE_UNRESOLVED"}
        elif op == "ADMISSIBLE_UNDER_CONSTRAINT":
            ok = c["action_class"] == "RETAIN_ALTERNATIVE" and c["target"] in r["alternatives"] and c.get("constraint_preserved") is True
        elif op == "BLOCKS_INFERENCE":
            ok = (c["action_class"] == "PRESERVE_UNCONFIRMED" and c["target"] == r["proposition"]) or (c["action_class"] == "RETAIN_REVIEW_SIGNAL" and c["target"] == r["trigger"])
        elif op == "SUPERSEDES":
            ok = (c["action_class"] == "APPLY_CURRENT" and c["target"] == r["new"]) or (c["action_class"] == "RETAIN_HISTORY" and c["target"] == r["old"])
        else:
            raise ValueError(f"unsupported operator: {op}")
        if ok:
            selected.append(cid)
    return sorted(selected)


def score(fixtures: list[dict]) -> dict:
    tp = emitted = gold_total = exact = fail_open = 0
    per_family: dict[str, dict[str, int]] = {f: {"tp":0,"emitted":0,"gold":0,"fixtures":0,"exact":0,"fail_open":0} for f in FAMILIES}
    per_fixture = {}
    for f in fixtures:
        pred = set(predict(f)); gold = set(f["gold"])
        hit = len(pred & gold)
        forbidden = {cid for cid,c in f["candidates"].items() if c.get("forbidden")}
        fo = len(pred & forbidden)
        tp += hit; emitted += len(pred); gold_total += len(gold); exact += int(pred == gold); fail_open += fo
        fam = per_family[f["family"]]
        fam["tp"] += hit; fam["emitted"] += len(pred); fam["gold"] += len(gold); fam["fixtures"] += 1; fam["exact"] += int(pred == gold); fam["fail_open"] += fo
        per_fixture[f["id"]] = {"family":f["family"],"predicted":sorted(pred),"gold":sorted(gold),"tp":hit,"fail_open":fo}
    family_metrics = {}
    for name,v in per_family.items():
        family_metrics[name] = {
            **v,
            "recall": v["tp"]/v["gold"] if v["gold"] else 1.0,
            "precision": v["tp"]/v["emitted"] if v["emitted"] else 0.0,
            "exact_set_rate": v["exact"]/v["fixtures"] if v["fixtures"] else 0.0,
        }
    recall = tp/gold_total if gold_total else 1.0
    precision = tp/emitted if emitted else 0.0
    passed = recall >= 0.90 and precision >= 0.80 and fail_open == 0
    return {
        "candidate_recall": recall,
        "candidate_precision": precision,
        "exact_set_rate": exact/len(fixtures),
        "true_positive_total": tp,
        "emitted_total": emitted,
        "gold_total": gold_total,
        "fail_open_forbidden_count": fail_open,
        "family_metrics": family_metrics,
        "per_fixture": per_fixture,
        "gate_pass": passed,
        "classification": "DETERMINISTIC_SYMBOLIC_CLOSURE_EXTERNALIZABLE" if passed else "RESIDUAL_REMAINS_UNRESOLVED",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True, help="freeze commit SHA")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--holdout", type=Path)
    args = ap.parse_args()
    fixtures = generate_holdout(args.seed)
    if args.holdout:
        args.holdout.write_text(json.dumps({"protocol":PROTOCOL,"seed":args.seed,"fixtures":fixtures}, indent=2) + "\n", encoding="utf-8")
    metrics = score(fixtures)
    result = {
        "schema_version": "FUNCTION_BOUNDARY_S2B_SYMBOLIC_ACTUAL_V1",
        "protocol": PROTOCOL,
        "seed_source": "freeze commit SHA",
        "seed": args.seed,
        "fixture_count": len(fixtures),
        "families": list(FAMILIES),
        "engine_input_boundary": "structured relation operator + structured candidate metadata; no gold and no candidate surface text",
        "metrics": metrics,
        "claim_limit": "A pass proves deterministic relation closure after structured operators and candidate metadata exist; it does not prove raw-language relation extraction or novel candidate invention is deterministic.",
        "github_actions_used": False,
        "google_drive_used": False,
        "qwen3_4b_used": False
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if metrics["gate_pass"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
