from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

EXPECTED_V4_REF = "f0f2d4a8634a130b710a326072438a51428929a3"
ROLLBACK_V4_REF = "c0cad551ca09f645ebe608bae4086de2e6f58bfd"
EXPECTED_V3_REF = "c847e967523a22444a30251fdbd1962adf56e16a"
LOCK_FILE = "SUITE_V4_CONFIGURATION_LOCK_CANDIDATE.json"

R3_CONTROLS = (
    "runtime_revision_watermark",
    "same_revision_state_digest_consistency",
    "plan_disposition_binding",
    "completed_descendant_criticality_filter",
    "explicit_stateful_v4_control_plane",
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"INVALID_JSON:{path.name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{path.name}")
    return value


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _constant(path: Path, name: str) -> str | None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name:
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
    return None


def _method(tree: ast.Module, class_name: str, method_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                    return item
    return None


def _has_arg(fn: ast.FunctionDef | ast.AsyncFunctionDef | None, name: str) -> bool:
    if fn is None:
        return False
    return name in {arg.arg for arg in [*fn.args.args, *fn.args.kwonlyargs]}


def _forwards_keyword(fn: ast.FunctionDef | ast.AsyncFunctionDef | None, name: str) -> bool:
    if fn is None:
        return False
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == name and isinstance(kw.value, ast.Name) and kw.value.id == name:
                    return True
    return False


def _expect(reasons: list[str], code: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        reasons.append(code)


def evaluate(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    active = _read_json(root / "SUITE_ACTIVE_RUNTIME.json")
    manifest = _read_json(root / "SUITE_V4_MANIFEST_CANDIDATE.json")
    config = _read_json(root / "ECV4_SUITE_CANDIDATE.json")
    lock = _read_json(root / LOCK_FILE)
    adapter_path = root / "src" / "ec_v4_adapter.py"
    contract_path = root / "src" / "ec_v4_candidate_contract.py"
    adapter_tree = ast.parse(adapter_path.read_text(encoding="utf-8"), filename=str(adapter_path))
    reasons: list[str] = []

    lock_ec = lock.get("ec_v4") or {}
    refs = {
        "ACTIVE": ((active.get("ec_v4") or {}).get("ref")),
        "MANIFEST": ((manifest.get("ec") or {}).get("ref")),
        "CONFIG": ((config.get("ec") or {}).get("ref")),
        "LOCK": lock_ec.get("ref"),
        "ADAPTER": _constant(adapter_path, "EXPECTED_V4_REF"),
        "CONTRACT": _constant(contract_path, "EXPECTED_V4_REF"),
    }
    for name, value in refs.items():
        _expect(reasons, f"V4_REF_MISMATCH:{name}", value, EXPECTED_V4_REF)

    rollback_refs = {
        "ACTIVE": ((active.get("ec_v4") or {}).get("rollback_ref")),
        "MANIFEST": ((manifest.get("ec") or {}).get("rollback_ref")),
        "CONFIG": ((config.get("ec") or {}).get("rollback_ref")),
        "LOCK": lock_ec.get("rollback_ref"),
        "CONTRACT": _constant(contract_path, "EXPECTED_V4_ROLLBACK_REF"),
    }
    for name, value in rollback_refs.items():
        _expect(reasons, f"ROLLBACK_REF_MISMATCH:{name}", value, ROLLBACK_V4_REF)

    v3_refs = {
        "ACTIVE": active.get("qualified_v3_inner_ref"),
        "MANIFEST": ((manifest.get("ec") or {}).get("qualified_v3_parent")),
        "CONFIG": ((config.get("ec") or {}).get("qualified_v3_parent")),
        "LOCK": lock_ec.get("qualified_v3_parent"),
    }
    for name, value in v3_refs.items():
        _expect(reasons, f"V3_INNER_REF_MISMATCH:{name}", value, EXPECTED_V3_REF)

    _expect(reasons, "LOCK_SCHEMA_MISMATCH", lock.get("schema_version"), 4)
    _expect(reasons, "LOCK_MODE_MISMATCH", lock.get("mode"), "FAIL_CLOSED")
    _expect(reasons, "LOCK_STATUS_MISMATCH", lock.get("status"), "V4_R3_ATOMIC_REPIN_LOCK")
    _expect(reasons, "LOCK_LOAD_REQUIREMENT_MISMATCH", lock.get("required_on_candidate_load"), True)

    authority = manifest.get("authority_model") or {}
    lock_authority = lock.get("authority") or {}
    _expect(reasons, "ACTIVE_GENERATION_MISMATCH", active.get("active_generation"), "V4")
    _expect(reasons, "ACTIVE_ARCHITECTURE_MISMATCH", active.get("architecture"), "V4_OUTER_CONTROL_OVER_QUALIFIED_V3_INNER_RUNTIME")
    _expect(reasons, "ACTIVE_CLOSURE_AUTHORITY_MISMATCH", active.get("inner_closure_authority"), "GPT-EC-V3")
    for subject, prefix in ((authority, "MANIFEST_AUTHORITY"), (lock_authority, "LOCK_AUTHORITY")):
        _expect(reasons, f"{prefix}_ACTIVE_GENERATION_MISMATCH", subject.get("active_generation"), "V4")
        _expect(reasons, f"{prefix}_OUTER_CONTROL_MISMATCH", subject.get("outer_control_authority"), "GPT-EC-V4:V4ControlPlane")
        _expect(reasons, f"{prefix}_OUTER_PROTOCOL_MISMATCH", subject.get("outer_control_protocol"), "EC_V4_CONTROL_PLANE_V1")
        _expect(reasons, f"{prefix}_CLOSURE_AUTHORITY_MISMATCH", subject.get("closure_authority"), "GPT-EC-V3")
        _expect(reasons, f"{prefix}_WORKER_SELF_CLOSE_MISMATCH", subject.get("worker_self_close_allowed"), False)
        _expect(reasons, f"{prefix}_DERIVED_AUTHORITY_MISMATCH", subject.get("derived_components_authoritative"), False)
    _expect(reasons, "MANIFEST_OUTER_REF_MISMATCH", authority.get("outer_control_exact_ref"), EXPECTED_V4_REF)
    _expect(reasons, "MANIFEST_STATEFUL_SCOPE_MISMATCH", authority.get("stateful_outer_control_scope"), "EXPLICIT_RUNTIME_INSTANCE")

    if active.get("production_ready") is not False:
        reasons.append("ACTIVE_RUNTIME_INVARIANT_MISMATCH")
    routing = manifest.get("routing") or {}
    if routing.get("exact_operation_binding") is not True:
        reasons.append("MANIFEST_ROUTING_INVARIANT_MISMATCH")
    if routing.get("raw_project_io_bypass_allowed") is not False or routing.get("generic_run_argv_enabled") is not False:
        reasons.append("MANIFEST_IO_ROUTING_INVARIANT_MISMATCH")

    controls = manifest.get("v4_controls") or {}
    compatibility = config.get("compatibility") or {}
    for key in (
        "dynamic_frontier",
        "decision_bound_evidence",
        "external_authority_resolution",
        "dynamic_state_authority_forwarding",
        "relevance_authority_forwarding",
        "v3_static_fallback",
        *R3_CONTROLS,
    ):
        _expect(reasons, f"V4_CONTROL_REQUIRED:{key}", controls.get(key), True)
    for key in ("dynamic_state_authority_forwarding", "relevance_authority_forwarding", *R3_CONTROLS):
        _expect(reasons, f"CONFIG_COMPATIBILITY_REQUIRED:{key}", compatibility.get(key), True)

    actual_invariants = {
        "runtime_stage": manifest.get("runtime_stage"),
        "production_ready": manifest.get("production_ready"),
        "exact_operation_binding": routing.get("exact_operation_binding"),
        "dynamic_frontier": controls.get("dynamic_frontier"),
        "decision_bound_evidence": controls.get("decision_bound_evidence"),
        "external_authority_resolution": controls.get("external_authority_resolution"),
        "dynamic_state_authority_forwarding": controls.get("dynamic_state_authority_forwarding"),
        "relevance_authority_forwarding": controls.get("relevance_authority_forwarding"),
        "v3_static_fallback": controls.get("v3_static_fallback"),
        **{key: controls.get(key) for key in R3_CONTROLS},
    }
    required_invariants = lock.get("required_invariants") or {}
    if not isinstance(required_invariants, Mapping) or not required_invariants:
        reasons.append("LOCK_REQUIRED_INVARIANTS_MISSING")
    else:
        for key, expected in required_invariants.items():
            _expect(reasons, f"LOCK_REQUIRED_INVARIANT_MISMATCH:{key}", actual_invariants.get(key), expected)

    select_fn = _method(adapter_tree, "ECV4SuiteBridge", "select_next_action")
    prior_fn = _method(adapter_tree, "ECV4SuiteBridge", "evaluate_prior_art")
    if not _has_arg(select_fn, "dynamic_state_authority"):
        reasons.append("DYNAMIC_STATE_AUTHORITY_ARGUMENT_MISSING")
    if not _forwards_keyword(select_fn, "dynamic_state_authority"):
        reasons.append("DYNAMIC_STATE_AUTHORITY_NOT_FORWARDED")
    if not _has_arg(prior_fn, "relevance_authority"):
        reasons.append("RELEVANCE_AUTHORITY_ARGUMENT_MISSING")
    if not _forwards_keyword(prior_fn, "relevance_authority"):
        reasons.append("RELEVANCE_AUTHORITY_NOT_FORWARDED")

    file_integrity = lock.get("file_integrity") or {}
    if not isinstance(file_integrity, Mapping) or not file_integrity:
        reasons.append("LOCK_FILE_INTEGRITY_MISSING")
    else:
        for relative, expected_sha in file_integrity.items():
            path = (root / str(relative)).resolve()
            if path != root and root not in path.parents:
                reasons.append(f"LOCK_PATH_ESCAPE:{relative}")
            elif not path.is_file():
                reasons.append(f"LOCKED_FILE_MISSING:{relative}")
            elif _git_blob_sha1(path) != expected_sha:
                reasons.append(f"LOCKED_FILE_DRIFT:{relative}")

    required_evidence = lock.get("required_evidence") or ()
    if not required_evidence:
        reasons.append("LOCK_REQUIRED_EVIDENCE_MISSING")
    for relative in required_evidence:
        path = root / str(relative)
        if not path.is_file():
            reasons.append(f"REQUIRED_EVIDENCE_MISSING:{relative}")
            continue
        evidence = _read_json(path)
        if not str(evidence.get("status") or "").startswith("PASS"):
            reasons.append(f"REQUIRED_EVIDENCE_NOT_PASS:{relative}")
        if ((evidence.get("ec_v4") or {}).get("ref")) != EXPECTED_V4_REF:
            reasons.append(f"REQUIRED_EVIDENCE_REF_MISMATCH:{relative}")
        if evidence.get("canonical_experimental_repin_authorized") is not True:
            reasons.append(f"REQUIRED_EVIDENCE_AUTHORIZATION_MISMATCH:{relative}")
        if evidence.get("integrated_cases_passed") != evidence.get("integrated_cases_total"):
            reasons.append(f"REQUIRED_EVIDENCE_INTEGRATED_CASES_MISMATCH:{relative}")

    passed = not reasons
    return {
        "protocol": "SUITE_V4_ATOMIC_REPIN_GATE_V4",
        "status": "PASS" if passed else "BLOCKED",
        "reasons": reasons,
        "v4_ref": EXPECTED_V4_REF,
        "rollback_ref": ROLLBACK_V4_REF,
        "v3_inner_ref": EXPECTED_V3_REF,
        "lock_integrity_verified": passed,
        "authority_forwarding_verified": passed,
        "r3_state_binding_verified": passed,
        "canonical_switch_authorized": passed,
        "production_ready": False,
    }


__all__ = ["evaluate"]
