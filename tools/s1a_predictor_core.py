#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from collections import Counter

FIELDS = ("primary_fact_id", "semantic_concept_id", "key_relation_id", "ambiguity", "goal_id")
STOPWORDS = {
    "a","an","and","are","as","at","be","been","being","but","by","for","from","has","have","in","is","it",
    "of","on","or","that","the","their","there","this","to","under","was","were","which","with","while","only",
    "all","both","one","two","three","same","current","identify","represent","semantic","state"
}
TOKEN_RE = re.compile(r"[a-z0-9]+")
ID_RE = re.compile(r"f\d+|c_[a-z0-9_]+|g\d+", re.I)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("_", " ").replace("-", " ")).strip()


def tokens(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(norm(text)) if t not in STOPWORDS]


def char3(text: str) -> Counter[str]:
    s = norm(text)
    return Counter(s[i:i+3] for i in range(max(0, len(s)-2)))


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    return dot/(na*nb) if na and nb else 0.0


def lexical_scores(query: str, docs: dict[str, str]) -> dict[str, float]:
    doc_tf = {k: Counter(tokens(v)) for k,v in docs.items()}
    n = len(doc_tf)
    df: Counter[str] = Counter()
    for tf in doc_tf.values():
        for term in tf:
            df[term] += 1
    idf = {term: math.log((n+1)/(freq+1))+1.0 for term,freq in df.items()}
    qtf = Counter(tokens(query))
    qv = {term: count*idf.get(term, math.log(n+1)+1.0) for term,count in qtf.items()}
    q3 = char3(query)
    out = {}
    for key,text in docs.items():
        dv = {term: count*idf.get(term, math.log(n+1)+1.0) for term,count in doc_tf[key].items()}
        token_score = cosine(qv,dv)
        tri_score = cosine(q3,char3(text))
        out[key] = 0.70*token_score + 0.30*tri_score
    return out


def pick_best(query: str, docs: dict[str,str]) -> tuple[str, dict[str,float]]:
    scores = lexical_scores(query, docs)
    best = sorted(scores, key=lambda k: (-scores[k], k))[0]
    return best, scores


def relation_refs(text: str, visible: dict) -> tuple[list[str], list[str], list[str]]:
    refs = ID_RE.findall(text)
    facts, concepts, goals = [], [], []
    for ref in refs:
        if ref in visible["facts"] and ref not in facts:
            facts.append(ref)
        elif ref in visible["concepts"] and ref not in concepts:
            concepts.append(ref)
        elif ref in visible["goals"] and ref not in goals:
            goals.append(ref)
    return facts, concepts, goals


def expand_relation(text: str, visible: dict) -> str:
    facts, concepts, goals = relation_refs(text, visible)
    semantic = [text]
    semantic += [visible["facts"][x] for x in facts]
    semantic += [visible["concepts"][x] for x in concepts]
    semantic += [visible["goals"][x] for x in goals]
    return " | ".join(semantic)


def predict(fixture: dict) -> dict:
    # Pure predictor: only fixture['visible'] is read. No oracle/category/provenance access.
    v = fixture["visible"]
    prompt = v["prompt"]

    relation_docs = {rid: expand_relation(text, v) for rid,text in v["relations"].items()}
    relation_id, relation_scores = pick_best(prompt, relation_docs)
    raw_relation = v["relations"][relation_id]
    rel_facts, rel_concepts, _ = relation_refs(raw_relation, v)

    goal_id, goal_scores = pick_best(prompt, v["goals"])

    if len(rel_concepts) == 1:
        concept_id = rel_concepts[0]
        concept_scores = {concept_id: 1.0}
    else:
        concept_id, concept_scores = pick_best(prompt + " | " + relation_docs[relation_id], v["concepts"])

    if len(rel_facts) == 1:
        fact_id = rel_facts[0]
        fact_scores = {fact_id: 1.0}
    else:
        fact_id, fact_scores = pick_best(prompt, v["facts"])

    rel_norm = raw_relation.upper()
    concept_norm = norm(v["concepts"][concept_id])
    ambiguity = "YES" if (
        "INSUFFICIENT_TO_RESOLVE" in rel_norm
        or "unresolved" in concept_norm
        or "cannot be resolved" in concept_norm
        or "insufficient to resolve" in concept_norm
    ) else "NO"

    return {
        "primary_fact_id": fact_id,
        "semantic_concept_id": concept_id,
        "key_relation_id": relation_id,
        "ambiguity": ambiguity,
        "goal_id": goal_id,
        "diagnostic_scores": {
            "relations": relation_scores,
            "concepts": concept_scores,
            "facts": fact_scores,
            "goals": goal_scores,
        },
    }


def score(fixtures: list[dict]) -> dict:
    correct = 0
    exact = 0
    dims = {f: 0 for f in FIELDS}
    rows = []
    per_family: dict[str, dict[str, int]] = {}
    for fixture in fixtures:
        pred_full = predict(fixture)
        pred = {f: pred_full[f] for f in FIELDS}
        oracle = fixture["oracle"]
        hits = {f: pred[f] == oracle[f] for f in FIELDS}
        n = sum(hits.values())
        correct += n
        exact += int(n == len(FIELDS))
        for f,ok in hits.items():
            dims[f] += int(ok)
        family = fixture.get("family", "UNSPECIFIED")
        bucket = per_family.setdefault(family, {"fixtures":0,"correct_fields":0,"field_decisions":0,"exact":0})
        bucket["fixtures"] += 1
        bucket["correct_fields"] += n
        bucket["field_decisions"] += len(FIELDS)
        bucket["exact"] += int(n == len(FIELDS))
        rows.append({
            "fixture_id": fixture["id"],
            "family": family,
            "prediction": pred,
            "oracle": oracle,
            "correct_fields": n,
            "exact_match": n == len(FIELDS),
        })
    total = len(fixtures)*len(FIELDS)
    family_metrics = {
        family: {
            **v,
            "primary_score": v["correct_fields"]/v["field_decisions"],
            "exact_rate": v["exact"]/v["fixtures"],
        }
        for family,v in per_family.items()
    }
    return {
        "field_correct_total": correct,
        "field_decisions": total,
        "primary_score": correct/total,
        "fixture_exact_match_count": exact,
        "fixture_exact_match_rate": exact/len(fixtures),
        "per_dimension_accuracy": {f: dims[f]/len(fixtures) for f in FIELDS},
        "per_family": family_metrics,
        "rows": rows,
    }
