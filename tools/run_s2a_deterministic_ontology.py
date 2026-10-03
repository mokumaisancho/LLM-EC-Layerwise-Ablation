#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

STOPWORDS = {
    "a","an","and","are","as","at","be","because","but","by","for","from","has","have","in","is","it",
    "of","on","or","that","the","their","there","this","to","under","until","was","were","which","with",
    "without","already","only","every","both","all","more","one","than","into","around","during","current"
}
TOKEN_RE = re.compile(r"[a-z0-9]+")
ID_RE = re.compile(r"f\d+|c_[a-z0-9_]+|g\d+", re.I)


def norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("_", " ").replace("-", " ")).strip()


def tokens(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(norm_text(text)) if t not in STOPWORDS]


def char_ngrams(text: str, n: int = 3) -> Counter[str]:
    s = norm_text(text)
    if len(s) < n:
        return Counter({s: 1}) if s else Counter()
    return Counter(s[i:i+n] for i in range(len(s) - n + 1))


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def tfidf_vectors(query: str, docs: dict[str, str]) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    doc_tf = {k: Counter(tokens(v)) for k, v in docs.items()}
    n = len(doc_tf)
    df: Counter[str] = Counter()
    for tf in doc_tf.values():
        for term in tf:
            df[term] += 1
    idf = {term: math.log((n + 1) / (freq + 1)) + 1.0 for term, freq in df.items()}

    def weight(tf: Counter[str]) -> dict[str, float]:
        return {term: count * idf.get(term, math.log(n + 1) + 1.0) for term, count in tf.items()}

    return weight(Counter(tokens(query))), {k: weight(tf) for k, tf in doc_tf.items()}


def resolve_selected_semantics(fixture: dict, arm: str) -> str:
    s1 = fixture[arm]
    d = fixture["semantic_dictionary"]
    fields = [
        ("facts", s1["primary_fact_id"]),
        ("concepts", s1["semantic_concept_id"]),
        ("relations", s1["key_relation_id"]),
        ("goals", s1["goal_id"]),
    ]
    parts: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        if text not in seen:
            seen.add(text)
            parts.append(text)

    for group, key in fields:
        add(d[group][key])

    relation_text = d["relations"][s1["key_relation_id"]]
    for ref in ID_RE.findall(relation_text):
        ref_l = ref.lower()
        for group in ("facts", "concepts", "goals"):
            for key, value in d[group].items():
                if key.lower() == ref_l:
                    add(value)
                    break

    add(f"ambiguity {s1['ambiguity']}")
    return " | ".join(parts)


def predict_fixture(fixture: dict, arm: str) -> dict:
    # Deliberately do not access fixture['gold'] or fixture['category'] here.
    query = resolve_selected_semantics(fixture, arm)
    docs = fixture["candidate_ontology"]
    q_tfidf, d_tfidf = tfidf_vectors(query, docs)
    q_tri = char_ngrams(query)
    scored: list[tuple[str, float, float, float]] = []
    for cid, text in docs.items():
        token_score = cosine(q_tfidf, d_tfidf[cid])
        tri_score = cosine(q_tri, char_ngrams(text))
        score = 0.70 * token_score + 0.30 * tri_score
        scored.append((cid, score, token_score, tri_score))
    scored.sort(key=lambda x: (-x[1], x[0]))
    emitted = sorted(cid for cid, *_ in scored[:3])
    return {
        "candidate_ids": emitted,
        "query": query,
        "scores": [
            {"candidate_id": cid, "combined": round(score, 12), "token": round(ts, 12), "char3": round(cs, 12)}
            for cid, score, ts, cs in scored
        ],
    }


def score_predictions(fixtures: list[dict], predictions: dict[str, dict]) -> dict:
    tp_total = 0
    emitted_total = 0
    gold_total = 0
    exact = 0
    per_fixture = {}
    residual_total = 0
    for fixture in fixtures:
        fid = fixture["id"]
        gold = set(fixture["gold"])
        emitted = set(predictions[fid]["candidate_ids"])
        tp = len(gold & emitted)
        residual = sorted(gold - emitted)
        tp_total += tp
        emitted_total += len(emitted)
        gold_total += len(gold)
        residual_total += len(residual)
        exact += int(gold == emitted)
        per_fixture[fid] = {
            "candidate_ids": sorted(emitted),
            "gold_count": len(gold),
            "tp": tp,
            "recall": tp / len(gold) if gold else 1.0,
            "precision": tp / len(emitted) if emitted else 0.0,
            "residual_gold": residual,
        }
    recall = tp_total / gold_total if gold_total else 1.0
    precision = tp_total / emitted_total if emitted_total else 0.0
    return {
        "candidate_recall": recall,
        "candidate_precision": precision,
        "true_positive_total": tp_total,
        "emitted_candidate_total": emitted_total,
        "gold_candidate_total": gold_total,
        "exact_set_count": exact,
        "exact_set_rate": exact / len(fixtures) if fixtures else 0.0,
        "residual_gold_total": residual_total,
        "residual_gold_fraction": residual_total / gold_total if gold_total else 0.0,
        "per_fixture": per_fixture,
    }


def classify(recall: float) -> str:
    if recall >= 0.80:
        return "MOSTLY_DETERMINISTIC_KNOWN_ONTOLOGY_REGION"
    if recall >= 0.40:
        return "MIXED_DETERMINISTIC_AND_GENERATIVE_REGION"
    return "GENERIC_DETERMINISTIC_RETRIEVAL_INSUFFICIENT"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture_json", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    raw = args.fixture_json.read_bytes()
    data = json.loads(raw)
    if data.get("protocol") != "FUNCTION_BOUNDARY_S2_V2":
        raise SystemExit("wrong protocol")
    if data.get("dataset_digest") != "130f57b09549e260311d69f1b22a56fbfb0a3220880009fd132c1e76e05df14c":
        raise SystemExit("dataset digest mismatch")

    fixtures = data["fixtures"]
    predictions: dict[str, dict[str, dict]] = {}
    for arm in ("oracle_s1", "actual_s1"):
        predictions[arm] = {f["id"]: predict_fixture(f, arm) for f in fixtures}

    arms = {arm: score_predictions(fixtures, predictions[arm]) for arm in predictions}
    result = {
        "schema_version": "FUNCTION_BOUNDARY_S2A_DETERMINISTIC_ACTUAL_V1",
        "protocol": "FUNCTION_BOUNDARY_S2A_DETERMINISTIC_V1",
        "source_protocol": data["protocol"],
        "source_dataset_digest": data["dataset_digest"],
        "source_file_sha256": hashlib.sha256(raw).hexdigest(),
        "predictor_contract": {
            "gold_visible_to_predictor": False,
            "category_visible_to_predictor": False,
            "emitted_candidates_per_fixture": 3,
            "score": "0.70 token TF-IDF cosine + 0.30 character-trigram cosine",
            "domain_specific_rules": False,
            "domain_specific_synonyms": False,
        },
        "arms": arms,
        "primary_classification": classify(arms["oracle_s1"]["candidate_recall"]),
        "comparison": {
            "qwen25_1p5b_oracle_s1_recall": 0.40,
            "qwen25_1p5b_oracle_s1_precision": 0.42105263157894735,
            "deterministic_minus_llm_recall": arms["oracle_s1"]["candidate_recall"] - 0.40,
        },
        "claim_limits": [
            "This measures deterministic retrieval over an explicit visible ontology, not native EC candidate generation.",
            "Unrecovered candidates remain a residual; they do not by themselves prove LLM necessity.",
            "No post-freeze tuning was performed by this runner."
        ],
        "github_actions_used": False,
        "google_drive_used": False,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
