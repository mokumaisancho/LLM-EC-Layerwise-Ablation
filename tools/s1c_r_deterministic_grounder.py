#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

PROTOCOL = "S1C_R_DETERMINISTIC_DEMONSTRATION_GROUNDER_V1"
TOKEN_RE = re.compile(r"[a-z0-9<>]+", re.I)
CLAUSE_RE = re.compile(r"(?:[.!?;:\n]+|\bbut\b|\bwhile\b|\bwhereas\b)", re.I)
STOPWORDS = {
    "a","an","and","are","as","at","be","been","being","by","for","from","has","have","in","is","it",
    "of","on","that","the","their","there","this","to","was","were","which","with",
}


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


def _similarity(query: str, docs: list[str]) -> list[float]:
    all_docs = docs + [query]
    tf = [Counter(_tokens(x)) for x in all_docs]
    df: Counter[str] = Counter()
    for row in tf:
        for term in row:
            df[term] += 1
    n = len(all_docs)
    idf = {term: math.log((n + 1) / (freq + 1)) + 1.0 for term, freq in df.items()}
    qtf = tf[-1]
    qv = {term: count * idf[term] for term, count in qtf.items()}
    q3 = _char3(query)
    scores = []
    for text, row in zip(docs, tf[:-1]):
        dv = {term: count * idf[term] for term, count in row.items()}
        token = _cosine(qv, dv)
        tri = _cosine(q3, _char3(text))
        scores.append(0.70 * token + 0.30 * tri)
    return scores


def _surface_positions(text: str, registry: dict[str, Any]) -> dict[str, int]:
    low = text.lower()
    out: dict[str, int] = {}
    for eid, item in registry.items():
        forms = item.get("surface_forms", []) if isinstance(item, dict) else []
        positions = [low.find(str(form).lower()) for form in forms if str(form) and low.find(str(form).lower()) >= 0]
        if positions:
            out[eid] = min(positions)
    return out


def _mask_entities(text: str, registry: dict[str, Any]) -> str:
    masked = text
    replacements: list[tuple[int, str, str]] = []
    for eid, item in registry.items():
        typ = item.get("type") if isinstance(item, dict) else None
        if not isinstance(typ, str):
            continue
        for form in item.get("surface_forms", []):
            form = str(form)
            if form:
                replacements.append((len(form), form, f"<{typ}>"))
    for _, form, repl in sorted(replacements, key=lambda x: (-x[0], x[1].lower())):
        masked = re.sub(re.escape(form), repl, masked, flags=re.I)
    return _norm(masked)


def _clauses(text: str) -> list[str]:
    rows = [_norm(x) for x in CLAUSE_RE.split(text) if _norm(x)]
    return rows or [_norm(text)]


def _mentioned_entities(text: str, registry: dict[str, Any]) -> list[str]:
    pos = _surface_positions(text, registry)
    return [eid for eid, _ in sorted(pos.items(), key=lambda kv: (kv[1], kv[0]))]


def _arg_types(inventory: dict[str, Any], pred: str) -> list[str] | None:
    item = inventory.get(pred)
    types = item.get("arg_types") if isinstance(item, dict) else None
    return list(types) if isinstance(types, list) else None


def _entity_type(registry: dict[str, Any], eid: str) -> str | None:
    item = registry.get(eid)
    return item.get("type") if isinstance(item, dict) else None


def _bind_arguments(clause: str, registry: dict[str, Any], arg_types: list[str]) -> list[str] | None:
    mentioned = _mentioned_entities(clause, registry)
    by_type: dict[str, list[str]] = defaultdict(list)
    for eid in mentioned:
        typ = _entity_type(registry, eid)
        if typ:
            by_type[typ].append(eid)

    used: set[str] = set()
    args: list[str] = []
    for typ in arg_types:
        pool = [eid for eid in by_type.get(typ, []) if eid not in used]
        if not pool:
            return None
        chosen = pool[0]
        used.add(chosen)
        args.append(chosen)
    return args


def _context_for_atom(raw_text: str, registry: dict[str, Any], atom: dict[str, Any]) -> str:
    clauses = _clauses(raw_text)
    arg_ids = [str(x) for x in atom.get("arguments", [])]
    forms: list[str] = []
    for eid in arg_ids:
        item = registry.get(eid, {})
        forms.extend(str(x).lower() for x in item.get("surface_forms", []) if str(x))
    if not forms:
        return _mask_entities(raw_text, registry)
    hits_all = [c for c in clauses if all(form in c.lower() for form in forms)]
    if hits_all:
        return _mask_entities(" ".join(hits_all), registry)
    hits_any = [c for c in clauses if any(form in c.lower() for form in forms)]
    return _mask_entities(" ".join(hits_any) if hits_any else raw_text, registry)


def _slot(atom: dict[str, Any]) -> tuple[str, str, str]:
    return (str(atom["predicate"]), str(atom["polarity"]), str(atom["modality"]))


def _build_prototypes(visible: dict[str, Any]) -> tuple[dict[tuple[str, str, str], list[str]], list[str], list[str]]:
    prototypes: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    ambiguous_docs: list[str] = []
    ok_docs: list[str] = []
    for demo in visible.get("demonstrations", []):
        raw = str(demo.get("raw_text", ""))
        registry = demo.get("entity_registry", {})
        typed_ir = demo.get("typed_ir", {})
        status = typed_ir.get("status")
        whole = _mask_entities(raw, registry)
        if status == "AMBIGUOUS":
            ambiguous_docs.append(whole)
            continue
        if status != "OK":
            continue
        ok_docs.append(whole)
        for atom in typed_ir.get("atoms", []):
            if not isinstance(atom, dict):
                continue
            prototypes[_slot(atom)].append(_context_for_atom(raw, registry, atom))
    return prototypes, ambiguous_docs, ok_docs


def _ambiguity_by_demo(query: str, ambiguous_docs: list[str], ok_docs: list[str]) -> bool:
    if not ambiguous_docs:
        return False
    docs = ambiguous_docs + ok_docs
    scores = _similarity(query, docs)
    if not scores:
        return False
    best_amb = max(scores[:len(ambiguous_docs)])
    best_ok = max(scores[len(ambiguous_docs):], default=-1.0)
    return best_amb > best_ok


def predict(fixture: dict[str, Any]) -> dict[str, Any]:
    visible = fixture["visible"]
    raw_text = str(visible["raw_text"])
    registry = visible["entity_registry"]
    inventory = visible["opaque_semantic_inventory"]
    prototypes, ambiguous_docs, ok_docs = _build_prototypes(visible)

    whole = _mask_entities(raw_text, registry)
    if _ambiguity_by_demo(whole, ambiguous_docs, ok_docs):
        return {"status": "AMBIGUOUS", "atoms": []}

    atoms: dict[tuple[str, tuple[str, ...], str, str], dict[str, Any]] = {}
    any_unresolved = False
    for clause in _clauses(raw_text):
        mentioned = _mentioned_entities(clause, registry)
        if not mentioned:
            continue
        query = _mask_entities(clause, registry)
        candidates: list[tuple[tuple[str, str, str], list[str]]] = []
        for slot, docs in prototypes.items():
            pred, _, _ = slot
            types = _arg_types(inventory, pred)
            if types is None:
                continue
            args = _bind_arguments(clause, registry, types)
            if args is not None:
                candidates.append((slot, args))
        if not candidates:
            any_unresolved = True
            continue

        slot_docs = [" ".join(prototypes[slot]) for slot, _ in candidates]
        scores = _similarity(query, slot_docs)
        ranked = sorted(
            zip(scores, candidates),
            key=lambda x: (-x[0], x[1][0], tuple(x[1][1])),
        )
        if not ranked:
            any_unresolved = True
            continue
        best_score, (best_slot, best_args) = ranked[0]
        if best_score <= 0.0:
            any_unresolved = True
            continue
        if len(ranked) > 1 and abs(best_score - ranked[1][0]) <= 1e-12 and ranked[1][1][0] != best_slot:
            any_unresolved = True
            continue

        pred, polarity, modality = best_slot
        atom = {
            "predicate": pred,
            "arguments": best_args,
            "polarity": polarity,
            "modality": modality,
        }
        key = (pred, tuple(best_args), polarity, modality)
        atoms[key] = atom

    if any_unresolved and not atoms:
        return {"status": "AMBIGUOUS", "atoms": []}
    return {"status": "OK", "atoms": [atoms[k] for k in sorted(atoms)]}


def predictor_manifest() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "oracle_visible": False,
        "family_visible": False,
        "hidden_gloss_visible": False,
        "domain_specific_dictionary": False,
        "learned_from": "model-visible frozen demonstrations only",
        "semantic_inventory_authority": "opaque IDs plus type/arity signatures only",
        "grounding_method": "clause-level demonstration retrieval with entity-type masking and typed argument binding",
        "similarity": "0.70 token-TFIDF cosine + 0.30 char-trigram cosine",
        "ambiguity": "nearest ambiguous demonstration must strictly outrank nearest OK demonstration, or no clause can be resolved",
        "tie_policy": "exact cross-slot score ties fail closed for the clause",
        "post_result_tuning": False,
    }
