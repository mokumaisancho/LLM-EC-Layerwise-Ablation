#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from pathlib import Path
from typing import Any

PROTOCOL = "FUNCTION_BOUNDARY_S2B2_B2_OPERATOR_HOLDOUT_V1"


def atom(pred: str, *args: str) -> dict[str, Any]:
    return {"pred": pred, "args": list(args)}


def instantiate(a: dict[str, Any], binding: dict[str, str]) -> dict[str, Any]:
    return atom(a["pred"], *(binding[x] for x in a["args"]))


def state_key(a: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    return a["pred"], tuple(a["args"])


def apply_hidden(before: list[dict[str, Any]], binding: dict[str, str], add: list[dict[str, Any]], delete: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state = {state_key(x) for x in before}
    dels = {state_key(instantiate(x, binding)) for x in delete}
    adds = {state_key(instantiate(x, binding)) for x in add}
    after = (state - dels) | adds
    return [atom(p, *args) for p, args in sorted(after)]


def schema(params: list[dict[str, str]], pre: list[dict[str, Any]], add: list[dict[str, Any]], delete: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "proposal_kind": "INDUCED_OPERATOR",
        "parameters": [p["name"] for p in params],
        "preconditions": copy.deepcopy(pre),
        "add_effects": copy.deepcopy(add),
        "delete_effects": copy.deepcopy(delete),
    }


def structural_fingerprint(params: list[dict[str, str]], pre: list[dict[str, Any]], add: list[dict[str, Any]], delete: list[dict[str, Any]]) -> str:
    payload = {
        "mode": "structured_transition_operator_induction",
        "parameter_types": [p["type"] for p in params],
        "pre_shapes": [[len(a["args"]), [next(p["type"] for p in params if p["name"] == x) for x in a["args"]]] for a in pre],
        "add_shapes": [[len(a["args"]), [next(p["type"] for p in params if p["name"] == x) for x in a["args"]]] for a in add],
        "delete_shapes": [[len(a["args"]), [next(p["type"] for p in params if p["name"] == x) for x in a["args"]]] for a in delete],
        "positive_examples": 2,
        "negative_examples": len(pre),
        "heldout_target": True,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def make_fixture(fid: str, family: str, variant: int, params: list[dict[str, str]], pre: list[dict[str, Any]], add: list[dict[str, Any]], delete: list[dict[str, Any]], base_vocab: dict[str, list[str]]) -> dict[str, Any]:
    first_type = params[0]["type"]
    vocab = copy.deepcopy(base_vocab)
    vocab.update({
        "noise_pos1": [first_type],
        "noise_pos2": [first_type],
        "noise_neg": [first_type],
        "noise_hold": [first_type],
        "known_marker": [first_type],
    })
    n_values = 3 + len(pre)
    entities: dict[str, list[str]] = {}
    for p in params:
        stem = f"{family}_v{variant}_{p['name'][1:]}"
        entities[p["name"]] = [f"{stem}_{i}" for i in range(n_values)]

    def binding(index: int) -> dict[str, str]:
        return {p["name"]: entities[p["name"]][index] for p in params}

    positives = []
    for index, noise_pred in ((0, "noise_pos1"), (1, "noise_pos2")):
        b = binding(index)
        before = [instantiate(x, b) for x in pre]
        before.append(atom(noise_pred, b[params[0]["name"]]))
        positives.append({"binding": b, "before": before, "after": apply_hidden(before, b, add, delete)})

    negatives = []
    for omit in range(len(pre)):
        b = binding(2 + omit)
        before = [instantiate(x, b) for i, x in enumerate(pre) if i != omit]
        before.append(atom("noise_neg", b[params[0]["name"]]))
        negatives.append({"binding": b, "before": before, "after": copy.deepcopy(before)})

    hb = binding(2 + len(pre))
    heldout_before = [instantiate(x, hb) for x in pre]
    heldout_before.append(atom("noise_hold", hb[params[0]["name"]]))
    heldout_after = apply_hidden(heldout_before, hb, add, delete)

    marker_param = params[0]["name"]
    supplied = [{
        "parameters": [p["name"] for p in params],
        "preconditions": [copy.deepcopy(pre[0])],
        "add_effects": [atom("known_marker", marker_param)],
        "delete_effects": copy.deepcopy(delete),
    }]

    visible = {
        "parameters": copy.deepcopy(params),
        "predicate_vocabulary": vocab,
        "supplied_primitive_ontology": supplied,
        "positive_examples": positives,
        "negative_examples": negatives,
        "heldout_target": {"binding": hb, "before": heldout_before},
    }
    return {
        "id": fid,
        "family": family,
        "structural_fingerprint": structural_fingerprint(params, pre, add, delete),
        "visible": visible,
        "oracle": {
            "semantic_signature": schema(params, pre, add, delete),
            "heldout_after": heldout_after,
        },
    }


def specs() -> list[dict[str, Any]]:
    return [
        {
            "family": "unary_1pre_add1_del1",
            "params": [{"name": "$x", "type": "item"}],
            "pre": [atom("pending", "$x")],
            "add": [atom("approved", "$x")],
            "delete": [atom("pending", "$x")],
            "vocab": {"pending": ["item"], "approved": ["item"]},
        },
        {
            "family": "unary_2pre_add1_del1",
            "params": [{"name": "$x", "type": "asset"}],
            "pre": [atom("eligible", "$x"), atom("draft", "$x")],
            "add": [atom("certified", "$x")],
            "delete": [atom("draft", "$x")],
            "vocab": {"eligible": ["asset"], "draft": ["asset"], "certified": ["asset"]},
        },
        {
            "family": "unary_1pre_add2_del1",
            "params": [{"name": "$x", "type": "task"}],
            "pre": [atom("queued", "$x")],
            "add": [atom("processed", "$x"), atom("logged", "$x")],
            "delete": [atom("queued", "$x")],
            "vocab": {"queued": ["task"], "processed": ["task"], "logged": ["task"]},
        },
        {
            "family": "unary_3pre_add2_del1",
            "params": [{"name": "$x", "type": "release"}],
            "pre": [atom("tested", "$x"), atom("signed", "$x"), atom("draft", "$x")],
            "add": [atom("published", "$x"), atom("audited", "$x")],
            "delete": [atom("draft", "$x")],
            "vocab": {"tested": ["release"], "signed": ["release"], "draft": ["release"], "published": ["release"], "audited": ["release"]},
        },
        {
            "family": "binary_2pre_addcross_delunary",
            "params": [{"name": "$a", "type": "job"}, {"name": "$b", "type": "node"}],
            "pre": [atom("job_ready", "$a"), atom("available", "$b")],
            "add": [atom("assigned", "$a", "$b")],
            "delete": [atom("available", "$b")],
            "vocab": {"job_ready": ["job"], "available": ["node"], "assigned": ["job", "node"]},
        },
        {
            "family": "binary_3pre_addunary_delcross",
            "params": [{"name": "$a", "type": "doc"}, {"name": "$b", "type": "reviewer"}],
            "pre": [atom("authorized_by", "$a", "$b"), atom("reviewer_active", "$b"), atom("pending", "$a")],
            "add": [atom("accepted", "$a")],
            "delete": [atom("authorized_by", "$a", "$b")],
            "vocab": {"authorized_by": ["doc", "reviewer"], "reviewer_active": ["reviewer"], "pending": ["doc"], "accepted": ["doc"]},
        },
        {
            "family": "binary_1crosspre_add2_delcross",
            "params": [{"name": "$a", "type": "record"}, {"name": "$b", "type": "vault"}],
            "pre": [atom("staged_at", "$a", "$b")],
            "add": [atom("stored_at", "$a", "$b"), atom("retained", "$a")],
            "delete": [atom("staged_at", "$a", "$b")],
            "vocab": {"staged_at": ["record", "vault"], "stored_at": ["record", "vault"], "retained": ["record"]},
        },
        {
            "family": "ternary_3pre_add2_delunary",
            "params": [{"name": "$a", "type": "pkg"}, {"name": "$b", "type": "src"}, {"name": "$c", "type": "dst"}],
            "pre": [atom("ready_pkg", "$a"), atom("source_ready", "$b"), atom("destination_ready", "$c")],
            "add": [atom("moved", "$a", "$b", "$c"), atom("verified", "$a")],
            "delete": [atom("ready_pkg", "$a")],
            "vocab": {"ready_pkg": ["pkg"], "source_ready": ["src"], "destination_ready": ["dst"], "moved": ["pkg", "src", "dst"], "verified": ["pkg"]},
        },
    ]


def make_cases() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seq = 1
    for spec in specs():
        for variant in (1, 2):
            out.append(make_fixture(
                f"B2{seq:02d}", spec["family"], variant,
                spec["params"], spec["pre"], spec["add"], spec["delete"], spec["vocab"],
            ))
            seq += 1
    return out


CASES = make_cases()


def seed_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16)


def generate(seed: str) -> list[dict[str, Any]]:
    rng = random.Random(seed_int(seed))
    rows = copy.deepcopy(CASES)
    rng.shuffle(rows)
    for f in rows:
        rng.shuffle(f["visible"]["supplied_primitive_ontology"])
        rng.shuffle(f["visible"]["positive_examples"])
        rng.shuffle(f["visible"]["negative_examples"])
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True, help="generator freeze commit SHA")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rows = generate(args.seed)
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    out = {
        "protocol": PROTOCOL,
        "seed_source": "generator freeze commit SHA",
        "seed": args.seed,
        "fixture_count": len(rows),
        "family_count": len({x["family"] for x in rows}),
        "holdout_digest": digest,
        "structural_fingerprints": sorted({x["structural_fingerprint"] for x in rows}),
        "fixtures": rows,
    }
    args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("protocol", "fixture_count", "family_count", "holdout_digest", "structural_fingerprints")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
