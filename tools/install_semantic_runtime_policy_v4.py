#!/usr/bin/env python3
"""Operator-only offline approval installer, for a private local runtime bundle.

This is an administrative tool, not a service endpoint; never accept remote
approval requests. Requires explicit bundle path and task/solver files.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from semantic_runtime.execution_v4 import _digest
from semantic_runtime.runtime import RuntimeContractError, validate_task_contract, discover_and_ground
from semantic_runtime.execution_v2 import _solver_contract

POLICY_NAME = "approved_policy_v3.json"
POLICY_PROTOCOL = "SEMANTIC_RUNTIME_APPROVED_POLICY_V3"


def install(bundle_dir: Path, policy_id: str, task: dict, solver: dict) -> dict:
    if not isinstance(policy_id, str) or not 1 <= len(policy_id) <= 128:
        raise RuntimeContractError("INVALID_POLICY_ID")
    validate_task_contract(task)
    discover_and_ground(task)
    _solver_contract(solver)
    if not bundle_dir.is_dir() or bundle_dir.is_symlink():
        raise RuntimeContractError("INVALID_BUNDLE_DIRECTORY")
    ds = bundle_dir.stat(follow_symlinks=False)
    if ds.st_uid != os.geteuid() or ds.st_mode & 0o022:
        raise RuntimeContractError("UNTRUSTED_BUNDLE_DIRECTORY")
    required = (bundle_dir / "execution_v4.py", bundle_dir / "__init__.py", bundle_dir / POLICY_NAME)
    if any(p.is_symlink() or not p.is_file() for p in required):
        raise RuntimeContractError("UNTRUSTED_BUNDLE_CONTENTS")
    policy_path = bundle_dir / POLICY_NAME
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if not isinstance(policy,dict) or policy.get("protocol") != POLICY_PROTOCOL or policy.get("approvals") != [] or set(policy) != {"protocol","approvals"}:
        raise RuntimeContractError("BUNDLE_MUST_BE_DEFAULT_DENY_BEFORE_INSTALL")
    policy["approvals"] = [{"policy_id": policy_id, "task_sha256": _digest(task),
                            "solver_sha256": _digest(solver)}]
    data = (json.dumps(policy,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
    fd = None
    temp = bundle_dir / (".approved_policy_v4_" + uuid.uuid4().hex)
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os,"O_NOFOLLOW",0), 0o600)
        with os.fdopen(fd,"wb") as output:
            fd = None
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, policy_path)
        dirfd = os.open(bundle_dir, os.O_RDONLY | getattr(os,"O_DIRECTORY",0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if fd is not None:
            os.close(fd)
        if temp.exists():
            temp.unlink()
    return {"status": "OPERATOR_POLICY_INSTALLED", "policy_id": policy_id,
            "task_sha256": _digest(task), "solver_sha256": _digest(solver),
            "install_mode": "ATOMIC_0600", "scope": "LOCAL_OPERATOR_BUNDLE_ONLY"}


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--bundle-dir", type=Path, required=True)
    p.add_argument("--policy-id", required=True)
    p.add_argument("--task", type=Path, required=True)
    p.add_argument("--solver", type=Path, required=True)
    a=p.parse_args()
    try:
        task=json.loads(a.task.read_text(encoding="utf-8"))
        solver=json.loads(a.solver.read_text(encoding="utf-8"))
        print(json.dumps(install(a.bundle_dir,a.policy_id,task,solver),sort_keys=True))
        return 0
    except (RuntimeContractError,OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({"terminal":"FAIL_CLOSED","reason":str(e)}),file=sys.stderr)
        return 3


if __name__=="__main__":
    raise SystemExit(main())
