#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

EXPECTED_BLOBS = {
    "score_s1c_v_denotational.py": "efe940abe8c1643ed0ccbe665b7430610205cea5",
    "s1c_v_deterministic_discovery.py": "c853b27ce6f2149f6619ccd88fb662a8bdaba67e",
    "generate_s1c_v_holdout.py": "c9922f731d989e59148ba37083d02909ee65a584",
    "preflight_s1c_v.py": "6383f7336bb7ed08d6fbad1a6da1ebf1c8343426",
    "run_s1c_v_paired_v1.py": "e277e735aa7b8a8d75ab4472e9174bd0bb7cead0",
}


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(raw)}\0".encode())
    h.update(raw)
    return h.hexdigest()


def fail(detail: str) -> int:
    print(json.dumps({"terminal": "S1C_V_RUNNER_PREFLIGHT_FAIL_CLOSED", "detail": detail}, indent=2))
    return 3


def main() -> int:
    for name, expected in EXPECTED_BLOBS.items():
        path = TOOLS / name
        if not path.exists():
            return fail("missing:" + name)
        got = git_blob_sha(path)
        if got != expected:
            return fail(f"blob_drift:{name}:{got}:{expected}")
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            return fail(f"py_compile:{name}:{exc}")

    sys.path.insert(0, str(TOOLS))
    try:
        import run_s1c_v_paired_v1 as runner
        import generate_s1c_v_holdout as generator
        import score_s1c_v_denotational as scorer
        import s1c_v_deterministic_discovery as deterministic
    except Exception as exc:
        return fail("import:" + repr(exc))

    p = subprocess.run(
        [sys.executable, str(TOOLS / "preflight_s1c_v.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if p.returncode:
        return fail("scientific_preflight:" + (p.stderr or p.stdout))
    try:
        scientific = json.loads(p.stdout)
    except Exception as exc:
        return fail("scientific_preflight_parse:" + repr(exc))
    if scientific.get("terminal") != "S1C_V_PREINFERENCE_PASS":
        return fail("scientific_preflight_not_pass")

    tasks = generator.generate()
    if len(tasks) != 8 or sum(len(t["visible"]["heldout_examples"]) for t in tasks) != 16:
        return fail("task_or_heldout_count")

    grammar_checks = []
    predictions = {}
    for task in tasks:
        grammar = runner.grammar_for(task)
        if not grammar:
            return fail("grammar_empty:" + task["task_id"])
        low = grammar.lower()
        if any(x in low for x in (
            "oracle","audit","family","retain_custody","release_custody","place_into","remove_from",
            "precedes","follows","admit","block","accept","reject","activate","retire",
            "connect","separate","delegate","reclaim"
        )):
            return fail("grammar_semantic_leakage:" + task["task_id"])
        if "slot_id" not in grammar or "training_members" not in grammar or "heldout_assignments" not in grammar:
            return fail("grammar_contract_missing:" + task["task_id"])
        grammar_checks.append({
            "task_id": task["task_id"],
            "grammar_sha256": hashlib.sha256(grammar.encode()).hexdigest(),
            "grammar_chars": len(grammar),
        })
        predictions[task["task_id"]] = deterministic.predict({"visible": task["visible"]})

    score = scorer.aggregate(tasks, predictions)
    if score.get("pass") is not True:
        return fail("deterministic_score_failed")

    out = {
        "terminal": "S1C_V_RUNNER_PREFLIGHT_PASS",
        "protocol": "S1C_SEMANTIC_SPACE_TCC_V1",
        "issue": 48,
        "blob_pins": EXPECTED_BLOBS,
        "task_count": len(tasks),
        "heldout_count": sum(len(t["visible"]["heldout_examples"]) for t in tasks),
        "grammar_checks": grammar_checks,
        "deterministic_preinference_primary": score["primary"],
        "deterministic_preinference_secondary": score["secondary"],
        "scientific_preflight_terminal": scientific["terminal"],
        "model_inference_executed": False,
        "model_acquisition_authorized": True,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
