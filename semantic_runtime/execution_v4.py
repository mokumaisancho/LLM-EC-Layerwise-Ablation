"""V4 local-operator authorization. Caller controls IR/task/solver/policy_id, never policy source.

Trust assumption: installation directory and executing OS user are under the owner's
control. Same-UID malicious code or compromised deployment is outside this boundary.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from .runtime import RuntimeContractError, canonical_json
from .execution_v2 import execute_validated_ir

PROTOCOL = "SEMANTIC_RUNTIME_EXECUTION_V4"
POLICY_PROTOCOL = "SEMANTIC_RUNTIME_APPROVED_POLICY_V3"
POLICY_FILENAME = "approved_policy_v3.json"
MAX_POLICY_BYTES = 65536


def _deny(code: str) -> None:
    raise RuntimeContractError(code)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _trusted_policy() -> dict[str, Any]:
    """Read fixed installed policy via an owner-controlled directory fd, no symlinks."""
    pkg_dir = Path(__file__).parent
    directory_fd: int | None = None
    fd: int | None = None
    try:
        dirflags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        directory_fd = os.open(pkg_dir, dirflags)
        directory_info = os.fstat(directory_fd)
        uid = os.geteuid()
        if not stat.S_ISDIR(directory_info.st_mode) or directory_info.st_uid != uid:
            _deny("POLICY_DIRECTORY_OWNER_INVALID")
        if directory_info.st_mode & 0o022:
            _deny("POLICY_DIRECTORY_GROUP_OR_WORLD_WRITABLE")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(POLICY_FILENAME, flags, dir_fd=directory_fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != uid:
            _deny("TRUSTED_POLICY_OWNER_OR_TYPE_INVALID")
        if info.st_mode & 0o022:
            _deny("TRUSTED_POLICY_GROUP_OR_WORLD_WRITABLE")
        if not 0 < info.st_size <= MAX_POLICY_BYTES:
            _deny("TRUSTED_POLICY_SIZE_INVALID")
        chunks = []
        remaining = MAX_POLICY_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(8192, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        if remaining == 0:
            _deny("TRUSTED_POLICY_SIZE_INVALID")
        policy = json.loads(b"".join(chunks).decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _deny("TRUSTED_POLICY_OPEN_OR_PARSE_FAILED")
    finally:
        if fd is not None:
            os.close(fd)
        if directory_fd is not None:
            os.close(directory_fd)
    if not isinstance(policy, dict) or set(policy) != {"protocol", "approvals"}:
        _deny("TRUSTED_POLICY_INVALID")
    if policy["protocol"] != POLICY_PROTOCOL:
        _deny("TRUSTED_POLICY_PROTOCOL_INVALID")
    approvals = policy["approvals"]
    if not isinstance(approvals, list) or len(approvals) > 128:
        _deny("TRUSTED_POLICY_APPROVALS_INVALID")
    ids: set[str] = set()
    for item in approvals:
        if not isinstance(item, dict) or set(item) != {"policy_id", "task_sha256", "solver_sha256"}:
            _deny("TRUSTED_POLICY_APPROVAL_INVALID")
        policy_id = item["policy_id"]
        if not isinstance(policy_id, str) or not 1 <= len(policy_id) <= 128 or policy_id in ids:
            _deny("TRUSTED_POLICY_ID_INVALID")
        ids.add(policy_id)
        for key in ("task_sha256", "solver_sha256"):
            value = item[key]
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                _deny("TRUSTED_POLICY_DIGEST_INVALID")
    return policy


def execute_authorized_ir(
    ir: dict[str, Any], task_contract: dict[str, Any],
    solver_contract: dict[str, Any], policy_id: str,
) -> dict[str, Any]:
    """Only execute the exact operator-approved task/solver pair; no external I/O."""
    if not isinstance(policy_id, str) or not 1 <= len(policy_id) <= 128:
        _deny("POLICY_ID_REQUIRED")
    policy = _trusted_policy()
    approval = next((x for x in policy["approvals"] if x["policy_id"] == policy_id), None)
    if approval is None:
        _deny("POLICY_NOT_APPROVED")
    try:
        task_digest, solver_digest = _digest(task_contract), _digest(solver_contract)
    except (TypeError, ValueError, OverflowError) as exc:
        _deny("CONTRACT_CANONICALIZATION_INVALID")
    if task_digest != approval["task_sha256"]:
        _deny("TASK_NOT_APPROVED")
    if solver_digest != approval["solver_sha256"]:
        _deny("SOLVER_NOT_APPROVED")
    result = execute_validated_ir(ir, task_contract, solver_contract)
    return {"protocol": PROTOCOL, "policy_id": policy_id, "execution": result}
