#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
from collections import defaultdict
from typing import Any

PROTOCOL = "S2B2_B2_INDEPENDENT_IDENTIFIABILITY_SCORER_V1"
MAX_PRE = 3
MAX_ADD = 3
DELETE_N = 1


def ak(a: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    return a["pred"], tuple(a["args"])


def atom(x: tuple[str, tuple[str, ...]]) -> dict[str, Any]:
    return {"pred": x[0], "args": list(x[1])}


def stateset(xs: list[dict[str, Any]]) -> set[tuple[str, tuple[str, ...]]]:
    return {ak(x) for x in xs}


def schema_canonical(s: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposal_kind": "INDUCED_OPERATOR",
        "parameters": list(s["parameters"]),
        "preconditions": [atom(x) for x in sorted({ak(a) for a in s["preconditions"]})],
        "add_effects": [atom(x) for x in sorted({ak(a) for a in s["add_effects"]})],
        "delete_effects": [atom(x) for x in sorted({ak(a) for a in s["delete_effects"]})],
    }


def skey(s: dict[str, Any]) -> str:
    return json.dumps(schema_canonical(s), sort_keys=True, separators=(",", ":"))


def typed_atom_universe(v: dict[str, Any]) -> list[tuple[str, tuple[str, ...]]]:
    vars_by_type: dict[str, list[str]] = defaultdict(list)
    for p in v["parameters"]:
        vars_by_type[p["type"]].append(p["name"])
    out: list[tuple[str, tuple[str, ...]]] = []
    for pred, arg_types in sorted(v["predicate_vocabulary"].items()):
        choices: list[list[str]] = []
        ok = True
        for typ in arg_types:
            vals = sorted(vars_by_type.get(typ, []))
            if not vals:
                ok = False
                break
            choices.append(vals)
        if not ok:
            continue
        for args in itertools.product(*choices) if choices else [()]:
            out.append((pred, tuple(args)))
    return out


def inv_binding(binding: dict[str, str]) -> dict[str, str] | None:
    inv: dict[str, str] = {}
    for var, val in binding.items():
        if val in inv:
            return None
        inv[val] = var
    return inv


def lift(concrete: tuple[str, tuple[str, ...]], binding: dict[str, str]) -> tuple[str, tuple[str, ...]] | None:
    inv = inv_binding(binding)
    if inv is None:
        return None
    p, args = concrete
    if any(a not in inv for a in args):
        return None
    return p, tuple(inv[a] for a in args)


def instantiate(template: tuple[str, tuple[str, ...]], binding: dict[str, str]) -> tuple[str, tuple[str, ...]]:
    return template[0], tuple(binding[a] for a in template[1])


def all_params_used(s: dict[str, Any]) -> bool:
    declared = set(s["parameters"])
    used: set[str] = set()
    for field in ("preconditions", "add_effects", "delete_effects"):
        for a in s[field]:
            used.update(x for x in a["args"] if isinstance(x, str) and x.startswith("$"))
    return declared.issubset(used)


def example_consistent(s: dict[str, Any], ex: dict[str, Any], positive: bool) -> bool:
    before = stateset(ex["before"])
    after = stateset(ex["after"])
    pre = {instantiate(ak(a), ex["binding"]) for a in s["preconditions"]}
    applicable = pre.issubset(before)
    if positive:
        if not applicable:
            return False
        delete = {instantiate(ak(a), ex["binding"]) for a in s["delete_effects"]}
        add = {instantiate(ak(a), ex["binding"]) for a in s["add_effects"]}
        return (before - delete) | add == after
    return after == before and not applicable


def enumerate_consistent(v: dict[str, Any]) -> list[dict[str, Any]]:
    positives = v["positive_examples"]
    negatives = v["negative_examples"]
    params = [p["name"] for p in v["parameters"]]
    universe = typed_atom_universe(v)

    # Effects are independently identified from exact observed positive deltas.
    add_options: set[tuple[tuple[str, tuple[str, ...]], ...]] = set()
    del_options: set[tuple[tuple[str, tuple[str, ...]], ...]] = set()
    for ex in positives:
        before, after = stateset(ex["before"]), stateset(ex["after"])
        adds: list[tuple[str, tuple[str, ...]]] = []
        dels: list[tuple[str, tuple[str, ...]]] = []
        for x in after - before:
            y = lift(x, ex["binding"])
            if y is None:
                return []
            adds.append(y)
        for x in before - after:
            y = lift(x, ex["binding"])
            if y is None:
                return []
            dels.append(y)
        add_options.add(tuple(sorted(set(adds))))
        del_options.add(tuple(sorted(set(dels))))
    if len(add_options) != 1 or len(del_options) != 1:
        return []
    adds = next(iter(add_options))
    dels = next(iter(del_options))
    if not (1 <= len(adds) <= MAX_ADD) or len(dels) != DELETE_N or set(adds) & set(dels):
        return []

    hits: dict[str, dict[str, Any]] = {}
    for n in range(1, MAX_PRE + 1):
        for pre in itertools.combinations(universe, n):
            s = {
                "proposal_kind": "INDUCED_OPERATOR",
                "parameters": params,
                "preconditions": [atom(x) for x in pre],
                "add_effects": [atom(x) for x in adds],
                "delete_effects": [atom(x) for x in dels],
            }
            if not all_params_used(s):
                continue
            if all(example_consistent(s, ex, True) for ex in positives) and all(example_consistent(s, ex, False) for ex in negatives):
                c = schema_canonical(s)
                hits[skey(c)] = c
    return [hits[k] for k in sorted(hits)]


def supplied_signature_set(v: dict[str, Any]) -> set[str]:
    out = set()
    for p in v.get("supplied_primitive_ontology", []):
        s = {
            "proposal_kind": "INDUCED_OPERATOR",
            "parameters": p["parameters"],
            "preconditions": p["preconditions"],
            "add_effects": p["add_effects"],
            "delete_effects": p["delete_effects"],
        }
        out.add(skey(s))
    return out


def heldout_after(s: dict[str, Any], heldout: dict[str, Any]) -> dict[str, Any]:
    before = stateset(heldout["before"])
    pre = {instantiate(ak(a), heldout["binding"]) for a in s["preconditions"]}
    if not pre.issubset(before):
        return {"applicable": False, "after": [atom(x) for x in sorted(before)]}
    delete = {instantiate(ak(a), heldout["binding"]) for a in s["delete_effects"]}
    add = {instantiate(ak(a), heldout["binding"]) for a in s["add_effects"]}
    after = (before - delete) | add
    return {"applicable": True, "after": [atom(x) for x in sorted(after)]}


def preflight_fixture(f: dict[str, Any]) -> dict[str, Any]:
    v = f["visible"]
    hits = enumerate_consistent(v)
    if len(hits) == 0:
        return {"valid": False, "terminal": "B2_NO_VALID_HYPOTHESIS", "consistent_count": 0}
    if len(hits) > 1:
        return {"valid": False, "terminal": "B2_AMBIGUOUS_HYPOTHESIS", "consistent_count": len(hits)}
    oracle = hits[0]
    if skey(oracle) in supplied_signature_set(v):
        return {"valid": False, "terminal": "ONTOLOGY_CLASS_NOT_ACTUALLY_NOVEL", "consistent_count": 1}
    hidden = f.get("oracle", {}).get("semantic_signature")
    if hidden is None or skey(hidden) != skey(oracle):
        return {"valid": False, "terminal": "GENERATOR_ORACLE_MISMATCH", "consistent_count": 1}
    ho = heldout_after(oracle, v["heldout_target"])
    expected_after = f.get("oracle", {}).get("heldout_after")
    if not ho["applicable"] or stateset(ho["after"]) != stateset(expected_after or []):
        return {"valid": False, "terminal": "HELDOUT_ORACLE_MISMATCH", "consistent_count": 1}
    training_bindings = {tuple(sorted(ex["binding"].items())) for ex in v["positive_examples"] + v["negative_examples"]}
    if tuple(sorted(v["heldout_target"]["binding"].items())) in training_bindings:
        return {"valid": False, "terminal": "HELDOUT_BINDING_NOT_NOVEL", "consistent_count": 1}
    return {"valid": True, "terminal": "B2_IDENTIFIABILITY_PASS", "consistent_count": 1, "oracle": oracle}


def validate_prediction(f: dict[str, Any], proposal: Any) -> dict[str, Any]:
    pf = preflight_fixture(f)
    if not pf["valid"]:
        return {"valid": False, "reason": "FIXTURE_NOT_IDENTIFIABLE"}
    if not isinstance(proposal, dict):
        return {"valid": False, "reason": "NOT_OBJECT"}
    if set(proposal) != {"proposal_kind", "parameters", "preconditions", "add_effects", "delete_effects"}:
        return {"valid": False, "reason": "WRONG_KEYS"}
    if proposal.get("proposal_kind") != "INDUCED_OPERATOR":
        return {"valid": False, "reason": "WRONG_KIND"}
    expected_params = [p["name"] for p in f["visible"]["parameters"]]
    if proposal.get("parameters") != expected_params:
        return {"valid": False, "reason": "PARAMETER_CONTRACT_MISMATCH"}
    try:
        c = schema_canonical(proposal)
    except Exception:
        return {"valid": False, "reason": "INVALID_SCHEMA_SHAPE"}
    universe = set(typed_atom_universe(f["visible"]))
    for field in ("preconditions", "add_effects", "delete_effects"):
        atoms = {ak(a) for a in c[field]}
        if not atoms.issubset(universe):
            return {"valid": False, "reason": "ATOM_OUTSIDE_TYPED_VOCAB"}
    if not (1 <= len(c["preconditions"]) <= MAX_PRE and 1 <= len(c["add_effects"]) <= MAX_ADD and len(c["delete_effects"]) == DELETE_N):
        return {"valid": False, "reason": "OUTSIDE_FROZEN_HYPOTHESIS_SIZE"}
    if set(map(ak, c["add_effects"])) & set(map(ak, c["delete_effects"])):
        return {"valid": False, "reason": "ADD_DELETE_OVERLAP"}
    if not all_params_used(c):
        return {"valid": False, "reason": "UNUSED_PARAMETER"}
    if skey(c) != skey(pf["oracle"]):
        return {"valid": False, "reason": "SEMANTIC_SIGNATURE_MISMATCH"}
    ho = heldout_after(c, f["visible"]["heldout_target"])
    if not ho["applicable"] or stateset(ho["after"]) != stateset(f["oracle"]["heldout_after"]):
        return {"valid": False, "reason": "HELDOUT_TRANSITION_FAIL"}
    return {"valid": True, "reason": "VALID"}


def score_rows(fixtures: list[dict[str, Any]], predictions: dict[str, Any], search_bound_ids: set[str] | None = None) -> dict[str, Any]:
    search_bound_ids = search_bound_ids or set()
    valid = invalid = fail_open = search_bound = 0
    reasons: dict[str, int] = defaultdict(int)
    fam = defaultdict(lambda: {"fixtures": 0, "valid": 0, "invalid": 0, "search_bound": 0})
    rows = []
    for f in fixtures:
        fid, family = f["id"], f["family"]
        fam[family]["fixtures"] += 1
        if fid in search_bound_ids:
            search_bound += 1
            fam[family]["search_bound"] += 1
            rows.append({"fixture_id": fid, "family": family, "valid": False, "reason": "DETERMINISTIC_SEARCH_BOUND", "prediction": predictions.get(fid)})
            continue
        pred = predictions.get(fid)
        s = validate_prediction(f, pred)
        ok = bool(s["valid"])
        valid += int(ok)
        invalid += int(not ok)
        fail_open += int((not ok) and pred is not None)
        reasons[s["reason"]] += 1
        fam[family]["valid"] += int(ok)
        fam[family]["invalid"] += int(not ok)
        rows.append({"fixture_id": fid, "family": family, "valid": ok, "reason": s["reason"], "prediction": pred})
    denom = len(fixtures) - search_bound
    return {
        "valid_induced_schema_rate": valid / denom if denom else 0.0,
        "valid_total": valid,
        "invalid_total": invalid,
        "fail_open_count": fail_open,
        "deterministic_search_bound_count": search_bound,
        "fixture_count": len(fixtures),
        "scored_fixture_count": denom,
        "reason_counts": dict(sorted(reasons.items())),
        "per_family": {k: {**v, "valid_rate": v["valid"] / (v["fixtures"] - v["search_bound"]) if v["fixtures"] > v["search_bound"] else None} for k, v in sorted(fam.items())},
        "rows": rows,
    }
