#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_json_text(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].lstrip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("MODEL_OUTPUT_NOT_JSON_OBJECT")
    return json.loads(text[start:end+1])


def post_json(url: str, payload: dict, timeout: int = 120):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_openai_compatible(endpoint: str, model: str, prompt: str):
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "Return only the requested JSON. Do not use hidden assumptions."},
            {"role": "user", "content": prompt},
        ],
    }
    response = post_json(url, payload)
    content = response["choices"][0]["message"]["content"]
    usage = response.get("usage") or {}
    return content, usage


def call_ollama(endpoint: str, model: str, prompt: str):
    url = endpoint.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": "Return only the requested JSON. Do not use hidden assumptions."},
            {"role": "user", "content": prompt},
        ],
    }
    response = post_json(url, payload)
    content = response["message"]["content"]
    usage = {
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
    }
    return content, usage


def prompt_for(s2: dict, state: dict):
    visible_s2 = {k: v for k, v in s2.items() if k != "oracle_constraints"}
    return """You are the selection/control stage of a reasoning system.
Use only the supplied candidate set and semantic state.
Select all semantically admissible candidate IDs, reject the rest, decide whether the problem framing requires revision, and decide closure.

Rules:
- Evidence and explicit dependencies outrank linguistic plausibility.
- If the semantic state contains an unexplained observation, reframing is required unless the selected transition resolves it.
- Multiple selected candidates may close only when they are explicitly marked semantically EQUIVALENT. COMPETING alternatives remain open.
- Do not invent candidate IDs.

Return exactly this JSON shape:
{
  "selected_candidate_ids": ["..."],
  "rejected_candidate_ids": ["..."],
  "reframe_required": true,
  "closure_class": "CLOSE|CONTINUE",
  "decision_reasons": ["..."]
}

candidate_set:
""" + json.dumps(visible_s2, ensure_ascii=False, sort_keys=True) + "\nsemantic_state:\n" + json.dumps(state, ensure_ascii=False, sort_keys=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="fixtures/phase1_v2/generated")
    ap.add_argument("--out", default="results/llm_s3_s4")
    args = ap.parse_args()

    provider = os.environ.get("LLM_PROVIDER", "openai-compatible")
    model = os.environ.get("LLM_MODEL")
    endpoint = os.environ.get("LLM_ENDPOINT")
    if not model or not endpoint:
        raise SystemExit("LLM_MODEL and LLM_ENDPOINT are required")

    root, out_root = Path(args.root), Path(args.out)
    count = 0
    for fixture in sorted(p for p in root.iterdir() if p.is_dir()):
        s2 = load(fixture / "oracle" / "s2_candidate_set.json")
        state = load(fixture / "upstream" / "s3_semantic_state.json")
        prompt = prompt_for(s2, state)
        started = time.perf_counter()
        if provider == "ollama":
            raw, usage = call_ollama(endpoint, model, prompt)
        else:
            raw, usage = call_openai_compatible(endpoint, model, prompt)
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        parsed = parse_json_text(raw)

        result = {
            "fixture_id": fixture.name,
            "implementation": "LLM",
            "model": model,
            "provider": provider,
            "upstream": {
                "candidate_set_hash": s2.get("content_hash"),
                "semantic_state_hash": state.get("content_hash"),
            },
            "s3": {
                "selected_candidate_ids": parsed.get("selected_candidate_ids", []),
                "rejected_candidate_ids": parsed.get("rejected_candidate_ids", []),
                "decision_reasons": parsed.get("decision_reasons", []),
                "reframe_required": bool(parsed.get("reframe_required")),
            },
            "s4": {"closure_class": parsed.get("closure_class")},
            "runtime": {
                "latency_ms": latency_ms,
                "usage": usage,
                "raw_output_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            },
        }
        out = out_root / (fixture.name + ".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        count += 1

    print(json.dumps({"run": "LLM_S3_S4", "provider": provider, "model": model, "fixture_count": count}, indent=2))


if __name__ == "__main__":
    main()
