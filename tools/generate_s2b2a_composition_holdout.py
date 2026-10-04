#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from pathlib import Path

PROTOCOL = "FUNCTION_BOUNDARY_S2B2A_COMPOSITION_HOLDOUT_V1"


def atom(pred: str, *args: str) -> dict:
    return {"pred": pred, "args": list(args)}


def one_arg_case(fid: str, family: str, operator: str, target: str, distractor: str,
                 ready_pred: str, required_pred: str, forbidden_pred: str,
                 good_action: str, unsafe_action: str, irrelevant_action: str) -> dict:
    return {
        "id": fid,
        "family": family,
        "visible": {
            "relation": {
                "operator": operator,
                "required_effects": [atom(required_pred, target)],
                "forbidden_effects": [atom(forbidden_pred, target)],
            },
            "state": [atom(ready_pred, target)],
            "domains": {"$x": [target, distractor]},
            "primitive_actions": [
                {"action_class": good_action, "parameters": ["$x"],
                 "preconditions": [atom(ready_pred, "$x")],
                 "effects": [atom(required_pred, "$x")]},
                {"action_class": unsafe_action, "parameters": ["$x"],
                 "preconditions": [],
                 "effects": [atom(required_pred, "$x"), atom(forbidden_pred, "$x")]},
                {"action_class": irrelevant_action, "parameters": ["$x"],
                 "preconditions": [atom(ready_pred, "$x")],
                 "effects": [atom("audit_logged", "$x")]},
            ],
            "existing_candidates": [
                {"action_class": irrelevant_action, "bindings": {"$x": target}},
                {"action_class": unsafe_action, "bindings": {"$x": distractor}},
            ],
        },
        "oracle": {"candidates": [{"action_class": good_action, "bindings": {"$x": target}}]},
    }


def two_arg_case(fid: str, family: str, operator: str,
                 left: str, left_distractor: str, right: str, right_distractor: str,
                 left_ready: str, right_ready: str, required_pred: str, forbidden_pred: str,
                 good_action: str, unsafe_action: str, irrelevant_action: str) -> dict:
    return {
        "id": fid,
        "family": family,
        "visible": {
            "relation": {
                "operator": operator,
                "required_effects": [atom(required_pred, left, right)],
                "forbidden_effects": [atom(forbidden_pred, left)],
            },
            "state": [atom(left_ready, left), atom(right_ready, right)],
            "domains": {"$a": [left, left_distractor], "$b": [right, right_distractor]},
            "primitive_actions": [
                {"action_class": good_action, "parameters": ["$a", "$b"],
                 "preconditions": [atom(left_ready, "$a"), atom(right_ready, "$b")],
                 "effects": [atom(required_pred, "$a", "$b")]},
                {"action_class": unsafe_action, "parameters": ["$a", "$b"],
                 "preconditions": [],
                 "effects": [atom(required_pred, "$a", "$b"), atom(forbidden_pred, "$a")]},
                {"action_class": irrelevant_action, "parameters": ["$a", "$b"],
                 "preconditions": [atom(left_ready, "$a")],
                 "effects": [atom("staged", "$a", "$b")]},
            ],
            "existing_candidates": [
                {"action_class": irrelevant_action, "bindings": {"$a": left, "$b": right}},
                {"action_class": unsafe_action, "bindings": {"$a": left_distractor, "$b": right_distractor}},
            ],
        },
        "oracle": {"candidates": [{"action_class": good_action, "bindings": {"$a": left, "$b": right}}]},
    }


CASES = [
    one_arg_case("K001", "safe_release", "SAFE_TRANSITION", "valve_A", "valve_B", "inspection_passed", "released", "safety_bypassed", "RELEASE_AFTER_CHECK", "FORCE_RELEASE", "LOG_RELEASE_REVIEW"),
    one_arg_case("K002", "safe_release", "SAFE_TRANSITION", "hatch_7", "hatch_8", "inspection_passed", "released", "safety_bypassed", "RELEASE_AFTER_CHECK", "FORCE_RELEASE", "LOG_RELEASE_REVIEW"),
    one_arg_case("K003", "verified_publish", "VERIFIED_PROMOTION", "artifact_R", "artifact_S", "verification_passed", "published", "unverified_publish", "PUBLISH_VERIFIED", "PUBLISH_ANYWAY", "RECORD_VERIFICATION"),
    one_arg_case("K004", "verified_publish", "VERIFIED_PROMOTION", "model_card_4", "model_card_5", "verification_passed", "published", "unverified_publish", "PUBLISH_VERIFIED", "PUBLISH_ANYWAY", "RECORD_VERIFICATION"),
    two_arg_case("K005", "retention_archive", "RETENTION_PRESERVING_MOVE", "record_9", "record_10", "vault_B", "vault_C", "retention_required", "destination_ready", "archived_at", "retention_lost", "ARCHIVE_PRESERVING", "MOVE_WITHOUT_RETENTION", "STAGE_ARCHIVE"),
    two_arg_case("K006", "retention_archive", "RETENTION_PRESERVING_MOVE", "case_21", "case_22", "cold_store_2", "cold_store_3", "retention_required", "destination_ready", "archived_at", "retention_lost", "ARCHIVE_PRESERVING", "MOVE_WITHOUT_RETENTION", "STAGE_ARCHIVE"),
    two_arg_case("K007", "snapshot_restore", "RECOVER_FROM_SNAPSHOT", "service_A", "service_B", "snap_41", "snap_42", "service_recoverable", "snapshot_valid", "restored_from", "destructive_reset", "RESTORE_SNAPSHOT", "RESET_AND_REBUILD", "MOUNT_SNAPSHOT"),
    two_arg_case("K008", "snapshot_restore", "RECOVER_FROM_SNAPSHOT", "db_primary", "db_replica", "snap_91", "snap_92", "service_recoverable", "snapshot_valid", "restored_from", "destructive_reset", "RESTORE_SNAPSHOT", "RESET_AND_REBUILD", "MOUNT_SNAPSHOT"),
    one_arg_case("K009", "threat_quarantine", "ISOLATE_CONFIRMED_THREAT", "file_X", "file_Y", "threat_confirmed", "isolated", "executed", "QUARANTINE_CONFIRMED", "EXECUTE_FOR_ANALYSIS", "TAG_FOR_REVIEW"),
    one_arg_case("K010", "threat_quarantine", "ISOLATE_CONFIRMED_THREAT", "container_17", "container_18", "threat_confirmed", "isolated", "executed", "QUARANTINE_CONFIRMED", "EXECUTE_FOR_ANALYSIS", "TAG_FOR_REVIEW"),
    two_arg_case("K011", "capacity_route", "ROUTE_WITH_CAPACITY", "job_3", "job_4", "node_E", "node_F", "job_ready", "capacity_available", "routed_to", "capacity_overrun", "ROUTE_ADMISSIBLE", "FORCE_ROUTE", "QUEUE_ROUTE"),
    two_arg_case("K012", "capacity_route", "ROUTE_WITH_CAPACITY", "batch_8", "batch_9", "worker_2", "worker_3", "job_ready", "capacity_available", "routed_to", "capacity_overrun", "ROUTE_ADMISSIBLE", "FORCE_ROUTE", "QUEUE_ROUTE"),
    one_arg_case("K013", "validated_seal", "SEAL_AFTER_VALIDATION", "package_M", "package_N", "validation_passed", "sealed", "sealed_unvalidated", "SEAL_VALIDATED", "SEAL_IMMEDIATELY", "LABEL_VALIDATION"),
    one_arg_case("K014", "validated_seal", "SEAL_AFTER_VALIDATION", "manifest_5", "manifest_6", "validation_passed", "sealed", "sealed_unvalidated", "SEAL_VALIDATED", "SEAL_IMMEDIATELY", "LABEL_VALIDATION"),
    one_arg_case("K015", "approved_activation", "ACTIVATE_AFTER_APPROVAL", "feature_Q", "feature_R", "approval_present", "activated", "activation_without_approval", "ACTIVATE_APPROVED", "BYPASS_APPROVAL", "RECORD_APPROVAL"),
    one_arg_case("K016", "approved_activation", "ACTIVATE_AFTER_APPROVAL", "policy_12", "policy_13", "approval_present", "activated", "activation_without_approval", "ACTIVATE_APPROVED", "BYPASS_APPROVAL", "RECORD_APPROVAL"),
]


def seed_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16], 16)


def generate(seed: str) -> list[dict]:
    rng = random.Random(seed_int(seed))
    fixtures = copy.deepcopy(CASES)
    rng.shuffle(fixtures)
    for f in fixtures:
        rng.shuffle(f["visible"]["primitive_actions"])
        rng.shuffle(f["visible"]["existing_candidates"])
        for values in f["visible"]["domains"].values():
            rng.shuffle(values)
    return fixtures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True, help="generator freeze commit SHA")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    fixtures = generate(args.seed)
    digest = hashlib.sha256(json.dumps(fixtures, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    out = {
        "protocol": PROTOCOL,
        "seed_source": "generator freeze commit SHA",
        "seed": args.seed,
        "fixture_count": len(fixtures),
        "family_count": len({f["family"] for f in fixtures}),
        "holdout_digest": digest,
        "fixtures": fixtures,
    }
    args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "protocol": PROTOCOL,
        "fixture_count": len(fixtures),
        "family_count": out["family_count"],
        "holdout_digest": digest,
        "fixture_order": [f["id"] for f in fixtures]
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
