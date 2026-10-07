"""V5 fail-closed grammar-bound execution for a finite, single-entity English command contract.

This is a constrained command parser, NOT open-ended natural language understanding.
No caller-provided grammar can authorize anything: grammar lives only in an owner-installed
trusted policy, and task and solver digests are checked before classification/execution.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from . import discovery
from .runtime import (
    RuntimeContractError, canonical_json, discover_and_ground,
    validate_semantic_ir, validate_task_contract,
)
from .execution_v2 import execute_validated_ir
from .execution_v4 import _digest

PROTOCOL = "SEMANTIC_RUNTIME_EXECUTION_V5"
POLICY_PROTOCOL = "SEMANTIC_RUNTIME_APPROVED_POLICY_V5"
GRAMMAR_PROTOCOL = "SEMANTIC_RUNTIME_EXPLICIT_GRAMMAR_V5"
POLICY_FILE = "approved_policy_v5.json"
TEMPLATE_RE = re.compile(r"^\{entity\} [a-z]+(?: [a-z]+){0,5}$")
MAX_POLICY_BYTES = 65536


def _fail(code: str) -> None:
    raise RuntimeContractError(code)


def _load_trusted_policy() -> dict[str, Any]:
    """Hardcoded package-relative file, O_NOFOLLOW, owner/permission checks."""
    package = Path(__file__).parent
    directory_fd = None
    file_fd = None
    try:
        directory_fd = os.open(package, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        directory_info = os.fstat(directory_fd)
        if not stat.S_ISDIR(directory_info.st_mode) or directory_info.st_uid != os.geteuid():
            _fail("POLICY_DIRECTORY_OWNER_INVALID")
        if directory_info.st_mode & 0o022:
            _fail("POLICY_DIRECTORY_WRITABLE_BY_OTHERS")
        file_fd = os.open(POLICY_FILE, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
        info = os.fstat(file_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
            _fail("POLICY_OWNER_TYPE_INVALID")
        if info.st_mode & 0o022:
            _fail("POLICY_WRITABLE_BY_OTHERS")
        if info.st_size < 1 or info.st_size > MAX_POLICY_BYTES:
            _fail("POLICY_SIZE_INVALID")
        data = os.read(file_fd, MAX_POLICY_BYTES + 1)
        if len(data) != info.st_size:
            _fail("POLICY_CONCURRENT_MUTATION_OR_OVERSIZE")
        policy = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail("POLICY_READ_FAILED")
    finally:
        if file_fd is not None: os.close(file_fd)
        if directory_fd is not None: os.close(directory_fd)
    if not isinstance(policy, dict) or set(policy) != {"protocol", "approvals"}:
        _fail("POLICY_FORMAT_INVALID")
    if policy["protocol"] != POLICY_PROTOCOL or not isinstance(policy["approvals"], list) or len(policy["approvals"]) > 64:
        _fail("POLICY_PROTOCOL_INVALID")
    seen = set()
    for item in policy["approvals"]:
        if not isinstance(item, dict) or set(item) != {"policy_id", "task_sha256", "solver_sha256", "grammar"}:
            _fail("POLICY_APPROVAL_FIELDS_INVALID")
        pid = item["policy_id"]
        if not isinstance(pid, str) or not 1 <= len(pid) <= 128 or pid in seen:
            _fail("POLICY_APPROVAL_ID_INVALID")
        seen.add(pid)
        for k in ("task_sha256", "solver_sha256"):
            d = item[k]
            if not isinstance(d, str) or len(d) != 64 or any(c not in "0123456789abcdef" for c in d):
                _fail("POLICY_DIGEST_INVALID")
        _validate_grammar_shape(item["grammar"])
    return policy


def _validate_grammar_shape(grammar: Any) -> None:
    if not isinstance(grammar, dict) or set(grammar) != {"protocol", "actions"} or grammar["protocol"] != GRAMMAR_PROTOCOL:
        _fail("GRAMMAR_PROTOCOL_INVALID")
    actions = grammar["actions"]
    if not isinstance(actions, list) or len(actions) != 2:
        _fail("GRAMMAR_EXACTLY_TWO_ACTIONS_REQUIRED")
    member_groups, templates, action_ids = [], [], []
    for item in actions:
        if not isinstance(item, dict) or set(item) != {"action_id", "training_members", "templates"}:
            _fail("GRAMMAR_ACTION_FIELDS_INVALID")
        aid = item["action_id"]
        members = item["training_members"]
        variants = item["templates"]
        if not isinstance(aid, str) or not aid or len(aid) > 64:
            _fail("GRAMMAR_ACTION_ID_INVALID")
        if not isinstance(members, list) or len(members) != 2 or len(set(members)) != 2 or any(not isinstance(x,str) for x in members):
            _fail("GRAMMAR_MEMBERS_INVALID")
        if not isinstance(variants, list) or not 1 <= len(variants) <= 16:
            _fail("GRAMMAR_TEMPLATES_INVALID")
        if any(not isinstance(v, str) or not TEMPLATE_RE.fullmatch(v) for v in variants):
            _fail("GRAMMAR_TEMPLATE_NONCANONICAL")
        member_groups.append(frozenset(members))
        templates.extend(variants)
        action_ids.append(aid)
    if len(set(action_ids)) != 2 or len(set(member_groups)) != 2 or len(set(templates)) != len(templates):
        _fail("GRAMMAR_DUPLICATE_ACTION_OR_TEMPLATE")


def _exact_template_matches(raw_text: str, entity_registry: dict[str, Any], grammar: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(entity_registry, dict) or len(entity_registry) != 1:
        return []
    value = next(iter(entity_registry.values()))
    typ = value["type"]
    masked = discovery.mask_entities(raw_text, entity_registry)
    matched = []
    for action in grammar["actions"]:
        for template in action["templates"]:
            expected = template.replace("{entity}", f"<{typ.lower()}>")
            if masked == expected:
                matched.append(action)
    return matched


def validate_grammar(task: dict[str, Any], grammar: dict[str, Any]) -> dict[str, str]:
    _validate_grammar_shape(grammar)
    visible = validate_task_contract(task)
    ir = discover_and_ground(task)
    slots_by_members = {frozenset(s["training_members"]): s["slot_id"] for s in ir["discovered_slots"]}
    members_by_id = {x["example_id"]: x for x in visible["training_examples"]}
    action_slots = {}
    member_union: set[str] = set()
    for action in grammar["actions"]:
        member_set = frozenset(action["training_members"])
        if member_set not in slots_by_members or member_union & member_set:
            _fail("GRAMMAR_ACTION_PARTITION_MISMATCH")
        member_union.update(member_set)
        for mid in member_set:
            member = members_by_id[mid]
            matches = _exact_template_matches(member["raw_text"], member["entity_registry"], grammar)
            if len(matches) != 1 or matches[0]["action_id"] != action["action_id"]:
                _fail("GRAMMAR_TRAINING_MEMBER_NOT_UNIQUE")
        action_slots[action["action_id"]] = slots_by_members[member_set]
    if member_union != set(members_by_id):
        _fail("GRAMMAR_TRAINING_COVERAGE_INVALID")
    return action_slots


def classify_explicit(task: dict[str, Any], grammar: dict[str, Any]) -> dict[str, Any]:
    """Every unknown, mixed, negated, translated, or unsupported phrase is abstained."""
    action_slots = validate_grammar(task, grammar)
    known = discover_and_ground(task)
    legacy_assignment = {x["example_id"]: x for x in known["heldout_assignments"]}
    output = []
    for example in task["visible"]["heldout_examples"]:
        eid = example["example_id"]
        matches = _exact_template_matches(example["raw_text"], example["entity_registry"], grammar)
        if len(matches) != 1:
            output.append({"example_id": eid, "status": "ABSTAIN_UNSUPPORTED_OR_AMBIGUOUS"})
            continue
        desired_slot = action_slots[matches[0]["action_id"]]
        actual = legacy_assignment.get(eid)
        if actual is None or actual["slot_id"] != desired_slot or actual["polarity"] != "POS" or actual["modality"] != "ASSERTED":
            output.append({"example_id": eid, "status": "ABSTAIN_GROUNDER_DISAGREEMENT"})
            continue
        entity_id = next(iter(example["entity_registry"]))
        if actual["arguments"] != [entity_id]:
            output.append({"example_id": eid, "status": "ABSTAIN_GROUNDER_ARGUMENT_MISMATCH"})
            continue
        output.append({"example_id": eid, "status": "EXPLICIT_MATCH", "slot_id": desired_slot, "action_id": matches[0]["action_id"]})
    return {"protocol": "SEMANTIC_RUNTIME_EXPLICIT_CLASSIFICATION_V5", "decisions": output}


def _approval(policy_id: str, task: dict[str, Any], solver: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy_id, str) or not 1 <= len(policy_id) <= 128:
        _fail("POLICY_ID_INVALID")
    item = next((x for x in _load_trusted_policy()["approvals"] if x["policy_id"] == policy_id), None)
    if item is None:
        _fail("POLICY_NOT_APPROVED")
    try:
        task_sha, solver_sha = _digest(task), _digest(solver)
    except (ValueError, TypeError, OverflowError):
        _fail("CONTRACT_SERIALIZATION_INVALID")
    if task_sha != item["task_sha256"]:
        _fail("TASK_NOT_APPROVED")
    if solver_sha != item["solver_sha256"]:
        _fail("SOLVER_NOT_APPROVED")
    return item


def classify_authorized(task: dict[str, Any], solver: dict[str, Any], policy_id: str) -> dict[str, Any]:
    item = _approval(policy_id, task, solver)
    return classify_explicit(task, item["grammar"])


def execute_authorized_ir(ir: dict[str, Any], task: dict[str, Any],
                          solver: dict[str, Any], policy_id: str) -> dict[str, Any]:
    item = _approval(policy_id, task, solver)
    decisions = classify_explicit(task, item["grammar"])["decisions"]
    target = solver.get("assignment_example_id")
    matches = [x for x in decisions if x["example_id"] == target]
    if len(matches) != 1 or matches[0]["status"] != "EXPLICIT_MATCH":
        _fail("EXECUTION_TARGET_NOT_EXPLICITLY_CLASSIFIED")
    validate_semantic_ir(ir, validate_task_contract(task))
    expected = discover_and_ground(task)
    if canonical_json(ir) != canonical_json(expected):
        _fail("IR_PROVENANCE_MISMATCH")
    result = execute_validated_ir(ir, task, solver)
    if result["slot_id"] != matches[0]["slot_id"]:
        _fail("EXECUTION_GROUNDER_SLOT_MISMATCH")
    return {"protocol": PROTOCOL, "policy_id": policy_id,
            "action_id": matches[0]["action_id"], "execution": result}
