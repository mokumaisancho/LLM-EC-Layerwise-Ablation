#!/usr/bin/env python3
"""One-shot actual native TCC Generator v3 + Runtime v3 on authorized Mac.

Control-plane proof only. Never asserts S3/S4 scientific qualification or root MVP.
No local Git clone, global configuration, service modification, paid tools or models.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import quote

ISSUE_REPO = "mokumaisancho/LLM-EC-Layerwise-Ablation"
REF = "feat/issue1-independent-s4-authority-audit-v19"
TCC_PIN = "786d52c1efbc9271096f9311d768ef49bcd116e2"
TCC_ROOT = Path.home() / "Library/Application Support/InitiativeDispatcher/tcc-compiler"
PROOF = b"issue1-native-tcc-v3-blocked-external-2026-10-14\n"
PINS = {
    "ACCEPTANCE_CRITERIA.md": "40e4d41914fb17ee5c7deb0cfd32276a41c9a1fc",
    "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json": "08407bec73278aeda8ddd2d4d6efc810dadf46f9",
    "docs/ISSUE1_SINGLE_SOURCE_TRACKER_V5.json": "56bd5ac25d47e1dd9e8ea9da6193679656b661f5",
    "docs/ISSUE1_S4_SOURCE_BOUND_OBLIGATION_POINTERS_V20.json": "a78df93af631f07b284dc3c8c74594f6989fbb6b",
    "docs/ISSUE1_TCC_NATIVE_CONTRACT_V22.json": "__V22_BLOB__",
}
RESULT_FILE = Path("native-control-result.json")
PROOF_FILE = Path("proof.txt")


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256(obj) -> str:
    return "sha256:" + hashlib.sha256(canonical(obj)).hexdigest()


def fetch_pinned(path: str) -> bytes:
    uri = f"repos/{ISSUE_REPO}/contents/{path}?ref={quote(REF, safe='')}"
    proc = subprocess.run(["gh", "api", uri], capture_output=True, check=False, timeout=25)
    if proc.returncode:
        raise RuntimeError("GITHUB_READ_FAILED:" + path)
    obj = json.loads(proc.stdout)
    if obj.get("type") != "file" or obj.get("encoding") != "base64":
        raise ValueError("NON_FILE_OR_ENCODING:" + path)
    data = base64.b64decode(obj["content"], validate=False)
    if git_blob(data) != PINS[path] or obj.get("sha") != PINS[path]:
        raise ValueError("SOURCE_PIN_MISMATCH:" + path)
    return data


def run_git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(TCC_ROOT), *args],
                       check=True, capture_output=True, text=True, timeout=12)
    return r.stdout.strip()


def native_check() -> None:
    if not TCC_ROOT.is_dir() or not (TCC_ROOT / ".git").exists():
        raise RuntimeError("PINNED_HOST_TCC_NOT_INSTALLED")
    if run_git("rev-parse", "HEAD") != TCC_PIN:
        raise ValueError("HOST_TCC_COMMIT_MISMATCH")
    if run_git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("HOST_TCC_TRACKED_TREE_DIRTY")
    for path in ["tcc/__init__.py", "tcc/core_v3.py", "tcc/runtime_v3.py",
                 "tcc/recipe_builder_v3.py", "tcc/generator_v3.py",
                 "tcc/suite_context.py", "tcc/suite_boundary.py",
                 "tcc/binding_generator_v3.py", "tcc/bindings_v3.py"]:
        source = TCC_ROOT / path
        if source.is_symlink() or not source.resolve().is_relative_to(TCC_ROOT.resolve()):
            raise ValueError("UPSTREAM_FILE_ESCAPE")
        expected = subprocess.run(
            ["git", "-C", str(TCC_ROOT), "show", TCC_PIN + ":" + path],
            capture_output=True, check=True, timeout=12
        ).stdout
        if source.read_bytes() != expected:
            raise ValueError("UPSTREAM_SOURCE_MISMATCH:" + path)


def build_context(spec: dict, fingerprint: str, node_fields: set[str]) -> dict:
    fields = ["tcc_id", "goal", "acceptance", "state_keys",
              "immutable_state_keys", "entry_nodes"]
    vals = [("/" + field, spec[field]) for field in fields]
    for node in spec["nodes"]:
        esc = node["id"].replace("~", "~0").replace("/", "~1")
        vals.extend((f"/nodes/{esc}/{field}", node[field]) for field in sorted(node_fields))
    facts = [{
        "fact_id": "declared:" + hashlib.sha256(path.encode()).hexdigest()[:20],
        "path": path, "value": value,
        "evidence_refs": ["ev:git-pinned-source"],
    } for path, value in vals]
    return {
        "schema": "suite.tcc-context.v0", "snapshot_id": "ISSUE1-SNAPSHOT-V22",
        "source_fingerprint": fingerprint, "base_source_fingerprint": fingerprint,
        "annotation_basis_fingerprint": fingerprint, "selected_issue_id": "ISSUE-1",
        "actionable_issue_ids": ["ISSUE-1"], "blocked_issue_ids": [],
        "discovered_issues": [], "blocked_nodes": [],
        "evidence_refs": ["ev:git-pinned-source"],
        "ordering_rule": None, "ordering_rule_refs": [], "ordering_scope_issue_ids": [],
        "cross_issue_effects": [], "resource_conflicts": [], "resource_policy": None,
        "resource_policy_refs": [], "acceptance_couplings": [],
        "normalization_complete": True, "scope_expanded": False,
        "evidence_sufficient": True, "undeclared_judgment": False,
        "decision_needed": "read-only native TCC audit; no ECv4 scientific closure",
        "negative_assertion_refs": {
            k: ["ev:git-pinned-source"] for k in
            ("cross_issue_effects", "resource_conflicts", "acceptance_couplings",
             "scope_expanded", "undeclared_judgment")
        }, "semantic_facts": facts,
    }


def write_result(doc: dict) -> None:
    pending = RESULT_FILE.with_suffix(".json.tmp")
    pending.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                       encoding="utf-8")
    os.replace(pending, RESULT_FILE)


def main() -> int:
    # No user absolute-path or arbitrary-command input. Only registered fixed operation.
    status = {
        "schema": "ISSUE1_NATIVE_TCC_CONTROL_RECEIPT_V22",
        "root_issue": 1, "scientific_mvp_passed": 2,
        "scientific_mvp_required": 18, "scientific_ac_promoted": 0,
        "mac_expensive_model_execution": False, "native_generator_invoked": False,
        "native_runtime_invoked": False, "tcc_upstream_pin": TCC_PIN,
        "scope": "control-only original science held BLOCKED_EXTERNAL",
        "status": "IN_PROGRESS",
    }
    try:
        data = {path: fetch_pinned(path) for path in PINS}
        spec_bundle = json.loads(data["docs/ISSUE1_TCC_NATIVE_CONTRACT_V22.json"])
        original = json.loads(data["docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json"])
        tracker = json.loads(data["docs/ISSUE1_SINGLE_SOURCE_TRACKER_V5.json"])
        v20 = json.loads(data["docs/ISSUE1_S4_SOURCE_BOUND_OBLIGATION_POINTERS_V20.json"])
        if (len(original["mvp"]["required_ac"]) != 18
            or tracker["current_outcome"]["root_original_AC_PASSED"] != 2
            or tracker["project"]["root_issue"] != 1
            or v20["summary"]["tasks"] != 164):
            raise ValueError("FROZEN_AC_OR_GOLD_STATE_DRIFT")
        if not (tracker["tasks"][4]["id"] == "D04"
                and tracker["tasks"][4]["status"] == "BLOCKED_EXTERNAL"):
            # Do not rely on ordering if tracker evolves: explicit lookup below.
            if next(x for x in tracker["tasks"] if x["id"] == "D04")["status"] != "BLOCKED_EXTERNAL":
                raise ValueError("S3_QUALIFICATION_STATE_DRIFT")
        task_by_id = {x["id"]: x for x in tracker["tasks"]}
        d04 = task_by_id["D04"]["status"] == "BLOCKED_EXTERNAL"
        d05 = task_by_id["D05"]["status"] == "BLOCKED_EXTERNAL"
        if not (d04 and d05):
            raise ValueError("SCIENCE_GATE_CHANGED_REQUIRES_NEW_QUALIFICATION")
        if v20["scope_limits"]["domain_policy_semantic_exhaustiveness_proven"] is not False:
            raise ValueError("S4_ATTESTATION_DRIFT")
        if not all(case["real_task_close_authorized"] is False for case in v20["cases"]):
            raise ValueError("CASE_S4_UNTRUSTED_CLOSE_FLAG")
        native_check()
        sys.path.insert(0, str(TCC_ROOT))
        from tcc.core_v3 import NODE_FIELDS, validate_spec, compile_spec, canonical_json
        from tcc.recipe_builder_v3 import generate_tcc_from_context
        from tcc.runtime_v3 import execute_graph

        spec = spec_bundle["spec"]
        errors = validate_spec(spec)
        status["native_validator_invoked"] = True
        if errors:
            raise ValueError("NATIVE_TCC_SPEC_INVALID:" + ",".join(errors))
        context = build_context(spec, sha256({"pins": PINS, "spec": spec}), NODE_FIELDS)
        generated = generate_tcc_from_context(context, current_tcc_id=spec["tcc_id"])
        status["native_generator_invoked"] = True
        status["generator_result"] = generated.get("result")
        if generated.get("result") != "tcc.spec.v3":
            raise ValueError("NATIVE_GENERATION_FAILED:" + str(generated.get("reason_code")))
        if canonical_json(generated["spec"]) != canonical_json(spec):
            raise ValueError("GENERATOR_DERIVED_SPEC_DRIFT")
        graph = compile_spec(generated["spec"])
        status["graph_spec_hash"] = graph["spec_hash"]

        def action(node, state, attempt):
            id_ = node["id"]
            if id_ == "D00_PINNED_PREFLIGHT":
                return {"status": "success", "writes": {"source_ok": True},
                        "evidence": ["actual-source-pins-5-verified"]}
            if id_ == "D04_INDEPENDENT_S3_GATE":
                return {"status": "success", "writes": {"d04_qualified": False},
                        "evidence": ["issue-59-no-independent-heldout-custody"]}
            if id_ == "D05_INDEPENDENT_S4_GATE":
                return {"status": "success", "writes": {"d05_qualified": False},
                        "evidence": ["issue-60-publisher-gold-not-independent-full-obligations"]}
            return {"status": "failure", "evidence": ["NO_REAL_TARGET_ONLY_EXECUTOR_BOUND"]}

        def authority_gate(node, state, attempt):
            allowed = bool(state.get("source_ok")) and state.get("d04_qualified") is True and state.get("d05_qualified") is True
            return {"outcome": "qualified" if allowed else "unqualified",
                    "evidence": ["S3-S4-external-custody-qualified:" + str(allowed)]}

        handlers = {
            node["id"]: (authority_gate if node["kind"] == "gate" else action)
            for node in spec["nodes"] if node["kind"] in ("gate", "action")
        }
        result = execute_graph(graph, handlers)
        status["native_runtime_invoked"] = True
        status["runtime"] = result
        if (result.get("result") != "TERMINAL"
            or result.get("terminal_id") != "BLOCK_EXTERNAL"
            or result.get("terminal_status") != "BLOCKED"
            or result.get("ecv4_closure") != "NOT_DECIDED"
            or result.get("state", {}).get("d04_qualified") is not False
            or result.get("state", {}).get("d05_qualified") is not False
            or any(x.get("node_id", "").startswith(("D06_", "D07_", "D08_", "D09_"))
                   for x in result.get("evidence", []))):
            raise ValueError("SCIENTIFIC_TERMINAL_NOT_FAIL_CLOSED")
        status["status"] = "NATIVE_TCC_CONTROL_PASS_SCIENCE_BLOCKED_EXTERNAL"
        write_result(status)
        # Only native generator+validator+runtime evidence creates this marker.
        PROOF_FILE.write_bytes(PROOF)
        if PROOF_FILE.read_bytes() != PROOF:
            raise ValueError("PROOF_BYTES_MISMATCH")
        print(json.dumps({
            "control_status": status["status"], "root_science_ac_pass": 2,
            "native_generator": True, "native_runtime": True,
            "graph_spec_hash": graph["spec_hash"],
            "result_sha256": hashlib.sha256(RESULT_FILE.read_bytes()).hexdigest(),
            "proof_sha256": hashlib.sha256(PROOF).hexdigest(),
        }, sort_keys=True))
        return 0
    except Exception as exc:
        status["status"] = "BLOCKED_HOST_OR_CONTRACT"
        status["error_type"] = type(exc).__name__
        status["error_code"] = str(exc)[:300]
        write_result(status)
        PROOF_FILE.unlink(missing_ok=True)
        print(json.dumps({
            "control_status": status["status"],
            "error_type": status["error_type"], "error_code": status["error_code"]
        }, sort_keys=True))
        return 3


if __name__ == "__main__":
    sys.exit(main())
