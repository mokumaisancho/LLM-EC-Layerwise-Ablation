from __future__ import annotations

import itertools
from typing import Any, Iterable, Sequence

PROTOCOL = "S1C_V31_PUBLIC_HYPOTHESIS_V1"
OPERATIONS = ("KEEP", "SET0", "SET1", "FLIP")
STATE_SPACE = tuple(itertools.product((0, 1), repeat=3))
TRAINING_PROBE_INDICES = (0, 1, 2, 4)
EVALUATION_PROBE_INDICES = (3, 5, 6, 7)

def normalize_code(code: Sequence[str]) -> tuple[str, str, str]:
    value = tuple(str(x).upper() for x in code)
    if len(value) != 3 or any(x not in OPERATIONS for x in value):
        raise ValueError("INVALID_PUBLIC_TRANSFORM_CODE")
    return value  # type: ignore[return-value]


def apply_code(code: Sequence[str], state: Sequence[int]) -> tuple[int, int, int]:
    ops = normalize_code(code)
    bits = tuple(int(x) for x in state)
    if len(bits) != 3 or any(x not in (0, 1) for x in bits):
        raise ValueError("INVALID_PUBLIC_STATE")
    out = []
    for op, bit in zip(ops, bits):
        if op == "KEEP":
            out.append(bit)
        elif op == "SET0":
            out.append(0)
        elif op == "SET1":
            out.append(1)
        else:
            out.append(1 - bit)
    return tuple(out)  # type: ignore[return-value]


def all_codes() -> tuple[tuple[str, str, str], ...]:
    return tuple(itertools.product(OPERATIONS, repeat=3))


PUBLIC_HYPOTHESES = all_codes()


def probe_input(index: int) -> tuple[int, int, int]:
    if not isinstance(index, int) or not 0 <= index < len(STATE_SPACE):
        raise ValueError("INVALID_PROBE_INDEX")
    return STATE_SPACE[index]


def observation(code: Sequence[str], index: int) -> dict[str, Any]:
    before = probe_input(index)
    return {
        "probe_id": f"Q{index:02d}",
        "before": list(before),
        "after": list(apply_code(code, before)),
    }


def observations(code: Sequence[str], indices: Iterable[int]) -> list[dict[str, Any]]:
    return [observation(code, int(i)) for i in indices]


def _parse_observation(row: dict[str, Any]) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    if not isinstance(row, dict):
        raise ValueError("OBSERVATION_OBJECT_REQUIRED")
    before = tuple(int(x) for x in row.get("before", ()))
    after = tuple(int(x) for x in row.get("after", ()))
    if len(before) != 3 or len(after) != 3 or any(x not in (0, 1) for x in before + after):
        raise ValueError("OBSERVATION_BITS_INVALID")
    return before, after  # type: ignore[return-value]


def candidates(rows: Iterable[dict[str, Any]]) -> tuple[tuple[str, str, str], ...]:
    parsed = [_parse_observation(x) for x in rows]
    return tuple(
        code
        for code in PUBLIC_HYPOTHESES
        if all(apply_code(code, before) == after for before, after in parsed)
    )


def code_key(code: Sequence[str]) -> str:
    return "|".join(normalize_code(code))


def code_from_key(value: str) -> tuple[str, str, str]:
    return normalize_code(str(value).split("|"))


def evaluation_predictions(code: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {
            "probe_id": f"Q{i:02d}",
            "predicted_after": list(apply_code(code, probe_input(i))),
        }
        for i in EVALUATION_PROBE_INDICES
    ]


def public_manifest() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "state_space": "3 binary coordinates",
        "coordinate_operations": list(OPERATIONS),
        "function_count": len(PUBLIC_HYPOTHESES),
        "training_probe_indices": list(TRAINING_PROBE_INDICES),
        "evaluation_probe_indices": list(EVALUATION_PROBE_INDICES),
        "selected_target_functions_visible": False,
        "semantic_slot_names_encoded": False,
    }


__all__ = [
    "PROTOCOL",
    "OPERATIONS",
    "STATE_SPACE",
    "TRAINING_PROBE_INDICES",
    "EVALUATION_PROBE_INDICES",
    "PUBLIC_HYPOTHESES",
    "all_codes",
    "apply_code",
    "candidates",
    "code_key",
    "code_from_key",
    "evaluation_predictions",
    "normalize_code",
    "observation",
    "observations",
    "probe_input",
    "public_manifest",
]
