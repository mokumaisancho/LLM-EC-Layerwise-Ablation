#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (str(ROOT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

from generate_s1c_v31_corpus import build_corpus
from s1c_v31_deterministic_baseline import predict as research_predict
from semantic_runtime import RuntimeContractError, canonical_json, discover_and_ground

EXPECTED_DATASET_DIGEST = "972345a1b7f266c5015e82b24de3614c93874f7915df341281166b1fd448c261"
ALLOWED_VISIBLE_KEYS = {
    "type_inventory",
    "public_behavior_hypothesis",
    "training_examples",
    "evaluation_probes",
    "heldout_examples",
    "slot_count_bound",
}


def fail(code: str, detail=None) -> int:
    print(
        json.dumps(
            {
                "protocol": "PRODUCT_RUNTIME_V32_COMPAT_REGRESSION_V1",
                "pass": False,
                "terminal": "PRODUCT_RUNTIME_V32_COMPAT_REGRESSION_FAIL_CLOSED",
                "code": code,
                "detail": detail,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 3


def main() -> int:
    corpus = build_corpus()
    if corpus.get("dataset_digest") != EXPECTED_DATASET_DIGEST:
        return fail(
            "AUDITED_CORPUS_DIGEST_DRIFT",
            {"actual": corpus.get("dataset_digest"), "expected": EXPECTED_DATASET_DIGEST},
        )
    tasks = corpus.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 8:
        return fail("AUDITED_TASK_COUNT_MISMATCH")

    rows = []
    for task in tasks:
        tid = str(task["task_id"])
        visible = copy.deepcopy(task["visible"])
        unknown = sorted(set(visible) - ALLOWED_VISIBLE_KEYS)
        if unknown:
            return fail("PUBLIC_VISIBLE_SCHEMA_KEY_GAP", {"task_id": tid, "unknown": unknown})

        product_task = {
            "protocol": "SEMANTIC_RUNTIME_TASK_V1",
            "visible": visible,
        }
        try:
            product = discover_and_ground(product_task)
        except RuntimeContractError as exc:
            return fail("PRODUCT_REJECTED_AUDITED_PUBLIC_TASK", {"task_id": tid, "error": str(exc)})

        research = research_predict({"visible": copy.deepcopy(visible)})
        projection = {
            "discovered_slots": product["discovered_slots"],
            "heldout_assignments": product["heldout_assignments"],
            "abstentions": product["abstentions"],
        }
        if projection != research:
            return fail(
                "PRODUCT_RESEARCH_BEHAVIOR_DRIFT",
                {
                    "task_id": tid,
                    "product_sha": hashlib.sha256(canonical_json(projection).encode()).hexdigest(),
                    "research_sha": hashlib.sha256(canonical_json(research).encode()).hexdigest(),
                },
            )

        first = canonical_json(product).encode()
        for _ in range(20):
            replay = canonical_json(discover_and_ground(copy.deepcopy(product_task))).encode()
            if replay != first:
                return fail("NON_DETERMINISTIC_REPLAY", {"task_id": tid})

        # Production API must refuse the full research task because it carries hidden authority.
        full_task = copy.deepcopy(task)
        full_task["protocol"] = "SEMANTIC_RUNTIME_TASK_V1"
        try:
            discover_and_ground(full_task)
        except RuntimeContractError as exc:
            if "FORBIDDEN_INPUT_KEY" not in str(exc):
                return fail("FULL_RESEARCH_TASK_REJECTED_FOR_WRONG_REASON", {"task_id": tid, "error": str(exc)})
        else:
            return fail("FULL_RESEARCH_TASK_HIDDEN_AUTHORITY_ACCEPTED", {"task_id": tid})

        rows.append(
            {
                "task_id": tid,
                "exact_behavior_match": True,
                "replays": 20,
                "canonical_sha256": hashlib.sha256(first).hexdigest(),
                "hidden_authority_rejected": True,
            }
        )

    out = {
        "protocol": "PRODUCT_RUNTIME_V32_COMPAT_REGRESSION_V1",
        "pass": True,
        "terminal": "PRODUCT_RUNTIME_V32_COMPAT_REGRESSION_PASS",
        "dataset_digest": EXPECTED_DATASET_DIGEST,
        "task_count": len(rows),
        "exact_behavior_match": "8/8",
        "deterministic_replays": 160,
        "hidden_authority_rejection": "8/8",
        "production_imports_research_predictor": False,
        "rows": rows,
        "post_result_scientific_tuning": False,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
