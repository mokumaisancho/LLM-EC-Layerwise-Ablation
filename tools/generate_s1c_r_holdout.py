#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
from copy import deepcopy
from pathlib import Path
from typing import Any

PROTOCOL = "S1C_R_RAW_LANGUAGE_HOLDOUT_V1"
SCORER_FREEZE_COMMIT = "a62e179d854f49c2e194e22358b185854bb376a2"
DETERMINISTIC_FREEZE_COMMIT = "7ba08d4b6e3d107f877cdf74b6891d11637031b4"
FIXED_SEED = "S1C_R_V1_OPAQUE_MAPPING_2026-10-07"

HIDDEN_PREDS = {
    "stable": ["T01"],
    "verified": ["T01"],
    "assigned_to": ["T01", "T02"],
    "depends_on": ["T01", "T01"],
}

FAMILIES = [
    "alias_reference_state",
    "binary_direction_passive",
    "negation_with_contrast",
    "requirement_vs_observation",
    "possibility_vs_observation",
    "multi_entity_conjunction",
    "cross_sentence_relation_state",
    "explicit_unresolved_alternative",
]

PRIOR_FAMILY_NAMES = {
    "temporal_interval_overlap",
    "quantified_exception_scope",
    "identity_merge_by_key",
    "prerequisite_dependency",
    "aggregate_vs_instance_scope",
    "conditional_branch_activation",
    "part_whole_attribution",
    "measurement_scope_missing",
    "safe_release",
    "verified_publish",
    "retention_archive",
    "snapshot_restore",
    "threat_quarantine",
    "capacity_route",
    "validated_seal",
    "approved_activation",
    "unary_1pre_1effect",
    "unary_2pre_1effect",
    "unary_1pre_2effect",
    "binary_2pre_1cross_effect",
    "binary_cross_pre_2effects",
    "binary_2cross_pre_1effect",
    "binary_0pre_2effects",
    "unary_3pre_2effect_split",
    "unary_1pre_add1_del1",
    "unary_2pre_add1_del1",
    "unary_1pre_add2_del1",
    "unary_3pre_add2_del1",
    "binary_2pre_addcross_delunary",
    "binary_3pre_addunary_delcross",
    "binary_1crosspre_add2_delcross",
    "ternary_3pre_add2_delunary",
}


def atom(pred: str, *args: str, polarity: str = "POS", modality: str = "ASSERTED") -> dict[str, Any]:
    return {
        "predicate": pred,
        "arguments": list(args),
        "polarity": polarity,
        "modality": modality,
    }


def typed_ir(atoms: list[dict[str, Any]] | None = None, status: str = "OK") -> dict[str, Any]:
    return {"status": status, "atoms": atoms or []}


def _opaque_map(fid: str) -> dict[str, str]:
    seed = int(hashlib.sha256(f"{FIXED_SEED}:{fid}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    hidden = list(HIDDEN_PREDS)
    opaque = [f"P{i:02d}" for i in range(1, len(hidden) + 1)]
    rng.shuffle(opaque)
    return dict(zip(hidden, opaque))


def _map_atom(a: dict[str, Any], pred_map: dict[str, str]) -> dict[str, Any]:
    out = deepcopy(a)
    out["predicate"] = pred_map[out["predicate"]]
    return out


def _map_ir(ir: dict[str, Any], pred_map: dict[str, str]) -> dict[str, Any]:
    return {
        "status": ir["status"],
        "atoms": [_map_atom(a, pred_map) for a in ir["atoms"]],
    }


def _registry(e1: str, e1_alias: str, e2: str, place: str) -> dict[str, Any]:
    return {
        "E01": {"type": "T01", "surface_forms": [e1, e1_alias]},
        "E02": {"type": "T01", "surface_forms": [e2]},
        "E03": {"type": "T02", "surface_forms": [place]},
    }


def _demo_registry(prefix: str) -> dict[str, Any]:
    return {
        "D01": {"type": "T01", "surface_forms": [f"{prefix} unit"]},
        "D02": {"type": "T01", "surface_forms": [f"{prefix} peer"]},
        "D03": {"type": "T02", "surface_forms": [f"{prefix} bay"]},
    }


def _demos(pred_map: dict[str, str], prefix: str) -> list[dict[str, Any]]:
    reg = _demo_registry(prefix)
    specs = [
        (f"{prefix} unit is stable.", typed_ir([atom("stable", "D01")])),
        (f"{prefix} unit is not stable.", typed_ir([atom("stable", "D01", polarity="NEG")])),
        (f"{prefix} unit is verified.", typed_ir([atom("verified", "D01")])),
        (f"{prefix} unit must be verified.", typed_ir([atom("verified", "D01", modality="REQUIRED")])),
        (f"{prefix} unit may be verified.", typed_ir([atom("verified", "D01", modality="POSSIBLE")])),
        (f"{prefix} unit is assigned to {prefix} bay.", typed_ir([atom("assigned_to", "D01", "D03")])),
        (f"{prefix} unit depends on {prefix} peer.", typed_ir([atom("depends_on", "D01", "D02")])),
        (
            f"The evidence leaves it unresolved whether {prefix} unit is stable or verified.",
            typed_ir(status="AMBIGUOUS"),
        ),
    ]
    return [
        {
            "raw_text": text,
            "entity_registry": deepcopy(reg),
            "typed_ir": _map_ir(ir, pred_map),
        }
        for text, ir in specs
    ]


def _inventory(pred_map: dict[str, str]) -> dict[str, Any]:
    return {
        pred_map[hidden]: {"arg_types": list(types)}
        for hidden, types in HIDDEN_PREDS.items()
    }


def _variant_entities(variant: int) -> tuple[str, str, str, str]:
    if variant == 0:
        return ("Arden module", "the module", "Beryl module", "North bay")
    return ("Cedar package", "the package", "Dover package", "West bay")


def _case_ir(family: str) -> dict[str, Any]:
    if family == "alias_reference_state":
        return typed_ir([atom("stable", "E01")])
    if family == "binary_direction_passive":
        return typed_ir([atom("assigned_to", "E01", "E03")])
    if family == "negation_with_contrast":
        return typed_ir([
            atom("verified", "E01"),
            atom("stable", "E01", polarity="NEG"),
        ])
    if family == "requirement_vs_observation":
        return typed_ir([
            atom("stable", "E01"),
            atom("verified", "E01", modality="REQUIRED"),
        ])
    if family == "possibility_vs_observation":
        return typed_ir([
            atom("stable", "E01"),
            atom("verified", "E01", modality="POSSIBLE"),
        ])
    if family == "multi_entity_conjunction":
        return typed_ir([
            atom("stable", "E01"),
            atom("verified", "E02"),
        ])
    if family == "cross_sentence_relation_state":
        return typed_ir([
            atom("assigned_to", "E01", "E03"),
            atom("stable", "E01"),
        ])
    if family == "explicit_unresolved_alternative":
        return typed_ir(status="AMBIGUOUS")
    raise KeyError(family)


def _raw_text(family: str, variant: int, e1: str, alias: str, e2: str, place: str) -> str:
    if family == "alias_reference_state":
        return (
            f"Inspection opened on {e1}. Later, {alias} remained stable."
            if variant == 0
            else f"The record first names {e1}; in the follow-up note, {alias} is described as stable."
        )
    if family == "binary_direction_passive":
        return (
            f"{place} received {e1} as its assigned item."
            if variant == 0
            else f"Assignment of {e1} was made to {place}."
        )
    if family == "negation_with_contrast":
        return (
            f"Although {e1} is verified, it is not stable."
            if variant == 0
            else f"{e1} is verified; nevertheless, {alias} does not remain stable."
        )
    if family == "requirement_vs_observation":
        return (
            f"{e1} is stable, and policy requires {alias} to be verified."
            if variant == 0
            else f"The observed state of {e1} is stable. The rule says {alias} must be verified."
        )
    if family == "possibility_vs_observation":
        return (
            f"{e1} is stable, while {alias} may also be verified."
            if variant == 0
            else f"Evidence confirms {e1} is stable and allows that {alias} could be verified."
        )
    if family == "multi_entity_conjunction":
        return (
            f"{e1} is stable while {e2} is verified."
            if variant == 0
            else f"At review time, {e1} remains stable and {e2} is verified."
        )
    if family == "cross_sentence_relation_state":
        return (
            f"{e1} is assigned to {place}. In the subsequent check, {alias} is stable."
            if variant == 0
            else f"The assignment places {e1} at {place}. A later note says {alias} remains stable."
        )
    if family == "explicit_unresolved_alternative":
        return (
            f"The evidence supports either that {e1} is stable or that {alias} is verified, but it does not decide which."
            if variant == 0
            else f"Records leave two unresolved readings for {e1}: stable versus verified; neither is established."
        )
    raise KeyError(family)


def make_fixture(seq: int, family: str, variant: int) -> dict[str, Any]:
    fid = f"R{seq:02d}"
    pred_map = _opaque_map(fid)
    e1, alias, e2, place = _variant_entities(variant)
    visible = {
        "raw_text": _raw_text(family, variant, e1, alias, e2, place),
        "entity_registry": _registry(e1, alias, e2, place),
        "opaque_semantic_inventory": _inventory(pred_map),
        "demonstrations": _demos(pred_map, f"Demo{seq:02d}"),
    }
    oracle = _map_ir(_case_ir(family), pred_map)
    return {
        "id": fid,
        "family": family,
        "structural_fingerprint": f"S1C_R::{family}::v{variant}",
        "visible": visible,
        "oracle": {"typed_ir": oracle},
        "audit": {
            "hidden_semantic_map": pred_map,
            "semantic_glosses": list(HIDDEN_PREDS),
            "variant": variant,
            "prior_family_name_collision": family in PRIOR_FAMILY_NAMES,
        },
    }


def generate() -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    seq = 1
    for family in FAMILIES:
        for variant in (0, 1):
            fixtures.append(make_fixture(seq, family, variant))
            seq += 1
    return fixtures


def digest(fixtures: list[dict[str, Any]]) -> str:
    payload = json.dumps(fixtures, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    fixtures = generate()
    out = {
        "protocol": PROTOCOL,
        "scorer_freeze_commit": SCORER_FREEZE_COMMIT,
        "deterministic_freeze_commit": DETERMINISTIC_FREEZE_COMMIT,
        "opaque_mapping_seed": FIXED_SEED,
        "fixture_count": len(fixtures),
        "family_count": len(FAMILIES),
        "families": list(FAMILIES),
        "prior_family_name_collisions": sorted({f["family"] for f in fixtures if f["audit"]["prior_family_name_collision"]}),
        "holdout_digest": digest(fixtures),
        "fixtures": fixtures,
    }
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in (
        "protocol","scorer_freeze_commit","deterministic_freeze_commit","fixture_count",
        "family_count","families","prior_family_name_collisions","holdout_digest"
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
