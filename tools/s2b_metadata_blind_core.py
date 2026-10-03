#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9_]+")
STOP = {"a","an","and","are","as","at","be","by","for","from","in","is","it","of","on","or","the","to","with","while"}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("-", " ")).strip()


def tokens(text: str) -> Counter[str]:
    return Counter(t for t in TOKEN_RE.findall(norm(text)) if t not in STOP)


def cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v*b.get(k,0) for k,v in a.items())
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    return dot/(na*nb) if na and nb else 0.0


def prototypes(relation: dict) -> tuple[list[str], list[str]]:
    op = relation["operator"]
    if op == "INSUFFICIENT_TO_RESOLVE":
        r = relation["referent"]
        return [
            f"request clarification for {r}",
            f"preserve {r} unresolved until evidence arrives",
        ], [
            f"bind {r} immediately to one option",
            f"continue without clarification for {r}",
            f"ignore ambiguity about {r}",
        ]
    if op == "ADMISSIBLE_UNDER_CONSTRAINT":
        c = relation["constraint"]
        return [
            f"retain an admissible alternative while preserving {c}",
            f"keep a valid option that satisfies {c}",
        ], [
            f"bypass {c}",
            f"remove {c}",
            f"discard all valid alternatives",
        ]
    if op == "BLOCKS_INFERENCE":
        t = relation["trigger"]; p = relation["proposition"]
        return [
            f"keep {p} unconfirmed",
            f"retain {t} as a review signal rather than proof",
        ], [
            f"confirm {p} from {t}",
            f"treat {t} as direct proof",
            f"ignore {t}",
        ]
    if op == "SUPERSEDES":
        new = relation["new"]; old = relation["old"]
        return [
            f"apply {new} as current",
            f"retain {old} as historical state",
        ], [
            f"apply {old} as current",
            f"treat {new} and {old} as equally current",
            f"ignore ordering between {new} and {old}",
            f"discard {new}",
        ]
    raise ValueError(f"unsupported operator: {op}")


def score_text(text: str, positive: list[str], negative: list[str]) -> float:
    q = tokens(text)
    pos = max(cosine(q, tokens(p)) for p in positive)
    neg = max(cosine(q, tokens(n)) for n in negative)
    return pos - neg


def predict(relation: dict, candidate_texts: dict[str,str], emit_count: int = 2) -> list[str]:
    # Candidate metadata is intentionally unavailable: only ID -> natural-language text.
    positive, negative = prototypes(relation)
    ranked = sorted(
        ((cid, score_text(text, positive, negative)) for cid,text in candidate_texts.items()),
        key=lambda x: (-x[1], x[0]),
    )
    return sorted(cid for cid,_ in ranked[:emit_count])
