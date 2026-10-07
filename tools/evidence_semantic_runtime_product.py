#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from semantic_runtime import canonical_json, discover_and_ground, execute_validated_ir
from tests.test_semantic_runtime_product import make_solver, make_task

EXPECTED_PRODUCT_PINS_BLOB = "a87611cbc93638e262a07ec67afdcf8d936d740b"
EXPECTED_RESEARCH_PINS_BLOB = "bdce80d5b6bfdc07a0d2ce799b099c0ed9ab22be"


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(raw)}\0".encode())
    h.update(raw)
    return h.hexdigest()


def run_json(cmd: list[str]) -> tuple[int, dict, str]:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    try:
        data = json.loads(p.stdout)
    except Exception:
        data = {"parse_error": True, "stdout_tail": p.stdout[-4000:]}
    return p.returncode, data, p.stderr[-4000:]


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[dict] = []

    product_pins = ROOT / "semantic_runtime" / "product_pins.json"
    research_pins = ROOT / "semantic_runtime" / "research_pins.json"
    checks["product_pin_manifest_blob_fixed"] = git_blob_sha(product_pins) == EXPECTED_PRODUCT_PINS_BLOB
    checks["research_pin_manifest_blob_fixed"] = git_blob_sha(research_pins) == EXPECTED_RESEARCH_PINS_BLOB

    p01_rc, p01, p01_err = run_json([sys.executable, str(ROOT / "tools" / "preflight_semantic_runtime_product.py")])
    checks["p01_replay_pass"] = p01_rc == 0 and p01.get("terminal") == "PRODUCT_P01_IMPLEMENT_RUNTIME_PASS"

    p02_rc, p02, p02_err = run_json([sys.executable, str(ROOT / "tools" / "regress_semantic_runtime_product_v2.py")])
    checks["p02_replay_pass"] = p02_rc == 0 and p02.get("terminal") == "PRODUCT_P02_REGRESSION_PASS"

    task = make_task()
    solver_contract = make_solver()

    api_ir = discover_and_ground(task)
    api_exec = execute_validated_ir(api_ir, solver_contract)
    api_ir_text = canonical_json(api_ir)
    api_exec_text = canonical_json(api_exec)
    ir_sha = hashlib.sha256(api_ir_text.encode()).hexdigest()
    exec_sha = hashlib.sha256(api_exec_text.encode()).hexdigest()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        task_path = td / "task.json"
        ir_path = td / "ir.json"
        solver_path = td / "solver.json"
        task_path.write_text(json.dumps(task), encoding="utf-8")
        solver_path.write_text(json.dumps(solver_contract), encoding="utf-8")

        discover = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "semantic_runtime_cli.py"), "discover-ground", str(task_path)],
            cwd=ROOT, text=True, capture_output=True,
        )
        checks["cli_discover_exit_zero"] = discover.returncode == 0
        cli_ir = json.loads(discover.stdout) if discover.returncode == 0 else None
        checks["api_cli_ir_identical"] = cli_ir is not None and canonical_json(cli_ir) == api_ir_text

        if cli_ir is not None:
            ir_path.write_text(json.dumps(cli_ir), encoding="utf-8")
            execute = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "semantic_runtime_cli.py"), "execute", str(ir_path), str(solver_path)],
                cwd=ROOT, text=True, capture_output=True,
            )
        else:
            execute = subprocess.CompletedProcess([], 99, "", "CLI_IR_MISSING")
        checks["cli_execute_exit_zero"] = execute.returncode == 0
        cli_exec = json.loads(execute.stdout) if execute.returncode == 0 else None
        checks["api_cli_execution_identical"] = cli_exec is not None and canonical_json(cli_exec) == api_exec_text

    checks["execution_applicable"] = api_exec.get("result", {}).get("applicable") is True
    checks["canonical_ir_sha_stable"] = ir_sha == "695312aaaeffa1d9f45e78957cbc4952791116998eb567050c692e15a4df199b"

    for name, ok in checks.items():
        if ok is not True:
            failures.append({"gate": name, "value": ok})

    passed = not failures
    out = {
        "protocol": "SEMANTIC_RUNTIME_PRODUCT_P03_EVIDENCE_V1",
        "issue": 54,
        "ecv4_phase": "I54:EVIDENCE",
        "pass": passed,
        "terminal": "PRODUCT_MVP_COMPLETE" if passed else "PRODUCT_P03_EVIDENCE_FAIL_CLOSED",
        "checks": checks,
        "canonical_ir_sha256": ir_sha,
        "canonical_execution_sha256": exec_sha,
        "p01_terminal": p01.get("terminal"),
        "p02_terminal": p02.get("terminal"),
        "p01_stderr_tail": p01_err,
        "p02_stderr_tail": p02_err,
        "failure_count": len(failures),
        "failures": failures,
        "product_claim": "Reusable deterministic semantic-space runtime is qualified for finite typed/auditable contracts represented by the frozen public runtime schemas.",
        "claim_limit": "No unrestricted ontology invention, open-ended world-knowledge acquisition, or general LLM replacement claim.",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
