from __future__ import annotations

"""Compatibility entrypoint for the current Suite V4 atomic gate.

The active gate is V4/R3. This module preserves the legacy callable and exception
surface while preventing callers from silently evaluating an older exact-ref
contract.
"""

from pathlib import Path

from suite_v4_atomic_gate_v4 import (
    EXPECTED_V3_REF,
    EXPECTED_V4_REF,
    ROLLBACK_V4_REF,
    evaluate,
)

EXPECTED_REF = EXPECTED_V4_REF
EXPECTED_V3_PARENT = EXPECTED_V3_REF


class SuiteV4AtomicGateError(RuntimeError):
    """Compatibility exception type retained for older callers."""


def evaluate_atomic_candidate(root: str | Path) -> dict:
    """Evaluate the current fail-closed V4/R3 repin gate."""
    try:
        return evaluate(root)
    except (OSError, ValueError, SyntaxError) as exc:
        raise SuiteV4AtomicGateError(str(exc)) from exc


__all__ = [
    "EXPECTED_REF",
    "EXPECTED_V3_PARENT",
    "ROLLBACK_V4_REF",
    "SuiteV4AtomicGateError",
    "evaluate_atomic_candidate",
]
