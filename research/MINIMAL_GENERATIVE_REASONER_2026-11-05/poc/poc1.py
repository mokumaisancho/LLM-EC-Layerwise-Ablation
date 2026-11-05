#!/usr/bin/env python3
"""Proof-of-concept: exact predictive quotients and abrupt scope-dependent abstraction loss.
No external LLM, pretraining, packages, datasets, or stochastic evaluation is needed.
"""
import json
import statistics
import time
from pathlib import Path


def output(x):
    return int((x & 3) == 0)


def step(x, a, bits):
    q, h = x & 3, x >> 2
    if a == 2:  # Observe previously hidden state by allowing the probe intervention
        nq = (q + (h & 1)) & 3
    else:
        nq = (q + 1 + a) & 3
    nh = (h >> 1) | (int(a == 1) << (bits - 3))
    return (nh << 2) | nq


def minimal_quotient(bits, actions):
    N = 1 << bits
    obs = [output(x) for x in range(N)]
    labels = obs[:]
    rounds = 0
    start = time.perf_counter()
    while True:
        keys = [(obs[x],) + tuple(labels[step(x, a, bits)] for a in actions) for x in range(N)]
        distinct = {key: idx for idx, key in enumerate(sorted(set(keys)))}
        refined = [distinct[key] for key in keys]
        rounds += 1
        if refined == labels:
            break
        # Group labels may be renumbered, but the stability test must check partition equality.
        # The sorted signature is deterministic and includes obs as its first element.
        labels = refined
        assert rounds <= N + 1
    duration = time.perf_counter() - start
    classes = len(set(labels))
    # Quotient consistency: every member of a class gives the same output and abstract successor.
    witness = {}
    for x in range(N):
        c = labels[x]
        key = (obs[x], tuple(labels[step(x, a, bits)] for a in actions))
        if c in witness:
            assert witness[c] == key
        else:
            witness[c] = key
    assert len(witness) == classes
    return labels, rounds, duration


def exact_symbolic_phi(bits, actions):
    # Derive whether phi(x)=(x & 3) is a valid future-preserving abstraction
    # without constructing a full N-state quotient table.
    count, bad = 0, None
    for x in range(1 << bits):
        for a in actions:
            q_next = (step(x, a, bits) & 3)
            candidate = ((x & 3) + 1 + a) & 3 if a != 2 else (x & 3)
            count += 1
            if q_next != candidate and bad is None:
                bad = {"state": x, "action": a, "actual_abstract_next": q_next,
                       "candidate_abstract_next": candidate}
    return {"tested_transitions": count, "pass": bad is None, "first_counterexample": bad}


def essential_bits(labels, bits):
    return [k for k in range(bits) if any(labels[x] != labels[x ^ (1 << k)]
                                        for x in range(1 << bits))]


def independent_trace_groups(bits, actions, horizon):
    """Independent observable-trace enumeration, not using partitions."""
    all_words = [()]
    frontier = [()]
    for _ in range(horizon):
        frontier = [word + (a,) for word in frontier for a in actions]
        all_words.extend(frontier)
    sigs = []
    for x in range(1 << bits):
        records = []
        for word in all_words:
            s = x
            outs = [output(s)]
            for a in word:
                s = step(s, a, bits)
                outs.append(output(s))
            records.append(tuple(outs))
        sigs.append(tuple(records))
    groups = {}
    return [groups.setdefault(sig, len(groups)) for sig in sigs]


def partitions_same(a, b):
    # An independent equivalence check across all pairs.
    return all((a[x] == a[y]) == (b[x] == b[y])
               for x in range(len(a)) for y in range(x + 1, len(a)))


def estimate_cost(bits, samples=200000, repeats=5):
    # Python microbenchmark on the exact same action sequence: not a general hardware speed claim.
    actions = [i & 1 for i in range(samples)]
    full_times, small_times = [], []
    for _ in range(repeats):
        x = 7
        sink = 0
        t0 = time.perf_counter()
        for a in actions:
            x = step(x, a, bits)
            sink += output(x)
        full_times.append(time.perf_counter() - t0)
        q = 7 & 3
        sink2 = 0
        t0 = time.perf_counter()
        for a in actions:
            q = (q + 1 + a) & 3
            sink2 += int(q == 0)
        small_times.append(time.perf_counter() - t0)
        assert sink == sink2
    return {"operations": samples, "repeats": repeats,
            "full_median_seconds": statistics.median(full_times),
            "small_median_seconds": statistics.median(small_times),
            "observed_speed_ratio": statistics.median(full_times) / statistics.median(small_times),
            "note": "Toy CPython benchmark, same restricted actions; omits quotient-discovery setup."}


def run():
    cases = []
    for bits in (4, 6, 8, 10, 12):
        for scope, actions in (("restricted", (0, 1)), ("probe_allowed", (0, 1, 2))):
            labels, rounds, secs = minimal_quotient(bits, actions)
            support = essential_bits(labels, bits)
            symbolic = exact_symbolic_phi(bits, actions)
            N = 1 << bits
            # Independent exact expected classes on this constructed model.
            assert len(set(labels)) == (4 if scope == "restricted" else N)
            assert support == ([0, 1] if scope == "restricted" else list(range(bits)))
            assert symbolic["pass"] == (scope == "restricted")
            cases.append({"bits": bits, "scope": scope,
                          "microstates": N, "minimal_predictive_states": len(set(labels)),
                          "state_count_ratio": N // len(set(labels)),
                          "minimum_label_bits": (len(set(labels)) - 1).bit_length(),
                          "essential_source_bits": support,
                          "refinement_rounds": rounds,
                          "exact_quotient_check": "PASS", "discovery_seconds": secs,
                          "symbolic_phi_check": symbolic})
    checks = []
    for scope, acts in (("restricted", (0, 1)), ("probe_allowed", (0, 1, 2))):
        labels, _, _ = minimal_quotient(4, acts)
        independent = independent_trace_groups(4, acts, horizon=6)
        checks.append({"scope": scope, "horizon": 6,
                       "independent_trace_check": "PASS" if partitions_same(labels, independent) else "FAIL",
                       "classes": len(set(independent))})
        assert partitions_same(labels, independent)
    # Counterexample for the false claim that x&3 suffices when action2 is permitted.
    x, a = 4, 2
    actual = step(x, a, 12) & 3
    assumed = x & 3
    assert actual != assumed
    # A single random probe has 1/2 expected one-step projection disagreement (uniform hidden h).
    disagreement = sum((step(x, a, 12) & 3) != (x & 3)
                       for x in range(1 << 12)) / (1 << 12)
    assert disagreement == .5
    report = {
        "experiment_id": "GEN001_POC1_FINITE_BEHAVIORAL_QUOTIENT_V1",
        "status": "PASS_SCOPED_SYNTHETIC_ONLY",
        "construction": "q=two low bits; h=other bits; restricted actions cannot expose h; optional probe reads its lowest bit while shifting h",
        "test_cases": cases,
        "independent_trace_tests": checks,
        "false_projection_fault_control": {"state": x, "action": a, "actual_q_next": actual,
                                           "assumed_q_next": assumed, "caught": actual != assumed},
        "probe_one_step_disagreement_uniform_hidden_state": disagreement,
        "pseudocritical_scope": "Action support changes at probe probability p=0: exact future-preserving quotient jumps from 4 to 2^bits for any positive p (under full future action support); not a thermodynamic phase transition.",
        "estimated_per_step_error_approximate_phi_given_probe_probability_p": "p/2 under uniformly random hidden state at current step; not a multi-step error bound",
        "cost_probe": estimate_cost(12),
        "limitations": ["Finite manually constructed state system: not spontaneous discovery of a new principle",
                        "Automata minimization enumerates all 2^bits microstates",
                        "No NN, LLM, biological dynamics, or novel scientific phenomenon tested",
                        "Minimal state count alone is not an end-to-end byte/time reduction",
                        "Ability to define observation, admissible actions, and verifier is assumed"],
        "next_blocker": "Automatically infer the abstraction and transition rule from a compact generative description or limited trajectories, while preserving future behavior under the actual action contract; avoid exhaustive state enumeration and account for discovery cost"
    }
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps({k: v for k, v in result.items() if k != "test_cases"}, ensure_ascii=False, indent=2))
    p = Path(__file__).with_name("results.json")
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
