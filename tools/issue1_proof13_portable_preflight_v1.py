#!/usr/bin/env python3
"""Portable, fail-closed AC13 preregistration and evidence structural gate.

Run entirely in a Linux/Python sandbox. No Mac/LLM/EC runtime required.
Structural validation is never independent third-party certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "issue1.proof13.portable-preflight.v1"
PLAN_SHA1 = "c3a27b518ba42cc8bf41c91bacaf78baf5efcaef"
EXPECTED = ("P01", "P02", "B01", "B02", "B03", "B04", "C01", "C02",
            "C03", "C04", "C05", "X01", "X02")
MVP_IDS = EXPECTED[:11]
ORIGINAL_AC18 = frozenset(f"AC-{n:02d}" for n in (*range(1, 10), *range(11, 18), 19, 20))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def demand(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def read_json(path: Path) -> dict:
    demand(path.is_file() and not path.is_symlink(), "FILE_MISSING_OR_SYMLINK:" + str(path))
    obj = json.loads(path.read_text(encoding="utf-8"))
    demand(type(obj) is dict, "JSON_OBJECT_REQUIRED:" + str(path))
    return obj


def check_plan(path: Path, *, expected_blob: str | None = None) -> dict:
    if expected_blob is None:
        expected_blob = PLAN_SHA1
    d = read_json(path)
    demand(git_blob_sha1(path.read_bytes()) == expected_blob, "G01_FROZEN_AC13_PLAN_CHANGED")
    demand(d.get("schema") == "issue1-independent-proof.ac.v1", "G01_PLAN_PROTOCOL_CHANGED")
    x = d.get("normative_contract") or {}
    demand(x.get("original_required_AC") == 18 and x.get("original_total_AC") == 20
           and x.get("original_materiality_abs") == .20, "G01_ORIGINAL_18_AC_OR_THRESHOLD_CHANGED")
    ac = d.get("acceptance_criteria", [])
    demand([a.get("id") for a in ac] == list(EXPECTED), "G01_PROOF13_AC_LIST_CHANGED")
    seen = set()
    for row in ac:
        demand(set(row.get("depends", [])).issubset(seen), "G01_PROOF13_CYCLE:" + row["id"])
        demand(set(row.get("parent", [])).issubset({f"AC-{n:02d}" for n in range(1, 21)}),
               "G01_UNKNOWN_ORIGINAL_AC:" + row["id"])
        demand(bool(row.get("evidence")) and bool(row.get("pass")), "G01_AC_MISSING_EVIDENCE:" + row["id"])
        seen.add(row["id"])
    demand(d.get("proof_package_mvp", {}).get("AC_count") == 11, "G01_MVP11_CHANGED")
    return d


def checked_artifact(root: Path, record: dict) -> dict:
    demand(set(record) == {"path", "sha256"}, "G02_ARTIFACT_MANIFEST_KEYS_INVALID")
    name = record["path"]
    demand(isinstance(name, str) and name and not Path(name).is_absolute(), "G02_ABSOLUTE_ARTIFACT_PATH")
    base = root.resolve(strict=True)
    submitted = root / name
    path = submitted.resolve(strict=False)
    demand(not submitted.is_symlink() and path.is_relative_to(base) and path.is_file(),
           "G02_ARTIFACT_OUTSIDE_ROOT_OR_MISSING")
    digest = sha256(path)
    demand(digest == record["sha256"], "G06_ARTIFACT_SHA256_CHANGED:" + name)
    return {"path": name, "verified_sha256": digest}


def validate_corpus(manifest: dict, *, min_holdout: int = 120) -> dict:
    """Check corpus isolation; neither authenticates annotators nor data origin."""
    demand(set(manifest) == {"schema", "documents"}
           and manifest["schema"] == "issue1.corpus.v1", "G03_CORPUS_SCHEMA_INVALID")
    items = manifest["documents"]
    demand(isinstance(items, list), "G03_DOCUMENT_LIST_REQUIRED")
    ids, sources, families, split_counts = set(), {}, {}, {"development": 0, "pilot": 0, "holdout": 0}
    holdout_families = set()
    for item in items:
        expected = {"id", "family", "split", "source_sha256", "source_uri", "license", "collected_at"}
        demand(type(item) is dict and set(item) == expected, "G03_DOCUMENT_SCHEMA_MISMATCH")
        ident, family, split, digest = (item[k] for k in ("id", "family", "split", "source_sha256"))
        demand(all(isinstance(x, str) and x for x in (ident, family, split, digest)),
               "G03_DOCUMENT_FIELD_MISSING")
        demand(split in split_counts and len(digest) == 64 and
               all(c in "0123456789abcdef" for c in digest), "G03_INVALID_SPLIT_OR_HASH")
        demand(ident not in ids, "G07_DUPLICATE_DOCUMENT_ID:" + ident)
        ids.add(ident)
        if family in families:
            demand(families[family] == split, "G03_CROSS_SPLIT_FAMILY_LEAK:" + family)
        if digest in sources:
            demand(sources[digest] == split, "G03_CROSS_SPLIT_EXACT_DOCUMENT_LEAK")
        families[family], sources[digest] = split, split
        demand(bool(item["source_uri"]) and bool(item["license"]) and bool(item["collected_at"]),
               "G02_DOCUMENT_PROVENANCE_FIELDS_MISSING")
        split_counts[split] += 1
        if split == "holdout":
            holdout_families.add(family)
    demand(split_counts["holdout"] >= min_holdout, "P02_HOLDOUT_TOO_SMALL")
    demand(bool(holdout_families), "P02_HOLDOUT_FAMILIES_MISSING")
    return {"schema_valid": True, "counts": split_counts,
            "unique_holdout_families": len(holdout_families),
            "near_duplicate_review_required": True,
            "independent_origin_certified": False}


def validate_trace(matrix: dict) -> dict:
    """Bidirectional coverage of explicitly supplied clauses and obligations only."""
    demand(type(matrix) is dict and set(matrix) ==
           {"schema", "requirements_baseline_sha256", "clauses", "obligations", "links", "empty_scope_proof"}
           and matrix["schema"] == "issue1.s4trace.v1", "C02_TRACE_SCHEMA_INVALID")
    demand(isinstance(matrix["requirements_baseline_sha256"], str)
           and len(matrix["requirements_baseline_sha256"]) == 64 and
           all(c in "0123456789abcdef" for c in matrix["requirements_baseline_sha256"]),
           "C01_BASELINE_HASH_REQUIRED")
    clauses, obligations = matrix["clauses"], matrix["obligations"]
    demand(isinstance(clauses, list) and isinstance(obligations, list), "C02_NOT_LISTS")
    demand(all(isinstance(x, str) and x for x in clauses + obligations), "C02_BAD_CLAUSE_ID")
    demand(len(clauses) == len(set(clauses)) and len(obligations) == len(set(obligations)),
           "C02_DUPLICATE_CLAUSE_OR_OBLIGATION")
    demand(isinstance(matrix["links"], list), "C02_LINKS_NOT_LIST")
    links = []
    for edge in matrix["links"]:
        demand(isinstance(edge, dict) and set(edge) == {"clause_id", "obligation_id"},
               "C02_LINK_SCHEMA_INVALID")
        pair = (edge["clause_id"], edge["obligation_id"])
        demand(pair[0] in clauses and pair[1] in obligations, "C02_UNKNOWN_OR_UNGROUNDED_LINK")
        demand(pair not in links, "G07_DUPLICATE_TRACE_LINK")
        links.append(pair)
    if not clauses or not obligations:
        demand(not clauses and not obligations, "C02_HALF_EMPTY_INVENTORY")
        demand(isinstance(matrix["empty_scope_proof"], str) and
               matrix["empty_scope_proof"].strip(), "C02_EMPTY_INVENTORY_UNPROVEN")
        return {"structurally_complete": not bool(clauses or obligations),
                "independent_completeness_certified": False, "empty_scope_proof_unverified": True}
    unlinked_clauses = sorted(set(clauses) - {x for x, _ in links})
    unlinked_obligations = sorted(set(obligations) - {y for _, y in links})
    demand(not unlinked_clauses and not unlinked_obligations,
           "C02_BIDIRECTIONAL_COVERAGE_MISSING:" + repr((unlinked_clauses, unlinked_obligations)))
    return {"structurally_complete": True, "clause_coverage": len(clauses),
            "obligation_coverage": len(obligations),
            "independent_completeness_certified": False}


def run(plan: Path, bundle_root: Path, submission: Path | None = None) -> dict:
    frozen = check_plan(plan)
    base = {"protocol": SCHEMA, "original_root_AC_pass": None,
            "original_MVP_required": 18, "proof_package_required": 11,
            "proof13_total": 13, "independent_proof_AC_pass": 0,
            "original_root_complete": False, "status": "BLOCKED_EXTERNAL_EVIDENCE",
            "required_evidence": {a["id"]: a["evidence"] for a in frozen["acceptance_criteria"]},
            "structural_preflight": {}, "artifact_sha256_verified": [], "errors": []}
    if submission is None:
        base["missing_first_prerequisite"] = ["P01", "P02", "B01", "C01"]
        return base
    data = read_json(submission)
    demand(set(data) == {"schema", "artifacts", "corpus", "trace"} and
           data["schema"] == "issue1.proof13.evidence.v1", "G01_SUBMISSION_SCHEMA_INVALID")
    demand(isinstance(data["artifacts"], list), "G02_ARTIFACTS_NOT_LIST")
    base["artifact_sha256_verified"] = [checked_artifact(bundle_root, r) for r in data["artifacts"]]
    if data["corpus"] is not None:
        base["structural_preflight"]["P02"] = validate_corpus(data["corpus"])
    if data["trace"] is not None:
        base["structural_preflight"]["C02"] = validate_trace(data["trace"])
    base["status"] = "STRUCTURE_CHECKED_INDEPENDENT_CUSTODY_NOT_AUTHENTICATED"
    base["missing_first_prerequisite"] = ["P01", "B02", "B03", "C01", "C02"]
    return base


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--plan", required=True, type=Path)
    p.add_argument("--bundle-root", required=True, type=Path)
    p.add_argument("--submission", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    try:
        report = run(args.plan, args.bundle_root, args.submission)
        if args.out:
            args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2  # An unverified structural preflight is NEVER scientific success.
    except Exception as exc:
        print(json.dumps({"protocol": SCHEMA, "status": "INTEGRITY_FAIL_CLOSED",
                          "error": f"{type(exc).__name__}:{str(exc)[:250]}"}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
