from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

PROTOCOL = "EC_V4_3_EQUATION_OBJECTIVE_CONTRACT_V1"
REQUIRED_EQUATION_FIELDS = ("equation_id", "variables", "operators", "objective_terms", "constraints", "normalization_terms", "output")


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _seq(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


def _canon_strings(value: Any) -> list[str]:
    return sorted({_norm(x) for x in _seq(value) if _norm(x)})


def _variable_signature(value: Any) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for raw in _seq(value):
        if isinstance(raw, Mapping):
            name = _norm(raw.get("name"))
            role = _norm(raw.get("role")).upper()
            shape = _norm(raw.get("shape"))
        else:
            name, role, shape = _norm(raw), "", ""
        if name:
            out.append((name, role, shape))
    return sorted(set(out))


def equation_fingerprint(equation: Mapping[str, Any]) -> str:
    payload = {
        "variables": _variable_signature(equation.get("variables")),
        "operators": _canon_strings(equation.get("operators")),
        "objective_terms": _canon_strings(equation.get("objective_terms")),
        "constraints": _canon_strings(equation.get("constraints")),
        "normalization_terms": _canon_strings(equation.get("normalization_terms")),
        "output": _norm(equation.get("output")),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def validate_equation_contract(contract: Mapping[str, Any] | None) -> dict[str, Any]:
    c = dict(contract or {})
    equations = _seq(c.get("equations"))
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    fingerprints: dict[str, str] = {}

    if not equations:
        errors.append({"type": "EQUATIONS_REQUIRED"})

    for index, raw in enumerate(equations):
        if not isinstance(raw, Mapping):
            errors.append({"type": "EQUATION_INVALID", "index": index})
            continue
        eq = dict(raw)
        eq_id = _norm(eq.get("equation_id"))
        if not eq_id:
            errors.append({"type": "EQUATION_ID_REQUIRED", "index": index})
            continue
        if eq_id in seen:
            errors.append({"type": "DUPLICATE_EQUATION_ID", "equation_id": eq_id})
        seen.add(eq_id)
        for field in REQUIRED_EQUATION_FIELDS[1:]:
            if field not in eq or eq.get(field) is None:
                errors.append({"type": "EQUATION_FIELD_REQUIRED", "equation_id": eq_id, "field": field})
        if not _variable_signature(eq.get("variables")):
            errors.append({"type": "EQUATION_VARIABLES_REQUIRED", "equation_id": eq_id})
        if not _canon_strings(eq.get("operators")):
            errors.append({"type": "EQUATION_OPERATORS_REQUIRED", "equation_id": eq_id})
        if not _norm(eq.get("output")):
            errors.append({"type": "EQUATION_OUTPUT_REQUIRED", "equation_id": eq_id})
        fingerprints[eq_id] = equation_fingerprint(eq)

    groups: dict[str, list[str]] = {}
    for eq_id, fp in fingerprints.items():
        groups.setdefault(fp, []).append(eq_id)
    duplicate_semantics = [ids for ids in groups.values() if len(ids) > 1]

    return {
        "protocol": PROTOCOL,
        "status": "PASS" if not errors else "REFRAME",
        "errors": errors,
        "equation_fingerprints": fingerprints,
        "semantically_identical_equation_groups": duplicate_semantics,
    }


def verify_equation_evidence(contract: Mapping[str, Any] | None, evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    definition = validate_equation_contract(contract)
    if definition["status"] != "PASS":
        return {"protocol": PROTOCOL, "status": "BLOCKED", "reason": "EQUATION_CONTRACT_INVALID", "errors": definition["errors"]}

    c = dict(contract or {})
    ev = dict(evidence or {})
    expected = {str(x["equation_id"]): dict(x) for x in _seq(c.get("equations")) if isinstance(x, Mapping)}
    observed = {str(x.get("equation_id")): dict(x) for x in _seq(ev.get("equations")) if isinstance(x, Mapping) and x.get("equation_id")}
    errors: list[dict[str, Any]] = []
    implementation_fingerprints: dict[str, str] = {}

    for eq_id, exp in expected.items():
        obs = observed.get(eq_id)
        if obs is None:
            errors.append({"type": "EQUATION_IMPLEMENTATION_EVIDENCE_MISSING", "equation_id": eq_id})
            continue
        if not _norm(obs.get("evidence_ref")):
            errors.append({"type": "EQUATION_EVIDENCE_REF_REQUIRED", "equation_id": eq_id})

        checks = (
            ("variables", _variable_signature(exp.get("variables")), _variable_signature(obs.get("variables"))),
            ("operators", _canon_strings(exp.get("operators")), _canon_strings(obs.get("operators"))),
            ("objective_terms", _canon_strings(exp.get("objective_terms")), _canon_strings(obs.get("objective_terms"))),
            ("constraints", _canon_strings(exp.get("constraints")), _canon_strings(obs.get("constraints"))),
            ("normalization_terms", _canon_strings(exp.get("normalization_terms")), _canon_strings(obs.get("normalization_terms"))),
        )
        for field, want, got in checks:
            if want != got:
                errors.append({"type": "EQUATION_SEMANTICS_MISMATCH", "equation_id": eq_id, "field": field, "expected": want, "observed": got})
        if _norm(exp.get("output")) != _norm(obs.get("output")):
            errors.append({"type": "EQUATION_OUTPUT_MISMATCH", "equation_id": eq_id, "expected": _norm(exp.get("output")), "observed": _norm(obs.get("output"))})

        implementation_fingerprints[eq_id] = _norm(obs.get("implementation_fingerprint")) or equation_fingerprint(obs)

    # If mathematically distinct equations are all mapped to one implementation fingerprint,
    # their semantics have been collapsed (e.g. scalar/diagonal/dense objectives -> one generic LS path).
    expected_fp = definition["equation_fingerprints"]
    ids = sorted(expected)
    for i, left in enumerate(ids):
        for right in ids[i + 1:]:
            if expected_fp.get(left) == expected_fp.get(right):
                continue
            l_impl = implementation_fingerprints.get(left)
            r_impl = implementation_fingerprints.get(right)
            if l_impl and l_impl == r_impl:
                errors.append({"type": "DISTINCT_EQUATIONS_COLLAPSED", "equation_ids": [left, right], "implementation_fingerprint": l_impl})

    unexpected = sorted(set(observed) - set(expected))
    if unexpected:
        errors.append({"type": "UNEXPECTED_EQUATION_IMPLEMENTATIONS", "equation_ids": unexpected})

    return {
        "protocol": PROTOCOL,
        "status": "PASS" if not errors else "BLOCKED",
        "errors": errors,
        "equation_count": len(expected),
        "implementation_fingerprints": implementation_fingerprints,
    }
