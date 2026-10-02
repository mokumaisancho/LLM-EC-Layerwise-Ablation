#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd: list[str], *, env: dict[str, str] | None = None, timeout: int = 1800) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env or os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout


def parse_last_json(text: str) -> dict:
    starts = [i for i, ch in enumerate(text) if ch == "{"]
    for start in reversed(starts):
        try:
            obj = json.loads(text[start:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    raise ValueError("NO_JSON_RESULT")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def emit(state: str, *, history: list[dict], details: dict | None = None, rc: int = 0) -> int:
    print(json.dumps({
        "protocol": "PHASE1_MVP_TCC_V1",
        "terminal_state": state,
        "history": history,
        "details": details or {},
        "manual_midrun_repair_allowed": False,
    }, ensure_ascii=False, indent=2))
    return rc


def main() -> int:
    contract = load(CONTRACT_PATH)
    history: list[dict] = []

    # P0: all static dependencies at once.
    rc, out = run([sys.executable, "tools/preflight_phase1_mvp_dependencies.py"], timeout=120)
    try:
        preflight = parse_last_json(out)
    except ValueError:
        return emit("INVALID_TEST_CONTRACT", history=history, details={"gate": "P0_PRECHECK", "output": out[-5000:]}, rc=2)
    history.append({"gate": "P0_PRECHECK", "rc": rc, "result": preflight})
    if rc != 0 or preflight.get("status") != "PASS":
        return emit("INVALID_TEST_CONTRACT", history=history, details={"blockers": preflight.get("blockers", [])}, rc=2)

    # P1: immutable foundation evidence; no regeneration here.
    qpath = ROOT / "results/phase1_v2_qualification_2026-10-03.json"
    q = load(qpath)
    expected_digest = contract["canonical_inputs"]["phase1_v2_dataset_sha256"]
    foundation_ok = (
        q.get("dataset_digest") == expected_digest
        and (q.get("leakage_gate") or {}).get("status") == "PASS"
        and (q.get("leakage_gate") or {}).get("blocking_findings") == 0
        and (q.get("oracle_replay") or {}).get("status") == "PASS"
        and (q.get("oracle_replay") or {}).get("fixtures_passed") == 10
        and (q.get("oracle_replay") or {}).get("fixtures_total") == 10
    )
    history.append({"gate": "P1_FOUNDATION_GATE", "pass": foundation_ok, "dataset_digest": q.get("dataset_digest")})
    if not foundation_ok:
        return emit("INVALID_TEST_CONTRACT", history=history, rc=2)

    # P2: adapter must be qualified, not merely present.
    adapter_q = ROOT / "results/ec_native_adapter_qualification.json"
    if not adapter_q.exists():
        return emit("BLOCKED_EC_NATIVE_ADAPTER", history=history, details={"missing": str(adapter_q.relative_to(ROOT))}, rc=3)
    adapter_doc = load(adapter_q)
    if adapter_doc.get("protocol") != "PHASE1_EC_NATIVE_ADAPTER_V1":
        return emit("BLOCKED_EC_NATIVE_ADAPTER", history=history, details={"reason": "ADAPTER_PROTOCOL_MISMATCH"}, rc=3)
    if adapter_doc.get("status") == "INCOMPATIBLE":
        return emit("EC_NATIVE_SCOPE_INCOMPATIBLE", history=history, details=adapter_doc, rc=4)
    if adapter_doc.get("status") != "PASS":
        return emit("BLOCKED_EC_NATIVE_ADAPTER", history=history, details=adapter_doc, rc=3)
    history.append({"gate": "P2_EC_ADAPTER_GATE", "pass": True, "qualification": adapter_doc})

    # P3: reportable EC run. The adapter-aware runner must exist by preflight.
    ec_root = os.environ.get("EC_V4_4_REPO_ROOT")
    if not ec_root:
        return emit("BLOCKED_EC_BINDING", history=history, details={"reason": "EC_V4_4_REPO_ROOT_REQUIRED"}, rc=5)
    ec_cmd = [sys.executable, "tools/run_ec_s3_s4.py", "--ec-repo-root", ec_root]
    rc, out = run(ec_cmd, timeout=300)
    history.append({"gate": "P3_EC_BIND_GATE", "rc": rc, "output_tail": out[-4000:]})
    if rc != 0:
        return emit("BLOCKED_EC_BINDING", history=history, details={"output": out[-5000:]}, rc=5)

    # P4 is statically enforced by preflight; record it explicitly.
    history.append({"gate": "P4_HARNESS_GATE", "pass": True})

    # P5: verified local 0.5B artifact. Transport is external to this controller; identity is not.
    model_path_text = os.environ.get("PHASE1_0P5B_MODEL_PATH")
    if not model_path_text:
        return emit("BLOCKED_0P5B_INGRESS", history=history, details={"reason": "PHASE1_0P5B_MODEL_PATH_NOT_MATERIALIZED"}, rc=6)
    model_path = Path(model_path_text)
    if not model_path.is_file():
        return emit("BLOCKED_0P5B_INGRESS", history=history, details={"reason": "MODEL_PATH_NOT_FILE", "path": str(model_path)}, rc=6)
    expected = contract["canonical_inputs"]["qwen2_5_0_5b"]
    actual_size = model_path.stat().st_size
    actual_sha = file_sha256(model_path)
    history.append({"gate": "P5_LLM_ASSET_GATE", "size": actual_size, "sha256": actual_sha})
    if actual_size != expected["size_bytes"] or actual_sha != expected["sha256"]:
        return emit("INTEGRITY_FAILED", history=history, details={"expected": expected, "actual": {"size_bytes": actual_size, "sha256": actual_sha}}, rc=7)

    # P6: cache fixed LLM outputs. Endpoint/model are explicit runtime inputs.
    required_env = ["LLM_ENDPOINT", "LLM_MODEL", "LLM_PROVIDER"]
    missing_env = [x for x in required_env if not os.environ.get(x)]
    if missing_env:
        return emit("INVALID_TEST_CONTRACT", history=history, details={"reason": "LLM_RUNTIME_ENV_MISSING", "missing": missing_env}, rc=2)

    for cmd in (
        [sys.executable, "tools/run_llm_s1_s2_cache.py"],
        [sys.executable, "tools/run_llm_s3_s4_cache.py", "--mode", "raw"],
        [sys.executable, "tools/run_llm_s3_s4_cache.py", "--mode", "schema_constrained"],
    ):
        rc, out = run(cmd, timeout=1800)
        history.append({"gate": "P6_LLM_CACHE_GATE", "cmd": cmd, "rc": rc, "output_tail": out[-3000:]})
        if rc != 0 and "schema_constrained" in cmd:
            return emit("INVALID_LLM_OUTPUT_CONTRACT", history=history, details={"output": out[-5000:]}, rc=8)
        if rc != 0:
            return emit("INVALID_TEST_CONTRACT", history=history, details={"output": out[-5000:]}, rc=2)

    # P7/P8/P9 are delegated to the versioned intervention/scoring tools.
    rc, out = run([sys.executable, "tools/run_phase1_oracle_substitution.py"], timeout=3600)
    history.append({"gate": "P7_A_B_C_D_E_RUN", "rc": rc, "output_tail": out[-4000:]})
    if rc != 0:
        if "UPSTREAM_HASH_MISMATCH" in out:
            return emit("UPSTREAM_HASH_MISMATCH", history=history, details={"output": out[-5000:]}, rc=9)
        return emit("INVALID_TEST_CONTRACT", history=history, details={"output": out[-5000:]}, rc=2)

    rc, out = run([sys.executable, "tools/score_phase1_mvp.py"], timeout=300)
    history.append({"gate": "P8_SCORE_AND_GAIN", "rc": rc, "output_tail": out[-4000:]})
    if rc != 0:
        return emit("INVALID_TEST_CONTRACT", history=history, details={"output": out[-5000:]}, rc=2)
    try:
        score = parse_last_json(out)
    except ValueError:
        return emit("INVALID_TEST_CONTRACT", history=history, details={"reason": "SCORER_JSON_MISSING"}, rc=2)

    # Capacity branch is fixed and may run once only.
    capacity = score.get("capacity") or {}
    if capacity.get("collapse") is True:
        if os.environ.get("PHASE1_CAPACITY_STAGE") == "1P5B":
            return emit("CAPACITY_LIMIT_AFTER_1P5B", history=history, details=score, rc=10)
        return emit("RUN_1P5B_ONCE", history=history, details={
            "reason": "FROZEN_CAPACITY_COLLAPSE_RULE_FIRED",
            "next_contract": "same fixtures/scoring; set PHASE1_CAPACITY_STAGE=1P5B and materialize frozen ~1.5B candidate",
            "score": score,
        }, rc=11)

    terminal = score.get("mvp_terminal_state")
    allowed = set(contract["terminal_states"])
    if terminal in allowed and (
        terminal.startswith("MVP_COARSE_LOCALIZED:")
        or terminal in {"MVP_NO_MATERIAL_LAYER", "MVP_AMBIGUOUS_DOMINANT_LAYER"}
    ):
        history.append({"gate": "P9_LOCALIZE", "terminal": terminal})
        return emit(terminal, history=history, details=score, rc=0)

    return emit("FAIL_CLOSED_UNKNOWN", history=history, details={"score": score}, rc=12)


if __name__ == "__main__":
    raise SystemExit(main())
