#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1_CONTRACT = ROOT / "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json"
V2_CONTRACT = ROOT / "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_V2_2026-10-03.json"
FOUNDATION = ROOT / "results/phase1_v2_qualification_2026-10-03.json"
ADAPTER_QUAL = ROOT / "results/ec_native_adapter_qualification.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd: list[str], timeout: int = 1800) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.returncode, p.stdout


def parse_last_json(text: str) -> dict:
    starts = [i for i, ch in enumerate(text) if ch == "{"]
    for start in reversed(starts):
        try:
            value = json.loads(text[start:])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass
    raise ValueError("NO_JSON_RESULT")


def emit(state: str, *, history: list[dict], details: dict | None = None, rc: int = 0) -> int:
    print(json.dumps({
        "protocol": "PHASE1_MVP_TCC_V2",
        "successor_of": "PHASE1_MVP_TCC_V1",
        "terminal_state": state,
        "history": history,
        "details": details or {},
        "manual_midrun_repair_allowed": False,
    }, ensure_ascii=False, indent=2))
    return rc


def main() -> int:
    v1 = load(V1_CONTRACT)
    v2 = load(V2_CONTRACT)
    history: list[dict] = []

    # P0 V2: only dependencies necessary to reach the earliest semantic gate.
    rc, out = run([sys.executable, "tools/preflight_phase1_mvp_dependencies_v2.py", "--stage", "early"], timeout=120)
    try:
        early = parse_last_json(out)
    except ValueError:
        return emit("INVALID_TEST_CONTRACT", history=history, details={"gate": "P0_EARLY_PRECHECK", "output": out[-5000:]}, rc=2)
    history.append({"gate": "P0_EARLY_PRECHECK", "rc": rc, "result": early})
    if rc != 0 or early.get("status") != "PASS":
        return emit("INVALID_TEST_CONTRACT", history=history, details={"blockers": early.get("blockers", [])}, rc=2)

    # P1: unchanged V1 foundation semantics.
    q = load(FOUNDATION)
    expected_digest = v1["canonical_inputs"]["phase1_v2_dataset_sha256"]
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

    # P2: semantic scope is authoritative before downstream-only dependencies.
    if not ADAPTER_QUAL.exists():
        return emit("BLOCKED_EC_NATIVE_ADAPTER", history=history, details={"missing": str(ADAPTER_QUAL.relative_to(ROOT))}, rc=3)
    adapter = load(ADAPTER_QUAL)
    if adapter.get("protocol") != v2["canonical_inputs"]["ec_adapter_protocol"]:
        return emit("BLOCKED_EC_NATIVE_ADAPTER", history=history, details={"reason": "ADAPTER_PROTOCOL_MISMATCH", "qualification": adapter}, rc=3)
    status = adapter.get("status")
    history.append({"gate": "P2_EC_ADAPTER_GATE", "status": status, "qualification": adapter})
    if status == "INCOMPATIBLE":
        return emit("EC_NATIVE_SCOPE_INCOMPATIBLE", history=history, details={
            "qualification": adapter,
            "v1_actual_terminal_preserved": "INVALID_TEST_CONTRACT",
            "downstream_issue22_required": False,
            "reason": "P2_TERMINAL_PRECEDES_DOWNSTREAM_ONLY_DEPENDENCIES_IN_V2",
        }, rc=4)
    if status != "PASS":
        return emit("BLOCKED_EC_NATIVE_ADAPTER", history=history, details=adapter, rc=3)

    # P2B: only compatible EC scope admits downstream A/B/E dependencies.
    rc, out = run([sys.executable, "tools/preflight_phase1_mvp_dependencies_v2.py", "--stage", "downstream"], timeout=120)
    try:
        downstream = parse_last_json(out)
    except ValueError:
        return emit("INVALID_TEST_CONTRACT", history=history, details={"gate": "P2B_DOWNSTREAM_PRECHECK", "output": out[-5000:]}, rc=2)
    history.append({"gate": "P2B_DOWNSTREAM_PRECHECK_IF_COMPATIBLE", "rc": rc, "result": downstream})
    if rc != 0 or downstream.get("status") != "PASS":
        return emit("INVALID_TEST_CONTRACT", history=history, details={"blockers": downstream.get("blockers", [])}, rc=2)

    # With P2 PASS and V1 static dependencies satisfied, reuse unchanged V1 continuation.
    rc, out = run([sys.executable, "tools/run_phase1_mvp_tcc.py"], timeout=7200)
    try:
        delegated = parse_last_json(out)
    except ValueError:
        return emit("FAIL_CLOSED_UNKNOWN", history=history, details={"reason": "V1_DELEGATE_JSON_MISSING", "output": out[-5000:]}, rc=12)
    history.append({"gate": "DELEGATE_V1_FROM_COMPATIBLE_STATE", "rc": rc, "v1_terminal": delegated.get("terminal_state")})
    terminal = delegated.get("terminal_state")
    if terminal not in set(v2["terminal_states"]):
        return emit("FAIL_CLOSED_UNKNOWN", history=history, details={"delegated": delegated}, rc=12)
    return emit(terminal, history=history, details={"delegated_v1_result": delegated}, rc=rc)


if __name__ == "__main__":
    raise SystemExit(main())
