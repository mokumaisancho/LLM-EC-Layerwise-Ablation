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

from semantic_runtime import bounded_log, canonical_json, discover_and_ground, execute_validated_ir
from tests.test_semantic_runtime_product import make_solver, make_task

PRODUCT_FILES = (
    "semantic_runtime/__init__.py",
    "semantic_runtime/public_hypotheses.py",
    "semantic_runtime/discovery.py",
    "semantic_runtime/solver.py",
    "semantic_runtime/runtime.py",
    "semantic_runtime/research_pins.json",
    "schemas/semantic_runtime_task_v1.json",
    "schemas/semantic_runtime_ir_v1.json",
    "schemas/semantic_runtime_solver_v1.json",
    "tools/semantic_runtime_cli.py",
    "tools/preflight_product_semantic_runtime.py",
    "tools/regress_product_runtime_v32_compat.py",
    "tests/test_semantic_runtime_product.py",
)


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(raw)}\0".encode())
    h.update(raw)
    return h.hexdigest()


def run_json(args: list[str]) -> dict:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"COMMAND_FAILED:{args}:{proc.stderr or proc.stdout}")
    return json.loads(proc.stdout)


def main() -> int:
    try:
        preflight = run_json([sys.executable, str(ROOT / "tools" / "preflight_product_semantic_runtime.py")])
        if preflight.get("terminal") != "PRODUCT_RUNTIME_PREFLIGHT_PASS":
            raise RuntimeError("P01_PREFLIGHT_NOT_PASS")

        regression = run_json([sys.executable, str(ROOT / "tools" / "regress_product_runtime_v32_compat.py")])
        if regression.get("terminal") != "PRODUCT_RUNTIME_V32_COMPAT_REGRESSION_PASS":
            raise RuntimeError("P02_REGRESSION_NOT_PASS")

        task = make_task()
        solver = make_solver()
        api_ir = discover_and_ground(task)
        api_execution = execute_validated_ir(api_ir, solver)

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            task_path = td / "task.json"
            solver_path = td / "solver.json"
            ir_path = td / "ir.json"
            task_path.write_text(json.dumps(task), encoding="utf-8")
            solver_path.write_text(json.dumps(solver), encoding="utf-8")

            cli_discover = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "semantic_runtime_cli.py"), "discover-ground", str(task_path)],
                cwd=ROOT, text=True, capture_output=True,
            )
            if cli_discover.returncode:
                raise RuntimeError("CLI_DISCOVER_FAILED:" + (cli_discover.stderr or cli_discover.stdout))
            cli_ir = json.loads(cli_discover.stdout)
            ir_path.write_text(json.dumps(cli_ir), encoding="utf-8")

            cli_execute = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "semantic_runtime_cli.py"), "execute", str(ir_path), str(solver_path)],
                cwd=ROOT, text=True, capture_output=True,
            )
            if cli_execute.returncode:
                raise RuntimeError("CLI_EXECUTE_FAILED:" + (cli_execute.stderr or cli_execute.stdout))
            cli_execution = json.loads(cli_execute.stdout)

        if canonical_json(api_ir) != canonical_json(cli_ir):
            raise RuntimeError("API_CLI_IR_MISMATCH")
        if canonical_json(api_execution) != canonical_json(cli_execution):
            raise RuntimeError("API_CLI_EXECUTION_MISMATCH")
        if cli_execution.get("result", {}).get("applicable") is not True:
            raise RuntimeError("END_TO_END_OPERATOR_NOT_APPLICABLE")
        if {"pred": "DONE", "args": ["JOB"]} not in cli_execution["result"]["after"]:
            raise RuntimeError("END_TO_END_EXPECTED_EFFECT_MISSING")

        log_row = bounded_log(
            "product_mvp",
            task_id="NON_ASSAY_SMOKE",
            terminal="PASS",
            oracle="must_not_log",
            raw_text="must_not_log",
        )
        if "oracle" in log_row or "raw_text" in log_row:
            raise RuntimeError("BOUNDED_LOG_REDACTION_FAILED")
        if len(canonical_json(log_row).encode("utf-8")) > 2048:
            raise RuntimeError("BOUNDED_LOG_SIZE_FAILED")

        manifest = {path: git_blob_sha(ROOT / path) for path in PRODUCT_FILES}
        out = {
            "protocol": "PRODUCT_SEMANTIC_RUNTIME_EVIDENCE_V1",
            "pass": True,
            "terminal": "PRODUCT_MVP_COMPLETE",
            "issue": 54,
            "p01_terminal": preflight["terminal"],
            "p02_terminal": regression["terminal"],
            "non_assay_end_to_end": {
                "api_cli_ir_byte_equivalent": True,
                "api_cli_execution_byte_equivalent": True,
                "operator_applicable": True,
                "expected_effect": {"pred": "DONE", "args": ["JOB"]},
                "canonical_ir_sha256": hashlib.sha256(canonical_json(cli_ir).encode()).hexdigest(),
                "canonical_execution_sha256": hashlib.sha256(canonical_json(cli_execution).encode()).hexdigest(),
            },
            "bounded_log_gate": "PASS",
            "research_pin_gate": preflight["research_pin_gate"],
            "v32_compatibility": regression["exact_behavior_match"],
            "product_file_blobs": manifest,
            "scientific_assets_modified": False,
            "github_actions_required": False,
            "google_drive_required": False,
            "claim_limit": "Finite typed/auditable semantic or transition spaces only; no unrestricted ontology invention or open-ended world-knowledge claim.",
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "protocol": "PRODUCT_SEMANTIC_RUNTIME_EVIDENCE_V1",
                    "pass": False,
                    "terminal": "PRODUCT_MVP_EVIDENCE_FAIL_CLOSED",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
