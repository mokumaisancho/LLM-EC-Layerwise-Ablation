#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

PROTOCOL = "PHASE1_EC_NATIVE_ADAPTER_V1"
EC_NATIVE_NOT_APPLICABLE = "EC_NATIVE_NOT_APPLICABLE"
EC_NATIVE = "EC_NATIVE"
STATUS = "INCOMPATIBLE"
PINNED_EC_REPO = "mokumaisancho/GPT-EC-Closure-Engine"
PINNED_EC_COMMIT = "d5ec423968f1c9242c590e5e77ccfd92d1f59eb2"

# This adapter is intentionally fail-closed. It qualifies which frozen Phase1
# subfunctions are actually isomorphic to ECv4.4; it does not simulate missing
# EC authority with harness-local rules.
_FORBIDDEN_RUNTIME_KEYS = {
    "hidden", "evaluation", "oracle_constraints", "gold", "expected",
    "acceptable_selected_candidate_ids", "acceptable_closure_classes",
    "forbidden_selections", "forbidden_closure_classes",
}


class OracleLeakageError(ValueError):
    pass


class ECNativeScopeIncompatible(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def assert_oracle_blind(value: Any, path: str = "$" ) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            norm = str(key).strip().lower()
            if norm in _FORBIDDEN_RUNTIME_KEYS or norm.startswith("oracle_"):
                raise OracleLeakageError(f"ORACLE_FIELD_FORBIDDEN:{path}.{key}")
            assert_oracle_blind(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            assert_oracle_blind(child, f"{path}[{i}]")


def subfunction_authority() -> dict[str, dict[str, Any]]:
    return {
        "s3_reframing": {
            "authority": EC_NATIVE,
            "ec_protocols": ["EC_V4_4_RESIDUAL_DETECTOR_V1", "EC_V4_4_FRAMING_SEARCH_V1"],
            "reportable": True,
            "evidence": "results/phase1_ecv44_reframe_actual_2026-10-03.json",
        },
        "s3_selection": {
            "authority": EC_NATIVE_NOT_APPLICABLE,
            "reportable": False,
            "reason": "EC_NEXT_ACTION_AUTHORITY_IS_SINGLETON_BUT_PHASE1_S3_REQUIRES_ADMISSIBLE_SET_SELECTION",
            "evidence_issue": 27,
            "counterexamples": ["M003", "M009"],
        },
        "s4_closure": {
            "authority": EC_NATIVE_NOT_APPLICABLE,
            "reportable": False,
            "reason": "FROZEN_S3_INTERFACE_DOES_NOT_IDENTIFY_CLOSURE_STATE",
            "evidence_issue": 28,
            "structural_upper_bound": 0.8,
        },
    }


def qualify_runtime_inputs(task: dict[str, Any], upstream: dict[str, Any]) -> dict[str, Any]:
    """Oracle-blind identity guard for any attempted adapter invocation.

    Qualification never transforms the persisted upstream artifact. Because the
    frozen full S3/S4 scope is incompatible, callers must stop at P2 rather than
    synthesize an EC answer.
    """
    task_before = canonical_hash(task)
    upstream_before = canonical_hash(upstream)
    task_copy = copy.deepcopy(task)
    upstream_copy = copy.deepcopy(upstream)
    assert_oracle_blind(task_copy)
    assert_oracle_blind(upstream_copy)
    task_after = canonical_hash(task)
    upstream_after = canonical_hash(upstream)
    if task_before != task_after or upstream_before != upstream_after:
        raise RuntimeError("UPSTREAM_MUTATION_DETECTED")
    return {
        "protocol": PROTOCOL,
        "status": STATUS,
        "oracle_blind": True,
        "input_identity": {
            "task_sha256_before": task_before,
            "task_sha256_after": task_after,
            "upstream_sha256_before": upstream_before,
            "upstream_sha256_after": upstream_after,
            "unchanged": True,
        },
        "subfunction_authority": subfunction_authority(),
        "terminal_state": "EC_NATIVE_SCOPE_INCOMPATIBLE",
    }


def qualification_document() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "status": STATUS,
        "oracle_blind": True,
        "ec_source": {"repository": PINNED_EC_REPO, "commit": PINNED_EC_COMMIT},
        "subfunction_authority": subfunction_authority(),
        "identity_contract": {
            "mode": "NO_TRANSFORM_FAIL_CLOSED",
            "upstream_mutation_allowed": False,
            "oracle_hidden_fields_allowed": False,
        },
        "qualification_evidence": {
            "s3_selection": {
                "ec_test": "01_repo/tests/test_ec_next_action_authority.py::test_ec_selects_exactly_one_next_action",
                "phase1_schema": "schemas/s3_selected_reframed_state.schema.json",
                "phase1_multi_select_fixtures": ["M003", "M009"],
                "issue": 27,
            },
            "s4_closure": {
                "phase1_schema": "schemas/s4_closure_execution_result.schema.json",
                "collisions": [
                    {"signature": "selected=1,rejected=1,reframe=false,residuals=[]", "close": ["M001","M002","M004","M006","M008","M010"], "continue": ["M007"]},
                    {"signature": "selected=2,rejected=1,reframe=false,residuals=[]", "close": ["M009"], "continue": ["M003"]}
                ],
                "structural_upper_bound": 0.8,
                "issue": 28,
            },
            "s3_reframing": {
                "actual_accuracy": 0.9,
                "result": "results/phase1_ecv44_reframe_actual_2026-10-03.json",
                "divergence_issue": 26,
            },
        },
        "terminal_state": "EC_NATIVE_SCOPE_INCOMPATIBLE",
        "github_actions_used": False,
    }


def _self_test() -> None:
    task = {"fixture_id": "SELFTEST", "intent": {"goal": "x"}}
    upstream = {"schema_version": "S3_SEMANTIC_STATE_V1", "state": {"x": 1}}
    before = (canonical_hash(task), canonical_hash(upstream))
    out = qualify_runtime_inputs(task, upstream)
    after = (canonical_hash(task), canonical_hash(upstream))
    assert before == after
    assert out["status"] == "INCOMPATIBLE"
    assert out["subfunction_authority"]["s3_selection"]["authority"] == EC_NATIVE_NOT_APPLICABLE
    assert out["subfunction_authority"]["s4_closure"]["authority"] == EC_NATIVE_NOT_APPLICABLE
    try:
        qualify_runtime_inputs(task, {"oracle_constraints": {"gold": True}})
    except OracleLeakageError:
        pass
    else:
        raise AssertionError("oracle leakage must fail closed")


if __name__ == "__main__":
    _self_test()
    print(json.dumps(qualification_document(), ensure_ascii=False, indent=2))
