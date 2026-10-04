#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

from generate_s2b2a_composition_holdout import generate

ROOT = Path(__file__).resolve().parents[1]
SEED = "f88e37abf64c10e7e56ce61b5b5c9d6fbb09a075"
EXPECTED_DIGEST = "a58e978a26f86f41ce9b08e36003e08c4682cd144a3d70a5aa945bd539f0f845"
RAW_CACHE = ROOT / "results" / "function_boundary_s2b2a_qwen25_1p5b_raw_cache_2026-10-04.json"
SAVED_RESULT = ROOT / "results" / "function_boundary_s2b2a_composition_paired_actual_2026-10-04.json"


def canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(fixtures: list[dict]) -> str:
    return hashlib.sha256(canon(fixtures).encode()).hexdigest()


def atom_key(a: dict) -> str:
    return canon(a)


def subst(v: Any, b: dict[str, str]) -> Any:
    if isinstance(v, str) and v.startswith("$"):
        return b[v]
    if isinstance(v, list):
        return [subst(x, b) for x in v]
    if isinstance(v, dict):
        return {k: subst(x, b) for k, x in v.items()}
    return v


def cand_key(c: dict) -> str:
    return canon({"action_class": c["action_class"], "bindings": {k: c["bindings"][k] for k in sorted(c["bindings"])}})


def independent_valid_candidates(visible: dict) -> list[dict]:
    """Independent declarative evaluator. Does not import/call s2b2a_composition_core."""
    state = {atom_key(a) for a in visible["state"]}
    req = {atom_key(a) for a in visible["relation"]["required_effects"]}
    forbid = {atom_key(a) for a in visible["relation"]["forbidden_effects"]}
    domains = visible["domains"]
    out: dict[str, dict] = {}

    for primitive in visible["primitive_actions"]:
        params = primitive.get("parameters", [])
        value_lists = [domains[p] for p in params]
        for combo in itertools.product(*value_lists):
            binding = dict(zip(params, combo))
            pre = {atom_key(subst(a, binding)) for a in primitive.get("preconditions", [])}
            if not pre.issubset(state):
                continue
            effects = {atom_key(subst(a, binding)) for a in primitive.get("effects", [])}
            if not req.issubset(effects):
                continue
            if effects & forbid:
                continue
            c = {"action_class": primitive["action_class"], "bindings": {k: binding[k] for k in sorted(binding)}}
            out[cand_key(c)] = c
    return [out[k] for k in sorted(out)]


def close(a: float, b: float, eps: float = 1e-12) -> bool:
    return abs(a - b) <= eps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-cache", type=Path, default=RAW_CACHE)
    ap.add_argument("--saved-result", type=Path, default=SAVED_RESULT)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    fixtures = generate(SEED)
    if len(fixtures) != 16:
        raise SystemExit("STAGE_A_AUDIT_FAIL: fixture count")
    if digest(fixtures) != EXPECTED_DIGEST:
        raise SystemExit("STAGE_A_AUDIT_FAIL: dataset digest")
    if len({f["family"] for f in fixtures}) != 8:
        raise SystemExit("STAGE_A_AUDIT_FAIL: family count")

    by_id = {f["id"]: f for f in fixtures}
    oracle_recomputed = {}
    for f in fixtures:
        valid = independent_valid_candidates(f["visible"])
        oracle = sorted(f["oracle"]["candidates"], key=cand_key)
        if [cand_key(x) for x in valid] != [cand_key(x) for x in oracle]:
            raise SystemExit(f"STAGE_A_AUDIT_FAIL: independent oracle mismatch {f['id']}")
        existing = {cand_key(x) for x in f["visible"]["existing_candidates"]}
        if existing & {cand_key(x) for x in oracle}:
            raise SystemExit(f"STAGE_A_AUDIT_FAIL: gold already present {f['id']}")
        oracle_recomputed[f["id"]] = valid

    raw_doc = json.loads(args.raw_cache.read_text(encoding="utf-8"))
    rows = raw_doc.get("rows", [])
    if len(rows) != 16 or len({r["fixture_id"] for r in rows}) != 16:
        raise SystemExit("STAGE_A_AUDIT_FAIL: raw cache completeness")

    tp = emitted = gold_total = exact = invalid = fail_open = 0
    family = {}
    for r in rows:
        fid = r["fixture_id"]
        if fid not in by_id:
            raise SystemExit(f"STAGE_A_AUDIT_FAIL: unknown raw fixture {fid}")
        parsed = json.loads(r["raw"])
        if canon(parsed) != canon(r["prediction"]):
            raise SystemExit(f"STAGE_A_AUDIT_FAIL: raw/prediction mismatch {fid}")
        oracle = oracle_recomputed[fid]
        if {cand_key(x) for x in r["oracle"]} != {cand_key(x) for x in oracle}:
            raise SystemExit(f"STAGE_A_AUDIT_FAIL: raw/oracle mismatch {fid}")
        ps = {cand_key(x) for x in r["prediction"]}
        gs = {cand_key(x) for x in oracle}
        hit = len(ps & gs)
        fo = len(ps - gs)
        ex = ps == gs
        if hit != int(r["tp"]) or fo != int(r["fail_open"]) or ex != bool(r["exact"]):
            raise SystemExit(f"STAGE_A_AUDIT_FAIL: row metric mismatch {fid}")
        tp += hit
        emitted += len(ps)
        gold_total += len(gs)
        exact += int(ex)
        invalid += int(bool(r["invalid"]))
        fail_open += fo
        fam = by_id[fid]["family"]
        family.setdefault(fam, {"fixtures": 0, "tp": 0})
        family[fam]["fixtures"] += 1
        family[fam]["tp"] += hit

    recall = tp / gold_total
    precision = tp / emitted
    f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
    exact_rate = exact / len(rows)

    expected = {"tp": 9, "emitted": 16, "gold": 16, "invalid": 0, "fail_open": 7}
    actual = {"tp": tp, "emitted": emitted, "gold": gold_total, "invalid": invalid, "fail_open": fail_open}
    if actual != expected:
        raise SystemExit(f"STAGE_A_AUDIT_FAIL: raw totals {actual}")

    saved = json.loads(args.saved_result.read_text(encoding="utf-8"))
    q = saved["arms"]["qwen25_1p5b"]
    numeric = {
        "candidate_recall": recall,
        "candidate_precision": precision,
        "f1": f1,
        "exact_set_rate": exact_rate,
    }
    for k, v in numeric.items():
        if not close(float(q[k]), v):
            raise SystemExit(f"STAGE_A_AUDIT_FAIL: saved {k}")
    if int(q["true_positive_total"]) != tp or int(q["emitted_total"]) != emitted or int(q["gold_total"]) != gold_total:
        raise SystemExit("STAGE_A_AUDIT_FAIL: saved totals")
    if int(q["invalid_output_count"]) != invalid or int(q["forbidden_fail_open_count"]) != fail_open:
        raise SystemExit("STAGE_A_AUDIT_FAIL: saved invalid/fail-open")

    result = {
        "schema_version": "FUNCTION_BOUNDARY_S2B2A_INDEPENDENT_AUDIT_V1",
        "protocol": "S2B2_MVP_TCC_V2",
        "terminal": "STAGE_A_AUDIT_PASS",
        "dataset_digest": EXPECTED_DIGEST,
        "fixture_count": 16,
        "family_count": 8,
        "oracle_independent_recompute_match": "16/16",
        "gold_absent_from_existing_candidates": "16/16",
        "raw_cache_rows": 16,
        "qwen_recomputed": {
            "tp": tp, "emitted": emitted, "gold": gold_total,
            "recall": recall, "precision": precision, "f1": f1,
            "exact_set_rate": exact_rate, "invalid": invalid, "fail_open": fail_open
        },
        "saved_result_match": True,
        "per_family_tp": family,
        "predictor_core_used_for_oracle_audit": False,
        "model_rerun": False
    }
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
