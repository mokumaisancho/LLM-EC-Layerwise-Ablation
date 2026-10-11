"""Research-local optional EC S3/S4 extension; frozen ECv4.4 stays unchanged."""
import hashlib
import importlib.util
import subprocess
from pathlib import Path

PROTOCOL = "PHASE1_S3_S4_LOCAL_EC_PLUGIN_V1"
COMMIT = "3f435ad4365d846d96264458540efb4848ce3541"
SOURCES = {
    "set": ("01_repo/src/v4/ec_layerwise_admissible_set_closure_v1.py",
            "c12e4743c89221a9b81a2f2fa98c4df9d61d72b2"),
    "policy": ("01_repo/src/v4/ec_layerwise_source_policy_authority_v2.py",
               "7da0cd8d876505cafdd5a9811132427e2f441a14"),
}

def file_blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() +
                        b"\0" + data).hexdigest()

def check_source(root):
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=12)
    if result.returncode or result.stdout.strip() != COMMIT:
        raise ValueError("PLUGIN_EC_COMMIT_MISMATCH")
    for name, (relative, blob) in SOURCES.items():
        p = root / relative
        if not p.is_file() or p.is_symlink() or file_blob(p) != blob:
            raise ValueError("PLUGIN_EC_SOURCE_DRIFT:" + name)

def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

def evaluate(ec_root, public_s2, task, policy, policy_sha, framing):
    root = Path(ec_root)
    check_source(root)
    native = module(root / SOURCES["set"][0], "phase1_native_set")
    policy_engine = module(root / SOURCES["policy"][0], "phase1_native_policy")
    derived = policy_engine.compile_source_policy(
        public_s2, task, policy, pinned_policy_sha256=policy_sha,
        source_commit=COMMIT)
    selected = native.select_admissible_set(
        public_s2, adjudications=derived["adjudications"],
        semantic_authority=derived["semantic_authority"])
    closure = policy_engine.evaluate_policy_closure(
        derived, selected, public_s2, task, policy,
        pinned_policy_sha256=policy_sha, framing=framing)
    check_source(root)
    if closure["real_world_close_authorized"] or (
            derived["natural_language_semantic_authority_qualified"]):
        raise ValueError("PLUGIN_SCOPE_MISMATCH")
    return {
        "protocol": PROTOCOL, "EC_source_commit": COMMIT,
        "s3_selected": selected["selection"]["selected_candidate_ids"],
        "s3_rejected": selected["selection"]["rejected_candidate_ids"],
        "s3_reasons": selected["selection"]["decision_reasons"],
        "s4_policy_obligations": derived["derived_required_conditions"],
        "s4_diagnostic": closure["closure_diagnostic"],
        "s4_unresolved": closure["unresolved_policy_obligations"],
        "finite_scope_plugin_works": True,
        "original_frozen_EC_unchanged": True,
        "natural_language_independent_validation": False,
        "real_world_close_authorized": False,
        "original_MVP_AC_pass_from_plugin": False,
    }


def diagnostic_probe(ec_root):
    """Actual native module smoke; authored formal cases, NOT independent gold."""
    root = Path(ec_root)
    check_source(root)
    policy_module = module(root / SOURCES["policy"][0], "phase1_probe_policy")
    policy = {
        "schema": "EC_PUBLIC_POLICY_V2",
        "policy_id": "issue1-research-plugin-smoke-formal-only",
        "policy_evidence_ref": "policy:phase1-plugin:dev",
        "operation_rules": {
            "opA": ["fact:a"], "opB": ["fact:b"], "opX": ["fact:x"],
        },
        "obligation_rules": {
            "approval": {
                "when": ["fact:approval_required"],
                "done_when": ["fact:approval_done"],
            },
        },
    }
    records = []
    for name, relation, approval in (
        ("competing", "COMPETING", False),
        ("equivalent", "EQUIVALENT", False),
        ("unresolved_approval", "EQUIVALENT", True),
    ):
        task = {
            "schema": "EC_FORMAL_FACTS_V2",
            "source_ref": "task:phase1-plugin:dev",
            "facts": {
                "a": True, "b": True, "x": False,
                "approval_required": approval,
                "approval_done": False,
            },
        }
        s2 = {
            "candidates": [
                {
                    "candidate_id": cid,
                    "semantic_transition": {"operation": "op" + cid},
                    "claims": [], "dependencies": [],
                    "evidence_refs": [policy["policy_evidence_ref"]],
                }
                for cid in ("A", "B", "X")
            ],
            "relation_groups": [{
                "group_id": "relation:phase1-plugin:dev",
                "relation_type": relation,
                "candidate_ids": ["A", "B"],
            }],
            "semantic_ir_hash": policy_module.digest(task),
            "source_refs": [policy["policy_evidence_ref"], task["source_ref"]],
        }
        actual = evaluate(
            root, s2, task, policy, policy_module.digest(policy),
            {"reframe_required": False, "reframe_resolved": False},
        )
        expected = "CONTINUE" if name != "equivalent" else "CLOSE"
        if (actual["s3_selected"] != ["A", "B"]
                or actual["s3_rejected"] != ["X"]
                or actual["s4_diagnostic"] != expected
                or actual["real_world_close_authorized"] is not False
                or actual["original_MVP_AC_pass_from_plugin"] is not False):
            raise ValueError("PLUGIN_FORMAL_S3_S4_SMOKE_FAILURE:" + name)
        if approval and actual["s4_unresolved"] != ["approval"]:
            raise ValueError("PLUGIN_S4_MISSING_OBLIGATION")
        if not approval and actual["s4_unresolved"]:
            raise ValueError("PLUGIN_S4_SPURIOUS_OBLIGATION")
        records.append({
            "name": name,
            "selected": actual["s3_selected"],
            "closure_diagnostic": actual["s4_diagnostic"],
            "required_condition_count": len(actual["s4_policy_obligations"]),
            "unresolved_count": len(actual["s4_unresolved"]),
        })
    check_source(root)
    return {
        "protocol": PROTOCOL,
        "status": "REAL_EC_MODULE_PLUGIN_MECHANICS_VERIFIED",
        "native_EC_commit": COMMIT,
        "source_git_blobs": {alias: pair[1] for alias, pair in SOURCES.items()},
        "case_count": len(records),
        "formal_cases": records,
        "plugin_location": "RESEARCH_REPO_ONLY",
        "frozen_original_ECv4_4_source_modified": False,
        "S3_S4_formal_capabilities_available": True,
        "independent_natural_language_semantics": False,
        "independent_real_world_task_S4_obligations": False,
        "original_18AC_scientific_PASSED": False,
    }
