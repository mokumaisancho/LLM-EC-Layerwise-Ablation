#!/usr/bin/env python3
"""P0 structural PoC: sufficient-state proof by dependency closure, no enumeration.
A small executable bit-level circuit is the single source for evaluation and support.
"""
import json
import random
from pathlib import Path


class E:
    def __init__(self, op, *args):
        self.op, self.args = op, args

    def deps(self):
        if self.op == 'var':
            return {self.args[0]}
        if self.op == 'const':
            return set()
        result = set()
        for e in self.args:
            result |= e.deps()
        return result

    def calc(self, x):
        if self.op == 'var':
            return (x >> self.args[0]) & 1
        if self.op == 'const':
            return self.args[0]
        vals = [e.calc(x) for e in self.args]
        if self.op == 'not':
            return 1 - vals[0]
        if self.op == 'xor':
            return vals[0] ^ vals[1]
        if self.op == 'and':
            return vals[0] & vals[1]
        raise AssertionError(self.op)


def V(i):
    return E('var', i)


def C(i):
    return E('const', i)


def N(a):
    return E('not', a)


def X(a, b):
    return E('xor', a, b)


def A(a, b):
    return E('and', a, b)


def circuit(n, action):
    q0, q1, h0 = V(0), V(1), V(2)
    if action == 0:
        lo = [N(q0), X(q1, q0)]  # q + 1 mod 4
    elif action == 1:
        lo = [q0, N(q1)]  # q + 2 mod 4
    elif action == 2:
        lo = [X(q0, h0), X(q1, A(q0, h0))]  # q + h0 mod 4
    else:
        raise AssertionError(action)
    return lo + [V(i + 1) for i in range(2, n - 1)] + [C(int(action == 1))]


def full_reference(x, action, n):
    q, h = x & 3, x >> 2
    new_q = ((q + (h & 1)) & 3) if action == 2 else ((q + 1 + action) & 3)
    new_h = (h >> 1) | (int(action == 1) << (n - 3))
    return (new_h << 2) | new_q


def evaluate(expressions, x):
    return sum(e.calc(x) << i for i, e in enumerate(expressions))


def structural_closure(n, actions):
    transforms = {a: circuit(n, a) for a in actions}
    keep = {0, 1}  # output == (q == 0) depends on these two bits
    sequence = [len(keep)]
    rounds = 0
    while True:
        newer = set(keep)
        for a in actions:
            for i in keep:
                newer |= transforms[a][i].deps()
        rounds += 1
        if newer == keep:
            break
        keep = newer
        sequence.append(len(keep))
    # This is a constructive future-preservation certificate: kept next-state
    # coordinates refer only to kept previous-state coordinates under each action.
    for a in actions:
        for i in keep:
            assert transforms[a][i].deps() <= keep
    return sorted(keep), rounds, sequence


def validate_against_reference(n, exhaustive=False, samples=2000):
    rng = random.Random(20261105 + n)
    states = range(1 << n) if exhaustive else (rng.getrandbits(n) for _ in range(samples))
    count = 0
    transforms = {a: circuit(n, a) for a in (0, 1, 2)}
    for x in states:
        for a, trans in transforms.items():
            assert evaluate(trans, x) == full_reference(x, a, n)
            count += 1
    return {'n': n, 'mode': 'exhaustive' if exhaustive else 'sample', 'checked': count, 'result': 'PASS'}


def run():
    validations = [validate_against_reference(n, exhaustive=True) for n in (4, 8, 12)]
    validations.append(validate_against_reference(128, exhaustive=False))
    cases = []
    for n in (12, 32, 128):
        for name, actions in (('restricted', (0, 1)), ('probe_allowed', (0, 1, 2))):
            kept, rounds, sequence = structural_closure(n, actions)
            assert kept == ([0, 1] if name == 'restricted' else list(range(n)))
            cases.append({'n': n, 'scope': name, 'retained_bits': kept,
                          'retained_count': len(kept), 'closure_rounds': rounds,
                          'intermediate_support_sizes': sequence,
                          'nominal_microstate_count': str(1 << n),
                          'soundness': 'PROVED_WITH_RESPECT_TO_CIRCUIT_DEPENDENCIES'})
    # A certificate for (0,1) cannot be reused when action 2 is newly allowed.
    x = 4
    false_conclusion = (full_reference(x, 2, 128) & 3) == (x & 3)
    assert not false_conclusion
    result = {
        'experiment_id': 'GEN001_POC3_SYMBOLIC_DEPENDENCY_CLOSURE_V1',
        'status': 'PASS_STRUCTURAL_PROOF_FOR_GENERATED_CIRCUIT_ONLY',
        'validations': validations, 'cases': cases,
        'scope_violation_fault_control': {'state': x, 'action': 2,
                                          'predicted_q_if_scope_unchanged': x & 3,
                                          'actual_q': full_reference(x, 2, 128) & 3,
                                          'caught': True},
        'conclusion': 'For this generated finite Boolean circuit, all kept successor bits depend only on kept bits for each admitted action; this guarantees output and future-state preservation without enumerating states.',
        'remaining_blocker': 'Build a trusted semantics-preserving translation from real ECv4.4/small-reasoner operations to a symbolic dependency IR; then derive the minimal (rather than merely sufficient) generative state and show useful novel reasoning on unseen tasks.',
        'limitations': ['Structural closure is sufficient but may not be minimal with cancellations or non-bitwise encodings',
                        'The circuit is handcrafted; compiler correctness for external code is not proven',
                        'The 128-bit validation is sampled; the structural theorem is relative to the generated circuit',
                        'No natural law discovery, living system, or LLM reasoning tested']}
    Path(__file__).with_name('results3.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


if __name__ == '__main__':
    result = run()
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, indent=2))
    for c in result['cases']:
        print(f'{c["n"]} bits, {c["scope"]}, retained {c["retained_count"]}, rounds {c["closure_rounds"]}')
