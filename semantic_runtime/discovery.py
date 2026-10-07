from __future__ import annotations

import itertools
import math
import re
from collections import Counter
from typing import Any

from .public_hypotheses import (
    candidates,
    evaluation_predictions,
)

PROTOCOL = "S1C_V31_DETERMINISTIC_DISCOVERY_V1"
TOKEN_RE = re.compile(r"[a-z0-9<>]+", re.I)
STOP = {
    "a","an","and","are","as","at","be","been","being","by","for","from","has","have",
    "in","is","it","of","on","or","that","the","their","there","this","to","was","were",
    "which","with","while",
}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).lower().replace("_", " ").replace("-", " ")).strip()


def tokens(text: str) -> list[str]:
    return [x for x in TOKEN_RE.findall(norm(text)) if x not in STOP]


def char3(text: str) -> Counter[str]:
    s = norm(text)
    return Counter(s[i:i+3] for i in range(max(0, len(s)-2)))


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def similarities(query: str, docs: list[str]) -> list[float]:
    all_docs = docs + [query]
    tfs = [Counter(tokens(x)) for x in all_docs]
    df = Counter()
    for row in tfs:
        for term in row:
            df[term] += 1
    n = len(all_docs)
    idf = {term: math.log((n + 1) / (freq + 1)) + 1.0 for term, freq in df.items()}
    q = {term: count * idf[term] for term, count in tfs[-1].items()}
    q3 = char3(query)
    out = []
    for text, row in zip(docs, tfs[:-1]):
        d = {term: count * idf[term] for term, count in row.items()}
        out.append(0.70 * cosine(q, d) + 0.30 * cosine(q3, char3(text)))
    return out


def _pairings():
    return (((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2)))


def discover_partition(train: list[dict[str, Any]]):
    if len(train) != 4:
        return None
    valid = []
    for pairing in _pairings():
        resolved = []
        ok = True
        for pair in pairing:
            merged = []
            for index in pair:
                merged.extend(train[index].get("behavior_observations") or [])
            c = candidates(merged)
            if len(c) != 1:
                ok = False
                break
            resolved.append(c[0])
        if ok and resolved[0] != resolved[1]:
            valid.append((pairing, resolved))
    if len(valid) != 1:
        return None

    pairing, codes = valid[0]
    groups = []
    for pair, code in zip(pairing, codes):
        members = sorted(str(train[i]["example_id"]) for i in pair)
        groups.append((members, code, pair))
    groups.sort(key=lambda x: x[0])
    return groups


def mask_entities(text: str, registry: dict[str, Any]) -> str:
    out = text
    replacements = []
    for item in registry.values():
        typ = item.get("type")
        for form in item.get("surface_forms", []):
            replacements.append((len(str(form)), str(form), f"<{typ}>"))
    for _, form, repl in sorted(replacements, key=lambda x: (-x[0], x[1].lower())):
        out = re.sub(re.escape(form), repl, out, flags=re.I)
    return norm(out)


def arg_types_for(ex: dict[str, Any]) -> list[str]:
    return [ex["entity_registry"][eid]["type"] for eid in sorted(ex["entity_registry"])]


def bind_args(text: str, registry: dict[str, Any], arg_types: list[str]) -> list[str] | None:
    low = text.lower()
    by_type: dict[str, list[tuple[int, str]]] = {}
    for eid, item in registry.items():
        positions = [
            low.find(str(form).lower())
            for form in item.get("surface_forms", [])
            if str(form) and low.find(str(form).lower()) >= 0
        ]
        if positions:
            by_type.setdefault(item["type"], []).append((min(positions), eid))
    for typ in by_type:
        by_type[typ].sort()

    args = []
    used = set()
    for typ in arg_types:
        pool = [eid for _, eid in by_type.get(typ, []) if eid not in used]
        if not pool:
            return None
        args.append(pool[0])
        used.add(pool[0])
    return args


def polarity_modality(text: str) -> tuple[str, str]:
    low = norm(text)
    polarity = "NEG" if re.search(r"\b(not|no|never|cannot|does not|do not|isn't|isnt)\b", low) else "POS"
    if re.search(r"\b(must|required|requires|shall|needs to|need to)\b", low):
        modality = "REQUIRED"
    elif re.search(r"\b(may|might|could|possible|possibly)\b", low):
        modality = "POSSIBLE"
    else:
        modality = "ASSERTED"
    return polarity, modality


def ambiguous(text: str) -> bool:
    low = norm(text)
    return (
        "unresolved between:" in low
        or "unclear whether" in low
        or ("either" in low and " or " in f" {low} ")
    )


def predict(task: dict[str, Any]) -> dict[str, Any]:
    visible = task["visible"]
    train = visible["training_examples"]
    held = visible["heldout_examples"]
    groups = discover_partition(train)

    if groups is None:
        return {
            "discovered_slots": [
                {
                    "slot_id": "S01",
                    "arg_types": [],
                    "training_members": [str(x["example_id"]) for x in train],
                    "evaluation_probe_predictions": [
                        {"probe_id": str(p["probe_id"]), "predicted_after": [0, 0, 0]}
                        for p in visible["evaluation_probes"]
                    ],
                }
            ],
            "heldout_assignments": [],
            "abstentions": [
                {"example_id": str(x["example_id"]), "status": "AMBIGUOUS"}
                for x in held
            ],
        }

    slots = []
    docs = []
    slot_types: dict[str, list[str]] = {}
    for i, (members, code, pair) in enumerate(groups, 1):
        sid = f"S{i:02d}"
        types = arg_types_for(train[pair[0]])
        slots.append(
            {
                "slot_id": sid,
                "arg_types": types,
                "training_members": members,
                "evaluation_probe_predictions": evaluation_predictions(code),
            }
        )
        slot_types[sid] = types
        docs.append(
            " ".join(
                mask_entities(train[index]["raw_text"], train[index]["entity_registry"])
                for index in pair
            )
        )

    sids = [s["slot_id"] for s in slots]
    assignments = []
    abstentions = []

    for ex in held:
        eid = str(ex["example_id"])
        raw = str(ex["raw_text"])
        if ambiguous(raw):
            abstentions.append({"example_id": eid, "status": "AMBIGUOUS"})
            continue

        query = mask_entities(raw, ex["entity_registry"])
        scores = similarities(query, docs)
        ranked = sorted(zip(scores, sids), key=lambda x: (-x[0], x[1]))
        if (
            not ranked
            or ranked[0][0] <= 0.0
            or (len(ranked) > 1 and abs(ranked[0][0] - ranked[1][0]) <= 1e-12)
        ):
            abstentions.append({"example_id": eid, "status": "AMBIGUOUS"})
            continue

        sid = ranked[0][1]
        args = bind_args(raw, ex["entity_registry"], slot_types[sid])
        if args is None:
            abstentions.append({"example_id": eid, "status": "AMBIGUOUS"})
            continue

        polarity, modality = polarity_modality(raw)
        assignments.append(
            {
                "example_id": eid,
                "slot_id": sid,
                "arguments": args,
                "polarity": polarity,
                "modality": modality,
            }
        )

    return {
        "discovered_slots": slots,
        "heldout_assignments": sorted(assignments, key=lambda x: x["example_id"]),
        "abstentions": sorted(abstentions, key=lambda x: x["example_id"]),
    }


def manifest() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "oracle_visible": False,
        "generator_visible": False,
        "validator_visible": False,
        "scorer_visible": False,
        "selected_target_functions_visible": False,
        "allowed_scientific_import": "s1c_v31_public_hypotheses only",
        "partition_method": "enumerate all three pairings; require exactly one partition where each pair union identifies one distinct public 64-class function",
        "heldout_method": "entity-masked lexical retrieval to discovered slot member texts",
        "post_result_tuning": False,
    }


__all__ = ["PROTOCOL", "discover_partition", "manifest", "predict"]
