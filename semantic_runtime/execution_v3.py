"""V3 operator-controlled policy gate; no caller-supplied policy paths.
Security boundary: installed package/its deployment is trusted, request data is not.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from .runtime import RuntimeContractError, canonical_json
from .execution_v2 import execute_validated_ir

POLICY_PATH = Path(__file__).with_name("approved_policy_v3.json")
PROTOCOL = "SEMANTIC_RUNTIME_EXECUTION_V3"
POLICY_PROTOCOL = "SEMANTIC_RUNTIME_APPROVED_POLICY_V3"

def _deny(reason: str) -> None:
    raise RuntimeContractError(reason)

def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def _trusted_policy() -> dict[str, Any]:
    # Intentionally never resolve an input path, environment variable, or request-provided policy.
    # Install and update only via the operator-controlled deployment; reject symlinks.
    if POLICY_PATH.is_symlink() or not POLICY_PATH.is_file():
        _deny("TRUSTED_POLICY_NOT_REGULAR_FILE")
    try:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _deny("TRUSTED_POLICY_UNREADABLE")
    if not isinstance(policy, dict) or set(policy) != {"protocol", "approvals"}:
        _deny("TRUSTED_POLICY_INVALID")
    if policy["protocol"] != POLICY_PROTOCOL or not isinstance(policy["approvals"], list):
        _deny("TRUSTED_POLICY_PROTOCOL_INVALID")
    for approval in policy["approvals"]:
        if not isinstance(approval,dict) or set(approval) != {"policy_id", "task_sha256", "solver_sha256"}:
            _deny("TRUSTED_APPROVAL_INVALID")
        if not isinstance(approval["policy_id"],str) or not approval["policy_id"]:
            _deny("TRUSTED_APPROVAL_ID_INVALID")
        for key in ("task_sha256","solver_sha256"):
            val=approval[key]
            if not isinstance(val,str) or len(val)!=64 or any(ch not in "0123456789abcdef" for ch in val):
                _deny("TRUSTED_APPROVAL_DIGEST_INVALID")
    if len({p["policy_id"] for p in policy["approvals"]})!=len(policy["approvals"]):
        _deny("TRUSTED_APPROVAL_ID_DUPLICATE")
    return policy

def execute_authorized_ir(ir: dict[str,Any], task_contract: dict[str,Any],
                          solver_contract: dict[str,Any], policy_id: str) -> dict[str,Any]:
    """Fail closed unless both supplied contracts match an installed operator-approved pair."""
    if not isinstance(policy_id,str) or not policy_id:
        _deny("POLICY_ID_REQUIRED")
    approval=next((a for a in _trusted_policy()["approvals"] if a["policy_id"]==policy_id),None)
    if approval is None:
        _deny("POLICY_NOT_APPROVED")
    if _digest(task_contract)!=approval["task_sha256"]:
        _deny("TASK_NOT_APPROVED")
    if _digest(solver_contract)!=approval["solver_sha256"]:
        _deny("SOLVER_NOT_APPROVED")
    result=execute_validated_ir(ir,task_contract,solver_contract)
    return {"protocol":PROTOCOL,"policy_id":policy_id,"execution":result}
