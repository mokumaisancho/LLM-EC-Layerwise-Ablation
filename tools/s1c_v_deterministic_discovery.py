#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from typing import Any

PROTOCOL = "S1C_V_DETERMINISTIC_DENOTATIONAL_DISCOVERY_V1"
TOKEN_RE = re.compile(r"[a-z0-9<>]+", re.I)
STOPWORDS = {
    "a","an","and","are","as","at","be","been","being","but","by","for","from","has","have","in","is","it",
    "of","on","or","that","the","their","there","this","to","was","were","which","with","while",
}
AMBIGUITY_CUES = ("unresolved", "does not decide", "cannot decide", "either", "unclear whether", "ambiguous")


def canon(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("_", " ").replace("-", " ")).strip()


def _tokens(text: str) -> list[str]:
    return [x for x in TOKEN_RE.findall(_norm(text)) if x not in STOPWORDS]


def _char3(text: str) -> Counter[str]:
    s = _norm(text)
    return Counter(s[i:i+3] for i in range(max(0, len(s)-2)))


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def _similarities(query: str, docs: list[str]) -> list[float]:
    all_docs = docs + [query]
    tfs = [Counter(_tokens(x)) for x in all_docs]
    df: Counter[str] = Counter()
    for row in tfs:
        for term in row:
            df[term] += 1
    n = len(all_docs)
    idf = {term: math.log((n + 1) / (freq + 1)) + 1.0 for term, freq in df.items()}
    qtf = tfs[-1]
    qv = {term: count * idf[term] for term, count in qtf.items()}
    q3 = _char3(query)
    scores = []
    for text, row in zip(docs, tfs[:-1]):
        dv = {term: count * idf[term] for term, count in row.items()}
        token = _cosine(qv, dv)
        tri = _cosine(q3, _char3(text))
        scores.append(0.70 * token + 0.30 * tri)
    return scores


def _mask_entities(text: str, registry: dict[str, Any]) -> str:
    masked = text
    replacements: list[tuple[int, str, str]] = []
    for _, item in registry.items():
        if not isinstance(item, dict):
            continue
        typ = item.get("type")
        if not isinstance(typ, str):
            continue
        for form in item.get("surface_forms", []):
            form = str(form)
            if form:
                replacements.append((len(form), form, f"<{typ}>"))
    for _, form, repl in sorted(replacements, key=lambda x: (-x[0], x[1].lower())):
        masked = re.sub(re.escape(form), repl, masked, flags=re.I)
    return _norm(masked)


def _slot_key(example: dict[str, Any]) -> str:
    sig = example.get("observable_behavior_signature")
    return hashlib.sha256(canon(sig).encode()).hexdigest()


def _slot_arg_types(example: dict[str, Any]) -> tuple[str, ...]:
    sig = example.get("observable_behavior_signature")
    if not isinstance(sig, dict):
        return ()
    arg_types = sig.get("arg_types", [])
    if not isinstance(arg_types, list) or not all(isinstance(x, str) for x in arg_types):
        return ()
    return tuple(arg_types)


def _surface_positions(text: str, registry: dict[str, Any]) -> dict[str, int]:
    low = text.lower()
    out: dict[str, int] = {}
    for eid, item in registry.items():
        if not isinstance(item, dict):
            continue
        positions = []
        for form in item.get("surface_forms", []):
            form = str(form)
            p = low.find(form.lower()) if form else -1
            if p >= 0:
                positions.append(p)
        if positions:
            out[str(eid)] = min(positions)
    return out


def _bind_arguments(text: str, registry: dict[str, Any], arg_types: tuple[str, ...]) -> list[str] | None:
    positions = _surface_positions(text, registry)
    by_type: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for eid, pos in positions.items():
        item = registry.get(eid)
        typ = item.get("type") if isinstance(item, dict) else None
        if isinstance(typ, str):
            by_type[typ].append((pos, eid))
    for typ in by_type:
        by_type[typ].sort()

    used: set[str] = set()
    args: list[str] = []
    for typ in arg_types:
        candidates = [eid for _, eid in by_type.get(typ, []) if eid not in used]
        if not candidates:
            return None
        chosen = candidates[0]
        used.add(chosen)
        args.append(chosen)
    return args


def _polarity_modality(text: str) -> tuple[str, str]:
    low = _norm(text)
    polarity = "NEG" if re.search(r"\b(not|no|never|does not|do not|isn't|isnt|cannot)\b", low) else "POS"
    if re.search(r"\b(must|required|requires|shall|needs to|need to)\b", low):
        modality = "REQUIRED"
    elif re.search(r"\b(may|might|could|possible|possibly)\b", low):
        modality = "POSSIBLE"
    else:
        modality = "ASSERTED"
    return polarity, modality


def _looks_ambiguous(text: str) -> bool:
    low = _norm(text)
    return (
        "unresolved" in low
        or "does not decide" in low
        or "cannot decide" in low
        or "unclear whether" in low
        or "ambiguous" in low
        or ("either" in low and " or " in f" {low} ")
    )


def predict(task: dict[str, Any]) -> dict[str, Any]:
    visible = task["visible"]
    training = visible["training_examples"]
    heldout = visible["heldout_examples"]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ex in training:
        grouped[_slot_key(ex)].append(ex)

    discovered_slots = []
    owner: dict[str, str] = {}
    slot_docs: dict[str, list[str]] = {}
    slot_types: dict[str, tuple[str, ...]] = {}
    ambiguous_slots: set[str] = set()

    for idx, key in enumerate(sorted(grouped), 1):
        rows = grouped[key]
        sid = f"S{idx:02d}"
        types = _slot_arg_types(rows[0])
        if any(_slot_arg_types(r) != types for r in rows):
            raise ValueError("INCONSISTENT_VISIBLE_ARG_TYPES_WITHIN_BEHAVIOR_CLUSTER")
        members = sorted(str(r["example_id"]) for r in rows)
        discovered_slots.append({
            "slot_id": sid,
            "arg_types": list(types),
            "training_members": members,
        })
        for mid in members:
            owner[mid] = sid
        slot_docs[sid] = [_mask_entities(str(r["raw_text"]), r["entity_registry"]) for r in rows]
        slot_types[sid] = types
        if any(bool((r.get("observable_behavior_signature") or {}).get("ambiguous")) for r in rows):
            ambiguous_slots.add(sid)

    all_slot_ids = sorted(slot_docs)
    slot_centers = [" ".join(slot_docs[sid]) for sid in all_slot_ids]

    heldout_assignments = []
    abstentions = []
    for ex in heldout:
        eid = str(ex["example_id"])
        raw = str(ex["raw_text"])
        registry = ex["entity_registry"]
        query = _mask_entities(raw, registry)
        scores = _similarities(query, slot_centers)
        ranked = sorted(zip(scores, all_slot_ids), key=lambda x: (-x[0], x[1]))
        if not ranked:
            abstentions.append({"example_id": eid, "status": "AMBIGUOUS"})
            continue

        best_score, sid = ranked[0]
        cross_slot_tie = len(ranked) > 1 and abs(best_score - ranked[1][0]) <= 1e-12 and ranked[1][1] != sid
        if best_score <= 0.0 or cross_slot_tie or _looks_ambiguous(raw) or sid in ambiguous_slots:
            abstentions.append({"example_id": eid, "status": "AMBIGUOUS"})
            continue

        args = _bind_arguments(raw, registry, slot_types[sid])
        if args is None:
            abstentions.append({"example_id": eid, "status": "AMBIGUOUS"})
            continue
        polarity, modality = _polarity_modality(raw)
        heldout_assignments.append({
            "example_id": eid,
            "slot_id": sid,
            "arguments": args,
            "polarity": polarity,
            "modality": modality,
        })

    return {
        "discovered_slots": discovered_slots,
        "heldout_assignments": sorted(heldout_assignments, key=lambda x: x["example_id"]),
        "abstentions": sorted(abstentions, key=lambda x: x["example_id"]),
    }


def predictor_manifest() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "oracle_visible": False,
        "family_visible": False,
        "canonical_slot_name_visible": False,
        "canonical_slot_id_visible": False,
        "discovery_rule": "cluster training examples by exact canonical observable_behavior_signature; slot IDs are arbitrary hash-order labels",
        "grounding_rule": "entity-type-masked lexical retrieval from heldout raw text to discovered slot training texts",
        "similarity": "0.70 token-TFIDF cosine + 0.30 char-trigram cosine",
        "argument_binding": "left-to-right visible mention binding under discovered slot arg_types",
        "polarity_modality": "generic lexical cues only",
        "abstention": "explicit ambiguity cue, unresolved binding, zero similarity, or exact cross-slot tie",
        "post_result_tuning": False,
    }
