#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import py_compile
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

PROTOCOL = "S1C_V31_PREFLIGHT_V1"

EXPECTED_BLOBS = {
    "docs/S1C_V31_DENOTATIONAL_DISCOVERY_CONTRACT_2026-10-07.json": "f77a112f90620e64c48fb824a65ca7a995b04212",
    "tools/s1c_v31_public_hypotheses.py": "fe7b7b9a6203624e93ffdce1d542404fd250e63d",
    "tools/generate_s1c_v31_corpus.py": "a324ddd9ad9fbeb4e7cbb0b4a684a65a153d3a4b",
    "tools/validate_s1c_v31_corpus.py": "65746d0224b527f02f9caa20595a2fdf0690fb2c",
    "tools/score_s1c_v31_denotational.py": "f2df24b1994bc8da2b66b6280b41aba37d02d10e",
    "tools/s1c_v31_deterministic_baseline.py": "b5bf066dd2dd55a2cdcf076b09f5183c441b9866",
    "tools/s1c_v31_json_schema.py": "e97276494ecd21b62a3ad23c5e37cb7cdaa2c68d",
}

PRIOR_STRUCTURAL_CORES = {
    "S1A_GRAPH_GROUNDING": (True, False, "GRAPH_OR_TYPED_SYMBOLS", False, False),
    "S2A_KNOWN_PRIMITIVE_COMPOSITION": (True, False, "KNOWN_PRIMITIVES", False, False),
    "S2B1_SCHEMA_SYNTHESIS": (True, False, "SCHEMA_REQUIREMENTS", False, False),
    "S2B2_OPERATOR_INDUCTION": (True, False, "POS_NEG_STATE_TRANSITIONS", False, False),
    "S1C_R_RAW_GROUNDING": (True, False, "TYPED_IR_DEMONSTRATIONS", False, False),
    "S1C_V2_INVALID": (False, True, "IDENTICAL_SLOT_SIGNATURE", False, False),
    "S1C_V3_INVALID": (False, True, "DISTINCT_PARTIAL_TRANSITION_PROBES", True, False),
}


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(raw)}\0".encode())
    h.update(raw)
    return h.hexdigest()


def fail(reason: str, detail: Any = None) -> int:
    print(
        json.dumps(
            {
                "protocol": PROTOCOL,
                "pass": False,
                "terminal": "S1C_V31_PREFLIGHT_FAIL_CLOSED",
                "reason": reason,
                "detail": detail,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 3


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module)
    return out


def _baseline_authority_gate() -> tuple[bool, dict[str, Any]]:
    path = TOOLS / "s1c_v31_deterministic_baseline.py"
    source = path.read_text(encoding="utf-8")
    imports = _imports(path)
    forbidden_modules = {
        "generate_s1c_v31_corpus",
        "validate_s1c_v31_corpus",
        "score_s1c_v31_denotational",
        "s1c_v3_reference_truth_tables",
        "s1c_v31_reference",
    }
    bad_imports = sorted(imports & forbidden_modules)
    forbidden_source_tokens = (
        "TASK_SPECS",
        "REFERENCE =",
        "target_code",
        "slot_references",
        "heldout_denotation",
        "training_gold",
    )
    bad_tokens = [x for x in forbidden_source_tokens if x in source]
    allowed_scientific = "s1c_v31_public_hypotheses" in imports
    return (
        not bad_imports and not bad_tokens and allowed_scientific,
        {
            "imports": sorted(imports),
            "bad_imports": bad_imports,
            "bad_tokens": bad_tokens,
            "public_hypothesis_import_present": allowed_scientific,
        },
    )


def _validator_independence_gate() -> tuple[bool, dict[str, Any]]:
    path = TOOLS / "validate_s1c_v31_corpus.py"
    imports = _imports(path)
    bad = sorted(x for x in imports if x.startswith("generate_s1c"))
    return (not bad, {"imports": sorted(imports), "generator_imports": bad})


def _scorer_independence_gate() -> tuple[bool, dict[str, Any]]:
    path = TOOLS / "score_s1c_v31_denotational.py"
    imports = _imports(path)
    bad = sorted(
        x for x in imports
        if x.startswith("generate_s1c") or x.startswith("validate_s1c") or x.startswith("s1c_v31_deterministic")
    )
    return (not bad, {"imports": sorted(imports), "forbidden_imports": bad})


def _structural_core(task: dict[str, Any]) -> tuple[Any, ...]:
    visible = task["visible"]
    serialized = json.dumps(visible, sort_keys=True)
    visible_slot_inventory = "slot_inventory" in serialized or "canonical_slot" in serialized
    unknown_partition = not visible_slot_inventory and '"target_code"' not in serialized
    train = visible["training_examples"]
    probe_sets = [
        tuple(row["probe_id"] for row in ex["behavior_observations"])
        for ex in train
    ]
    bundles = [
        json.dumps(ex["behavior_observations"], sort_keys=True)
        for ex in train
    ]
    behavior = (
        "DISTINCT_PARTIAL_TRANSITION_PROBES"
        if len(set(probe_sets)) == len(train) and len(set(bundles)) == len(train)
        else "OTHER"
    )
    has_unseen_probe_output_target = bool(visible.get("evaluation_probes"))
    held_behavior_visible = any("behavior_observations" in ex for ex in visible["heldout_examples"])
    return (
        visible_slot_inventory,
        unknown_partition,
        behavior,
        has_unseen_probe_output_target,
        held_behavior_visible,
    )


def main() -> int:
    for relative, expected in EXPECTED_BLOBS.items():
        path = ROOT / relative
        if not path.exists():
            return fail("FROZEN_SOURCE_MISSING", relative)
        actual = blob_sha(path)
        if actual != expected:
            return fail("FROZEN_SOURCE_DRIFT", {"path": relative, "actual": actual, "expected": expected})
        if path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as exc:
                return fail("PY_COMPILE_FAILED", {"path": relative, "error": repr(exc)})

    sys.path.insert(0, str(TOOLS))
    try:
        import generate_s1c_v31_corpus as generator
        import validate_s1c_v31_corpus as oracle
        import score_s1c_v31_denotational as scorer
        import s1c_v31_deterministic_baseline as baseline
        import s1c_v31_json_schema as schema
        import s1c_v31_public_hypotheses as public
    except Exception as exc:
        return fail("IMPORT_FAILED", repr(exc))

    ok, detail = _baseline_authority_gate()
    if not ok:
        return fail("PREDICTOR_HIDDEN_REFERENCE_ACCESS", detail)
    baseline_authority = detail

    ok, detail = _validator_independence_gate()
    if not ok:
        return fail("GENERATOR_ORACLE_NOT_INDEPENDENTLY_RECOMPUTED", detail)
    validator_authority = detail

    ok, detail = _scorer_independence_gate()
    if not ok:
        return fail("SCORER_INDEPENDENCE_VIOLATION", detail)
    scorer_authority = detail

    corpus = generator.build_corpus()
    if corpus.get("task_count") != 8 or corpus.get("training_count") != 32 or corpus.get("heldout_count") != 24:
        return fail(
            "CORPUS_COUNT_MISMATCH",
            {k: corpus.get(k) for k in ("task_count", "training_count", "heldout_count")},
        )

    validation = oracle.validate_corpus(corpus)
    if validation.get("pass") is not True:
        return fail("ORACLE_VALIDATION_FAIL", validation.get("failures"))

    structural_rows = []
    for task in corpus["tasks"]:
        core = _structural_core(task)
        collisions = [name for name, prior in PRIOR_STRUCTURAL_CORES.items() if core == prior]
        ok = (
            core == (False, True, "DISTINCT_PARTIAL_TRANSITION_PROBES", True, False)
            and not collisions
            and task.get("structural_descriptor")
            == "UNKNOWN_PARTITION_FROM_DISTINCT_PARTIAL_TRANSITIONS_WITH_PUBLIC_GENERIC_HYPOTHESIS__UNSEEN_PROBE_PREDICTION__RAW_LANGUAGE_TRANSFER"
        )
        structural_rows.append(
            {
                "task_id": task["task_id"],
                "core": list(core),
                "prior_core_collisions": collisions,
                "pass": ok,
            }
        )
        if not ok:
            return fail("STRUCTURAL_HOLDOUT_REUSE", structural_rows[-1])

    ambiguity_rows = []
    for task in corpus["tasks"]:
        tid = task["task_id"]
        ref = validation["references"][tid]["heldout"]
        amb = [eid for eid, row in ref.items() if row.get("status") == "AMBIGUOUS"]
        normal = [eid for eid, row in ref.items() if row.get("status") == "OK"]
        visible_amb = [
            ex["example_id"]
            for ex in task["visible"]["heldout_examples"]
            if "unresolved between:" in str(ex["raw_text"]).lower()
        ]
        ok = len(amb) == 1 and len(normal) == 2 and set(amb) == set(visible_amb)
        ambiguity_rows.append(
            {
                "task_id": tid,
                "ambiguous_ids": amb,
                "normal_ids": normal,
                "visible_ambiguity_ids": visible_amb,
                "pass": ok,
            }
        )
        if not ok:
            return fail("AMBIGUITY_COVERAGE_MISSING", ambiguity_rows[-1])

    predictions = {
        task["task_id"]: baseline.predict({"visible": task["visible"]})
        for task in corpus["tasks"]
    }
    score = scorer.aggregate(corpus["tasks"], predictions, validation["references"])
    if score.get("pass") is not True:
        return fail("BASELINE_NOT_SCOREABLE", score)
    if score["primary"]["training_partition_adjusted_rand_index"] != 1.0:
        return fail("PUBLIC_HYPOTHESIS_PARTITION_NOT_IDENTIFIED", score["primary"])
    if score["primary"]["unseen_probe_behavior_accuracy"] != 1.0:
        return fail("PUBLIC_HYPOTHESIS_BEHAVIOR_NOT_IDENTIFIED", score["primary"])

    schema_rows = []
    for task in corpus["tasks"]:
        row = schema.static_contract_check(task)
        schema_rows.append(
            {
                "task_id": task["task_id"],
                "pass": row["pass"],
                "failure_count": row["failure_count"],
                "runtime_smoke_required": row["runtime_smoke_required"],
            }
        )
        if row["pass"] is not True:
            return fail("JSON_SCHEMA_STATIC_FAIL", {"task_id": task["task_id"], "failures": row["failures"]})

    public_manifest = public.public_manifest()
    if "probe_layout" in public_manifest:
        return fail("PUBLIC_AUTHORITY_CONTAINS_CONSTRUCTION_LAYOUT")
    if public_manifest.get("function_count") != 64:
        return fail("PUBLIC_HYPOTHESIS_COUNT_MISMATCH", public_manifest)

    out = {
        "protocol": PROTOCOL,
        "pass": True,
        "terminal": "S1C_V31_PREFLIGHT_PASS",
        "source_blob_pins": EXPECTED_BLOBS,
        "corpus": {
            "task_count": corpus["task_count"],
            "training_count": corpus["training_count"],
            "heldout_count": corpus["heldout_count"],
            "dataset_digest": corpus["dataset_digest"],
        },
        "public_hypothesis": public_manifest,
        "baseline_authority_gate": baseline_authority,
        "validator_independence_gate": validator_authority,
        "scorer_independence_gate": scorer_authority,
        "oracle_validation_terminal": validation["terminal"],
        "structural_rows": structural_rows,
        "ambiguity_rows": ambiguity_rows,
        "baseline_primary": score["primary"],
        "baseline_secondary": score["secondary"],
        "schema_rows": schema_rows,
        "scientific_rule": (
            "No contract, public hypothesis class, scorer, corpus, oracle validator, deterministic baseline, "
            "schema, prompt, metric, threshold or fixture repair is authorized after paired model results. "
            "Unexpected failure requires a versioned successor and complete refreeze."
        ),
        "required_next_gate": "S1C_V31_SYNTHETIC_JSON_SCHEMA_RUNTIME_SMOKE_PASS",
        "model_inference_authorized": False,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
