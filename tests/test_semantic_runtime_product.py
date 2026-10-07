from __future__ import annotations

import copy
import hashlib
import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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

STATE = list(itertools.product((0, 1), repeat=3))


def _apply(code, state):
    out = []
    for op, bit in zip(code, state):
        if op == "KEEP":
            out.append(bit)
        elif op == "SET0":
            out.append(0)
        elif op == "SET1":
            out.append(1)
        else:
            out.append(1 - bit)
    return out


def _obs(code, index):
    return {
        "probe_id": f"Q{index:02d}",
        "before": list(STATE[index]),
        "after": _apply(code, STATE[index]),
    }


def _entity(eid):
    return {eid: {"type": "T01", "surface_forms": [f"{eid} item"]}}


def _train(eid, text, code, indices):
    return {
        "example_id": eid,
        "raw_text": text,
        "entity_registry": _entity(eid),
        "behavior_observations": [_obs(code, i) for i in indices],
    }


def _held(eid, text):
    return {"example_id": eid, "raw_text": text, "entity_registry": _entity(eid)}


def make_task():
    open_code = ("SET1", "KEEP", "KEEP")
    close_code = ("SET0", "FLIP", "KEEP")
    return {
        "protocol": "SEMANTIC_RUNTIME_TASK_V1",
        "visible": {
            "type_inventory": ["T01"],
            "training_examples": [
                _train("T01", "T01 item opens channel", open_code, (0, 1)),
                _train("T02", "T02 item activates channel", open_code, (2, 4)),
                _train("T03", "T03 item closes channel", close_code, (0, 2)),
                _train("T04", "T04 item disables channel", close_code, (1, 4)),
            ],
            "evaluation_probes": [
                {"probe_id": f"Q{i:02d}", "before": list(STATE[i])}
                for i in (3, 5, 6, 7)
            ],
            "heldout_examples": [
                _held("H01", "H01 item activates channel"),
                _held("H02", "H02 item disables channel"),
                _held(
                    "H03",
                    "The evidence is unresolved between: H03 item activates channel OR H03 item disables channel",
                ),
            ],
        },
    }


def make_solver():
    return {
        "protocol": "SEMANTIC_RUNTIME_SOLVER_V1",
        "assignment_example_id": "H01",
        "required_polarity": "POS",
        "required_modality": "ASSERTED",
        "parameter_from_arguments": {"$X": 0},
        "static_binding": {"$TASK": "JOB"},
        "before": [
            {"pred": "READY", "args": ["E01"]},
            {"pred": "PENDING", "args": ["JOB"]},
        ],
        "operator_schema": {
            "preconditions": [
                {"pred": "READY", "args": ["$X"]},
                {"pred": "PENDING", "args": ["$TASK"]},
            ],
            "add_effects": [{"pred": "DONE", "args": ["$TASK"]}],
            "delete_effects": [{"pred": "PENDING", "args": ["$TASK"]}],
        },
    }


class ProductSemanticRuntimeTests(unittest.TestCase):
    def test_01_two_slot_discovery_and_ambiguity(self):
        ir = discover_and_ground(make_task())
        self.assertEqual(len(ir["discovered_slots"]), 2)
        self.assertEqual(
            {x["example_id"] for x in ir["heldout_assignments"]},
            {"H01", "H02"},
        )
        self.assertEqual(
            ir["abstentions"],
            [{"example_id": "H03", "status": "AMBIGUOUS"}],
        )

    def test_02_byte_stable_replay(self):
        a = canonical_json(discover_and_ground(make_task())).encode()
        b = canonical_json(discover_and_ground(copy.deepcopy(make_task()))).encode()
        self.assertEqual(a, b)
        self.assertEqual(
            hashlib.sha256(a).hexdigest(),
            "695312aaaeffa1d9f45e78957cbc4952791116998eb567050c692e15a4df199b",
        )

    def test_03_forbidden_oracle_input(self):
        task = make_task()
        task["oracle"] = {"answer": "forbidden"}
        with self.assertRaisesRegex(RuntimeContractError, "FORBIDDEN_INPUT_KEY"):
            discover_and_ground(task)

    def test_04_malformed_input_rejected(self):
        task = make_task()
        task["visible"]["training_examples"] = task["visible"]["training_examples"][:3]
        with self.assertRaisesRegex(RuntimeContractError, "EXACTLY_FOUR"):
            discover_and_ground(task)

    def test_05_nonidentifiable_discovery_fails_closed(self):
        task = make_task()
        for row in task["visible"]["training_examples"]:
            row["behavior_observations"] = [{"probe_id": "Q00", "before": [0,0,0], "after": [0,0,0]}]
        with self.assertRaisesRegex(RuntimeContractError, "DISCOVERY_NOT_UNIQUELY_IDENTIFIABLE"):
            discover_and_ground(task)

    def test_06_duplicate_membership_rejected(self):
        task = make_task()
        ir = discover_and_ground(task)
        bad = copy.deepcopy(ir)
        bad["discovered_slots"][1]["training_members"] = list(
            bad["discovered_slots"][0]["training_members"]
        )
        with self.assertRaisesRegex(RuntimeContractError, "TRAINING_PARTITION_NOT_EXACT"):
            validate_semantic_ir(bad, task["visible"])

    def test_07_downstream_execute(self):
        ir = discover_and_ground(make_task())
        out = execute_validated_ir(ir, make_solver())
        self.assertTrue(out["result"]["applicable"])
        self.assertIn(
            {"pred": "DONE", "args": ["JOB"]},
            out["result"]["after"],
        )

    def test_08_ambiguous_execution_fails_closed(self):
        ir = discover_and_ground(make_task())
        solver = make_solver()
        solver["assignment_example_id"] = "H03"
        with self.assertRaisesRegex(RuntimeContractError, "AMBIGUOUS"):
            execute_validated_ir(ir, solver)

    def test_09_bounded_log_redacts_sensitive_fields(self):
        self.assertEqual(
            bounded_log("runtime", task_id="X", oracle="secret", raw_text="secret"),
            {"event": "runtime", "task_id": "X"},
        )

    def test_10_cli_smoke(self):
        task = make_task()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "task.json"
            path.write_text(json.dumps(task), encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "semantic_runtime_cli.py"), "discover-ground", str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
        self.assertEqual(run.returncode, 0, run.stderr)
        parsed = json.loads(run.stdout)
        self.assertEqual(parsed["protocol"], "SEMANTIC_RUNTIME_IR_V1")


if __name__ == "__main__":
    unittest.main()
