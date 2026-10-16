#!/usr/bin/env python3
"""Issue1: compare an LLM-proposed EC v2 formal policy to an independently
source-frozen formal reference, using SymPy's SAT reasoning.

This verifies only *formal* equivalence, not NL→formal semantic fidelity.
Source custody and genuine independence must be certified outside this script.
No source benchmark gold, solution labels, or task-specific expected answers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from sympy import And, Not, Symbol, Xor
from sympy.logic.inference import satisfiable

PROTOCOL = "EC_PUBLIC_POLICY_V2"
REQUIRED = {"schema", "policy_id", "policy_evidence_ref", "operation_rules", "obligation_rules"}
BANNED = {"oracle", "gold", "hidden", "expected", "answer", "fixture_id",
          "reference_label", "correct_label", "acceptable_candidate_ids",
          "oracle_constraints", "evaluation", "scorer", "prediction"}

class PolicyEquivalenceError(ValueError):
    pass


def must(ok: bool, reason: str) -> None:
    if not ok:
        raise PolicyEquivalenceError(reason)


def decode_unique(p: Path) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            must(key not in result, "DUPLICATE_JSON_KEY:" + key)
            result[key] = value
        return result
    return json.loads(p.read_text(encoding="utf8"), object_pairs_hook=pairs)


def digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def ban_private(v: Any):
    if isinstance(v, dict):
        for k, sub in v.items():
            must(isinstance(k, str) and k.lower() not in BANNED
                 and not k.lower().startswith("oracle_"), "PRIVATE_FIELD:" + str(k))
            ban_private(sub)
    elif isinstance(v, list):
        for sub in v:
            ban_private(sub)
    else:
        must(type(v) in (str, int, bool, float, type(None)), "BAD_TYPE")


def validate(v):
    ban_private(v)
    must(isinstance(v, dict) and set(v) == REQUIRED and v["schema"] == PROTOCOL,
         "POLICY_SCHEMA")
    must(isinstance(v["policy_id"], str) and v["policy_id"].strip(), "POLICY_ID")
    must(isinstance(v["policy_evidence_ref"], str) and v["policy_evidence_ref"].strip(),
         "EVIDENCE_REF")
    must(isinstance(v["operation_rules"], dict) and v["operation_rules"], "EMPTY_OPS")
    must(isinstance(v["obligation_rules"], dict), "BAD_OBLIGATIONS")
    for k, literals in v["operation_rules"].items():
        must(isinstance(k, str) and k and isinstance(literals, list), "BAD_OPERATION")
        parse_expr(literals)
    for k, rule in v["obligation_rules"].items():
        must(isinstance(k, str) and k and isinstance(rule, dict)
             and set(rule) == {"when", "done_when"}, "BAD_OBLIGATION")
        parse_expr(rule["when"])
        parse_expr(rule["done_when"])


def parse_expr(literals):
    """Use exact native EC v2 literal grammar: fact:name / not:fact:name.
    No LLM-generated Python, eval(), arbitrary code or implicit FALSE.
    """
    must(isinstance(literals, list) and all(isinstance(v, str) for v in literals)
         and len(set(literals)) == len(literals), "INVALID_CONJUNCTION")
    terms = []
    for v in literals:
        neg = v.startswith("not:fact:")
        prefix = "not:fact:" if neg else "fact:"
        must(v.startswith(prefix) and len(v) > len(prefix), "UNKNOWN_LITERAL:" + v)
        name = v[len(prefix):]
        must(" " not in name and "\n" not in name and ":" not in name,
             "INVALID_ATOM:" + name)
        term = Symbol(name)
        terms.append(Not(term) if neg else term)
    return And(*terms)


def compare_expr(reference_literals, proposed_literals):
    reference = parse_expr(reference_literals)
    proposed = parse_expr(proposed_literals)
    witness = satisfiable(Xor(reference, proposed), all_models=False)
    if witness is False:
        return {"equivalent": True, "counterexample": None}
    return {"equivalent": False, "counterexample": {
        str(k): bool(v) for k, v in sorted(witness.items(), key=lambda x: str(x[0]))
        if str(k) != "True"}}


def compare(reference: dict, proposal: dict, pinned_reference_sha256: str):
    validate(reference)
    validate(proposal)
    must(isinstance(pinned_reference_sha256, str) and len(pinned_reference_sha256) == 64
         and digest(reference) == pinned_reference_sha256, "PINNED_REFERENCE_CHANGED")
    must(reference["policy_id"] == proposal["policy_id"], "POLICY_ID_MISMATCH")
    must(reference["policy_evidence_ref"] == proposal["policy_evidence_ref"],
         "POLICY_SOURCE_REF_MISMATCH")
    output = []
    for family, keys in (("operation_rules", None), ("obligation_rules", ("when", "done_when"))):
        a, b = reference[family], proposal[family]
        missing = sorted(set(a) - set(b))
        additional = sorted(set(b) - set(a))
        if missing or additional:
            output.append({"path": family, "equivalent": False,
                           "missing": missing, "additional": additional, "counterexample": None})
        for key in sorted(set(a) & set(b)):
            components = (keys if keys else (None,))
            for component in components:
                lhs = a[key][component] if component else a[key]
                rhs = b[key][component] if component else b[key]
                item = compare_expr(lhs, rhs)
                output.append({"path": family + "." + key + ("." + component if component else ""),
                               **item})
    eq = all(v["equivalent"] for v in output)
    return {
        "schema": "ISSUE1_INDEPENDENT_FORMAL_POLICY_EQUIVALENCE_V1",
        "reference_sha256": pinned_reference_sha256,
        "proposal_sha256": digest(proposal),
        "formal_equivalent_to_pinned_reference": eq,
        "checks": output,
        "reuse": "SymPy SAT counterexample model checking + EC formal policy v2 grammar",
        "source_independence_established_by_this_algorithm": False,
        "natural_language_meaning_preserved_proven": False,
        "independent_external_authority_proven": False,
        "safe_to_claim_original_phase1_s3_semantic_AC": False,
        "original_science_AC_promoted": 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--proposal", type=Path, required=True)
    ap.add_argument("--pinned-reference-sha256", required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = compare(decode_unique(args.reference), decode_unique(args.proposal),
                     args.pinned_reference_sha256)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf8")
    print(output)
    raise SystemExit(0 if result["formal_equivalent_to_pinned_reference"] else 3)


if __name__ == "__main__":
    main()
