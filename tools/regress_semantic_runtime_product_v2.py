#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from semantic_runtime import (
    RuntimeContractError,
    bounded_log,
    canonical_json,
    discover_and_ground,
    execute_validated_ir,
    validate_semantic_ir,
)
from tests.test_semantic_runtime_product import make_solver, make_task


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(raw)}\0".encode())
    h.update(raw)
    return h.hexdigest()


def pin_check(path: Path) -> tuple[bool, list[dict[str, Any]]]:
    pins = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for rel, expected in sorted(pins["files"].items()):
        p = ROOT / rel
        actual = git_blob_sha(p) if p.exists() else None
        rows.append({"path": rel, "expected": expected, "actual": actual, "pass": actual == expected})
    return all(x["pass"] for x in rows), rows


def expect_contract_error(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        fn()
    except RuntimeContractError as exc:
        return {"name": name, "pass": True, "error": str(exc)}
    except Exception as exc:
        return {"name": name, "pass": False, "error": f"UNEXPECTED:{type(exc).__name__}:{exc}"}
    return {"name": name, "pass": False, "error": "SILENT_ACCEPT"}


def main() -> int:
    failures: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}

    product_ok, product_rows = pin_check(ROOT / "semantic_runtime" / "product_pins.json")
    research_ok, research_rows = pin_check(ROOT / "semantic_runtime" / "research_pins.json")
    checks["product_pins_11_of_11"] = product_ok and len(product_rows) == 11
    checks["research_pins_21_of_21"] = research_ok and len(research_rows) == 21

    task = make_task()
    baseline = canonical_json(discover_and_ground(task))
    baseline_sha = hashlib.sha256(baseline.encode()).hexdigest()

    repeat_shas = [
        hashlib.sha256(canonical_json(discover_and_ground(copy.deepcopy(task))).encode()).hexdigest()
        for _ in range(100)
    ]
    checks["in_process_100x_byte_stable"] = len(set(repeat_shas)) == 1 and repeat_shas[0] == baseline_sha

    permutation_shas: list[str] = []
    for perm in itertools.permutations(range(4)):
        variant = copy.deepcopy(task)
        original = variant["visible"]["training_examples"]
        variant["visible"]["training_examples"] = [original[i] for i in perm]
        output = canonical_json(discover_and_ground(variant))
        permutation_shas.append(hashlib.sha256(output.encode()).hexdigest())
    checks["training_order_24x_invariant"] = len(set(permutation_shas)) == 1 and permutation_shas[0] == baseline_sha

    cli_outputs: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "task.json"
        path.write_text(json.dumps(task), encoding="utf-8")
        cli_rows = []
        for _ in range(5):
            run = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "semantic_runtime_cli.py"), "discover-ground", str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            cli_rows.append({"returncode": run.returncode, "stderr": run.stderr[-1000:]})
            cli_outputs.append(run.stdout)
    checks["cli_5x_byte_stable"] = all(x["returncode"] == 0 for x in cli_rows) and len(set(cli_outputs)) == 1 and cli_outputs[0].strip() == baseline

    negative_rows: list[dict[str, Any]] = []

    def bad_root():
        x = copy.deepcopy(task); x["metadata"] = "x"; discover_and_ground(x)
    negative_rows.append(expect_contract_error("unknown_root_field", bad_root))

    def bad_visible():
        x = copy.deepcopy(task); x["visible"]["metadata"] = "x"; discover_and_ground(x)
    negative_rows.append(expect_contract_error("unknown_visible_field", bad_visible))

    def bad_hidden():
        x = copy.deepcopy(task); x["visible"]["heldout_examples"][0]["oracle"] = {"x": 1}; discover_and_ground(x)
    negative_rows.append(expect_contract_error("hidden_key_nested", bad_hidden))

    def bad_eval_before():
        x = copy.deepcopy(task); x["visible"]["evaluation_probes"][0]["before"] = [0,0,0]; discover_and_ground(x)
    negative_rows.append(expect_contract_error("evaluation_before_mismatch", bad_eval_before))

    def bad_obs_before():
        x = copy.deepcopy(task); x["visible"]["training_examples"][0]["behavior_observations"][0]["before"] = [1,1,1]; discover_and_ground(x)
    negative_rows.append(expect_contract_error("observation_before_mismatch", bad_obs_before))

    def bad_obs_duplicate():
        x = copy.deepcopy(task)
        first = copy.deepcopy(x["visible"]["training_examples"][0]["behavior_observations"][0])
        x["visible"]["training_examples"][0]["behavior_observations"].append(first)
        discover_and_ground(x)
    negative_rows.append(expect_contract_error("duplicate_observation_probe", bad_obs_duplicate))

    def bad_entity_type():
        x = copy.deepcopy(task); x["visible"]["heldout_examples"][0]["entity_registry"]["E01"]["type"] = "UNKNOWN"; discover_and_ground(x)
    negative_rows.append(expect_contract_error("unknown_entity_type", bad_entity_type))

    def bad_heldout_duplicate():
        x = copy.deepcopy(task); x["visible"]["heldout_examples"][1]["example_id"] = x["visible"]["heldout_examples"][0]["example_id"]; discover_and_ground(x)
    negative_rows.append(expect_contract_error("duplicate_heldout_id", bad_heldout_duplicate))

    ir = discover_and_ground(task)

    def bad_ir_probe():
        x = copy.deepcopy(ir)
        row = x["discovered_slots"][0]["evaluation_probe_predictions"][0]
        original = list(row["predicted_after"])
        row["predicted_after"] = [1 - original[0], original[1], original[2]]
        validate_semantic_ir(x, task["visible"])
    negative_rows.append(expect_contract_error("forged_ir_probe_prediction", bad_ir_probe))

    def bad_ir_argument():
        x = copy.deepcopy(ir); x["heldout_assignments"][0]["arguments"] = ["UNKNOWN"]
        validate_semantic_ir(x, task["visible"])
    negative_rows.append(expect_contract_error("forged_ir_unknown_argument", bad_ir_argument))

    def bad_solver_extra():
        x = make_solver(); x["metadata"] = "x"; execute_validated_ir(ir, x)
    negative_rows.append(expect_contract_error("solver_unknown_field", bad_solver_extra))

    def bad_solver_index():
        x = make_solver(); x["parameter_from_arguments"] = {"$X": 99}; execute_validated_ir(ir, x)
    negative_rows.append(expect_contract_error("solver_argument_index", bad_solver_index))

    checks["negative_contract_cases_12_of_12"] = len(negative_rows) == 12 and all(x["pass"] for x in negative_rows)

    log = bounded_log("regression", task_id="T", oracle="secret", hidden_payload="secret", raw_text="secret", count=1)
    checks["bounded_log_redaction"] = (
        "oracle" not in canonical_json(log).lower()
        and "hidden" not in canonical_json(log).lower()
        and "raw" not in canonical_json(log).lower()
        and len(canonical_json(log).encode()) <= 2048
    )

    solver_out = execute_validated_ir(ir, make_solver())
    checks["downstream_adapter_smoke"] = solver_out["result"]["applicable"] is True

    for name, value in checks.items():
        if value is not True:
            failures.append({"gate": name, "value": value})

    passed = not failures
    out = {
        "protocol": "SEMANTIC_RUNTIME_PRODUCT_P02_REGRESSION_V1",
        "issue": 54,
        "ecv4_phase": "I54:REGRESSION",
        "pass": passed,
        "terminal": "PRODUCT_P02_REGRESSION_PASS" if passed else "PRODUCT_P02_REGRESSION_FAIL_CLOSED",
        "checks": checks,
        "baseline_output_sha256": baseline_sha,
        "negative_rows": negative_rows,
        "product_pin_rows": product_rows,
        "research_pin_rows": research_rows,
        "failure_count": len(failures),
        "failures": failures,
        "next_ecv4_phase": "I54:EVIDENCE" if passed else "I54:REPAIR",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
