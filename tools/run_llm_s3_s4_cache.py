#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "selected_candidate_ids": {"type": "array", "items": {"type": "string"}},
        "rejected_candidate_ids": {"type": "array", "items": {"type": "string"}},
        "reframe_required": {"type": "boolean"},
        "closure_class": {"type": "string", "enum": ["CLOSE", "CONTINUE"]},
        "decision_reasons": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "selected_candidate_ids",
        "rejected_candidate_ids",
        "reframe_required",
        "closure_class",
        "decision_reasons",
    ],
}


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
    return json.loads(text[start:end + 1])


def validate_output_contract(parsed: object, candidate_ids: set[str]) -> tuple[bool, str | None]:
    if not isinstance(parsed, dict):
        return False, "NOT_OBJECT"
    required = set(OUTPUT_SCHEMA["required"])
    if set(parsed) != required:
        return False, "KEY_SET_MISMATCH"

    selected = parsed.get("selected_candidate_ids")
    rejected = parsed.get("rejected_candidate_ids")
    reasons = parsed.get("decision_reasons")
    if not isinstance(selected, list) or not all(isinstance(x, str) for x in selected):
        return False, "SELECTED_IDS_INVALID"
    if not isinstance(rejected, list) or not all(isinstance(x, str) for x in rejected):
        return False, "REJECTED_IDS_INVALID"
    if not isinstance(reasons, list) or not all(isinstance(x, str) for x in reasons):
        return False, "DECISION_REASONS_INVALID"
    if not isinstance(parsed.get("reframe_required"), bool):
        return False, "REFRAME_INVALID"
    if parsed.get("closure_class") not in {"CLOSE", "CONTINUE"}:
        return False, "CLOSURE_INVALID"

    selected_set, rejected_set = set(selected), set(rejected)
    if selected_set & rejected_set:
        return False, "SELECT_REJECT_OVERLAP"
    if not selected_set <= candidate_ids or not rejected_set <= candidate_ids:
        return False, "UNKNOWN_CANDIDATE_ID"
    if selected_set | rejected_set != candidate_ids:
        return False, "CANDIDATE_PARTITION_INCOMPLETE"
    return True, None


def post_json(url: str, payload: dict, timeout: int = 120):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_openai_compatible(endpoint: str, model: str, prompt: str, schema_constrained: bool, seed: int | None):
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "Return only the requested JSON. Do not use hidden assumptions."},
            {"role": "user", "content": prompt},
        ],
    }
    if seed is not None:
        payload["seed"] = seed
    if schema_constrained:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "s3_s4_decision", "strict": True, "schema": OUTPUT_SCHEMA},
        }
    response = post_json(url, payload)
    content = response["choices"][0]["message"]["content"]
    usage = response.get("usage") or {}
    return content, usage


def call_ollama(endpoint: str, model: str, prompt: str, schema_constrained: bool, seed: int | None):
    url = endpoint.rstrip("/") + "/api/chat"
    options = {"temperature": 0}
    if seed is not None:
        options["seed"] = seed
    payload = {
        "model": model,
        "stream": False,
        "options": options,
        "messages": [
            {"role": "system", "content": "Return only the requested JSON. Do not use hidden assumptions."},
            {"role": "user", "content": prompt},
        ],
    }
    if schema_constrained:
        payload["format"] = OUTPUT_SCHEMA
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


def cache_matches(doc: dict, *, model: str, provider: str, mode: str, s2_hash: str | None, state_hash: str | None) -> bool:
    return (
        doc.get("model") == model
        and doc.get("provider") == provider
        and doc.get("measurement_mode") == mode
        and (doc.get("upstream") or {}).get("candidate_set_hash") == s2_hash
        and (doc.get("upstream") or {}).get("semantic_state_hash") == state_hash
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="fixtures/phase1_v2/generated")
    ap.add_argument("--out", default=None)
    ap.add_argument("--mode", choices=["raw", "schema_constrained"], default="schema_constrained")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    provider = os.environ.get("LLM_PROVIDER", "openai-compatible")
    model = os.environ.get("LLM_MODEL")
    endpoint = os.environ.get("LLM_ENDPOINT")
    seed_text = os.environ.get("LLM_SEED")
    seed = int(seed_text) if seed_text not in {None, ""} else None
    if not model or not endpoint:
        raise SystemExit("LLM_MODEL and LLM_ENDPOINT are required")

    mode = args.mode
    schema_constrained = mode == "schema_constrained"
    out_root = Path(args.out) if args.out else Path("results/llm_s3_s4") / mode
    root = Path(args.root)
    count = 0
    reused = 0
    contract_ok_count = 0

    for fixture in sorted(p for p in root.iterdir() if p.is_dir()):
        s2 = load(fixture / "oracle" / "s2_candidate_set.json")
        state = load(fixture / "upstream" / "s3_semantic_state.json")
        s2_hash = s2.get("content_hash")
        state_hash = state.get("content_hash")
        out = out_root / (fixture.name + ".json")
        if out.exists() and not args.force:
            existing = load(out)
            if cache_matches(existing, model=model, provider=provider, mode=mode, s2_hash=s2_hash, state_hash=state_hash):
                reused += 1
                count += 1
                contract_ok_count += int(bool(existing.get("format_contract_ok")))
                continue

        prompt = prompt_for(s2, state)
        started = time.perf_counter()
        if provider == "ollama":
            raw, usage = call_ollama(endpoint, model, prompt, schema_constrained, seed)
        else:
            raw, usage = call_openai_compatible(endpoint, model, prompt, schema_constrained, seed)
        latency_ms = round((time.perf_counter() - started) * 1000, 3)

        parsed = None
        parse_error = None
        contract_error = None
        try:
            parsed = parse_json_text(raw)
            candidate_ids = {str(c.get("candidate_id")) for c in s2.get("candidates", [])}
            format_contract_ok, contract_error = validate_output_contract(parsed, candidate_ids)
        except Exception as exc:
            format_contract_ok = False
            parse_error = f"{type(exc).__name__}:{exc}"

        result = {
            "fixture_id": fixture.name,
            "implementation": "LLM",
            "model": model,
            "provider": provider,
            "measurement_mode": mode,
            "schema_constrained": schema_constrained,
            "format_contract_ok": format_contract_ok,
            "format_error": parse_error or contract_error,
            "semantic_metrics_eligible": bool(format_contract_ok and schema_constrained),
            "upstream": {
                "candidate_set_hash": s2_hash,
                "semantic_state_hash": state_hash,
            },
            "runtime": {
                "temperature": 0,
                "seed": seed,
                "latency_ms": latency_ms,
                "usage": usage,
                "raw_output_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            },
        }
        if format_contract_ok and isinstance(parsed, dict):
            result["s3"] = {
                "selected_candidate_ids": parsed["selected_candidate_ids"],
                "rejected_candidate_ids": parsed["rejected_candidate_ids"],
                "decision_reasons": parsed["decision_reasons"],
                "reframe_required": parsed["reframe_required"],
            }
            result["s4"] = {"closure_class": parsed["closure_class"]}
        else:
            result["s3"] = None
            result["s4"] = None

        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        count += 1
        contract_ok_count += int(format_contract_ok)

    summary = {
        "run": "LLM_S3_S4",
        "provider": provider,
        "model": model,
        "measurement_mode": mode,
        "schema_constrained": schema_constrained,
        "fixture_count": count,
        "cache_reused": reused,
        "format_contract_ok_count": contract_ok_count,
        "format_contract_rate": (contract_ok_count / count) if count else 0.0,
        "semantic_metrics_reportable": bool(schema_constrained and count and contract_ok_count == count),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if schema_constrained and contract_ok_count != count:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
