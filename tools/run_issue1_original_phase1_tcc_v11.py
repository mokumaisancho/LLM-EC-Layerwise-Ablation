#!/usr/bin/env python3
"""Issue #1 TCC v11 successor: integrate Issue #61 replay regressions.

Original v10 and historical raw v1 remain pinned and unchanged. The new
branch is a separate, fail-closed preflight; neither development replay
nor TCC execution certifies actual scientific Phase1 AC.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.issue1_phase1_ae_gate_v1 import h
from tools.issue1_phase1_ae_gate_v2 import TrustedReplay, verify as replay_v2
from tools.run_issue1_original_phase1_tcc_v10 import (
    run as baseline_v10, git_head, git_blob, TCC_SOURCE,
)
from tools.run_issue57_tcc_generator_gate import context_for, node

PROTOCOL = "ISSUE1_ORIGINAL_PHASE1_TCC_V11"
ADDED_SOURCES = (
    "tools/issue1_phase1_ae_gate_v2.py",
    "tools/run_issue1_original_phase1_tcc_v11.py",
    "tests/test_issue1_phase1_ae_gate_v2.py",
    "tests/test_issue1_original_phase1_tcc_v11.py",
)


def must(ok, label):
    if not ok:
        raise ValueError(label)


def seals():
    result = {}
    for name in ADDED_SOURCES:
        p = ROOT / name
        revision = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD:" + name],
            capture_output=True, text=True, timeout=12)
        must(p.is_file() and not p.is_symlink()
             and revision.returncode == 0
             and revision.stdout.strip() == git_blob(p.read_bytes()),
             "G0_V11_SOURCE_UNTRACKED_OR_MUTATED:" + name)
        result[name] = revision.stdout.strip()
    return result


def manifest():
    return {
        "schema": "tcc.spec.v3",
        "tcc_id": "ISSUE1-ORIGINAL-S1-S4-AC18-V11-ISSUE61",
        "goal": "Run unchanged original Phase1 v10 TCC, independent target-only E replay adversarial gate, optional trusted replay, and fail-closed original AC decision.",
        "acceptance": [
            "Preserve original 18 mandatory AC, 0.20 threshold and frozen v1/v10.",
            "Run independent source-bound downstream replay for all E layers; hostile rehashed multilayer interventions must be rejected.",
            "Never promote toy replay or authored raw receipts to original Phase1 scientific evidence.",
            "Report #59 S3 and #60 S4 and #61 real authority as blockers.",
        ],
        "state_keys": ["source_v11", "original_v10", "replay_regression",
                       "real_trace", "exit_check"],
        "immutable_state_keys": [],
        "entry_nodes": ["pin_additional_sources"],
        "nodes": [
            node("pin_additional_sources", "action", writes=("source_v11",),
                 failure="blocked_integrity"),
            node("run_existing_original_v10_TCC", "action",
                 depends=("pin_additional_sources",), writes=("original_v10",),
                 failure="blocked_integrity"),
            node("test_target_only_replay_v2", "action",
                 depends=("run_existing_original_v10_TCC",),
                 writes=("replay_regression",), failure="blocked_integrity"),
            node("replay_external_AE_if_trusted", "action",
                 depends=("test_target_only_replay_v2",), writes=("real_trace",),
                 failure="blocked_integrity"),
            node("strict_original_18AC_gate", "gate",
                 depends=("replay_external_AE_if_trusted",),
                 reads=("source_v11", "original_v10",
                        "replay_regression", "real_trace"),
                 branches={"verified_all_original_AC": "root_science_verified",
                           "native_semantics_unqualified": "blocked_native",
                           "trusted_AE_missing": "blocked_AE",
                           "integrity_incomplete": "blocked_integrity"}),
            node("root_science_verified", "terminal", terminal="SUCCESS"),
            node("blocked_native", "terminal", terminal="BLOCKED"),
            node("blocked_AE", "terminal", terminal="BLOCKED"),
            node("blocked_integrity", "terminal", terminal="BLOCKED"),
        ],
    }


def run(tcc_root: Path, native_successor: Path | None = None,
        raw_v2: dict | None = None, hidden_gold: dict | None = None,
        public_inputs: dict | None = None,
        trusted_replay: TrustedReplay | None = None) -> dict:
    must(git_head(tcc_root) == TCC_SOURCE, "G0_TCC_COMPILER_CHANGED")
    must(sum(x is not None for x in (
        raw_v2, hidden_gold, public_inputs, trusted_replay)) in (0, 4),
         "G8_INCOMPLETE_EXTERNAL_REPLAY_AUTHORITY")
    if str(tcc_root) not in sys.path:
        sys.path.insert(0, str(tcc_root))
    from tcc.core_v3 import compile_spec, normalize_spec, validate_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph, to_ecv4_evidence

    original_head = git_head(ROOT)
    spec = manifest()
    ctx = context_for(spec, original_head)
    ctx.update(
        selected_issue_id="ISSUE-1",
        actionable_issue_ids=["ISSUE-1"],
        blocked_issue_ids=[],
        snapshot_id="ISSUE1-V11:" + original_head[:12],
        source_fingerprint="sha256:" + hashlib.sha256(
            json.dumps(spec, sort_keys=True).encode()).hexdigest(),
    )
    generated = generate_tcc_from_context(ctx)
    must(generated.get("result") == "tcc.spec.v3"
         and not validate_spec(generated["spec"])
         and generated["spec"] == normalize_spec(spec),
         "G1_TCC_V11_REWRITE")
    graph = compile_spec(generated["spec"])
    pinned = seals()
    state = {"errors": [], "replay": "NOT_PROVIDED", "dev_tests": None}

    def reseal():
        must(seals() == pinned, "G7_V11_SOURCES_CHANGED_DURING_EXECUTION")

    def done(key, witness):
        reseal()
        return {"status": "success", "writes": {key: True},
                "evidence": [witness]}

    def capture(key, callback):
        try:
            return callback()
        except Exception as exc:
            state["errors"].append(key + ":" + type(exc).__name__ +
                                   ":" + str(exc)[:180])
            return {"status": "failure", "evidence": ["G7_" + key + "_FAIL_CLOSED"]}

    def source(_n, _s, _a):
        return capture("SOURCE", lambda: done(
            "source_v11", "G0_ADDITIONAL_V11_SOURCES_PINNED"))

    def baseline(_n, _s, _a):
        def action():
            old = baseline_v10(tcc_root, native_successor)
            must(old["original_root_pass"] == 2
                 and old["original_root_required"] == 18
                 and old["TCC_terminal"] == "blocked_native"
                 and old["source_and_input_seals_stable"]
                 and not old["errors"], "G11_V10_ORIGINAL_STATE_CHANGED")
            state["baseline"] = old
            return done("original_v10", "V10_NATIVE_BLOCKER_PRESERVED")
        return capture("BASELINE", action)

    def regression(_n, _s, _a):
        def action():
            suite = unittest.defaultTestLoader.loadTestsFromName(
                "tests.test_issue1_phase1_ae_gate_v2")
            out = unittest.TextTestRunner(
                stream=io.StringIO(), verbosity=0).run(suite)
            must(out.wasSuccessful() and out.testsRun == 17,
                 "G8_TARGET_ONLY_NEGATIVE_TESTS_FAILED")
            state["dev_tests"] = out.testsRun
            return done("replay_regression", "V2_DEV_ADVERSARIAL_17_PASS")
        return capture("REGRESSION", action)

    def real(_n, _s, _a):
        def action():
            if raw_v2 is not None:
                output = replay_v2(
                    raw_v2, hidden_gold, public_inputs, trusted_replay)
                must(output["source_bound_deterministic_replay_verified"]
                     and not output["original_AC18_pass_automatically"],
                     "G8_FALSE_SCIENTIFIC_REPLAY_PASS")
                state["replay"] = "STRUCTURAL_RERUN_ONLY_NOT_INDEPENDENT_SCIENCE"
                state["replay_stages"] = output["replayed_stages"]
            return done("real_trace", "NO_SCIENTIFIC_AE_AUTHORITY_CLAIM")
        return capture("REPLAY", action)

    def decide(_n, flags, _a):
        if not all(flags.get(k) is True for k in (
            "source_v11", "original_v10",
            "replay_regression", "real_trace")):
            return {"outcome": "integrity_incomplete",
                    "evidence": ["BLOCKED_REQUIRED_GATE"]}
        # v10 proves native S3/S4 incompatibility, #59/#60 remain open.
        # Neither 15 development tests nor real trace structure alone can
        # turn any of the remaining 16 original AC to PASS.
        return {"outcome": "native_semantics_unqualified",
                "evidence": ["ISSUE59_ISSUE60_NATIVE_SEMANTICS_UNQUALIFIED",
                             "ISSUE61_REAL_CAUSAL_AUTHORITY_NOT_ATTESTED"]}

    executed = execute_graph(graph, {
        "pin_additional_sources": source,
        "run_existing_original_v10_TCC": baseline,
        "test_target_only_replay_v2": regression,
        "replay_external_AE_if_trusted": real,
        "strict_original_18AC_gate": decide,
    })
    must(executed.get("result") == "TERMINAL"
         and executed["terminal_id"] in (
             "blocked_native", "blocked_AE", "blocked_integrity"),
         "G11_V11_FALSE_ROOT_COMPLETION")
    reseal()
    return {
        "protocol": PROTOCOL, "TCC_nodes": len(graph["nodes"]),
        "TCC_edges": len(graph["edges"]),
        "TCC_terminal": executed["terminal_id"],
        "ECv4_handoff": to_ecv4_evidence(graph, executed),
        "original_TCC_v10_terminal": state.get("baseline", {}).get("TCC_terminal"),
        "original_root_pass": 2, "original_root_required": 18,
        "replay_v2_negative_test_count": state["dev_tests"],
        "replay_v2_real_evidence": state["replay"],
        "replay_v2_stages": state.get("replay_stages"),
        "open_blockers": [59, 60, 61],
        "source_git_blobs": pinned,
        "source_seals_stable": pinned == seals(),
        "errors": state["errors"],
        "original_science_complete": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tcc-root", type=Path, required=True)
    parser.add_argument("--native-successor", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.tcc_root, args.native_successor)
        data = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            must(not args.out.is_symlink(), "G7_OUTPUT_SYMLINK")
            args.out.write_text(data)
        else:
            print(data, end="")
        return 2 if not result["errors"] else 3
    except Exception as exc:
        print(json.dumps({"protocol": PROTOCOL, "terminal": "INTEGRITY_FAIL_CLOSED",
                          "error": type(exc).__name__ + ":" + str(exc)[:180]}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
