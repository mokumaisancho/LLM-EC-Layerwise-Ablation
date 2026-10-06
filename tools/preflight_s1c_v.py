#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from typing import Any

from generate_s1c_v_holdout import PRIOR_FAMILIES, TASK_SPECS, canon, fingerprint, generate
from s1c_v_deterministic_discovery import predict, predictor_manifest
from score_s1c_v_denotational import aggregate

PROTOCOL = "S1C_V_PREINFERENCE_GATE_V1"
EXPECTED_TASKS = 8
EXPECTED_TRAINING = 32
EXPECTED_HELDOUT = 16


def sha(v: Any) -> str:
    return hashlib.sha256(canon(v).encode()).hexdigest()


def main() -> int:
    tasks = generate()
    failures: list[dict[str, Any]] = []
    checks: dict[str, bool] = {}

    checks["task_count"] = len(tasks) == EXPECTED_TASKS
    checks["training_count"] = sum(len(t["visible"]["training_examples"]) for t in tasks) == EXPECTED_TRAINING
    checks["heldout_count"] = sum(len(t["visible"]["heldout_examples"]) for t in tasks) == EXPECTED_HELDOUT
    checks["family_count"] = len({t["family"] for t in tasks}) == EXPECTED_TASKS
    checks["prior_family_name_collision_zero"] = not ({t["family"] for t in tasks} & PRIOR_FAMILIES)
    checks["generator_families_match_frozen_specs"] = [t["family"] for t in tasks] == [x["family"] for x in TASK_SPECS]

    visible_hashes: dict[str, str] = {}
    training_partition_identifiable = 0
    heldout_denotation_identifiable = 0
    neutral_behavior_key_count = 0
    oracle_key_leakage_zero = 0

    for task in tasks:
        tid = task["task_id"]
        visible = task["visible"]
        oracle = task["oracle"]
        visible_hashes[tid] = sha(visible)

        visible_serialized = canon(visible)
        if all(x not in visible_serialized for x in (
            '"oracle"', '"audit"', '"hidden_semantic_keys"', '"training_denotation_by_example"',
            '"heldout_denotation_by_example"', '"heldout_semantics"', '"family"'
        )):
            oracle_key_leakage_zero += 1
        else:
            failures.append({"task_id": tid, "gate": "V05_ORACLE_KEY_LEAKAGE"})

        train = visible["training_examples"]
        groups: dict[str, list[str]] = {}
        arg_types_by_fp: dict[str, list[str]] = {}
        neutral = True
        for ex in train:
            sig = ex["observable_behavior_signature"]
            fp = fingerprint(sig)
            groups.setdefault(fp, []).append(ex["example_id"])
            arg_types_by_fp[fp] = list(sig["arg_types"])
            sig_text = canon(sig)
            if any(name in sig_text.lower() for name in (
                "custody","placement","preced","follow","access","accept","reject",
                "activate","retire","connect","separate","delegate","reclaim"
            )):
                neutral = False

        if len(groups) == 2 and sorted(len(v) for v in groups.values()) == [2, 2]:
            training_partition_identifiable += 1
        else:
            failures.append({"task_id": tid, "gate": "V06_TRAINING_DENOTATION_NON_IDENTIFIABLE", "groups": groups})

        if neutral:
            neutral_behavior_key_count += 1
        else:
            failures.append({"task_id": tid, "gate": "V05_ANSWER_BEARING_BEHAVIOR_SIGNATURE"})

        expected_train_den = oracle["training_denotation_by_example"]
        recomputed_train_den = {
            ex["example_id"]: fingerprint(ex["observable_behavior_signature"])
            for ex in train
        }
        if expected_train_den != recomputed_train_den:
            failures.append({"task_id": tid, "gate": "V06_TRAINING_DENOTATION_RECOMPUTE_MISMATCH"})

        if oracle["denotation_arg_types"] != arg_types_by_fp:
            failures.append({"task_id": tid, "gate": "V06_DENOTATION_TYPE_MISMATCH"})

        train_fps = set(groups)
        held_fps = set(oracle["heldout_denotation_by_example"].values())
        if held_fps == train_fps:
            heldout_denotation_identifiable += 1
        else:
            failures.append({
                "task_id": tid,
                "gate": "V06_HELDOUT_DENOTATION_OUTSIDE_DISCOVERED_SPACE",
                "training": sorted(train_fps),
                "heldout": sorted(held_fps),
            })

    checks["visible_oracle_key_leakage_zero"] = oracle_key_leakage_zero == EXPECTED_TASKS
    checks["training_partition_identifiable"] = training_partition_identifiable == EXPECTED_TASKS
    checks["heldout_denotation_identifiable"] = heldout_denotation_identifiable == EXPECTED_TASKS
    checks["behavior_signatures_non_mnemonic"] = neutral_behavior_key_count == EXPECTED_TASKS
    checks["visible_hash_unique"] = len(set(visible_hashes.values())) == EXPECTED_TASKS

    manifest = predictor_manifest()
    checks["deterministic_oracle_hidden"] = manifest.get("oracle_visible") is False
    checks["deterministic_family_hidden"] = manifest.get("family_visible") is False
    checks["deterministic_canonical_names_hidden"] = manifest.get("canonical_slot_name_visible") is False
    checks["deterministic_canonical_ids_hidden"] = manifest.get("canonical_slot_id_visible") is False
    checks["no_post_result_tuning"] = manifest.get("post_result_tuning") is False

    predictions = {t["task_id"]: predict({"visible": t["visible"]}) for t in tasks}
    deterministic = aggregate(tasks, predictions)
    checks["deterministic_outputs_score_under_frozen_scorer"] = deterministic.get("pass") is True

    passed = all(checks.values()) and not failures
    out = {
        "protocol": PROTOCOL,
        "pass": passed,
        "terminal": "S1C_V_PREINFERENCE_PASS" if passed else "S1C_V_PREINFERENCE_FAIL_CLOSED",
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "task_count": len(tasks),
        "training_count": sum(len(t["visible"]["training_examples"]) for t in tasks),
        "heldout_count": sum(len(t["visible"]["heldout_examples"]) for t in tasks),
        "visible_hashes": visible_hashes,
        "deterministic_preinference_score": {
            "primary": deterministic.get("primary"),
            "secondary": deterministic.get("secondary"),
        },
        "scientific_rule": "No contract, scorer, deterministic algorithm, generator, prompt, slot budget, or metric repair is authorized after observing paired model results. Failure requires a versioned successor protocol.",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
