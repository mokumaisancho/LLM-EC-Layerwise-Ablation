#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

PROTOCOL = "FUNCTION_BOUNDARY_S1A_GRAPH_GROUNDING_DIAGNOSTIC_V1"
EXPECTED_SOURCE_PROTOCOL = "FUNCTION_BOUNDARY_S1_V1"
EXPECTED_DATASET_DIGEST = "4d15e1b89c6382a8a5252558525db55cccc700096ad5c92e97d384c9d59cd190"
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
    # Deliberately no access to fixture['oracle'] or fixture['category'].
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
            "goals": goal_scores
        }
    }


def score(fixtures: list[dict]) -> dict:
    correct = 0
    exact = 0
    dims = {f: 0 for f in FIELDS}
    rows = []
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
        rows.append({
            "fixture_id": fixture["id"],
            "prediction": pred,
            "oracle": oracle,
            "correct_fields": n,
            "exact_match": n == len(FIELDS)
        })
    total = len(fixtures)*len(FIELDS)
    return {
        "field_correct_total": correct,
        "field_decisions": total,
        "primary_score": correct/total,
        "fixture_exact_match_count": exact,
        "fixture_exact_match_rate": exact/len(fixtures),
        "per_dimension_accuracy": {f: dims[f]/len(fixtures) for f in FIELDS},
        "rows": rows
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("fixture_json", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args=ap.parse_args()
    raw=args.fixture_json.read_bytes()
    data=json.loads(raw)
    if data.get("protocol") != EXPECTED_SOURCE_PROTOCOL:
        raise SystemExit("wrong source protocol")
    if data.get("dataset_digest") != EXPECTED_DATASET_DIGEST:
        raise SystemExit("dataset digest mismatch")
    result=score(data["fixtures"])
    out={
        "schema_version":"FUNCTION_BOUNDARY_S1A_GRAPH_GROUNDING_DIAGNOSTIC_ACTUAL_V1",
        "protocol":PROTOCOL,
        "source_protocol":data["protocol"],
        "source_dataset_digest":data["dataset_digest"],
        "source_file_sha256":hashlib.sha256(raw).hexdigest(),
        "predictor_contract":{
            "oracle_visible_to_predictor":False,
            "category_visible_to_predictor":False,
            "domain_specific_rules":False,
            "domain_specific_synonyms":False,
            "relation_selection":"0.70 token-TFIDF cosine + 0.30 char-trigram cosine on prompt vs ID-expanded relation semantics",
            "unique_relation_reference":"use unique referenced concept/fact directly",
            "multi_or_no_reference":"generic lexical retrieval",
            "goal_selection":"generic lexical retrieval from raw prompt",
            "ambiguity":"YES only for explicit insufficient/unresolved semantics"
        },
        "result":result,
        "comparison":{"qwen25_1p5b_primary":0.72,"qwen25_1p5b_exact":0.40},
        "stage2_gate":{"threshold":0.60,"pass":result["primary_score"]>=0.60},
        "claim_limits":[
            "Retrospective diagnostic only; the benchmark was inspected before this deterministic baseline was created.",
            "This tests grounding against supplied semantic dictionaries, not ontology induction from unconstrained raw text.",
            "No post-score tuning is performed by this runner."
        ],
        "github_actions_used":False,
        "google_drive_used":False,
        "qwen3_4b_used":False
    }
    args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
