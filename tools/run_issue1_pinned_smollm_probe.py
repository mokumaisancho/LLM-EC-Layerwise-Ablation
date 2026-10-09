#!/usr/bin/env python3
"""Pinned actual SmolLM2 GGUF reference inference on exposed development fixtures.

Independent of scientific LLM0 designation. This is a *diagnostic* and never
reads private gold, installs policy, or claims matched V4 / scientific scores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from semantic_runtime import discover_and_ground
from semantic_runtime.constrained_v5 import classify_explicit
from tests.test_semantic_runtime_v5_grammar import make_field_task, make_grammar

EXPECTED_MODEL_SHA256 = "2e8040ceae7815abe0dcb3540b9995eaa1fa0d2ca9e797d0a635ae4433c68c2d"
EXPECTED_MODEL_BYTES = 105454432
MODEL_FILE = "SmolLM2-135M-Instruct-Q4_K_M.gguf"
UPSTREAM_REVISION = "09816acd5d99df7be770d85ea30822623dab342c"
UPSTREAM_REPO = "bartowski/SmolLM2-135M-Instruct-GGUF"
PROMPT_TEMPLATE = (
    "Respond with exactly ONE action label: OPEN, CLOSE, or ABSTAIN. "
    "OPEN means explicit opening/activation of claim review. "
    "CLOSE means explicit closing/disabling of claim review. "
    "ABSTAIN means unresolved, contradictory, denied, hypothetical, "
    "unsupported, or unintelligible text. "
    "Examples: 'Claim A opens review' -> OPEN; "
    "'Claim B disables review' -> CLOSE; "
    "'Evidence is unresolved between opening and closing review' -> ABSTAIN. "
    "Do not explain. Text: {input} Answer:"
)
LABELS = {"OPEN", "CLOSE", "ABSTAIN"}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def verify_model(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError("MODEL_FILE_MISSING_OR_SYMLINK")
    if path.stat().st_size != EXPECTED_MODEL_BYTES:
        raise ValueError("MODEL_SIZE_MISMATCH")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            h.update(chunk)
    if h.hexdigest() != EXPECTED_MODEL_SHA256:
        raise ValueError("MODEL_SHA_MISMATCH")
    return {"repo": UPSTREAM_REPO, "revision": UPSTREAM_REVISION,
            "model": MODEL_FILE, "file_size": EXPECTED_MODEL_BYTES,
            "file_sha256": h.hexdigest(),
            "scientific_original_llm0_designation": "NOT_ESTABLISHED"}


def run_one(llama: Path, model: Path, prompt: str, *, seconds: int, grammar: str | None = None):
    command = [
        str(llama), "--single-turn", "--no-warmup", "-m", str(model),
        "-p", prompt, "-n", "16", "-t", "4", "-ngl", "0",
        "--temp", "0", "--seed", "0", "-no-cnv", "--simple-io",
        "--no-display-prompt", "--log-disable",
    ]
    if grammar is not None:
        command += ["--grammar", grammar]
    proc = subprocess.run(command, capture_output=True, text=True,
                          timeout=seconds, stdin=subprocess.DEVNULL)
    raw_stdout = proc.stdout
    if proc.returncode != 0:
        raise RuntimeError("MODEL_INFERENCE_FAILED:" + str(proc.returncode) + ":" + proc.stderr[-300:])
    # The CLI deliberately truncates the *displayed* prompt near 512 chars.
    # Never require verbatim echoed prompt for extraction; anchor to the
    # actual input UI marker and the timing trailer instead.
    marker = "\n\n> "
    position = raw_stdout.rfind(marker)
    if position < 0:
        raise RuntimeError("MODEL_INPUT_MARKER_MISSING:" + digest(raw_stdout.encode()))
    start = raw_stdout.find("\n\n", position + len(marker))
    if start < 0:
        raise RuntimeError("MODEL_RESPONSE_DELIMITER_MISSING:" + digest(raw_stdout.encode()))
    body = re.split(r"\n+\[ Prompt: ", raw_stdout[start + 2:], maxsplit=1)[0].strip()
    if len(body) > 512 or not body:
        raise RuntimeError("MODEL_RESPONSE_EMPTY_OR_TOO_LONG")
    return {"raw_response": body,
            "parsed_action": body if body in LABELS else "FORMAT_ERROR",
            "full_cli_stdout_sha256": digest(raw_stdout.encode()),
            "full_cli_stdout_bytes": len(raw_stdout.encode()),
            "raw_stderr_sha256": digest(proc.stderr.encode())}


def run(model: Path, llama: Path, seconds: int) -> dict:
    pin = verify_model(model)
    if not llama.is_file():
        raise ValueError("LLAMA_CLI_NOT_FOUND")
    task = make_field_task()
    grammar = make_grammar()
    ir = discover_and_ground(task)
    strict = classify_explicit(task, grammar)
    slot_ids = {frozenset(row["training_members"]): row["slot_id"]
                for row in ir["discovered_slots"]}
    mapping = {slot_ids[frozenset(("T01", "T02"))]: "OPEN",
               slot_ids[frozenset(("T03", "T04"))]: "CLOSE"}
    v1_by_id = {row["example_id"]: row for row in ir["heldout_assignments"]}
    abstentions = {row["example_id"]: row for row in ir["abstentions"]}
    v5_by_id = {row["example_id"]: row for row in strict["decisions"]}
    cases = task["visible"]["heldout_examples"]
    ids = {row["example_id"] for row in cases}
    if len(ids) != 16 or set(v1_by_id) & set(abstentions) or set(v1_by_id) | set(abstentions) != ids or set(v5_by_id) != ids:
        raise RuntimeError("COVERAGE_NOT_EXACTLY_16")
    records = []
    for row in cases:
        cid = row["example_id"]
        prompt = PROMPT_TEMPLATE.format(input=row["raw_text"])
        actual = run_one(llama, model, prompt, seconds=seconds)
        vi = v1_by_id.get(cid)
        v1_action = (mapping.get(vi["slot_id"], "ABSTAIN")
                     if vi is not None and vi["polarity"] == "POS" and vi["modality"] == "ASSERTED"
                     else "ABSTAIN")
        decision = v5_by_id[cid]
        v5_action = (mapping.get(decision["slot_id"], "ABSTAIN")
                     if decision["status"] == "EXPLICIT_MATCH" else "ABSTAIN")
        records.append({"case_id": cid, "raw_text": row["raw_text"],
                        "input_sha256": digest(row["raw_text"].encode()),
                        "prompt_sha256": digest(prompt.encode()), **actual,
                        "v1_action": v1_action, "v1_status": "CLASSIFIED" if vi else abstentions[cid]["status"],
                        "v5_action": v5_action, "v5_status": decision["status"],
                        "llm_versus_v1_equal": actual["parsed_action"] == v1_action,
                        "llm_versus_v5_equal": actual["parsed_action"] == v5_action})
    return {
        "protocol": "ISSUE1_PINNED_SMOLLM_REFERENCE_ACTUAL_DEV_DIAGNOSTIC_V1",
        "source": "SEEN_H01_TO_H16_DEVELOPMENT_FIXTURE",
        "study_claim": "ACTUAL_INFERENCE_ONLY_NO_SCIENTIFIC_FOUR_ARM",
        "model_pin": pin, "prompt_template_sha256": digest(PROMPT_TEMPLATE.encode()),
        "task_sha256": digest(canonical(task)), "upstream_v1_sha256": digest(canonical(ir)),
        "strict_v5_sha256": digest(canonical(strict)),
        "runtime": {"engine": "llama.cpp", "actual_local_inference": True,
                    "temp": 0, "seed": 0, "threads": 4, "gpu_layers": 0,
                    "max_new_tokens": 16, "max_per_case_seconds": seconds},
        "cases": records,
        "case_count": len(records),
        "llm_strict_label_count": sum(r["parsed_action"] in LABELS for r in records),
        "llm_format_error_count": sum(r["parsed_action"] == "FORMAT_ERROR" for r in records),
        "llm_v1_label_agreement_count": sum(r["llm_versus_v1_equal"] for r in records),
        "llm_v5_label_agreement_count": sum(r["llm_versus_v5_equal"] for r in records),
        "independent_test_set": False, "private_gold_read": False,
        "genuine_authorized_v4_run": False, "true_original_llm0_verified": False,
        "scientific_retention_score": None, "four_arm_quality_claim": "NOT_ESTABLISHED",
        "terminal": "ACTUAL_PINNED_MODEL_DIAGNOSTIC_DONE_EXTERNAL_INDEPENDENT_STUDY_REQUIRED",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--llama-cli", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=30)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.model, args.llama_cli, args.seconds), ensure_ascii=False,
                         sort_keys=True, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"protocol": "ISSUE1_PINNED_SMOLLM_REFERENCE_ACTUAL_DEV_DIAGNOSTIC_V1",
                          "terminal": "FAIL_CLOSED", "error": type(exc).__name__,
                          "detail": str(exc)[:600]}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
