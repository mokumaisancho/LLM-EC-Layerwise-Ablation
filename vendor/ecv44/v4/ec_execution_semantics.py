from __future__ import annotations

from typing import Any, Mapping, Sequence

PROTOCOL = "EC_V4_2_EXECUTION_SEMANTICS_V1"
CADENCES = frozenset({"PER_SAMPLE", "PER_MINIBATCH", "PER_STEP", "PER_EPOCH", "PER_RUN", "ONCE"})
DEFAULT_MIN_STOCHASTIC_SEEDS = 3


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


def validate_execution_contract(contract: Mapping[str, Any] | None) -> dict[str, Any]:
    c = dict(contract or {})
    errors: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []

    transforms = _list(c.get("dynamic_transformations"))
    for index, raw in enumerate(transforms):
        item = dict(raw) if isinstance(raw, Mapping) else {}
        tid = _norm(item.get("id"))
        cadence = _norm(item.get("required_cadence")).upper()
        source_ref = _norm(item.get("source_ref"))
        if not tid:
            errors.append({"type": "TRANSFORMATION_ID_REQUIRED", "index": index})
        if cadence not in CADENCES:
            errors.append({"type": "TRANSFORMATION_CADENCE_REQUIRED", "id": tid or None, "value": cadence or None})
        if not source_ref:
            errors.append({"type": "TRANSFORMATION_SOURCE_REF_REQUIRED", "id": tid or None})
        trace.append({"check": "DYNAMIC_TRANSFORMATION", "id": tid or None, "required_cadence": cadence or None, "ok": bool(tid and cadence in CADENCES and source_ref)})

    stochastic = bool(c.get("stochastic"))
    generalization_claim = bool(c.get("generalization_claim"))
    evaluation = c.get("evaluation")
    evaluation = dict(evaluation) if isinstance(evaluation, Mapping) else {}
    min_seeds = int(evaluation.get("minimum_distinct_seeds") or 0)
    if stochastic and min_seeds < DEFAULT_MIN_STOCHASTIC_SEEDS:
        errors.append({"type": "STOCHASTIC_MIN_SEEDS_TOO_LOW", "minimum_required": DEFAULT_MIN_STOCHASTIC_SEEDS, "configured": min_seeds})

    partitions = {_norm(x).upper() for x in _list(evaluation.get("required_partitions")) if _norm(x)}
    if not partitions:
        errors.append({"type": "EVALUATION_PARTITIONS_REQUIRED"})
    if generalization_claim and "OOD" not in partitions:
        errors.append({"type": "OOD_PARTITION_REQUIRED_FOR_GENERALIZATION"})

    aggregation = _norm(evaluation.get("aggregation")).upper()
    if stochastic and aggregation not in {"PER_SEED_AND_AGGREGATE", "PER_SEED"}:
        errors.append({"type": "PER_SEED_AGGREGATION_REQUIRED", "value": aggregation or None})

    return {
        "protocol": PROTOCOL,
        "status": "PASS" if not errors else "REFRAME",
        "errors": errors,
        "decision_trace": trace,
        "requirements": {
            "stochastic": stochastic,
            "generalization_claim": generalization_claim,
            "minimum_distinct_seeds": min_seeds,
            "required_partitions": sorted(partitions),
            "aggregation": aggregation or None,
        },
    }


def verify_execution_evidence(contract: Mapping[str, Any] | None, evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    definition = validate_execution_contract(contract)
    if definition["status"] != "PASS":
        return {"protocol": PROTOCOL, "status": "BLOCKED", "reason": "EXECUTION_CONTRACT_INVALID", "definition": definition, "errors": list(definition["errors"])}

    c = dict(contract or {})
    ev = dict(evidence or {})
    errors: list[dict[str, Any]] = []
    observed_transforms = {
        _norm(x.get("id")): dict(x)
        for x in _list(ev.get("dynamic_transformations"))
        if isinstance(x, Mapping) and _norm(x.get("id"))
    }
    for raw in _list(c.get("dynamic_transformations")):
        item = dict(raw)
        tid = _norm(item.get("id"))
        required = _norm(item.get("required_cadence")).upper()
        observed = observed_transforms.get(tid, {})
        actual = _norm(observed.get("observed_cadence")).upper()
        if actual != required:
            errors.append({"type": "TRANSFORMATION_CADENCE_MISMATCH", "id": tid, "required": required, "observed": actual or None})
        if not _norm(observed.get("evidence_ref")):
            errors.append({"type": "TRANSFORMATION_RUNTIME_EVIDENCE_REQUIRED", "id": tid})

    evaluation = dict(c.get("evaluation") or {})
    minimum = int(evaluation.get("minimum_distinct_seeds") or 0)
    seeds = {_norm(x) for x in _list(ev.get("seeds")) if _norm(x)}
    if len(seeds) < minimum:
        errors.append({"type": "INSUFFICIENT_DISTINCT_SEEDS", "minimum_required": minimum, "observed": len(seeds)})

    required_partitions = {_norm(x).upper() for x in _list(evaluation.get("required_partitions")) if _norm(x)}
    observed_partitions = {_norm(x).upper() for x in _list(ev.get("evaluated_partitions")) if _norm(x)}
    missing_partitions = sorted(required_partitions - observed_partitions)
    if missing_partitions:
        errors.append({"type": "EVALUATION_PARTITIONS_MISSING", "missing": missing_partitions})

    per_seed = ev.get("per_seed_results")
    if bool(c.get("stochastic")) and not isinstance(per_seed, Mapping):
        errors.append({"type": "PER_SEED_RESULTS_REQUIRED"})
    elif isinstance(per_seed, Mapping):
        keys = {str(k) for k in per_seed}
        missing_seed_results = sorted(seed for seed in seeds if seed not in keys)
        if missing_seed_results:
            errors.append({"type": "PER_SEED_RESULTS_INCOMPLETE", "missing": missing_seed_results})

    return {
        "protocol": PROTOCOL,
        "status": "PASS" if not errors else "BLOCKED",
        "errors": errors,
        "observed": {"distinct_seed_count": len(seeds), "evaluated_partitions": sorted(observed_partitions)},
    }
