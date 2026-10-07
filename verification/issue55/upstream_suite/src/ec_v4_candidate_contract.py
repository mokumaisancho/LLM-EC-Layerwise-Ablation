from __future__ import annotations

from typing import Any, Mapping

EXPECTED_SUITE_BASE = "8c5e24edc610116ca6da2e925796490a464b274c"
EXPECTED_V3_PARENT = "c847e967523a22444a30251fdbd1962adf56e16a"
EXPECTED_V4_REF = "f0f2d4a8634a130b710a326072438a51428929a3"
EXPECTED_V4_ROLLBACK_REF = "c0cad551ca09f645ebe608bae4086de2e6f58bfd"
EXPECTED_V4_BRANCH = "GPT-EC-V4"
EXPECTED_EC_REPO = "mokumaisancho/GPT-EC-Closure-Engine"


class ECV4CandidateContractError(ValueError):
    pass


def validate_ec_v4_candidate(candidate: Mapping[str, Any], *, qualified_suite_manifest: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if candidate.get("schema_version") != 2:
        reasons.append("BAD_CANDIDATE_SCHEMA")
    if candidate.get("status") != "EXPERIMENTAL_PINNED_CANDIDATE":
        reasons.append("BAD_CANDIDATE_STATUS")
    if candidate.get("suite_base_ref") != EXPECTED_SUITE_BASE:
        reasons.append("SUITE_BASE_REF_MISMATCH")

    ec = candidate.get("ec") or {}
    expected_ec = {
        "generation": "V4",
        "repo": EXPECTED_EC_REPO,
        "branch": EXPECTED_V4_BRANCH,
        "ref": EXPECTED_V4_REF,
        "rollback_ref": EXPECTED_V4_ROLLBACK_REF,
        "qualified_v3_parent": EXPECTED_V3_PARENT,
    }
    for key, expected in expected_ec.items():
        if ec.get(key) != expected:
            reasons.append(f"EC_V4_{key.upper()}_MISMATCH")

    compatibility = candidate.get("compatibility") or {}
    required_compatibility = (
        "v3_gateway_preserved",
        "v3_permit_contract_preserved",
        "v3_postflight_contract_preserved",
        "v3_human_utility_final_gate_preserved",
        "authority_hardening_r2",
        "dynamic_state_authority_forwarding",
        "relevance_authority_forwarding",
        "runtime_revision_watermark",
        "same_revision_state_digest_consistency",
        "plan_disposition_binding",
        "completed_descendant_criticality_filter",
        "explicit_stateful_v4_control_plane",
    )
    for key in required_compatibility:
        if compatibility.get(key) is not True:
            reasons.append(f"COMPATIBILITY_REQUIRED:{key}")
    if compatibility.get("new_outer_control_protocol") != "EC_V4_CONTROL_PLANE_V1":
        reasons.append("V4_OUTER_CONTROL_PROTOCOL_MISMATCH")

    invariants = candidate.get("suite_invariants") or {}
    if invariants.get("github_actions_enabled") is not False:
        reasons.append("GITHUB_ACTIONS_MUST_REMAIN_DISABLED")
    if invariants.get("exact_operation_binding") is not True:
        reasons.append("EXACT_OPERATION_BINDING_REQUIRED")
    if invariants.get("worker_self_close_allowed") is not False:
        reasons.append("WORKER_SELF_CLOSE_MUST_REMAIN_FALSE")
    if invariants.get("derived_components_authoritative") is not False:
        reasons.append("DERIVED_COMPONENTS_MUST_REMAIN_NON_AUTHORITATIVE")
    if invariants.get("production_ready") is not False:
        reasons.append("V4_CANDIDATE_MUST_NOT_CLAIM_PRODUCTION_READY")

    components = qualified_suite_manifest.get("components") or {}
    v3 = components.get("GPT-EC-V3") or {}
    if v3.get("ref") != EXPECTED_V3_PARENT:
        reasons.append("QUALIFIED_SUITE_V3_PIN_DRIFT")
    routing = qualified_suite_manifest.get("routing") or {}
    if routing.get("github_actions_enabled") is not False:
        reasons.append("QUALIFIED_SUITE_ACTIONS_DRIFT")
    if routing.get("exact_operation_binding") is not True:
        reasons.append("QUALIFIED_SUITE_OPERATION_BINDING_DRIFT")

    evidence = candidate.get("required_candidate_evidence") or {}
    for key in (
        "ec_runtime_qualification",
        "ec_r2_delta_qualification",
        "post_layout_requalification",
        "ec_r3_integrated_qualification",
    ):
        if not str(evidence.get(key) or "").strip():
            reasons.append(f"CANDIDATE_EVIDENCE_REQUIRED:{key}")

    return {
        "status": "PASS" if not reasons else "BLOCKED",
        "reasons": reasons,
        "v4_ref": ec.get("ref"),
        "rollback_ref": ec.get("rollback_ref"),
        "qualified_v3_ref": v3.get("ref"),
        "main_pin_change_authorized": not reasons,
        "next_gate": "ATOMIC_V4_R3_REPIN_QUALIFICATION",
    }


__all__ = [
    "ECV4CandidateContractError",
    "EXPECTED_SUITE_BASE",
    "EXPECTED_V3_PARENT",
    "EXPECTED_V4_REF",
    "EXPECTED_V4_ROLLBACK_REF",
    "validate_ec_v4_candidate",
]
