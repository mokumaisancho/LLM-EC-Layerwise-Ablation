#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

CONTRACT_COMMIT = "96a99c0a58f5063f72b3dfd593c6e14e3a29a96c"
INDUCER_COMMIT = "30d47b6c36a195f986cb26e36d5245e4bbf0d89a"
SCORER_COMMIT = "9c4ab5f12f33f443d213d8e6854a0461b461ae33"
GENERATOR_COMMIT = "78cc047200e8e5338294efcc3ad45039c31755bf"
CONTRACT_PATH = "docs/FUNCTION_BOUNDARY_S2B2_B2_OPERATOR_INDUCTION_CONTRACT_2026-10-05.json"
INDUCER_PATH = "tools/s2b2b2_enumerative_inducer.py"
SCORER_PATH = "tools/score_s2b2b2_operator_induction.py"
GENERATOR_PATH = "tools/generate_s2b2b2_operator_holdout.py"
B1_MANIFEST = ROOT / "fixtures/function_boundary_s2b2_b1_schema_synth_manifest_2026-10-04.json"
FORBIDDEN_VISIBLE_KEYS = {"gold", "oracle", "expected", "family", "category", "hidden_operator", "heldout_after", "semantic_signature", "score", "label"}


def fail(terminal: str, detail: str) -> None:
    print(json.dumps({"terminal": terminal, "detail": detail}, indent=2), flush=True)
    raise SystemExit(2)


def git_show(commit: str, path: str) -> bytes:
    p = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True)
    if p.returncode:
        fail("IMPLEMENTATION_PREFLIGHT_FAILED", f"git show failed {commit}:{path}")
    return p.stdout


def require_frozen(commit: str, path: str) -> None:
    current = (ROOT / path).read_bytes()
    frozen = git_show(commit, path)
    if current != frozen:
        fail("FREEZE_ORDER_VIOLATION", f"frozen asset drift: {path}")


def scan_forbidden(v: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(v, dict):
        for k, x in v.items():
            if k in FORBIDDEN_VISIBLE_KEYS:
                hits.append(f"{path}.{k}")
            hits.extend(scan_forbidden(x, f"{path}.{k}"))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            hits.extend(scan_forbidden(x, f"{path}[{i}]"))
    return hits


def canonical_visible_hash(v: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    for path in (INDUCER_PATH, SCORER_PATH, GENERATOR_PATH):
        try:
            py_compile.compile(str(ROOT / path), doraise=True)
        except Exception as e:
            fail("IMPLEMENTATION_PREFLIGHT_FAILED", f"py_compile {path}: {e}")

    require_frozen(CONTRACT_COMMIT, CONTRACT_PATH)
    require_frozen(INDUCER_COMMIT, INDUCER_PATH)
    require_frozen(SCORER_COMMIT, SCORER_PATH)
    require_frozen(GENERATOR_COMMIT, GENERATOR_PATH)

    contract = json.loads((ROOT / CONTRACT_PATH).read_text())
    if contract.get("protocol") != "S2B2_MVP_TCC_V3" or contract.get("scoring", {}).get("materiality_abs") != 0.20:
        fail("INVALID_TEST_CONTRACT", "B2 protocol/materiality drift")
    if not contract.get("identifiability_gate", {}).get("must_run_before_model_inference"):
        fail("INVALID_TEST_CONTRACT", "identifiability gate not mandatory")
    if contract.get("paired_authority", {}).get("deterministic_may_induce_operator") is not True or contract.get("paired_authority", {}).get("qwen_may_induce_operator") is not True:
        fail("ASYMMETRIC_CAPABILITY_CONTRACT", "B2 induction authority differs")

    gen = importlib.import_module("generate_s2b2b2_operator_holdout")
    ind = importlib.import_module("s2b2b2_enumerative_inducer")
    scorer = importlib.import_module("score_s2b2b2_operator_induction")
    rows = gen.generate(GENERATOR_COMMIT)
    if len(rows) != 16 or len({f["family"] for f in rows}) != 8:
        fail("INVALID_TEST_CONTRACT", "B2 fixture/family count")

    b1 = json.loads(B1_MANIFEST.read_text())
    b1fps = set(b1.get("structural_fingerprints", []))
    b2fps = {f["structural_fingerprint"] for f in rows}
    if len(b2fps) != 8 or b1fps & b2fps:
        fail("HOLDOUT_NOT_INDEPENDENT", "B2 fingerprints overlap B1 or family count drift")

    audit_rows = []
    for f in rows:
        visible = f["visible"]
        hits = scan_forbidden(visible)
        if hits:
            fail("ORACLE_OR_LABEL_LEAKAGE", f"{f['id']} visible hits {hits}")
        if set(visible.get("heldout_target", {})) != {"binding", "before"}:
            fail("B2_TARGET_LEAKS_SCHEMA", f"{f['id']} heldout target fields")
        if "after" in visible["heldout_target"]:
            fail("B2_TARGET_LEAKS_SCHEMA", f"{f['id']} heldout after visible")
        if len(visible.get("positive_examples", [])) < 2:
            fail("INVALID_TEST_CONTRACT", f"{f['id']} positive count")
        hidden_pre_n = len(f["oracle"]["semantic_signature"]["preconditions"])
        if len(visible.get("negative_examples", [])) != hidden_pre_n:
            fail("INVALID_TEST_CONTRACT", f"{f['id']} negative omission count")

        pf = scorer.preflight_fixture(f)
        if not pf.get("valid") or pf.get("consistent_count") != 1:
            fail(pf.get("terminal", "B2_IDENTIFIABILITY_FAILED"), f"{f['id']} count={pf.get('consistent_count')}")
        det = ind.induce(visible)
        if det.get("status") != "UNIQUE" or det.get("consistent_count") != 1:
            fail("DETERMINISTIC_SEARCH_BOUND", f"{f['id']} deterministic status={det.get('status')}")
        if scorer.skey(det["schema"]) != scorer.skey(pf["oracle"]):
            fail("ORACLE_PREDICTOR_DISAGREEMENT", f["id"])
        if scorer.skey(pf["oracle"]) in scorer.supplied_signature_set(visible):
            fail("ONTOLOGY_CLASS_NOT_ACTUALLY_NOVEL", f["id"])

        train_bindings = {tuple(sorted(e["binding"].items())) for e in visible["positive_examples"] + visible["negative_examples"]}
        heldout_binding = tuple(sorted(visible["heldout_target"]["binding"].items()))
        if heldout_binding in train_bindings:
            fail("HELDOUT_BINDING_NOT_NOVEL", f["id"])

        audit_rows.append({
            "fixture_id": f["id"],
            "family": f["family"],
            "structural_fingerprint": f["structural_fingerprint"],
            "consistent_hypotheses": 1,
            "visible_sha256": canonical_visible_hash(visible),
            "deterministic_matches_independent_oracle": True,
        })

    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    out = {
        "schema_version": "FUNCTION_BOUNDARY_S2B2_B2_PREFLIGHT_V1",
        "protocol": "S2B2_MVP_TCC_V3",
        "terminal": "B2_PREFLIGHT_PASS",
        "contract_commit": CONTRACT_COMMIT,
        "inducer_commit": INDUCER_COMMIT,
        "scorer_commit": SCORER_COMMIT,
        "generator_commit": GENERATOR_COMMIT,
        "fixture_count": 16,
        "family_count": 8,
        "holdout_digest": digest,
        "structural_fingerprints": sorted(b2fps),
        "b1_fingerprint_overlap": 0,
        "identifiable_unique_count": 16,
        "deterministic_unique_match_count": 16,
        "leakage_count": 0,
        "model_inference": False,
        "rows": audit_rows,
    }
    print(json.dumps(out, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
