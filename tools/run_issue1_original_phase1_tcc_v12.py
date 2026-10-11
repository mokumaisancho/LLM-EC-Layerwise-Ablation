#!/usr/bin/env python3
"""Original Phase1 narrow successor TCC v12: real bounded W4B/W4C code gate.

This nests the unchanged versioned original v11, validates a separately
pinned EC source-policy v2, runs public-only S3/S4 regression, and fails
closed at the missing independent natural-language/custody authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_issue1_original_phase1_tcc_v11 import (
    run as root_v11, git_head, git_blob, TCC_SOURCE,
)
from tools.run_issue57_tcc_generator_gate import context_for, node

PROTOCOL = "ISSUE1_ORIGINAL_PHASE1_SOURCE_POLICY_TCC_V12"
NATIVE_COMMIT = "b5eb0c7d57ce819194e7ca840628007bd582274b"
NATIVE_PIN = {
    "01_repo/src/v4/ec_layerwise_source_policy_authority_v2.py":
        "7da0cd8d876505cafdd5a9811132427e2f441a14",
    "01_repo/tests/test_ec_layerwise_source_policy_authority_v2.py":
        "4b3325d418874be139b71cb7c715040fd9586821",
}
ADDED_SOURCE = [
    "tools/run_issue1_original_phase1_tcc_v12.py",
    "tests/test_issue1_original_phase1_tcc_v12.py",
]


def must(valid, label):
    if not valid:
        raise ValueError(label)


def source_pins(path, source_files, exact_commit=None):
    must(path.is_dir() and not path.is_symlink(),
         "G0_PINNED_DIRECTORY_MISSING")
    if exact_commit is not None:
        must(git_head(path) == exact_commit, "G0_SOURCE_COMMIT_MISMATCH")
    out = {}
    for file_name, expected_blob in source_files.items():
        file = path / file_name
        must(file.is_file() and not file.is_symlink(),
             "G0_SOURCE_MISSING:" + file_name)
        commit_blob = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD:" + file_name],
            capture_output=True, text=True, timeout=15)
        must(commit_blob.returncode == 0 and
             commit_blob.stdout.strip() == expected_blob and
             expected_blob == git_blob(file.read_bytes()),
             "G0_SOURCE_BLOB_MISMATCH:" + file_name)
        out[file_name] = expected_blob
    return out


def manifest():
    return {
        "schema": "tcc.spec.v3",
        "tcc_id": "ISSUE1-ORIGINAL-S1-S4-AC18-V12-W4BC",
        "goal": "Autonomously run original Phase1 v11, verify native v2 source pins, 46 W4B/W4C tests and 24 formal public-only cases, and never turn formal bounded policies into independently known natural semantic authority.",
        "acceptance": [
            "Keep frozen original 18 mandatory AC, S1-S4, original materiality .20.",
            "Validate versioned public source-typed S3 full set and S4 exhaustive formal inventory.",
            "Pass native 46 source tests including 24 disjoint formal public tasks.",
            "Reject unknown semantics, silent omissions, forged authority and Oracle leakage.",
            "Never qualify unknown real-world obligations or naturally expressed inputs from formal fixtures.",
            "Do not promote W4 source mechanics to original AC or bypass #61 real Oracle runner."
        ],
        "state_keys": ["new_sources", "original_v11", "native_pin",
                       "public_policy_tests", "scope_gate"],
        "immutable_state_keys": [],
        "entry_nodes": ["freeze_new_tcc_v12"],
        "nodes": [
            node("freeze_new_tcc_v12", "action", writes=("new_sources",),
                 failure="blocked_integrity"),
            node("replay_original_tcc_v11", "action",
                 depends=("freeze_new_tcc_v12",),
                 writes=("original_v11",), failure="blocked_integrity"),
            node("pin_new_source_policy_engine", "action",
                 depends=("replay_original_tcc_v11",),
                 writes=("native_pin",), failure="blocked_integrity"),
            node("run_W4B_S3_W4C_S4_policy_tests", "action",
                 depends=("pin_new_source_policy_engine",),
                 writes=("public_policy_tests",),
                 failure="blocked_integrity"),
            node("verify_scientific_authority_scope", "action",
                 depends=("run_W4B_S3_W4C_S4_policy_tests",),
                 writes=("scope_gate",), failure="blocked_integrity"),
            node("strict_original_18AC_exit", "gate",
                 depends=("verify_scientific_authority_scope",),
                 reads=("new_sources", "original_v11", "native_pin",
                        "public_policy_tests", "scope_gate"),
                 branches={
                     "independent_semantics_missing": "blocked_external_semantics",
                     "whole_AE_missing": "blocked_AE",
                     "original_18AC_science_pass": "root_science_verified",
                 }),
            node("blocked_external_semantics", "terminal", terminal="BLOCKED"),
            node("blocked_AE", "terminal", terminal="BLOCKED"),
            node("root_science_verified", "terminal", terminal="SUCCESS"),
            node("blocked_integrity", "terminal", terminal="BLOCKED"),
        ],
    }


def run(tcc_root: Path, old_native_root: Path, policy_native_root: Path):
    must(git_head(tcc_root) == TCC_SOURCE, "G0_TCC_COMPILER_CHANGED")
    if str(tcc_root) not in sys.path:
        sys.path.insert(0, str(tcc_root))
    from tcc.core_v3 import compile_spec, normalize_spec, validate_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph, to_ecv4_evidence

    head = git_head(ROOT)
    spec = manifest()
    ctx = context_for(spec, head)
    ctx.update(
        selected_issue_id="ISSUE-1", actionable_issue_ids=["ISSUE-1"],
        blocked_issue_ids=[],
        snapshot_id="ISSUE1-TCC12:" + head[:12],
        source_fingerprint="sha256:" + hashlib.sha256(
            json.dumps(spec, sort_keys=True).encode()).hexdigest(),
    )
    generated = generate_tcc_from_context(ctx)
    must(generated.get("result") == "tcc.spec.v3"
         and not validate_spec(generated["spec"])
         and generated["spec"] == normalize_spec(spec),
         "G1_V12_COMPILER_GRAPH_CHANGED")
    graph = compile_spec(generated["spec"])
    own = {name: git_blob((ROOT / name).read_bytes())
           for name in ADDED_SOURCE}
    pinned = source_pins(ROOT, own)
    old_seals = source_pins(policy_native_root, NATIVE_PIN, NATIVE_COMMIT)
    state = {"errors": [], "native_tests": None, "natural_semantics": False}

    def seal():
        must(source_pins(ROOT, own) == pinned,
             "G7_V12_SOURCE_CHANGED_DURING_EXECUTION")
        must(source_pins(policy_native_root, NATIVE_PIN, NATIVE_COMMIT) == old_seals,
             "G7_NATIVE_POLICY_CODE_CHANGED_DURING_EXECUTION")

    def okay(key, receipt):
        seal()
        return {"status": "success", "writes": {key: True},
                "evidence": [receipt]}

    def catch(group, fn):
        try:
            return fn()
        except Exception as error:
            state["errors"].append(
                group + ":" + type(error).__name__ + ":" + str(error)[:170])
            return {"status": "failure",
                    "evidence": ["G7_" + group + "_INTEGRITY_REJECTED"]}

    def own_source(_n, _s, _a):
        return catch("V12", lambda: okay(
            "new_sources", "V12_SOURCE_REPO_BLOBS_PINNED"))

    def prior(_n, _s, _a):
        def call():
            v11 = root_v11(tcc_root, old_native_root)
            must(v11["TCC_terminal"] == "blocked_native"
                 and v11["original_root_pass"] == 2
                 and v11["original_root_required"] == 18
                 and v11["replay_v2_negative_test_count"] == 17
                 and not v11["errors"] and v11["source_seals_stable"],
                 "G11_V11_CAUSAL_GATE_OR_ORIGINAL_AC_DRIFT")
            state["v11"] = {
                "terminal": v11["TCC_terminal"],
                "source_and_input_seals": v11["source_seals_stable"],
                "replay_adversarial_tests": 17,
            }
            return okay("original_v11", "ORIGINAL_18AC_V11_CAUSAL_GATE_VALID")
        return catch("ORIGINAL", call)

    def native(_n, _s, _a):
        return catch("NATIVE", lambda: okay(
            "native_pin", "W4B_W4C_NATIVE_POLICY_V2_SOURCE_AND_TEST_SEALED"))

    def exercise(_n, _s, _a):
        def call():
            command = [sys.executable, "-B", "-m", "unittest", "-q",
                       "01_repo.tests.test_ec_layerwise_source_policy_authority_v2",
                       "01_repo.tests.test_ec_layerwise_typed_evidence_authority_v1",
                       "01_repo.tests.test_ec_layerwise_admissible_set_closure_v1"]
            p = subprocess.run(
                command, cwd=policy_native_root, capture_output=True,
                text=True, timeout=45, check=False)
            must(p.returncode == 0 and "Ran 46 tests" in p.stderr
                 and "OK" in p.stderr,
                 "G8_NATIVE_46_TESTS_FAILED:" + p.stderr[-150:])
            state["native_tests"] = 46
            state["formal_disjoint_dev_cases"] = 24
            return okay("public_policy_tests",
                        "W4B_W4C_46_NEGATIVE_TESTS_24_DISJOINT_FORMAL_CASES_PASS")
        return catch("TESTS", call)

    def scope(_n, _s, _a):
        def call():
            # No data-owning tester or source string can certify independent
            # natural-language truth or a complete inventory outside the
            # pinned finite policy. W5 must remain blocked.
            state["natural_semantics"] = False
            state["real_world_obligation_completeness"] = False
            state["trusted_real_AE_runtime"] = False
            return okay("scope_gate", "FORMAL_POLICY_ONLY_INDEPENDENT_NL_UNKNOWN")
        return catch("SCOPE", call)

    def decide(_n, flags, _a):
        if not all(flags.get(k) is True for k in
                   ("new_sources", "original_v11", "native_pin",
                    "public_policy_tests", "scope_gate")):
            return {"outcome": "whole_AE_missing",
                    "evidence": ["DEPENDENT_GATE_NOT_VALIDATED"]}
        must(not state["natural_semantics"] and
             not state["real_world_obligation_completeness"] and
             not state["trusted_real_AE_runtime"],
             "G11_FALSE_SCIENTIFIC_PROMOTION")
        return {"outcome": "independent_semantics_missing",
                "evidence": [
                    "ISSUE59_NATURAL_SEMANTIC_AUTHORITY_UNPROVEN",
                    "ISSUE60_REAL_WORLD_OBLIGATION_COMPLETENESS_UNPROVEN",
                    "ISSUE61_REAL_AE_RUNNER_UNATTESTED",
                ]}

    execution = execute_graph(graph, {
        "freeze_new_tcc_v12": own_source,
        "replay_original_tcc_v11": prior,
        "pin_new_source_policy_engine": native,
        "run_W4B_S3_W4C_S4_policy_tests": exercise,
        "verify_scientific_authority_scope": scope,
        "strict_original_18AC_exit": decide,
    })
    must(execution.get("result") == "TERMINAL" and
         execution["terminal_id"] in
         ("blocked_integrity", "blocked_external_semantics", "blocked_AE"),
         "G11_ORIGINAL_UNQUALIFIED_ROOT_EXIT")
    seal()
    return {
        "protocol": PROTOCOL,
        "TCC_nodes": len(graph["nodes"]),
        "TCC_edges": len(graph["edges"]),
        "TCC_terminal": execution["terminal_id"],
        "ECv4_handoff": to_ecv4_evidence(graph, execution),
        "original_root_pass": 2,
        "original_root_required": 18,
        "prior_original_v11": state.get("v11"),
        "native_git_commit": NATIVE_COMMIT,
        "new_native_pinned_blobs": old_seals,
        "new_native_policy_tests": state["native_tests"],
        "new_formal_disjoint_cases": state.get("formal_disjoint_dev_cases"),
        "independent_natural_semantics_proven": False,
        "independently_complete_real_world_obligations": False,
        "real_matched_AE_validated": False,
        "open_blockers": [59, 60, 61],
        "source_seals_stable": pinned == source_pins(ROOT, own)
            and old_seals == source_pins(
                policy_native_root, NATIVE_PIN, NATIVE_COMMIT),
        "errors": state["errors"],
        "original_science_complete": False,
    }


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--tcc-root", type=Path, required=True)
    cli.add_argument("--old-native-root", type=Path, required=True)
    cli.add_argument("--policy-native-root", type=Path, required=True)
    cli.add_argument("--out", type=Path)
    args = cli.parse_args()
    try:
        output = run(args.tcc_root, args.old_native_root,
                     args.policy_native_root)
        result = json.dumps(output, indent=2, sort_keys=True,
                            ensure_ascii=False) + "\n"
        if args.out:
            must(not args.out.is_symlink(), "G7_OUTPUT_SYMLINK")
            args.out.write_text(result, encoding="utf-8")
        else:
            print(result, end="")
        return 2 if not output["errors"] else 3
    except Exception as error:
        print(json.dumps({"protocol": PROTOCOL,
                          "terminal": "INTEGRITY_FAIL_CLOSED",
                          "error": type(error).__name__ + ":" +
                          str(error)[:200]}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
