#!/usr/bin/env python3
"""MGR-P3: 2-bit XOR projection discovery from partial observations.

Projector selection sees sampled microstates and their two successors only.
The exhaustive 256-state test is applied strictly AFTER projector selection.
Ten seeds per case; no LLM, no weights, no training or external packages.
"""
import json
import random
from pathlib import Path
from run_poc import STATES, ACTIONS, parity, step, output

MASKS = sorted(range(1, 256), key=lambda m: (m.bit_count(), m))
PAIRS = [(a, b) for i, a in enumerate(MASKS) for b in MASKS[i + 1:]]


def valid_pair(k, pair, states):
    m1, m2 = pair
    seen = {}
    for z in states:
        key = parity(z & m1) | (parity(z & m2) << 1)
        after = []
        for action in ACTIONS:
            zz = step(z, action, k)
            after.append(parity(zz & m1) | (parity(zz & m2) << 1))
        sig = (output(z), *after)
        if key in seen and seen[key] != sig:
            return False
        seen[key] = sig
    return True


def discover(k, sample):
    for idx, pair in enumerate(PAIRS, start=1):
        if valid_pair(k, pair, sample):
            return pair, idx
    return None, len(PAIRS)


def run():
    records = []
    for k in (0, 1):
        for size in (8, 12, 16, 24, 32, 64):
            for seed_index in range(10):
                seed = 20261105 + seed_index
                sample = random.Random(seed + 1000 * k).sample(STATES, size)
                pair, attempted = discover(k, sample)
                passed = pair is not None and valid_pair(k, pair, STATES)
                records.append({
                    "k": k, "observed_states": size, "seed": seed,
                    "candidate": [f"0x{m:02x}" for m in pair] if pair else None,
                    "tested_mask_pairs": attempted,
                    "sample_pass": pair is not None,
                    "independent_full_state_pass": bool(passed),
                    "false_pass": pair is not None and not passed
                })
    summary = []
    for k in (0, 1):
        for size in (8, 12, 16, 24, 32, 64):
            sub = [r for r in records if r["k"] == k and r["observed_states"] == size]
            summary.append({
                "k": k, "observed_states": size, "seeds": len(sub),
                "sample_pass_count": sum(r["sample_pass"] for r in sub),
                "full_pass_count": sum(r["independent_full_state_pass"] for r in sub),
                "false_pass_count": sum(r["false_pass"] for r in sub),
                "no_candidate_count": sum(not r["sample_pass"] for r in sub)
            })
    return {
        "protocol": "MGR-P3-PARTIAL-TRANSITION-PROJECTION-V2",
        "method": "32,385 two-mask XOR projections; sample-only selection; frozen candidate then exhaustive world check. Ten seeds per condition.",
        "candidate_count": len(PAIRS), "summary": summary, "runs": records,
        "limitations": [
            "Synthetic eight-bit model family, not general intelligence",
            "Strong interface: both successor states observable for sampled states",
            "Search restricted to linear two-bit XOR masks",
            "Exhaustive-world validation is post-selection external oracle",
            "No actual NN or CPU/memory acceleration measured"
        ]
    }


if __name__ == "__main__":
    result = run()
    Path(__file__).with_name("sparse_discovery_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    for row in result["summary"]:
        print(row)
