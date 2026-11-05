#!/usr/bin/env python3
"""Exact minimum predictive quotient of a scrambled GF(2) system.
Proof: observable rows W=span(C, C M_a, C M_a M_b, ...). States with
identical future outputs are precisely ker(W), hence 2^rank(W) classes.
No 2^n enumeration is used except for independent n<=8 cross-checks.
"""
import json
from pathlib import Path


def dot(row, state):
    return (row & state).bit_count() & 1


def eval_rows(rows, state):
    return sum(dot(row, state) << i for i, row in enumerate(rows))


def mul_row(row, matrix):
    v = 0
    while row:
        bit = row & -row
        v ^= matrix[bit.bit_length() - 1]
        row ^= bit
    return v


def mul(a, b):
    return [mul_row(row, b) for row in a]


def system(n):
    allbits = (1 << n) - 1
    A = [allbits, allbits ^ 2] + [1 << i for i in range(2, n)]
    B = [2 ^ (allbits ^ 3), 3] + [1 << i for i in range(2, n)]
    assert mul(A, B) == [1 << i for i in range(n)]
    def native(action):
        pair = {0: [2, 1], 1: [3, 1], 2: [5, 2]}[action]
        tail = ([1 << (i + 1) for i in range(2, n - 1)] + [4]) if action == 2 else [1 << i for i in range(2, n)]
        return pair + tail
    return {a: mul(mul(B, native(a)), A) for a in range(3)}, A[0]


def quotient(matrices, observed_row, actions):
    pivots = {}
    def add(row):
        while row:
            p = row.bit_length() - 1
            if p in pivots:
                row ^= pivots[p]
            else:
                pivots[p] = row
                return True
        return False
    add(observed_row)
    while True:
        previous = len(pivots)
        snapshot = list(pivots.values())
        for row in snapshot:
            for a in actions:
                add(mul_row(row, matrices[a]))
        if len(pivots) == previous:
            break
    basis = [pivots[p] for p in sorted(pivots, reverse=True)]
    def coeff(row):
        encoded = 0
        for j, b in enumerate(basis):
            if (row >> (b.bit_length() - 1)) & 1:
                row ^= b
                encoded ^= 1 << j
        assert row == 0
        return encoded
    updates = {a: [coeff(mul_row(b, matrices[a])) for b in basis] for a in actions}
    readout = coeff(observed_row)
    for a in actions:
        for b, update in zip(basis, updates[a]):
            assert mul_row(b, matrices[a]) == mul_row(update, basis)
    return basis, updates, readout


def exhaustive_check(n, matrices, observed, actions, basis):
    count = 1 << n
    labels = [dot(observed, x) for x in range(count)]
    while True:
        signatures = [(dot(observed, x),) + tuple(labels[eval_rows(matrices[a], x)] for a in actions) for x in range(count)]
        dictionary = {s: k for k, s in enumerate(sorted(set(signatures)))}
        newer = [dictionary[s] for s in signatures]
        if len(set(newer)) == len(set(labels)):
            labels = newer
            break
        labels = newer
    projected = [eval_rows(basis, x) for x in range(count)]
    l2p, p2l = {}, {}
    for label, p in zip(labels, projected):
        assert l2p.setdefault(label, p) == p
        assert p2l.setdefault(p, label) == label
    assert len(l2p) == 1 << len(basis)
    return len(l2p)


def run():
    results = []
    for n in (6, 8, 16, 32, 128):
        matrices, observed = system(n)
        assert observed.bit_count() == n
        for scope, acts, expected in [('restricted', (0, 1), 2), ('probe_allowed', (0, 1, 2), n)]:
            basis, updates, readout = quotient(matrices, observed, acts)
            assert len(basis) == expected
            for t in range(1024):
                x = (t * 0x9e3779b97f4a7c15 ^ (t >> 3)) & ((1 << n) - 1)
                q = eval_rows(basis, x)
                assert dot(observed, x) == dot(readout, q)
                for a in acts:
                    assert eval_rows(basis, eval_rows(matrices[a], x)) == eval_rows(updates[a], q)
            brute = exhaustive_check(n, matrices, observed, acts, basis) if n <= 8 else None
            results.append({'bits': n, 'scope': scope, 'rank': len(basis), 'minimal_states': str(1 << len(basis)),
                            'all_original_bits_relevant_to_output': True, 'independent_brute_state_count': brute,
                            'linear_semantics_check': 'PASS', 'matrix_literal_bits_raw': len(acts) * n*n,
                            'matrix_literal_bits_projected': n*len(basis) + len(acts)*len(basis)**2})
    return {'id': 'GEN001_POC4_MINIMAL_LINEAR_OBSERVABILITY_V1',
            'status': 'PASS_SCOPED_EXACT_MINIMAL_QUOTIENT', 'cases': results,
            'limitation': 'Known, crafted linear GF(2) model; minimal rank is exact for this model only; does not demonstrate general intelligence or universal phase transition.',
            'blocker': 'Automatic future-preserving coordinate discovery for nonlinear or unknown mechanisms with proof, including encoding/discovery cost.'}


if __name__ == '__main__':
    report = run()
    Path(__file__).with_name('poc4_repro_results.json').write_text(json.dumps(report, indent=2) + '\n')
    for c in report['cases']:
        print(c['bits'], c['scope'], c['rank'], c['independent_brute_state_count'])
    print(report['status'])
