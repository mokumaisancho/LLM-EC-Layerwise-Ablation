#!/usr/bin/env python3
"""Issue #1/#57/#58: read-only TCC Generator v3 boundary for real four-arm evidence.

Never treats a sealed hash, operator statement or historical fixture as a scientific
certificate. All code/results live in this repository; tcc-compiler is read-only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TCC_SOURCE = "786d52c1efbc9271096f9311d768ef49bcd116e2"
REQUIREMENTS = (
    ("gold", "Independent unseen public corpus and adjudicated precommitted private gold"),
    ("original_llm", "Genuine source-pinned LLM0 raw output for precisely the same public cases"),
    ("matched_v4", "Real V1/V4/V5 execution with identical input/task/policy constraints"),
    ("raw_seal", "Time-ordered four-arm raw output seal before gold reveal"),
    ("independent_review", "Independent review of unseenness, provenance and chronology"),
    ("ablation", "Upstream-frozen, controlled V5 grammar gate subtraction evidence"),
)
REFS = {
    "issue1": "https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/1",
    "issue57": "https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/57",
    "issue58": "https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/58",
    "blind_v2": "evaluation/BLIND_FOUR_ARM_METHOD_V2.md",
    "prior_checkpoint": "results/issue57_conservation_gate_verification_2026-10-09.json",
    "compiler_pin": "https://github.com/mokumaisancho/tcc-compiler/commit/" + TCC_SOURCE,
}
ALL_FIELDS = (
    "id", "kind", "depends_on", "reads", "writes", "branches", "failure_target",
    "destructive", "rollback", "idempotent", "max_attempts", "retry_guard",
    "terminal_status", "join_gate", "join_inputs", "compensation_actions",
    "rollback_order", "compensated_target", "loop_max_iterations", "loop_exhausted_target",
)

def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()

def node(name, kind, *, depends=(), branches=None, failure=None, reads=(), writes=(), terminal=None):
    return {
        "id": name, "kind": kind, "depends_on": list(depends),
        "reads": list(reads), "writes": list(writes), "branches": branches or {},
        "failure_target": failure, "destructive": False, "rollback": None,
        "idempotent": True, "max_attempts": 1, "retry_guard": None,
        "terminal_status": terminal, "join_gate": None, "join_inputs": {},
        "compensation_actions": [], "rollback_order": [], "compensated_target": None,
        "loop_max_iterations": None, "loop_exhausted_target": None,
    }

def make_spec():
    steps = ["method"] + [name for name, _ in REQUIREMENTS]
    entries = [node("run_method_preflight", "action", writes=["method_passed"],
                    failure="blocked_method_preflight")]
    for i, name in enumerate(steps):
        next_target = steps[i + 1] if i + 1 < len(steps) else "ready_for_external_qualification"
        if next_target in steps:
            next_target += "_gate"
        entries.append(node(name + "_gate", "gate", branches={"pass": next_target, "fail": "blocked_" + name},
                            depends=("run_method_preflight",) if i == 0 else (),
                            reads=("method_passed",) if i == 0 else ()))
    entries.extend([
        node("ready_for_external_qualification", "terminal", terminal="SUCCESS"),
        node("blocked_method_preflight", "terminal", terminal="BLOCKED"),
        *(node("blocked_" + name, "terminal", terminal="BLOCKED") for name in steps),
    ])
    spec = {
        "schema": "tcc.spec.v3",
        "tcc_id": "ISSUE57-BLIND-FOUR-ARM-EVIDENCE-CHAIN-V1",
        "goal": "Origin #1: scientifically meaningful four-arm retention and controlled gate ablation, no fabricated outputs",
        "acceptance": [
            "All four genuine matched-arm raw outputs on new unseen cases, after gold precommit",
            "Independent custody and gold disclosure after output seal",
            "Critical and tail retention, contrast pairs and abstention separated",
            "Controlled layer/gate ablation with identical upstream outputs",
            "Never certify independent provenance from self-attestation or hashes alone",
            "Issue #1/#57/#58 remain open until independent scientific evidence exists",
        ],
        "state_keys": ["method_passed"], "immutable_state_keys": [],
        "entry_nodes": ["run_method_preflight"], "nodes": entries,
    }
    return spec

def context_for(spec, source_commit):
    evidence_refs = ["ev:" + k for k in REFS]
    facts = []
    def add(path, value):
        fact_name = hashlib.sha256(path.encode()).hexdigest()[:16]
        facts.append({"fact_id": "fact:" + fact_name, "path": path, "value": value,
                      "evidence_refs": evidence_refs})
    for key in ("tcc_id", "goal", "acceptance", "state_keys", "immutable_state_keys", "entry_nodes"):
        add("/" + key, spec[key])
    for item in spec["nodes"]:
        for field in ALL_FIELDS:
            add("/nodes/" + item["id"] + "/" + field, item[field])
    neg = {"cross_issue_effects": ["ev:issue1"],
           "resource_conflicts": ["ev:issue1"],
           "acceptance_couplings": ["ev:issue57"],
           "scope_expanded": ["ev:issue1"],
           "undeclared_judgment": ["ev:issue57"]}
    return {
        "schema": "suite.tcc-context.v0",
        "snapshot_id": "ISSUE57-CHECKPOINT:" + source_commit[:16],
        "source_fingerprint": "sha256:" + sha({"source_commit": source_commit, "refs": REFS, "spec": spec}),
        "base_source_fingerprint": "sha256:" + sha({"source_commit":source_commit,"basis":"issue1-57-58"}),
        "annotation_basis_fingerprint": "sha256:" + sha({"source_commit":source_commit,"basis":"issue1-57-58"}),
        "selected_issue_id": "ISSUE-57",
        "actionable_issue_ids": ["ISSUE-57"],
        "blocked_issue_ids": ["ISSUE-58"],
        "discovered_issues": [], "blocked_nodes": [],
        "evidence_refs": evidence_refs,
        "ordering_rule": None, "ordering_rule_refs": [], "ordering_scope_issue_ids": [],
        "cross_issue_effects": [], "resource_conflicts": [],
        "resource_policy": None, "resource_policy_refs": [],
        "acceptance_couplings": [],
        "normalization_complete": True, "scope_expanded": False,
        "evidence_sufficient": True, "undeclared_judgment": False,
        "decision_needed": "none", "negative_assertion_refs": neg,
        "semantic_facts": facts, "semantic_proposals": [],
    }

def audit():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/audit_issue58_suite_ecv4.py")],
        cwd=ROOT, capture_output=True, text=True, timeout=90,
        env=None,
    )
    try:
        value = json.loads(proc.stdout)
    except ValueError:
        value = {}
    counts = value.get("runtime", {}).get("test_counts", {})
    acceptable = (
        proc.returncode == 0 and value.get("pass") is True
        and value.get("suite", {}).get("pass") is True
        and value.get("ecv4", {}).get("pass") is True
        and sum(counts.values()) >= 45
        and counts.get("blind_evaluator", 0) >= 24
        and counts.get("three_stage_cli", 0) >= 5
        and counts.get("legacy_retention", 0) >= 16
    )
    return acceptable, {"returncode": proc.returncode, "checks": counts,
                        "suite_pass": value.get("suite", {}).get("pass"),
                        "ecv4_pass": value.get("ecv4", {}).get("pass"),
                        "terminal": value.get("terminal"),
                        "error_tail": proc.stderr[-300:]}

def run(tcc_root: Path, source_commit: str):
    head = subprocess.run(["git", "-C", str(tcc_root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, timeout=10)
    if head.returncode != 0 or head.stdout.strip() != TCC_SOURCE:
        raise RuntimeError("TCC_SOURCE_PIN_MISMATCH")
    if str(tcc_root) not in sys.path:
        sys.path.insert(0, str(tcc_root))
    from tcc.recipe_builder_v3 import build_recipe_from_context, generate_tcc_from_context
    from tcc.core_v3 import validate_spec, compile_spec, normalize_spec
    from tcc.runtime_v3 import execute_graph, to_ecv4_evidence
    spec = make_spec()
    context = context_for(spec, source_commit)
    built = build_recipe_from_context(context)
    if built.get("result") != "suite.tcc-generation-recipe.v4":
        raise RuntimeError("TCC_BUILDER_BLOCKED:" + json.dumps(built, ensure_ascii=False)[:900])
    generated = generate_tcc_from_context(context)
    if generated.get("result") != "tcc.spec.v3":
        raise RuntimeError("TCC_GENERATION_BLOCKED:" + json.dumps(generated, ensure_ascii=False)[:900])
    material = generated["spec"]
    if validate_spec(material):
        raise RuntimeError("TCC_SPEC_INVALID:" + str(validate_spec(material)))
    if material != normalize_spec(spec):
        raise RuntimeError("TCC_GENERATOR_SEMANTIC_DRIFT")
    graph = compile_spec(material)
    method_pass, method_evidence = audit()
    # External evidence requirements are deliberately NOT auto-certified.
    # No arbitrary local JSON can prove who adjudicated gold or whether it was unseen.
    evidence_available = {name: False for name, _ in REQUIREMENTS}
    blockers = {
        name: {"status": "UNVERIFIED_EXTERNAL_EVIDENCE",
               "requirement": description}
        for name, description in REQUIREMENTS
    }
    def method_handler(_node, _state, _attempt):
        return {
            "status": "success" if method_pass else "failure",
            "writes": {"method_passed": True} if method_pass else {},
            "evidence": ["audit_issue58:" + ("PASS" if method_pass else "FAIL")],
        }
    def gate_handler(name):
        def handler(_node, state, _attempt):
            good = state.get("method_passed") is True if name == "method" else evidence_available[name]
            return {"outcome": "pass" if good else "fail",
                    "evidence": ["gate:" + name + ":" + ("PASS" if good else "UNVERIFIED")]}
        return handler
    handlers = {"run_method_preflight": method_handler}
    handlers.update({name + "_gate": gate_handler(name)
                     for name in ["method"] + [name for name, _ in REQUIREMENTS]})
    executed = execute_graph(graph, handlers)
    if executed.get("result") != "TERMINAL" or executed.get("terminal_status") not in ("BLOCKED", "SUCCESS"):
        raise RuntimeError("TCC_EXECUTION_FAILED:" + json.dumps(executed, ensure_ascii=False)[:900])
    if executed["terminal_status"] == "SUCCESS":
        raise RuntimeError("TCC_UNEXPECTED_FALSE_SCIENTIFIC_SUCCESS")
    chain = to_ecv4_evidence(graph, executed)
    return {
        "protocol": "ISSUE57_TCC_GENERATOR_GATE_V1",
        "origin_issue": 1, "parent": 57, "audit": 58,
        "research_repo": "mokumaisancho/LLM-EC-Layerwise-Ablation",
        "source_commit": source_commit,
        "tcc_compiler_ref": TCC_SOURCE,
        "tcc_reference_read_only": True,
        "generator_result": generated["result"],
        "recipe_result": built["result"],
        "recipe_id": built["recipe"]["recipe_id"],
        "source_fingerprint": context["source_fingerprint"],
        "spec_hash": graph["spec_hash"],
        "compiled_node_count": len(graph["nodes"]),
        "compiled_edge_count": len(graph["edges"]),
        "generator_semantic_drift": False,
        "method_preflight": method_evidence,
        "method_pass": method_pass,
        "evidence_gate": {key: blockers[key] for key in blockers},
        "tcc_runtime": {"result": executed["result"],
                        "terminal_status": executed["terminal_status"],
                        "terminal_id": executed["terminal_id"],
                        "event_count": len(executed["evidence"]),
                        "events": executed["evidence"]},
        "ecv4_handoff": chain,
        "ecv4_closure_authorized": False,
        "scientific_four_arm_actual": "NOT_RUN",
        "non_degradation_established": False,
        "stop_state": "EXTERNAL_INDEPENDENT_GOLD_REQUIRED",
        "next_action": "Supply independently adjudicated unseen corpus and separately held gold commitments. Freeze genuine same-case LLM0/V1/V4/V5 outputs before disclosure; externally verify provenance; controlled intervention only after that."
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tcc-root", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    try:
        result = run(args.tcc_root, args.source_commit)
    except Exception as exc:
        print(json.dumps({"protocol": "ISSUE57_TCC_GENERATOR_GATE_V1",
                          "stop_state": "TCC_FAIL_CLOSED", "error": str(exc)},
                         ensure_ascii=False, sort_keys=True))
        return 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["method_pass"] else 3

if __name__ == "__main__":
    raise SystemExit(main())
