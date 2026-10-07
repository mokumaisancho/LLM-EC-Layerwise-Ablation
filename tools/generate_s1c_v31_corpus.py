from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from s1c_v31_public_hypotheses import (
    EVALUATION_PROBE_INDICES,
    code_key,
    observations,
    probe_input,
    public_manifest,
)

PROTOCOL = "S1C_V31_CORPUS_GENERATOR_V1"
PROBE_LAYOUT = {
    "A1": (0, 1),
    "A2": (2, 4),
    "B1": (0, 2),
    "B2": (1, 4),
}
STRUCTURAL_DESCRIPTOR = (
    "UNKNOWN_PARTITION_FROM_DISTINCT_PARTIAL_TRANSITIONS_WITH_PUBLIC_GENERIC_HYPOTHESIS"
    "__UNSEEN_PROBE_PREDICTION__RAW_LANGUAGE_TRANSFER"
)

# Generator-only construction specification. It is deliberately not emitted.
# Predictor import of this module is forbidden by the V3.1 preflight.
TASK_SPECS = [
    {
        "task_id": "V311",
        "arg_types": ["T01", "T02"],
        "a_code": ("SET1", "KEEP", "KEEP"),
        "b_code": ("SET0", "KEEP", "KEEP"),
        "a_train": ["couples with", "binds to"],
        "b_train": ["decouples from", "disconnects from"],
        "a_held": "may connect with",
        "a_modality": "POSSIBLE",
        "b_held": "separates from",
        "order": [0, 2, 1, 3],
    },
    {
        "task_id": "V312",
        "arg_types": ["T01"],
        "a_code": ("SET1", "KEEP", "KEEP"),
        "b_code": ("KEEP", "SET1", "KEEP"),
        "a_train": ["reserves", "holds in reserve"],
        "b_train": ["releases reservation on", "frees from reservation"],
        "a_held": "sets aside in reserve",
        "b_held": "removes the reservation from",
        "order": [2, 0, 3, 1],
    },
    {
        "task_id": "V313",
        "arg_types": ["T01", "T02"],
        "a_code": ("SET0", "KEEP", "KEEP"),
        "b_code": ("KEEP", "SET1", "KEEP"),
        "a_train": ["hands control to", "passes control to"],
        "b_train": ["takes control back from", "recovers control from"],
        "a_held": "transfers control to",
        "b_held": "reclaims control from",
        "order": [1, 2, 0, 3],
    },
    {
        "task_id": "V314",
        "arg_types": ["T01"],
        "a_code": ("KEEP", "SET0", "KEEP"),
        "b_code": ("KEEP", "KEEP", "SET1"),
        "a_train": ["reveals", "makes visible"],
        "b_train": ["conceals", "keeps hidden"],
        "a_held": "does not reveal",
        "a_polarity": "NEG",
        "b_held": "keeps concealed",
        "order": [3, 0, 2, 1],
    },
    {
        "task_id": "V315",
        "arg_types": ["T01", "T02"],
        "a_code": ("KEEP", "SET0", "KEEP"),
        "b_code": ("KEEP", "KEEP", "SET0"),
        "a_train": ["mounts on", "attaches as a mount to"],
        "b_train": ["unmounts from", "removes the mount from"],
        "a_held": "is mounted onto",
        "b_held": "is detached from",
        "order": [2, 1, 3, 0],
    },
    {
        "task_id": "V316",
        "arg_types": ["T01"],
        "a_code": ("KEEP", "KEEP", "SET1"),
        "b_code": ("KEEP", "KEEP", "SET0"),
        "a_train": ["subscribes", "enrolls for updates"],
        "b_train": ["unsubscribes", "leaves the update feed"],
        "a_held": "must subscribe",
        "a_modality": "REQUIRED",
        "b_held": "opts out of updates",
        "order": [1, 3, 0, 2],
    },
    {
        "task_id": "V317",
        "arg_types": ["T01", "T02"],
        "a_code": ("FLIP", "KEEP", "KEEP"),
        "b_code": ("KEEP", "FLIP", "KEEP"),
        "a_train": ["pairs with", "forms a pair with"],
        "b_train": ["unpairs from", "dissolves the pair with"],
        "a_held": "is paired to",
        "b_held": "is unpaired from",
        "order": [3, 1, 2, 0],
    },
    {
        "task_id": "V318",
        "arg_types": ["T01"],
        "a_code": ("FLIP", "KEEP", "KEEP"),
        "b_code": ("KEEP", "KEEP", "FLIP"),
        "a_train": ["marks", "places a mark on"],
        "b_train": ["unmarks", "clears the mark on"],
        "a_held": "labels as marked",
        "b_held": "removes the mark",
        "order": [0, 3, 2, 1],
    },
]


def canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def registry(prefix: str, arg_types: list[str]) -> dict[str, Any]:
    out = {
        "E01": {
            "type": arg_types[0],
            "surface_forms": [f"{prefix} item"],
        }
    }
    if len(arg_types) == 2:
        out["E02"] = {
            "type": arg_types[1],
            "surface_forms": [f"{prefix} zone"],
        }
    return out


def sentence(prefix: str, phrase: str, arg_types: list[str]) -> str:
    if len(arg_types) == 1:
        return f"{prefix} item {phrase}."
    return f"{prefix} item {phrase} {prefix} zone."


def _training_rows(spec: dict[str, Any]) -> list[dict[str, Any]]:
    raw = [
        ("A1", spec["a_train"][0], spec["a_code"], PROBE_LAYOUT["A1"]),
        ("A2", spec["a_train"][1], spec["a_code"], PROBE_LAYOUT["A2"]),
        ("B1", spec["b_train"][0], spec["b_code"], PROBE_LAYOUT["B1"]),
        ("B2", spec["b_train"][1], spec["b_code"], PROBE_LAYOUT["B2"]),
    ]
    shuffled = [raw[i] for i in spec["order"]]
    rows = []
    for visible_index, (_hidden_label, phrase, code, probes) in enumerate(shuffled, 1):
        prefix = f"{spec['task_id']}T{visible_index}"
        rows.append(
            {
                "example_id": f"{spec['task_id']}T{visible_index:02d}",
                "raw_text": sentence(prefix, phrase, spec["arg_types"]),
                "entity_registry": registry(prefix, spec["arg_types"]),
                "behavior_observations": observations(code, probes),
            }
        )
    return rows


def _heldout_rows(spec: dict[str, Any]) -> list[dict[str, Any]]:
    held = []
    for side, phrase, idx in (
        ("A", spec["a_held"], 1),
        ("B", spec["b_held"], 2),
    ):
        prefix = f"{spec['task_id']}H{idx}"
        held.append(
            {
                "example_id": f"{spec['task_id']}H{idx:02d}",
                "raw_text": sentence(prefix, phrase, spec["arg_types"]),
                "entity_registry": registry(prefix, spec["arg_types"]),
            }
        )

    prefix = f"{spec['task_id']}H3"
    a = sentence(prefix, spec["a_held"], spec["arg_types"])[:-1]
    b = sentence(prefix, spec["b_held"], spec["arg_types"])[:-1]
    held.append(
        {
            "example_id": f"{spec['task_id']}H03",
            "raw_text": f"The evidence is unresolved between: {a} OR {b}.",
            "entity_registry": registry(prefix, spec["arg_types"]),
        }
    )
    return held


def build_task(spec: dict[str, Any]) -> dict[str, Any]:
    visible_hypothesis = public_manifest()
    visible_hypothesis.pop("probe_layout", None)
    visible_hypothesis["evaluation_probe_inputs"] = [
        {
            "probe_id": f"Q{i:02d}",
            "before": list(probe_input(i)),
        }
        for i in EVALUATION_PROBE_INDICES
    ]
    return {
        "task_id": spec["task_id"],
        "structural_descriptor": STRUCTURAL_DESCRIPTOR,
        "visible": {
            "type_inventory": sorted(set(spec["arg_types"])),
            "public_behavior_hypothesis": visible_hypothesis,
            "training_examples": _training_rows(spec),
            "evaluation_probes": visible_hypothesis["evaluation_probe_inputs"],
            "heldout_examples": _heldout_rows(spec),
            "slot_count_bound": {"min": 1, "max": 4},
        },
    }


def generate() -> list[dict[str, Any]]:
    return [build_task(spec) for spec in TASK_SPECS]


def digest(tasks: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canon(tasks).encode()).hexdigest()


def build_corpus() -> dict[str, Any]:
    tasks = generate()
    return {
        "protocol": PROTOCOL,
        "task_count": len(tasks),
        "training_count": sum(len(t["visible"]["training_examples"]) for t in tasks),
        "heldout_count": sum(len(t["visible"]["heldout_examples"]) for t in tasks),
        "dataset_digest": digest(tasks),
        "tasks": tasks,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    out = build_corpus()
    args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: out[k] for k in ("protocol", "task_count", "training_count", "heldout_count", "dataset_digest")},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
