#!/usr/bin/env python3
"""Original Issue #1 AC20/MVP18 one-shot source-sealed TCC v13.

Runs every machine-feasible pinned predecessor, materializes a real AC20
dependency ledger, checks optional lightweight model, attempts any supplied
A-E trusted structural replay, then stops with an exact blocker. It NEVER
promotes author-owned structural receipts or typed policy to scientific AC.
No background process or GitHub Actions is launched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_issue1_original_phase1_scope_v1 import run as original_audit
from tools.issue1_phase1_ae_gate_v2 import TrustedReplay, verify as replay_v2
from tools.run_issue1_original_phase1_tcc_v12 import (
    run as prior_v12, git_head, git_blob, TCC_SOURCE,
)
from tools.run_issue57_tcc_generator_gate import context_for, node

PROTOCOL = "ISSUE1_ORIGINAL_PHASE1_AC18_ONECALL_TCC_V13"
PLAN_PATH = "docs/ISSUE1_ORIGINAL_PHASE1_AC18_ONECALL_PLAN_V13_2026-10-11.json"
PIN_FILES = (
    "ACCEPTANCE_CRITERIA.md",
    "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json",
    "tools/issue1_phase1_ae_gate_v2.py",
    "tools/run_issue1_original_phase1_tcc_v12.py",
    "tools/run_issue1_original_phase1_tcc_v13.py",
    "tests/test_issue1_original_phase1_tcc_v13.py",
    PLAN_PATH,
)
STEPS = (
    "W00_SOURCE_AND_CONTRACT",
    "W01_EXECUTE_V12",
    "W02_REBUILD_AC_DAG",
    "W03_CHECK_LLM_CAPACITY",
    "W04_CHECK_S3_SEMANTICS",
    "W05_CHECK_S4_COMPLETENESS",
    "W06_VERIFY_REAL_RUNNER",
    "W07_RUN_MATCHED_AE",
    "W08_SCORE_CAUSAL_METRICS",
    "W09_AC20_SCORE",
    "W10_STRICT_EXIT",
)
NODES = (
    "freeze_original_contract",
    "run_existing_tcc_v12",
    "rebuild_original_ac20_dag",
    "inspect_llm_asset",
    "assess_independent_s3",
    "assess_independent_s4",
    "replay_real_runner_if_available",
    "classify_original_matched_ae",
    "score_layerwise_if_qualified",
    "evaluate_all_original_ac",
    "strict_original_mvp_exit",
)


def require(ok, label):
    if not ok:
        raise ValueError(label)


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            data = handle.read(1024 * 1024)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def git_pins() -> dict:
    pins = {}
    for name in PIN_FILES:
        file = ROOT / name
        got = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD:" + name],
            text=True, capture_output=True, timeout=12,
        )
        require(file.is_file() and not file.is_symlink()
                and got.returncode == 0
                and got.stdout.strip() == git_blob(file.read_bytes()),
                "G0_TRUSTED_SOURCE_BLOB_DRIFT:" + name)
        pins[name] = got.stdout.strip()
    return pins


def user_files_seal(paths) -> dict:
    existing = [p for p in paths if p is not None]
    canonical = [str(p.resolve()) for p in existing]
    require(len(canonical) == len(set(canonical)), "G6_RAW_GOLD_PATH_ALIAS")
    output = {}
    for path in existing:
        require(path.is_file() and not path.is_symlink(),
                "G6_INPUT_NOT_REGULAR_FILE")
        output[str(path.resolve())] = digest_file(path)
    return output


def load_plan() -> tuple[dict, dict]:
    original = json.loads(
        (ROOT / "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json").read_text()
    )
    plan = json.loads((ROOT / PLAN_PATH).read_text())
    require(plan["protocol"] == "ISSUE1_ORIGINAL_PHASE1_AC18_ONECALL_PLAN_V13"
            and plan["frozen_contract_git_blob"] == git_pins()[
                "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json"]
            and plan["original_ac_dependencies"] == original["ac_dependencies"]
            and plan["original_mvp_required"] == original["mvp"]["required_ac"]
            and plan["post_mvp"] == original["mvp"]["post_mvp_ac"]
            and plan["frozen_materiality_abs"] == 0.20
            and plan["frozen_tie_abs"] == 0.10,
            "G9_FROZEN_ORIGINAL_MVP_PLAN_DRIFT")
    must_ac = {f"AC-{i:02d}" for i in range(1, 21)}
    require(set(plan["original_ac_dependencies"]) == must_ac
            and set(plan["ac_work_gates"]) == must_ac
            and len(plan["original_mvp_required"]) == 18
            and len(set(plan["original_mvp_required"])) == 18
            and set(plan["original_mvp_required"]).isdisjoint(
                plan["post_mvp"])
            and set(plan["original_mvp_required"] + plan["post_mvp"]) == must_ac,
            "G1_AC20_COVERAGE_OR_MVP_SCOPE_CHANGED")
    require(list(plan["work_gates"]) == list(STEPS)
            and all(set(row["needs"]) <= set(STEPS)
                    for row in plan["work_gates"].values())
            and all(set(gates) <= set(STEPS)
                    for gates in plan["ac_work_gates"].values()),
            "G1_WORK_DAG_MISSING_OR_UNKNOWN_EDGE")
    visited = set()
    for work in STEPS:
        require(set(plan["work_gates"][work]["needs"]) <= visited,
                "G1_WORK_DAG_NOT_TOPOLOGICAL:" + work)
        visited.add(work)
    visited_ac = set()
    order = []
    all_ac = set(plan["original_ac_dependencies"])
    while len(visited_ac) < 20:
        ready = sorted(
            item for item, edges in plan["original_ac_dependencies"].items()
            if item not in visited_ac
            and all(edge in visited_ac
                    for edge in edges if edge in all_ac)
        )
        require(bool(ready), "G1_AC_DAG_CYCLE")
        for ac in ready:
            require(all(
                edge in all_ac or edge in original["issue_dependencies"]
                or (ac == "AC-18" and edge == "AC-10_IF_NEEDED")
                for edge in plan["original_ac_dependencies"][ac]),
                "G1_UNKNOWN_AC_PARENT:" + ac)
        order.extend(ready)
        visited_ac.update(ready)
    return plan, {"order": order, "norm": original}


def model_seal(path: Path | None, metadata: dict) -> dict:
    if path is None:
        return {"status": "MODEL_OPTIONAL_PATH_NOT_PROVIDED",
                "asset_verified": False, "inference_qualified": False}
    require(path.is_file() and not path.is_symlink(),
            "G12_MODEL_FILE_MISSING_OR_SYMLINK")
    expected = metadata["canonical_inputs"]["qwen2_5_0_5b"]
    actual_size = path.stat().st_size
    require(actual_size == expected["size_bytes"],
            "G12_MODEL_CAPACITY_SIZE_MISMATCH")
    actual_hash = digest_file(path)
    require(actual_hash == expected["sha256"],
            "G12_MODEL_SOURCE_HASH_MISMATCH")
    return {"status": "PINNED_0P5B_ASSET_VERIFIED",
            "asset_verified": True,
            "inference_qualified": False,
            "path": str(path.resolve()),
            "bytes": actual_size, "sha256": actual_hash}


def manifest() -> dict:
    return {
        "schema": "tcc.spec.v3",
        "tcc_id": "ISSUE1-ORIGINAL-S1-S4-AC18-ONECALL-V13",
        "goal": "Run every machine-feasible original Phase1 AC dependency to fixed point in a single call, with immutable sources, genuine model intake, source-typed S3/S4 diagnostics, target-only replay if provided and fail-closed root 18AC science.",
        "acceptance": [
            "Original frozen 20 AC / 18 required / AC10+AC18 post-MVP, no scope creep.",
            "Execute genuine pinned TCC v12/v11/v10 and native 46 tests.",
            "Recompute all AC20 dependency edges and do not pass any unsupported AC.",
            "Verify optional 0.5B model size and SHA, not substitute asset for inference.",
            "Source-typed S3/S4 is formal diagnostics only; independent meaning and inventory required.",
            "Only trusted replay validates target-only Oracle; no author receipt equals science.",
            "Check raw/gold/policy/source integrity at every transition and terminal.",
            "Finish autonomously with explicit blocker states, without repeated prompts.",
            "Never infer causal layer from end-to-end alone or change frozen 0.20.",
        ],
        "state_keys": [
            "source", "v12", "ac_dag", "model", "s3", "s4",
            "runner", "ae", "score", "ac20",
        ],
        "immutable_state_keys": [],
        "entry_nodes": [NODES[0]],
        "nodes": [
            node(NODES[0], "action", writes=("source",),
                 failure="blocked_integrity"),
            node(NODES[1], "action", depends=(NODES[0],),
                 writes=("v12",), failure="blocked_integrity"),
            node(NODES[2], "action", depends=(NODES[1],),
                 writes=("ac_dag",), failure="blocked_integrity"),
            node(NODES[3], "action", depends=(NODES[2],),
                 writes=("model",), failure="blocked_integrity"),
            node(NODES[4], "action", depends=(NODES[2],),
                 writes=("s3",), failure="blocked_integrity"),
            node(NODES[5], "action", depends=(NODES[2],),
                 writes=("s4",), failure="blocked_integrity"),
            node(NODES[6], "action",
                 depends=(NODES[3], NODES[4], NODES[5]),
                 writes=("runner",), failure="blocked_integrity"),
            node(NODES[7], "action", depends=(NODES[6],),
                 writes=("ae",), failure="blocked_integrity"),
            node(NODES[8], "action", depends=(NODES[7],),
                 writes=("score",), failure="blocked_integrity"),
            node(NODES[9], "action", depends=(NODES[8],),
                 writes=("ac20",), failure="blocked_integrity"),
            node(NODES[10], "gate", depends=(NODES[9],),
                 reads=("source", "v12", "ac_dag", "model", "s3",
                        "s4", "runner", "ae", "score", "ac20"),
                 branches={
                     "root_18AC_science_proven": "root_science_verified",
                     "external_S3_S4_missing": "blocked_semantics",
                     "model_inference_unqualified": "blocked_llm",
                     "real_runner_unqualified": "blocked_runner",
                     "matched_AE_unqualified": "blocked_ae",
                     "original_ac_not_proven": "blocked_ac",
                 }),
            node("root_science_verified", "terminal", terminal="SUCCESS"),
            node("blocked_semantics", "terminal", terminal="BLOCKED"),
            node("blocked_llm", "terminal", terminal="BLOCKED"),
            node("blocked_runner", "terminal", terminal="BLOCKED"),
            node("blocked_ae", "terminal", terminal="BLOCKED"),
            node("blocked_ac", "terminal", terminal="BLOCKED"),
            node("blocked_integrity", "terminal", terminal="BLOCKED"),
        ],
    }


def run(tcc_root: Path, old_native_root: Path, policy_native_root: Path,
        model_path: Path | None = None, arms: Path | None = None,
        gold: Path | None = None, public: Path | None = None,
        trusted_replay: TrustedReplay | None = None) -> dict:
    require(git_head(tcc_root) == TCC_SOURCE, "G0_TCC_COMPILER_DRIFT")
    require(all(p is None for p in (arms, gold, public))
            or all(p is not None for p in (arms, gold, public)),
            "G6_INCOMPLETE_RAW_GOLD_PUBLIC_TRIPLET")
    require(trusted_replay is None or all(
        p is not None for p in (arms, gold, public)),
        "G8_TRUSTED_REPLAY_WITHOUT_DATA")
    if str(tcc_root) not in sys.path:
        sys.path.insert(0, str(tcc_root))
    from tcc.core_v3 import compile_spec, normalize_spec, validate_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph, to_ecv4_evidence

    fixed_head = git_head(ROOT)
    pins_before = git_pins()
    data_before = user_files_seal((arms, gold, public))
    if model_path is not None:
        require(model_path.is_file() and not model_path.is_symlink(),
                "G12_MODEL_FILE_INVALID")
        model_meta_before = (
            model_path.stat().st_size, model_path.stat().st_mtime_ns)
    else:
        model_meta_before = None
    plan, normative = load_plan()
    graph_spec = manifest()
    ctx = context_for(graph_spec, fixed_head)
    ctx.update(
        selected_issue_id="ISSUE-1",
        actionable_issue_ids=["ISSUE-1"],
        blocked_issue_ids=[],
        snapshot_id="ISSUE1-V13:" + fixed_head[:12],
        source_fingerprint="sha256:" + hashlib.sha256(
            json.dumps(graph_spec, sort_keys=True).encode()).hexdigest(),
    )
    generated = generate_tcc_from_context(ctx)
    require(generated.get("result") == "tcc.spec.v3"
            and not validate_spec(generated["spec"])
            and generated["spec"] == normalize_spec(graph_spec),
            "G1_TCC_GENERATOR_ALTERED_FROZEN_GRAPH")
    graph = compile_spec(generated["spec"])
    state = {
        "errors": [], "work": {}, "audits": {}, "next": [],
        "actual_scientific_inference": False,
        "external_S3_independence": False,
        "external_S4_completeness": False,
        "actual_model_and_cache_qualified": False,
        "independent_oracle_custody": False,
        "qualified_real_AE": False,
    }

    def recheck():
        require(git_head(ROOT) == fixed_head and git_pins() == pins_before,
                "G0_G7_SOURCE_MUTATED_DURING_TRIAL")
        require(user_files_seal((arms, gold, public)) == data_before,
                "G7_RAW_GOLD_PUBLIC_CHANGED_DURING_TRIAL")
        if model_path is not None:
            require(model_path.is_file() and not model_path.is_symlink()
                    and (model_path.stat().st_size,
                         model_path.stat().st_mtime_ns) == model_meta_before,
                    "G12_MODEL_MUTATED_DURING_TRIAL")

    def done(flag, receipt):
        recheck()
        return {"status": "success", "writes": {flag: True},
                "evidence": [receipt]}

    def guard(stage, fn):
        try:
            recheck()
            return fn()
        except Exception as exc:
            state["errors"].append(
                stage + ":" + type(exc).__name__ + ":" + str(exc)[:190])
            return {"status": "failure",
                    "evidence": ["G0_G7_ABORT_" + stage.upper()]}

    def source(_n, _s, _a):
        def action():
            require(len(plan["original_mvp_required"]) == 18
                    and len(normative["order"]) == 20,
                    "G1_INITIAL_FROZEN_MVP_MISMATCH")
            state["work"][STEPS[0]] = "PASS_FROZEN_PROTOCOL_ONLY"
            return done("source", "FROZEN_20AC_18MVP_0P20")
        return guard("source", action)

    def old(_n, _s, _a):
        def action():
            result = prior_v12(tcc_root, old_native_root,
                               policy_native_root)
            require(result["TCC_terminal"] == "blocked_external_semantics"
                    and result["original_root_pass"] == 2
                    and result["original_root_required"] == 18
                    and result["new_native_policy_tests"] == 46
                    and result["new_formal_disjoint_cases"] == 24
                    and result["source_seals_stable"]
                    and result["errors"] == []
                    and not result["original_science_complete"],
                    "G11_V12_FALSE_SCIENCE_OR_SOURCE_DRIFT")
            state["work"][STEPS[1]] = "PASS_MACHINE_FEASIBLE_V12_ONLY"
            state["audits"]["v12"] = {
                "terminal": result["TCC_terminal"],
                "nodes": result["TCC_nodes"],
                "edges": result["TCC_edges"],
                "native_tests": result["new_native_policy_tests"],
                "formal_dev_cases": result["new_formal_disjoint_cases"],
                "verified_source_seals": result["source_seals_stable"],
                "original_ac_pass": result["original_root_pass"],
            }
            return done("v12", "V12_NATIVE_46_FORMAL_24_NO_ROOT_PROMOTION")
        return guard("v12", action)

    def dag(_n, _s, _a):
        def action():
            original = original_audit(ROOT)
            require(original["original_mvp_AC_pass"] == 2
                    and original["original_mvp_AC_total"] == 18
                    and set(k for k, v in
                            original["original_AC20_status"].items()
                            if v == "PASS") == {"AC-19", "AC-20"},
                    "G11_CANNOT_PROMOTE_AC_FROM_STRUCTURAL_TESTS")
            state["audits"]["old_AC20"] = original["original_AC20_status"]
            state["work"][STEPS[2]] = "PASS_AC20_TOPOLOGY_NO_AC_PROMOTION"
            return done("ac_dag", "AC20_ORDER_18_REQUIRED_POST10_18")
        return guard("dag", action)

    def model(_n, _s, _a):
        def action():
            receipt = model_seal(model_path, normative["norm"])
            state["audits"]["model"] = receipt
            state["work"][STEPS[3]] = (
                "MODEL_ASSET_VERIFIED_INFERENCE_NOT_YET_QUALIFIED"
                if receipt["asset_verified"] else
                "BLOCKED_MODEL_ASSET_NOT_PROVIDED")
            if not receipt["asset_verified"]:
                state["next"].append(
                    "Provide original frozen 0.5B model artifact, or use "
                    "a source-qualified allowed model ingress path.")
            return done("model", "MODEL_ASSET_NOT_LLM_CAUSAL_PROOF")
        return guard("model", action)

    def s3(_n, _s, _a):
        def action():
            state["work"][STEPS[4]] = "BLOCKED_INDEPENDENT_NATURAL_LANGUAGE_S3"
            state["next"].append(
                "#59 independent blind natural-language S1/S2→S3 source "
                "semantics, all-admissible candidate judgments")
            return done("s3", "SOURCE_POLICY_ONLY_NO_NATURAL_SEMANTICS")
        return guard("s3", action)

    def s4(_n, _s, _a):
        def action():
            state["work"][STEPS[5]] = "BLOCKED_INDEPENDENT_REAL_TASK_S4"
            state["next"].append(
                "#60 independently complete task obligations; attest "
                "positive empty inventories and real source issuer")
            return done("s4", "FORMAL_INVENTORY_NOT_REAL_TASK_COMPLETENESS")
        return guard("s4", action)

    def runner(_n, _s, _a):
        def action():
            if arms is None:
                state["work"][STEPS[6]] = "BLOCKED_TRUE_RUNTIME_NOT_PROVIDED"
            elif trusted_replay is None:
                state["work"][STEPS[6]] = (
                    "BLOCKED_UNTRUSTED_RAW_RECEIPTS_NO_REPLAY_AUTHORITY")
            else:
                raw = json.loads(arms.read_text())
                hidden = json.loads(gold.read_text())
                inputs = json.loads(public.read_text())
                result = replay_v2(raw, hidden, inputs, trusted_replay)
                require(result["source_bound_deterministic_replay_verified"]
                        and not result["original_AC18_pass_automatically"],
                        "G11_REPLAY_STRUCTURAL_GAINS_PROMOTED_TO_SCIENCE")
                state["audits"]["replay"] = {
                    "stages": result["replayed_stages"],
                    "oracle_gains_diagnostic_only":
                        result["recomputed_oracle_gains"],
                    "material_layers_diagnostic_only":
                        result["material_layers_diagnostic_only"],
                    "independent_oracle_custody_verified": False,
                }
                state["work"][STEPS[6]] = (
                    "STRUCTURAL_REPLAY_ONLY_EXTERNAL_PROVENANCE_NOT_ATTESTED")
            state["next"].append(
                "#61 independently sourced real LLM/EC/Oracle runtime "
                "receipts with output/code/model identity and Oracle blind custody")
            return done("runner", "STRUCTURAL_REPLAY_NOT_CAUSAL_SCIENCE")
        return guard("runner", action)

    def ae(_n, _s, _a):
        def action():
            state["work"][STEPS[7]] = (
                "BLOCKED_REAL_MATCHED_A_B_C_D_E"
                if arms is None else
                "UNQUALIFIED_TRACE_PRESENT_REAL_MATCHED_AE_NOT_ATTESTED")
            state["next"].append(
                "#9 genuine A/B/C/D and E_S1..E_S4 same-upstream executions, "
                "candidate-rank and closure metrics")
            return done("ae", "REAL_FOUR_LAYER_AE_NOT_YET_QUALIFIED")
        return guard("ae", action)

    def score(_n, _s, _a):
        def action():
            # Diagnostic gains from a replay must NEVER be treated as a
            # semantic model-vs-native causal localization.
            state["work"][STEPS[8]] = (
                "DIAGNOSTIC_GAIN_ONLY_NO_SCIENTIFIC_LOCALIZATION"
                if "replay" in state["audits"] else
                "BLOCKED_NO_GENUINE_LAYERWISE_METRICS")
            state["audits"]["score_policy"] = {
                "materiality_abs": plan["frozen_materiality_abs"],
                "dominance_tie_abs": plan["frozen_tie_abs"],
                "actual_dominant_layer": None,
                "reframing_recovery_measured": False,
                "false_closure_measured": False,
                "missed_reframe_measured": False,
            }
            return done("score", "NO_FALSE_END_TO_END_CAUSAL_ATTRIBUTION")
        return guard("score", action)

    def ac20(_n, _s, _a):
        def action():
            status = state["audits"]["old_AC20"]
            ledger = {}
            for ident in normative["order"]:
                parents = plan["original_ac_dependencies"][ident]
                missing_ac = [edge for edge in parents
                              if edge in status and status[edge] != "PASS"]
                work = plan["ac_work_gates"][ident]
                qualifying = status[ident] == "PASS"
                require(not qualifying or not missing_ac,
                        "G2_AC_CHILD_PASSED_WITH_UNMET_PARENT:" + ident)
                ledger[ident] = {
                    "state": status[ident],
                    "depends_on": parents,
                    "unmet_AC_parents": missing_ac,
                    "work_gate_dependencies": work,
                    "unqualified_work": [
                        gate for gate in work if not
                        state["work"].get(gate, "").startswith(
                            ("PASS_", "MODEL_ASSET_VERIFIED"))
                    ],
                    "MVP_required": ident in
                                    plan["original_mvp_required"],
                }
            require(len(ledger) == 20
                    and {k for k, v in ledger.items()
                         if v["state"] == "PASS"} == {"AC-19", "AC-20"},
                    "G11_MVP_AC_UNSUPPORTED_PROMOTION")
            # A machine gate may run and PASS operationally, but AC cannot
            # pass until independent, true causal experiment is validated.
            state["audits"]["AC20_dependency_ledger"] = ledger
            state["audits"]["AC_pass"] = 2
            state["audits"]["AC_unproven"] = [
                key for key in plan["original_mvp_required"]
                if ledger[key]["state"] != "PASS"
            ]
            require(len(state["audits"]["AC_unproven"]) == 16,
                    "G11_UNSUPPORTED_AC_COUNT")
            state["work"][STEPS[9]] = "PASS_DAG_RECOMPUTED_2_OF_18_ONLY"
            return done("ac20", "AC20_PARENT_GATES_AND_MVP18_RECHECKED")
        return guard("ac20", action)

    def exit_gate(_n, flags, _a):
        if not all(flags.get(x) is True for x in
                   ("source", "v12", "ac_dag", "model", "s3",
                    "s4", "runner", "ae", "score", "ac20")):
            return {"outcome": "original_ac_not_proven",
                    "evidence": ["INCOMPLETE_WORKFLOW_FROZEN_FAIL_CLOSED"]}
        state["work"][STEPS[10]] = "BLOCKED_ORIGINAL_AC_2_OF_18"
        return {"outcome": "external_S3_S4_missing",
                "evidence": ["ISSUES59_60_INDEPENDENCE_MISSING",
                             "ISSUE61_REAL_CAUSAL_CUSTODY_PENDING",
                             "ISSUE9_MATCHED_AE_UNDONE",
                             "ORIGINAL_AC_2_OF_18"]}

    executions = execute_graph(graph, {
        NODES[0]: source,
        NODES[1]: old,
        NODES[2]: dag,
        NODES[3]: model,
        NODES[4]: s3,
        NODES[5]: s4,
        NODES[6]: runner,
        NODES[7]: ae,
        NODES[8]: score,
        NODES[9]: ac20,
        NODES[10]: exit_gate,
    })
    require(executions.get("result") == "TERMINAL"
            and executions["terminal_id"] in
            ("blocked_semantics", "blocked_llm", "blocked_runner",
             "blocked_ae", "blocked_ac", "blocked_integrity"),
            "G11_UNQUALIFIED_ROOT_TERMINAL")
    recheck()
    if model_path is not None:
        require(digest_file(model_path) ==
                normative["norm"]["canonical_inputs"][
                    "qwen2_5_0_5b"]["sha256"],
                "G12_MODEL_SOURCE_CHANGED_DURING_EVALUATION")
    ac_ledger = state["audits"].get("AC20_dependency_ledger", {})
    return {
        "protocol": PROTOCOL,
        "original_issue": 1,
        "original_mvp": {"required": 18, "pass": 2, "unproven": 16,
                         "post_mvp": ["AC-10", "AC-18"]},
        "frozen_materiality_abs": 0.20,
        "TCC_nodes": len(graph["nodes"]),
        "TCC_edges": len(graph["edges"]),
        "TCC_terminal": executions["terminal_id"],
        "ECv4_handoff": to_ecv4_evidence(graph, executions),
        "issue_state_snapshot": plan["issue_state_snapshot"],
        "work_state_by_dependency": state["work"],
        "AC20_dependency_ledger": ac_ledger,
        "AC20_topological_order": normative["order"],
        "unproven_MVP_AC": state["audits"].get("AC_unproven"),
        "qualified_model_asset": state["audits"].get("model"),
        "optional_structural_replay": state["audits"].get("replay"),
        "actual_science_vs_diagnostic": state["audits"].get("score_policy"),
        "next_external_dependencies": list(dict.fromkeys(state["next"])),
        "source_git_blobs": pins_before,
        "source_and_user_data_seals_stable":
            pins_before == git_pins()
            and data_before == user_files_seal((arms, gold, public)),
        "errors": state["errors"],
        "scientific_phase1_complete": False,
        "no_background_or_Github_Actions": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tcc-root", type=Path, required=True)
    parser.add_argument("--old-native-root", type=Path, required=True)
    parser.add_argument("--policy-native-root", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--arms", type=Path)
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--public", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = run(
            args.tcc_root, args.old_native_root, args.policy_native_root,
            args.model, args.arms, args.gold, args.public)
        encoded = json.dumps(result, indent=2, sort_keys=True,
                             ensure_ascii=False) + "\n"
        if args.out:
            require(not args.out.is_symlink(), "G7_OUTPUT_SYMLINK")
            args.out.write_text(encoded)
            print(json.dumps({
                "TCC_terminal": result["TCC_terminal"],
                "original_AC": "2/18",
                "stages": len(result["work_state_by_dependency"]),
                "errors": result["errors"],
            }))
        else:
            print(encoded, end="")
        return 2 if not result["errors"] else 3
    except Exception as exc:
        print(json.dumps({
            "protocol": PROTOCOL,
            "terminal": "INTEGRITY_FAIL_CLOSED",
            "error": type(exc).__name__ + ":" + str(exc)[:250],
        }))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
