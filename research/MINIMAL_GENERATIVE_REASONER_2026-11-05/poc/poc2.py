#!/usr/bin/env python3
"""Counterfactual probe discovers relevant source bits, even for huge implicit state spaces.
No training, model compression, or large LLM. Discovery is conditional on chosen probes/horizon.
"""
import json
import random
from pathlib import Path


def output(x):
    return int((x & 3) == 0)


def step(x, a, bits):
    q, h = x & 3, x >> 2
    nq = (q + (h & 1)) & 3 if a == 2 else (q + 1 + a) & 3
    nh = (h >> 1) | (int(a == 1) << (bits - 3))
    return (nh << 2) | nq


def trace(x, actions, bits):
    results = [output(x)]
    for a in actions:
        x = step(x, a, bits)
        results.append(output(x))
    return tuple(results)


def discover_support(bits, action_set, horizon):
    """Pairwise interventions from zero state; test repeated permitted actions only.

    This is a deliberately simple non-exhaustive discovery heuristic, NOT a proof of
    globally sufficient abstraction for an arbitrary black-box system.
    """
    action_words = [tuple([a] * horizon) for a in action_set]
    queries = 0
    support, earliest = [], {}
    for bit in range(bits):
        found = False
        for word in action_words:
            t0 = trace(0, word, bits)
            t1 = trace(1 << bit, word, bits)
            queries += 2
            differences = [t for t, (u, v) in enumerate(zip(t0, t1)) if u != v]
            if differences:
                earliest[bit] = min(earliest.get(bit, horizon + 1), differences[0])
                found = True
        if found:
            support.append(bit)
    return {"support_bits": support, "min_impact_horizon_per_bit": earliest,
            "trajectory_queries": queries, "action_words": len(action_words),
            "exhaustive_state_enumeration": False}


def rare_action_one_step(bits, samples=1000, rare_probe_probability=.001, seed=20261105):
    rng = random.Random(seed)
    observed_probe = 0
    found = set()
    # Passive observation records one-step traces, with matched one-bit perturbation
    # only as a diagnostic proxy for observation-limited causal identification.
    for _ in range(samples):
        a = 2 if rng.random() < rare_probe_probability else rng.randrange(2)
        observed_probe += (a == 2)
        x = rng.randrange(1 << bits)
        bit = rng.randrange(bits)
        if trace(x, (a,), bits) != trace(x ^ (1 << bit), (a,), bits):
            found.add(bit)
    return {"samples": samples, "rare_probe_probability": rare_probe_probability,
            "observed_probes": observed_probe, "seen_effect_bits": sorted(found),
            "meaning": "Random action policy plus paired one-bit perturbation; not a purely passive observation and not a guarantee of global support"}


def run():
    tests = []
    for bits in (12, 20, 32):
        restricted = discover_support(bits, (0, 1), bits)
        expanded = discover_support(bits, (0, 1, 2), bits)
        assert restricted["support_bits"] == [0, 1]
        assert expanded["support_bits"] == list(range(bits))
        tests.append({"bits": bits, "implicit_microstates": 1 << bits,
                      "restricted": restricted, "probe_allowed": expanded})
    horizons = []
    for h in (0, 1, 2, 4, 8, 16, 18):
        x = discover_support(20, (0, 1, 2), h)
        assert len(x["support_bits"]) == min(20, 2 + h)
        horizons.append({"horizon": h, "detected_support_count": len(x["support_bits"]),
                         "support_bits": x["support_bits"]})
    passive = [rare_action_one_step(20, samples=s) for s in (1000, 5000)]
    result = {
        "experiment_id": "GEN001_POC2_COUNTERFACTUAL_SUPPORT_V1",
        "status": "PASS_SCOPED_DIAGNOSTIC_ONLY",
        "tests": tests,
        "horizon_sweep": horizons,
        "rare_action_one_step_controls": passive,
        "interpretation": "20-32 bit support found via O(bits) intervention trajectory queries and O(bits^2) simulated transition steps without enumerating 2^bits states; exactness is certified only in separately exhaustive small-system POC1.",
        "limitations": ["Hand-designed counterfactuals, not general symbolic causal discovery",
                        "Bit relevance is necessary but not sufficient for constructing a minimal Markov abstraction",
                        "No guarantee that an unseen branch, alternative starting state or action word is harmless",
                        "Large-n result is sampled diagnostic, not an exhaustive formal proof"],
        "next_blocker": "Turn inferred support into a verifiably future-preserving abstraction with proof or counterexample-guided refinement, without 2^bits state enumeration"
    }
    Path(__file__).with_name("results2.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    j = run()
    print(json.dumps({k: v for k, v in j.items() if k != "tests"}, ensure_ascii=False, indent=2))
    for x in j["tests"]:
        print(f'{x["bits"]} bits, restricted {len(x["restricted"]["support_bits"])} bits, probe {len(x["probe_allowed"]["support_bits"])} bits, queries {x["probe_allowed"]["trajectory_queries"]}')
