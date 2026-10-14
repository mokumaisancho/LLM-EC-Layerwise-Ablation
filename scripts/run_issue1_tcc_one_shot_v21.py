#!/usr/bin/env python3
"""Fail-closed native tcc-compiler v3 entrypoint for research Issue #1.

Requires an authorized, PINNED tcc-compiler checkout. No implicit cloning,
network search, paid jobs, GitHub Actions, local device control or LLM model run.
A BLOCKED terminal preserves the scientific issue's open status.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/ISSUE1_TCC_ONE_SHOT_CONTRACT_AND_EXECUTION_V21.json"
RESULT = ROOT / "results/issue1_tcc_native_v21.json"
TCC_PIN = "902a62c640c7ab568431b6b25c41a020c039c504"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256(obj):
    return "sha256:" + hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def git_value(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.DEVNULL).strip()


def source_gate(doc):
    pins = {
        "ACCEPTANCE_CRITERIA.md": doc["source"]["frozen_ac_blob"],
        "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json": doc["source"]["frozen_mvp_blob"],
        "docs/ISSUE1_SINGLE_SOURCE_TRACKER_V5.json": doc["source"]["tracker_blob"],
        "docs/ISSUE1_S4_SOURCE_BOUND_OBLIGATION_POINTERS_V20.json": doc["source"]["v20_inventory_blob"],
    }
    diffs = []
    for rel, want in pins.items():
        path = ROOT / rel
        if not path.is_file():
            diffs.append("MISSING:" + rel)
            continue
        got = git_value(ROOT, "hash-object", rel)
        if got != want:
            diffs.append("SOURCE_MISMATCH:" + rel)
    return diffs


def facts_for(spec, fields):
    top = ("tcc_id", "goal", "acceptance", "state_keys", "immutable_state_keys", "entry_nodes")
    items = [("/" + key, spec[key]) for key in top]
    for node in spec["nodes"]:
        node_id = node["id"].replace("~", "~0").replace("/", "~1")
        for key in sorted(fields):
            items.append((f"/nodes/{node_id}/{key}", node[key]))
    facts = []
    for path, value in items:
        facts.append({
            "fact_id": "declared:" + hashlib.sha256(path.encode()).hexdigest()[:20],
            "path": path,
            "value": value,
            "evidence_refs": ["ev:verified_contract"],
        })
    return facts


def build_context(spec, source_fingerprint, node_fields):
    return {
        "schema": "suite.tcc-context.v0",
        "snapshot_id": "ISSUE1-CONTROL-AUDIT-V21",
        "source_fingerprint": source_fingerprint,
        "base_source_fingerprint": source_fingerprint,
        "annotation_basis_fingerprint": source_fingerprint,
        "selected_issue_id": "ISSUE-1",
        "actionable_issue_ids": ["ISSUE-1"],
        "blocked_issue_ids": [],
        "discovered_issues": [],
        "blocked_nodes": [],
        "evidence_refs": ["ev:verified_contract"],
        "ordering_rule": None,
        "ordering_rule_refs": [],
        "ordering_scope_issue_ids": [],
        "cross_issue_effects": [],
        "resource_conflicts": [],
        "resource_policy": None,
        "resource_policy_refs": [],
        "acceptance_couplings": [],
        "normalization_complete": True,
        "scope_expanded": False,
        "evidence_sufficient": True,
        "undeclared_judgment": False,
        "decision_needed": "none: read-only science evidence audit, no global ECv4 closure",
        "negative_assertion_refs": {
            k: ["ev:verified_contract"] for k in
            ("cross_issue_effects", "resource_conflicts", "acceptance_couplings",
             "scope_expanded", "undeclared_judgment")
        },
        "semantic_facts": facts_for(spec, node_fields),
    }


def write_result(obj):
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
    result = {
        "schema": "ISSUE1_NATIVE_TCC_RUN_V21",
        "root_issue": 1,
        "mvp_ac_passed_before_run": 2,
        "mvp_ac_required": 18,
        "native_generator_invoked": False,
        "native_runtime_invoked": False,
        "science_ac_promoted": 0,
        "scientific_closure_authorized": False,
    }
    errors = source_gate(doc)
    if errors:
        result.update(status="INTEGRITY_FAILED", errors=errors)
        write_result(result)
        return 2
    source = os.environ.get("TCC_COMPILER_PATH", "")
    if not source or not Path(source).is_dir():
        result.update(status="BLOCKED_NATIVE_TCC_CHECKOUT_MISSING",
                      reason="Set TCC_COMPILER_PATH to an authorized checkout pinned at 902a62c.")
        write_result(result)
        return 3
    if git_value(source, "rev-parse", "HEAD") != TCC_PIN:
        result.update(status="INTEGRITY_FAILED", reason="UNPINNED_TCC_COMPILER")
        write_result(result)
        return 2
    sys.path.insert(0, str(Path(source).resolve()))
    from tcc.core_v3 import NODE_FIELDS, compile_spec, validate_spec
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.runtime_v3 import execute_graph

    spec = doc["spec"]
    errs = validate_spec(spec)
    if errs:
        result.update(status="INVALID_TCC_SPEC", errors=errs)
        write_result(result)
        return 2
    context = build_context(spec, sha256({"pins": doc["source"], "spec": spec}), NODE_FIELDS)
    generated = generate_tcc_from_context(context, current_tcc_id=spec["tcc_id"])
    result["native_generator_invoked"] = True
    result["generator_result"] = generated.get("result")
    if generated.get("result") != "tcc.spec.v3":
        result.update(status="GENERATOR_FAIL_CLOSED", generator_reason=generated.get("reason_code"),
                      generator_errors=generated.get("errors", []))
        write_result(result)
        return 3
    graph = compile_spec(generated["spec"])
    prior = doc["execution"]
    qualified04 = prior["proofs"]["D04"]["qualified"] is True
    qualified05 = prior["proofs"]["D05"]["qualified"] is True
    source_ok = prior["proofs"]["D00"] == "PASS"
    def action(node, state, attempt):
        key = node["id"]
        if key == "D00_SOURCE_AND_AC_PREFLIGHT":
            return {"status": "success" if source_ok else "failure",
                    "writes": {"precheck_ok": source_ok} if source_ok else {},
                    "evidence": ["verified-source-git-blobs"]}
        if key == "D04_INDEPENDENT_S3":
            return {"status": "success", "writes": {"d04_qualified": qualified04,
                    "d04_evidence": "BLOCKED_EXTERNAL" if not qualified04 else "QUALIFIED"},
                    "evidence": ["issue59-independent-gold-gate"]}
        if key == "D05_COMPLETE_S4":
            return {"status": "success", "writes": {"d05_qualified": qualified05,
                    "d05_evidence": "BLOCKED_EXTERNAL" if not qualified05 else "QUALIFIED"},
                    "evidence": ["issue60-independent-obligation-gate"]}
        # A scientific experiment must be supplied by a separately qualified real executor.
        # Declared no-op handlers are forbidden.
        return {"status": "failure", "evidence": ["REAL_TARGET_ONLY_EXECUTOR_NOT_BOUND"]}

    def authority_gate(node, state, attempt):
        selected = "ready" if state["precheck_ok"] and state["d04_qualified"] and state["d05_qualified"] else "external_missing"
        return {"outcome": selected, "evidence": ["genuine-external-authority-gate:" + selected]}

    handlers = {
        node["id"]: (authority_gate if node["kind"] == "gate" else action)
        for node in generated["spec"]["nodes"] if node["kind"] in {"action", "gate"}
    }
    actual = execute_graph(graph, handlers)
    result["native_runtime_invoked"] = True
    result["runtime_result"] = actual
    result["tcc_graph_spec_hash"] = graph["spec_hash"]
    result["status"] = "NATIVE_TCC_BLOCKED_EXTERNAL" if actual.get("terminal_status") == "BLOCKED" else "NATIVE_TCC_" + str(actual.get("result"))
    write_result(result)
    return 3 if actual.get("terminal_status") == "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
