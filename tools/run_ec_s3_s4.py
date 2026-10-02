#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

EC_V4_4_REPO = "mokumaisancho/GPT-EC-Closure-Engine"
EC_V4_4_COMMIT = "d5ec423968f1c9242c590e5e77ccfd92d1f59eb2"
EC_V4_4_PROTOCOL = "EC_V4_4_RESIDUAL_DETECTOR_V1"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=10,
        ).strip()
    except Exception as exc:
        raise RuntimeError(f"EC_GIT_HEAD_UNAVAILABLE:{type(exc).__name__}") from exc


def load_ecv44(repo_root: Path):
    repo_root = repo_root.resolve()
    head = git_head(repo_root)
    if head != EC_V4_4_COMMIT:
        raise RuntimeError(f"EC_COMMIT_MISMATCH:{head}")

    module_path = repo_root / "01_repo" / "src" / "v4" / "ec_residual_detector.py"
    if not module_path.is_file():
        raise RuntimeError("EC_RESIDUAL_DETECTOR_MISSING")

    spec = importlib.util.spec_from_file_location("llm_ec_pinned_ec_residual_detector", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("EC_MODULE_SPEC_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    protocol = getattr(mod, "PROTOCOL", None)
    if protocol != EC_V4_4_PROTOCOL:
        raise RuntimeError(f"EC_PROTOCOL_MISMATCH:{protocol}")
    if not callable(getattr(mod, "detect_residuals", None)):
        raise RuntimeError("EC_DETECT_RESIDUALS_MISSING")

    ec_provenance = {
        "repository": EC_V4_4_REPO,
        "commit": head,
        "protocol": protocol,
        "module_path": "01_repo/src/v4/ec_residual_detector.py",
        "module_sha256": file_sha256(module_path),
        "reportable": True,
    }
    return mod, ec_provenance


def select_candidates(candidate_set: dict) -> tuple[list[str], list[str], list[dict]]:
    selected, rejected, reasons = [], [], []
    for candidate in candidate_set.get("candidates", []):
        cid = candidate.get("candidate_id")
        evidence = [x for x in candidate.get("evidence_refs", []) if str(x).strip()]
        dependencies = [x for x in candidate.get("dependencies", []) if str(x).strip()]
        admitted = bool(evidence and dependencies)
        if admitted:
            selected.append(cid)
            reasons.append({"candidate_id": cid, "decision": "SELECT", "rule": "EVIDENCE_AND_DEPENDENCY_PRESENT"})
        else:
            rejected.append(cid)
            reasons.append({"candidate_id": cid, "decision": "REJECT", "rule": "EVIDENCE_OR_DEPENDENCY_MISSING"})
    return selected, rejected, reasons


def ec_residuals(state: dict, ec_mod):
    result = ec_mod.detect_residuals(
        state["intent"],
        state["framing"],
        observations=state.get("observations", []),
    )
    protocol = result.get("protocol")
    if protocol != EC_V4_4_PROTOCOL:
        raise RuntimeError(f"EC_RUNTIME_PROTOCOL_MISMATCH:{protocol}")
    return result.get("residuals", [])


def selected_relation(candidate_set: dict, selected: list[str]):
    selected_set = set(selected)
    if len(selected_set) < 2:
        return None
    for group in candidate_set.get("relation_groups", []):
        ids = set(group.get("candidate_ids", []))
        if selected_set <= ids:
            return group.get("relation_type")
    return None


def closure_decision(candidate_set: dict, selected: list[str], state: dict, residuals: list[dict]):
    ops = {
        c.get("candidate_id"): (c.get("semantic_transition") or {}).get("operation")
        for c in candidate_set.get("candidates", [])
    }
    selected_ops = [ops.get(cid) for cid in selected]
    relation = selected_relation(candidate_set, selected)

    if len(selected) > 1 and relation == "COMPETING":
        return "CONTINUE", [{"type": "MULTIPLE_COMPETING_ADMISSIBLE_BRANCHES"}]
    if len(selected) > 1 and relation not in {"EQUIVALENT"}:
        return "CONTINUE", [{"type": "MULTIPLE_UNRESOLVED_ADMISSIBLE_BRANCHES"}]
    if any("unresolved" in str(v.get("semantic_key", "")).lower() for v in state["framing"]["variables"].values()):
        return "CONTINUE", [{"type": "REQUIRED_CONDITION_UNRESOLVED"}]
    if residuals and any(str(op).startswith(("ADD_", "REFRAME_")) for op in selected_ops if op):
        return "CLOSE", []
    if residuals:
        return "CONTINUE", residuals
    return "CLOSE", []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="fixtures/phase1_v2/generated")
    ap.add_argument("--out", default="results/ec_s3_s4")
    ap.add_argument("--ec-repo-root", default=os.environ.get("EC_V4_4_REPO_ROOT"))
    args = ap.parse_args()

    if not args.ec_repo_root:
        raise SystemExit("EC_V4_4_REPO_ROOT is required; reportable EC runs are fail-closed")

    ec_mod, ec_provenance = load_ecv44(Path(args.ec_repo_root))
    root, out_root = Path(args.root), Path(args.out)
    rows = []

    for fixture in sorted(p for p in root.iterdir() if p.is_dir()):
        s2 = load_json(fixture / "oracle" / "s2_candidate_set.json")
        state = load_json(fixture / "upstream" / "s3_semantic_state.json")
        selected, rejected, reasons = select_candidates(s2)
        residuals = ec_residuals(state, ec_mod)
        reframe = bool(residuals)
        closure, closure_residuals = closure_decision(s2, selected, state, residuals)
        result = {
            "fixture_id": fixture.name,
            "implementation": "EC",
            "ec_mode": "ECV4_4_REPORTABLE",
            "ec_protocol": EC_V4_4_PROTOCOL,
            "ec_provenance": ec_provenance,
            "upstream": {
                "candidate_set_hash": s2.get("content_hash"),
                "semantic_state_hash": state.get("content_hash"),
            },
            "s3": {
                "selected_candidate_ids": selected,
                "rejected_candidate_ids": rejected,
                "decision_reasons": reasons,
                "residuals": residuals,
                "reframe_required": reframe,
            },
            "s4": {
                "closure_class": closure,
                "residuals": closure_residuals,
                "selected_relation": selected_relation(s2, selected),
            },
        }
        out = out_root / (fixture.name + ".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows.append(result)

    print(json.dumps({
        "run": "EC_S3_S4",
        "fixture_count": len(rows),
        "result_count": len(rows),
        "ec_provenance": ec_provenance,
        "status": "PASS_REPORTABLE",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
