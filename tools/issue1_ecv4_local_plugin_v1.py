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
                        b"\\0" + data).hexdigest()

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
