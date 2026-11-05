#!/usr/bin/env python3
"""MGR-P1: exact, finite-state minimal predictive representation experiment.

Zero LLMs, zero pretrained weights, zero external dependencies.
A deliberately specified synthetic model: evidence of *conditions*, not
proof of general intelligence or spontaneous discovery of representations.
"""
from __future__ import annotations
import json
from itertools import combinations
from pathlib import Path

BITS = 8
STATES = tuple(range(1 << BITS))
ACTIONS = (0, 1)


def parity(x: int) -> int:
    return x.bit_count() & 1


def encode(phase: int, noise: int) -> int:
    """Invertible coordinate mixing: hide both phase bits in noise parity."""
    m = parity(noise)
    return (noise << 2) | ((phase & 1) ^ m) | (((phase >> 1 ^ m) & 1) << 1)


def decode(z: int) -> tuple[int, int]:
    noise = z >> 2
    m = parity(noise)
    phase = (z & 1 ^ m) | (((z >> 1 ^ m) & 1) << 1)
    return phase, noise


def step(z: int, action: int, k: int) -> int:
    """k of six hidden bits can affect future output through local dynamics."""
    phase, noise = decode(z)
    next_phase = (phase + 1 + action + ((noise & 1) if k else 0)) % 4
    low = (noise & ((1 << k) - 1)) >> 1
    high_width = 6 - k
    high = noise >> k
    high_next = ((17 * high + 13 * phase + 3 * action + 7) &
                 ((1 << high_width) - 1)) if high_width else 0
    return encode(next_phase, low | (high_next << k))


def output(z: int) -> int:
    return decode(z)[0] >> 1


def canonical_groups(signatures: list[tuple]) -> list[int]:
    ids = {v: i for i, v in enumerate(sorted(set(signatures)))}
    return [ids[v] for v in signatures]


def minimal_quotient(k: int) -> tuple[list[int], int]:
    """Standard Moore refinement: equal outputs under all possible futures."""
    groups = canonical_groups([(output(z),) for z in STATES])
    iterations = 0
    while True:
        sig = [(output(z), *(groups[step(z, a, k)] for a in ACTIONS))
               for z in STATES]
        new = canonical_groups(sig)
        iterations += 1
        if new == groups:
            return new, iterations
        groups = new


def prove_quotient(k: int, groups: list[int]) -> bool:
    """Exhaustive congruence check; future parity follows by induction."""
    expected = {}
    for z in STATES:
        sig = (output(z), *(groups[step(z, a, k)] for a in ACTIONS))
        if groups[z] in expected and sig != expected[groups[z]]:
            return False
        expected[groups[z]] = sig
    return True


def projection_valid(k: int, mask: int) -> bool:
    seen = {}
    for z in STATES:
        key = z & mask
        sig = (output(z), *(step(z, a, k) & mask for a in ACTIONS))
        if key in seen and seen[key] != sig:
            return False
        seen[key] = sig
    return True


def smallest_axis_projection(k: int) -> tuple[int, int]:
    for count in range(BITS + 1):
        for positions in combinations(range(BITS), count):
            mask = sum(1 << i for i in positions)
            if projection_valid(k, mask):
                return count, mask
    raise AssertionError("Full state must be a valid projection")


def independent(mask: int, chosen: list[int]) -> bool:
    pivots = {}
    for item in chosen:
        x = item
        while x:
            pos = x.bit_length() - 1
            if pos not in pivots:
                pivots[pos] = x
                break
            x ^= pivots[pos]
    while mask:
        pos = mask.bit_length() - 1
        if pos not in pivots:
            return True
        mask ^= pivots[pos]
    return False


def linear_projection(groups: list[int]) -> tuple[list[int], int]:
    by_group = {}
    for z in STATES:
        by_group.setdefault(groups[z], []).append(z)
    invariants = [
        mask for mask in range(1, 1 << BITS)
        if all(len({parity(z & mask) for z in values}) == 1
               for values in by_group.values())
    ]
    basis = []
    for mask in sorted(invariants, key=lambda v: (v.bit_count(), v)):
        if independent(mask, basis):
            basis.append(mask)
    distinguishable = len({
        tuple(parity(z & m) for m in basis) for z in STATES
    })
    return basis, distinguishable


def negative_control(k: int, groups: list[int]) -> bool:
    """Forcibly merge one output=1 group with an output=0 group: must FAIL."""
    forged = groups[:]
    zero = next(z for z in STATES if output(z) == 0)
    one = next(z for z in STATES if output(z) == 1)
    before = forged[one]
    forged = [forged[zero] if g == before else g for g in forged]
    return not prove_quotient(k, forged)


def run() -> dict:
    assert all(encode(*decode(z)) == z for z in STATES), "Bijection failed"
    records = []
    for k in range(7):
        groups, rounds = minimal_quotient(k)
        n = len(set(groups))
        assert prove_quotient(k, groups), "Invalid future behavior"
        assert negative_control(k, groups), "False positive verifier"
        axis_bits, axis_mask = smallest_axis_projection(k)
        basis, linear_states = linear_projection(groups)
        assert n == (4 if k == 0 else 6 * (1 << (k - 1)))
        assert axis_bits == 8
        assert (linear_states == n) == (k == 0)
        # Check all 256x2 transitions and one-bit output independently
        transition_signatures = {}
        for z in STATES:
            sig = (output(z), *(groups[step(z, a, k)] for a in ACTIONS))
            transition_signatures.setdefault(groups[z], sig)
            assert transition_signatures[groups[z]] == sig
        min_bits = (n - 1).bit_length()
        micro_table_bits = 256 * (2 * 8 + 1)
        macro_table_bits = n * (2 * min_bits + 1)
        records.append({
            "k": k,
            "raw_states": 256,
            "minimal_future_equivalent_states": n,
            "minimal_state_encoding_bits": min_bits,
            "min_axis_aligned_bits": axis_bits,
            "axis_mask": f"0x{axis_mask:02x}",
            "xor_invariant_masks": [f"0x{m:02x}" for m in basis],
            "xor_projection_is_exact": linear_states == n,
            "xor_projection_distinguishable_states": linear_states,
            "xor_projection_gates": sum(m.bit_count() - 1 for m in basis),
            "quotient_refinement_rounds": rounds,
            "explicit_micro_table_bits": micro_table_bits,
            "explicit_quotient_table_bits": macro_table_bits,
            "table_ratio_only": round(micro_table_bits / macro_table_bits, 3),
            "future_congruence_256x2_pass": True,
            "tampered_merge_rejected": True
        })
    return {
        "protocol": "MGR-P1-FINITE-QUOTIENT-V1",
        "environment": "Python standard library, no pretraining/LLM",
        "hypotheses_tested": [
            "H1 coordinate change reveals exact 2-bit future-sufficient state",
            "H2 hidden future influence invalidates a superficially compact projection",
            "H3 exact predictive quotient need not be representable by linear XOR features"
        ],
        "records": records,
        "not_measured": [
            "run-time speedup", "actual NN reasoning ability",
            "general-purpose LLM parity", "minimum program/source length",
            "finding coordinates without enumeration", "physical phase transition"
        ],
        "decision": "Next blocker: learn a future-preserving projection and useful dynamics without enumerating all microstates or hiding costs in transforms, verifiers or physical priors."
    }


if __name__ == "__main__":
    result = run()
    path = Path(__file__).with_name("results.json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
