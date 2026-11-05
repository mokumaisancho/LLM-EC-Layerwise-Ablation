#!/usr/bin/env python3
"""MGR-P2: short observation can make an invalid state quotient look exact.
Standard-library only. Depends on neighboring run_poc.py (MGR-P1).
"""
import json
from collections import Counter, deque
from pathlib import Path
from run_poc import ACTIONS, STATES, output, step, canonical_groups, minimal_quotient


def false_merges(coarse, exact):
    count_coarse = Counter(coarse)
    count_joint = Counter(zip(coarse, exact))
    comb2 = lambda n: n * (n - 1) // 2
    return sum(comb2(n) for n in count_coarse.values()) - sum(comb2(n) for n in count_joint.values())


def witness(k, coarse, exact):
    by_coarse = {}
    for z in STATES:
        by_coarse.setdefault(coarse[z], []).append(z)
    for members in by_coarse.values():
        representatives = {}
        for z in members:
            representatives.setdefault(exact[z], z)
            if len(representatives) > 1:
                a, b = list(representatives.values())[:2]
                queue = deque([(a, b, ())])
                visited = {(a, b)}
                while queue:
                    x, y, actions = queue.popleft()
                    if output(x) != output(y):
                        return {
                            "initial_states": [a, b],
                            "distinguishing_actions": list(actions),
                            "output_pair": [output(x), output(y)],
                            "steps_to_distinguish": len(actions)
                        }
                    for action in ACTIONS:
                        pair = (step(x, action, k), step(y, action, k))
                        if pair not in visited:
                            visited.add(pair)
                            queue.append((*pair, actions + (action,)))
                raise AssertionError("Different true causal states must be distinguishable")
    return None


def run():
    results = []
    for k in range(7):
        exact, _ = minimal_quotient(k)
        groups = canonical_groups([(output(z),) for z in STATES])
        records = []
        groups_h1 = None
        for h in range(9):
            records.append({
                "horizon_steps": h,
                "apparent_states": len(set(groups)),
                "false_future_equivalence_pairs": false_merges(groups, exact)
            })
            if h < 8:
                groups = canonical_groups([
                    (output(z), *(groups[step(z, u, k)] for u in ACTIONS))
                    for z in STATES
                ])
                if h == 0:
                    groups_h1 = groups
        first_exact = next(r["horizon_steps"] for r in records
                           if r["false_future_equivalence_pairs"] == 0)
        results.append({
            "k": k,
            "true_minimal_states": len(set(exact)),
            "minimum_horizon_to_exact": first_exact,
            "depths": records,
            "horizon_1_false_merge_witness": witness(k, groups_h1, exact)
        })
    return {
        "protocol": "MGR-P2-OBSERVATION-HORIZON-V1",
        "method": "All synthetic states covered; horizon truncation is NOT random observation sampling",
        "results": results,
        "not_claimed": [
            "sample complexity for unknown real systems",
            "general intelligence",
            "weights-only inference",
            "unbounded or physically-real phase transitions"
        ]
    }


if __name__ == "__main__":
    result = run()
    dest = Path(__file__).with_name("horizon_results.json")
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    for row in result["results"]:
        print(row["k"], row["true_minimal_states"], row["minimum_horizon_to_exact"])
    print("k6 horizon-1 counterexample:", result["results"][6]["horizon_1_false_merge_witness"])
