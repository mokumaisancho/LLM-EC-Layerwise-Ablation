#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

PROTOCOL = "S1C_V_DENOTATIONAL_DISCOVERY_HOLDOUT_V1"
CONTRACT_FREEZE_COMMIT = "a86e19bd02047a8c7e7d22aa67f399511eb04879"
SCORER_FREEZE_COMMIT = "066bc56f799c209c5642b62acc8b4b7ad0a3e208"
DETERMINISTIC_FREEZE_COMMIT = "347b752db4250cc09b7b237e5881da5b0f503042"

TASK_SPECS = [
    {
        "family": "custody_transition",
        "arg_types": ["T01", "T02"],
        "a": ("retain_custody", ["keeps custody of", "continues holding"], "remains in the care of"),
        "b": ("release_custody", ["releases custody of", "hands over"], "is released by"),
    },
    {
        "family": "placement_transition",
        "arg_types": ["T01", "T02"],
        "a": ("place_into", ["places into", "moves inside"], "is placed within"),
        "b": ("remove_from", ["removes from", "takes out of"], "is removed from"),
    },
    {
        "family": "ordering_relation",
        "arg_types": ["T01", "T01"],
        "a": ("precedes", ["comes before", "occurs earlier than"], "precedes"),
        "b": ("follows", ["comes after", "occurs later than"], "follows"),
    },
    {
        "family": "access_decision",
        "arg_types": ["T01"],
        "a": ("admit", ["is admitted", "is allowed through"], "may enter"),
        "b": ("block", ["is blocked", "is denied entry"], "cannot enter"),
    },
    {
        "family": "quality_decision",
        "arg_types": ["T01"],
        "a": ("accept", ["passes review", "is accepted"], "is approved"),
        "b": ("reject", ["fails review", "is rejected"], "is declined"),
    },
    {
        "family": "lifecycle_transition",
        "arg_types": ["T01"],
        "a": ("activate", ["is switched on", "becomes active"], "is activated"),
        "b": ("retire", ["is taken out of service", "becomes retired"], "is decommissioned"),
    },
    {
        "family": "connectivity_transition",
        "arg_types": ["T01", "T02"],
        "a": ("connect", ["links with", "is connected to"], "connects to"),
        "b": ("separate", ["disconnects from", "is isolated from"], "separates from"),
    },
    {
        "family": "control_transition",
        "arg_types": ["T01", "T02"],
        "a": ("delegate", ["delegates control to", "assigns control to"], "places under the control of"),
        "b": ("reclaim", ["takes control back from", "reclaims control from"], "takes back control from"),
    },
]

PRIOR_FAMILIES = {
    "alias_reference_state","binary_direction_passive","negation_with_contrast",
    "requirement_vs_observation","possibility_vs_observation","multi_entity_conjunction",
    "cross_sentence_relation_state","explicit_unresolved_alternative",
    "temporal_interval_overlap","quantified_exception_scope","identity_merge_by_key",
    "prerequisite_dependency","aggregate_vs_instance_scope","conditional_branch_activation",
    "part_whole_attribution","measurement_scope_missing","safe_release","verified_publish",
    "retention_archive","snapshot_restore","threat_quarantine","capacity_route","validated_seal",
    "approved_activation","unary_1pre_1effect","unary_2pre_1effect","unary_1pre_2effect",
    "binary_2pre_1cross_effect","binary_cross_pre_2effects","binary_2cross_pre_1effect",
    "binary_0pre_2effects","unary_3pre_2effect_split","unary_1pre_add1_del1",
    "unary_2pre_add1_del1","unary_1pre_add2_del1","unary_3pre_add2_del1",
    "binary_2pre_addcross_delunary","binary_3pre_addunary_delcross",
    "binary_1crosspre_add2_delcross","ternary_3pre_add2_delunary",
}


def canon(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(signature: dict[str, Any]) -> str:
    return hashlib.sha256(canon(signature).encode()).hexdigest()


def behavior_signature(task_index: int, side: int, arg_types: list[str]) -> dict[str, Any]:
    # Neutral observable transition signature: no semantic names or mnemonic labels.
    base = task_index * 7 + side * 3
    return {
        "arg_types": list(arg_types),
        "probe_outputs": [
            {"probe": "Q01", "before_bits": [0, 1, 0], "after_bits": [1, (base + 1) % 2, 0]},
            {"probe": "Q02", "before_bits": [1, 0, 1], "after_bits": [(base + 1) % 2, 1, side]},
            {"probe": "Q03", "before_bits": [0, 0, 1], "after_bits": [side, 1, (base // 2) % 2]},
        ],
        "ambiguous": False,
    }


def registry(prefix: str, arg_types: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if len(arg_types) >= 1:
        out["E01"] = {"type": arg_types[0], "surface_forms": [f"{prefix} item"]}
    if len(arg_types) >= 2:
        out["E02"] = {"type": arg_types[1], "surface_forms": [f"{prefix} zone"]}
    return out


def sentence(prefix: str, phrase: str, arg_types: list[str], passive: bool = False) -> str:
    if len(arg_types) == 1:
        return f"{prefix} item {phrase}."
    if passive:
        return f"{prefix} item {phrase} {prefix} zone."
    return f"{prefix} item {phrase} {prefix} zone."


def make_task(task_index: int, spec: dict[str, Any]) -> dict[str, Any]:
    task_id = f"V{task_index:02d}"
    arg_types = list(spec["arg_types"])
    sig_a = behavior_signature(task_index, 0, arg_types)
    sig_b = behavior_signature(task_index, 1, arg_types)
    fp_a = fingerprint(sig_a)
    fp_b = fingerprint(sig_b)

    training = []
    for side_name, side_spec, sig, side_num in (
        ("a", spec["a"], sig_a, 0),
        ("b", spec["b"], sig_b, 1),
    ):
        _, phrases, _ = side_spec
        for variant, phrase in enumerate(phrases):
            exid = f"{task_id}T{side_num * 2 + variant + 1:02d}"
            prefix = f"{task_id}{side_name.upper()}{variant + 1}"
            training.append({
                "example_id": exid,
                "raw_text": sentence(prefix, phrase, arg_types),
                "entity_registry": registry(prefix, arg_types),
                "observable_behavior_signature": deepcopy(sig),
            })

    heldout = []
    heldout_semantics: dict[str, Any] = {}
    heldout_denotation: dict[str, str] = {}
    for side_name, side_spec, fp, side_num in (
        ("a", spec["a"], fp_a, 0),
        ("b", spec["b"], fp_b, 1),
    ):
        _, _, held_phrase = side_spec
        exid = f"{task_id}H{side_num + 1:02d}"
        prefix = f"{task_id}H{side_num + 1}"
        polarity = "POS"
        modality = "ASSERTED"
        phrase = held_phrase
        # Two predeclared modality probes, unrelated to semantic slot identity.
        if task_index == 4 and side_num == 0:
            modality = "POSSIBLE"
        if task_index == 5 and side_num == 1:
            polarity = "NEG"
            phrase = "is not decommissioned"
        heldout.append({
            "example_id": exid,
            "raw_text": sentence(prefix, phrase, arg_types),
            "entity_registry": registry(prefix, arg_types),
        })
        args = ["E01"] + (["E02"] if len(arg_types) == 2 else [])
        heldout_semantics[exid] = {
            "status": "OK",
            "arguments": args,
            "polarity": polarity,
            "modality": modality,
        }
        heldout_denotation[exid] = fp

    training_denotation = {}
    for row in training:
        training_denotation[row["example_id"]] = fingerprint(row["observable_behavior_signature"])

    return {
        "task_id": task_id,
        "family": spec["family"],
        "visible": {
            "type_inventory": sorted(set(arg_types)),
            "training_examples": training,
            "heldout_examples": heldout,
            "slot_count_bound": {"min": 1, "max": 8},
        },
        "oracle": {
            "training_denotation_by_example": training_denotation,
            "heldout_denotation_by_example": heldout_denotation,
            "denotation_arg_types": {
                fp_a: arg_types,
                fp_b: arg_types,
            },
            "heldout_semantics": heldout_semantics,
        },
        "audit": {
            "hidden_semantic_keys": {
                fp_a: spec["a"][0],
                fp_b: spec["b"][0],
            },
            "behavior_fingerprints": [fp_a, fp_b],
            "family": spec["family"],
        },
    }


def generate() -> list[dict[str, Any]]:
    return [make_task(i, spec) for i, spec in enumerate(TASK_SPECS, 1)]


def digest(tasks: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canon(tasks).encode()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    tasks = generate()
    out = {
        "protocol": PROTOCOL,
        "contract_freeze_commit": CONTRACT_FREEZE_COMMIT,
        "scorer_freeze_commit": SCORER_FREEZE_COMMIT,
        "deterministic_freeze_commit": DETERMINISTIC_FREEZE_COMMIT,
        "task_count": len(tasks),
        "heldout_count": sum(len(t["visible"]["heldout_examples"]) for t in tasks),
        "training_count": sum(len(t["visible"]["training_examples"]) for t in tasks),
        "family_count": len({t["family"] for t in tasks}),
        "families": [t["family"] for t in tasks],
        "prior_family_name_collisions": sorted({t["family"] for t in tasks} & PRIOR_FAMILIES),
        "dataset_digest": digest(tasks),
        "tasks": tasks,
    }
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in (
        "protocol","contract_freeze_commit","scorer_freeze_commit","deterministic_freeze_commit",
        "task_count","heldout_count","training_count","family_count","families",
        "prior_family_name_collisions","dataset_digest"
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
