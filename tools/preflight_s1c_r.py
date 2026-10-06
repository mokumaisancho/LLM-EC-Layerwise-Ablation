#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from typing import Any

from generate_s1c_r_holdout import FAMILIES, PRIOR_FAMILY_NAMES, generate
from score_s1c_r_typed_ir import score_rows, validate_typed_ir
from s1c_r_deterministic_grounder import predict, predictor_manifest

PROTOCOL = "S1C_R_PREINFERENCE_GATE_V1"
EXPECTED_FIXTURES = 16
EXPECTED_FAMILIES = 8

PRIOR_STRUCTURE_DESCRIPTORS = {
    "temporal_interval_reasoning",
    "quantified_exception_scope",
    "identity_key_merge",
    "prerequisite_dependency",
    "aggregate_instance_scope",
    "conditional_branch_activation",
    "part_whole_attribution",
    "measurement_missingness",
    "known_primitive_composition",
    "explicit_schema_synthesis",
    "operator_induction_from_transitions",
}

CURRENT_STRUCTURE_DESCRIPTORS = {
    "alias_reference_state": "alias_coreference_to_unary_state",
    "binary_direction_passive": "passive_voice_binary_direction",
    "negation_with_contrast": "contrastive_assertion_plus_negated_state",
    "requirement_vs_observation": "asserted_state_plus_required_state",
    "possibility_vs_observation": "asserted_state_plus_possible_state",
    "multi_entity_conjunction": "two_entities_two_unary_atoms_shared_clause",
    "cross_sentence_relation_state": "binary_relation_plus_cross_sentence_coreferent_state",
    "explicit_unresolved_alternative": "explicit_two_reading_abstention",
}


def canon(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(x: Any) -> str:
    return hashlib.sha256(canon(x).encode()).hexdigest()


def infer_demo_mapping(visible: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    semantic_cues = {
        "stable": "stable",
        "verified": "verified",
        "assigned to": "assigned_to",
        "depends on": "depends_on",
    }
    for demo in visible["demonstrations"]:
        ir = demo["typed_ir"]
        if ir["status"] != "OK" or len(ir["atoms"]) != 1:
            continue
        text = demo["raw_text"].lower()
        atom = ir["atoms"][0]
        for cue, hidden in semantic_cues.items():
            if cue in text:
                prior = mapping.get(hidden)
                if prior is not None and prior != atom["predicate"]:
                    raise AssertionError(f"inconsistent demo mapping for {hidden}")
                mapping[hidden] = atom["predicate"]
    return mapping


def independent_expected(fixture: dict[str, Any]) -> dict[str, Any]:
    v = fixture["visible"]
    text = v["raw_text"].lower()
    mapping = infer_demo_mapping(v)
    if set(mapping) != {"stable", "verified", "assigned_to", "depends_on"}:
        raise AssertionError("demo mapping incomplete")

    def a(hidden: str, args: list[str], polarity: str = "POS", modality: str = "ASSERTED") -> dict[str, Any]:
        return {
            "predicate": mapping[hidden],
            "arguments": args,
            "polarity": polarity,
            "modality": modality,
        }

    family = fixture["family"]
    if family == "alias_reference_state":
        return {"status": "OK", "atoms": [a("stable", ["E01"])]}
    if family == "binary_direction_passive":
        return {"status": "OK", "atoms": [a("assigned_to", ["E01", "E03"])]}
    if family == "negation_with_contrast":
        return {"status": "OK", "atoms": [
            a("verified", ["E01"]),
            a("stable", ["E01"], polarity="NEG"),
        ]}
    if family == "requirement_vs_observation":
        return {"status": "OK", "atoms": [
            a("stable", ["E01"]),
            a("verified", ["E01"], modality="REQUIRED"),
        ]}
    if family == "possibility_vs_observation":
        return {"status": "OK", "atoms": [
            a("stable", ["E01"]),
            a("verified", ["E01"], modality="POSSIBLE"),
        ]}
    if family == "multi_entity_conjunction":
        return {"status": "OK", "atoms": [
            a("stable", ["E01"]),
            a("verified", ["E02"]),
        ]}
    if family == "cross_sentence_relation_state":
        return {"status": "OK", "atoms": [
            a("assigned_to", ["E01", "E03"]),
            a("stable", ["E01"]),
        ]}
    if family == "explicit_unresolved_alternative":
        if not any(x in text for x in ("does not decide", "unresolved", "neither is established")):
            raise AssertionError("ambiguous fixture lacks explicit unresolved evidence")
        return {"status": "AMBIGUOUS", "atoms": []}
    raise AssertionError(f"unknown family {family}")


def main() -> int:
    fixtures = generate()
    failures: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}

    checks["fixture_count"] = len(fixtures) == EXPECTED_FIXTURES
    checks["family_count"] = len({f["family"] for f in fixtures}) == EXPECTED_FAMILIES
    checks["family_names_unique"] = len(FAMILIES) == len(set(FAMILIES))
    checks["prior_family_name_collision_zero"] = not (set(FAMILIES) & PRIOR_FAMILY_NAMES)
    checks["structural_descriptor_collision_zero"] = not (set(CURRENT_STRUCTURE_DESCRIPTORS.values()) & PRIOR_STRUCTURE_DESCRIPTORS)

    visible_hashes: dict[str, str] = {}
    oracle_recompute = 0
    oracle_scorer_valid = 0
    opaque_inventory_ok = 0
    no_answer_bearing_inventory_fields = 0
    demo_mapping_complete = 0

    for f in fixtures:
        fid = f["id"]
        v = f["visible"]
        visible_hashes[fid] = sha(v)

        inv = v.get("opaque_semantic_inventory", {})
        if (
            set(inv) == {"P01", "P02", "P03", "P04"}
            and all(isinstance(x, dict) and set(x) == {"arg_types"} for x in inv.values())
        ):
            opaque_inventory_ok += 1
        if all(
            key not in canon(v)
            for key in ('"hidden_semantic_map"', '"semantic_glosses"', '"family"', '"oracle"', '"downstream_expected_result"', '"scoring_annotation"')
        ):
            no_answer_bearing_inventory_fields += 1

        try:
            mapping = infer_demo_mapping(v)
            if set(mapping) == {"stable", "verified", "assigned_to", "depends_on"} and len(set(mapping.values())) == 4:
                demo_mapping_complete += 1
        except Exception as exc:
            failures.append({"fixture_id": fid, "gate": "R07_IDENTIFIABLE_DEMO_MAPPING", "error": str(exc)})

        oracle = f["oracle"]["typed_ir"]
        checked = validate_typed_ir(v, oracle)
        if checked["valid"]:
            oracle_scorer_valid += 1
        else:
            failures.append({"fixture_id": fid, "gate": "ORACLE_TYPED_IR_VALID", "reason": checked["reason"]})

        try:
            independently = independent_expected(f)
            expected_check = validate_typed_ir(v, independently)
            oracle_check = validate_typed_ir(v, oracle)
            if expected_check["valid"] and oracle_check["valid"] and expected_check["canonical"] == oracle_check["canonical"]:
                oracle_recompute += 1
            else:
                failures.append({"fixture_id": fid, "gate": "INDEPENDENT_ORACLE_RECOMPUTE_MISMATCH"})
        except Exception as exc:
            failures.append({"fixture_id": fid, "gate": "INDEPENDENT_ORACLE_RECOMPUTE", "error": str(exc)})

    checks["opaque_inventory_only_ids_and_signatures"] = opaque_inventory_ok == EXPECTED_FIXTURES
    checks["model_visible_hidden_field_leakage_zero"] = no_answer_bearing_inventory_fields == EXPECTED_FIXTURES
    checks["demo_mapping_identifiable"] = demo_mapping_complete == EXPECTED_FIXTURES
    checks["oracle_valid_under_independent_scorer"] = oracle_scorer_valid == EXPECTED_FIXTURES
    checks["independent_oracle_recompute"] = oracle_recompute == EXPECTED_FIXTURES
    checks["visible_hash_count"] = len(set(visible_hashes)) == EXPECTED_FIXTURES

    predictions = {f["id"]: predict({"visible": f["visible"]}) for f in fixtures}
    det_score = score_rows(fixtures, predictions)
    checks["deterministic_output_scored_without_oracle_access"] = bool(det_score.get("pass"))

    manifest = predictor_manifest()
    checks["grounder_manifest_oracle_hidden"] = manifest.get("oracle_visible") is False
    checks["grounder_manifest_family_hidden"] = manifest.get("family_visible") is False
    checks["grounder_manifest_post_result_tuning_false"] = manifest.get("post_result_tuning") is False

    passed = all(bool(v) for v in checks.values()) and not failures
    out = {
        "protocol": PROTOCOL,
        "pass": passed,
        "terminal": "S1C_R_PREINFERENCE_PASS" if passed else "S1C_R_PREINFERENCE_FAIL_CLOSED",
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "fixture_count": len(fixtures),
        "family_count": len({f["family"] for f in fixtures}),
        "visible_hashes": visible_hashes,
        "deterministic_preinference_score": {
            "primary": det_score.get("primary"),
            "secondary": det_score.get("secondary"),
            "valid_prediction_rate": det_score.get("valid_prediction_rate"),
            "invalid_prediction_count": det_score.get("invalid_prediction_count"),
        },
        "scientific_rule": "No generator, scorer, predictor, threshold, or fixture repair is authorized after this gate from observed scores. Failure requires a versioned successor protocol.",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
