#!/usr/bin/env python3
"""Independent algebraic verifier for typed GF(2) quotient proposals.

This checker does NOT import the coordinate-discovery implementation.
A proof of equality between GF(2) linear maps establishes correctness for
all 2**n original states, rather than relying on random or finite samples.
"""
import hashlib
import json


def raw_fingerprint(n, matrices, observed):
    record = {'n': n, 'output': hex(observed),
              'actions': {str(a): [hex(row) for row in rows] for a, rows in sorted(matrices.items())}}
    blob = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(blob).hexdigest()


def multiply_row(coefficients, rows):
    out = 0
    i = 0
    while coefficients:
        if coefficients & 1:
            out ^= rows[i]
        i += 1
        coefficients >>= 1
    return out


def rank(rows):
    pivots = {}
    for row in rows:
        while row:
            leading = row.bit_length() - 1
            if leading in pivots:
                row ^= pivots[leading]
            else:
                pivots[leading] = row
                break
    return len(pivots)


def full_observability_rank(n, matrices, observed, actions):
    pivots = {}
    def add(row):
        while row:
            leading = row.bit_length() - 1
            if leading in pivots:
                row ^= pivots[leading]
            else:
                pivots[leading] = row
                return
    add(observed)
    while True:
        old = len(pivots)
        rows = list(pivots.values())
        for row in rows:
            for a in actions:
                add(multiply_row(row, matrices[a]))
        if len(pivots) == old:
            return old
        assert len(pivots) <= n


def verify(candidate, n, matrices, observed, expected_actions, *, require_minimal=True):
    fail = lambda reason, **details: {'status': 'FAIL', 'reason': reason, **details}
    if candidate.get('protocol') != 'ABSTRACTION_CANDIDATE_V1' or candidate.get('domain') != 'GF2_LINEAR':
        return fail('SCHEMA_OR_DOMAIN_MISMATCH')
    if candidate.get('n') != n or n <= 0:
        return fail('STATE_WIDTH_MISMATCH')
    if candidate.get('actions') != list(expected_actions):
        return fail('ACTION_SET_MISMATCH')
    if candidate.get('source_sha256') != raw_fingerprint(n, matrices, observed):
        return fail('SOURCE_HASH_MISMATCH')
    rows = [int(x, 16) for x in candidate['phi_rows_hex']]
    r = len(rows)
    if not 0 < r <= n or any(x < 0 or x.bit_length() > n for x in rows):
        return fail('INVALID_PROJECTION_SHAPE')
    if rank(rows) != r:
        return fail('DEPENDENT_PROJECTION_COORDINATES')
    readout = int(candidate['output_row_hex'], 16)
    if readout.bit_length() > r or observed != multiply_row(readout, rows):
        return fail('OUTPUT_NOT_PRESERVED')
    count = 0
    for action in expected_actions:
        updates = candidate.get('delta_rows_hex', {}).get(str(action))
        if not isinstance(updates, list) or len(updates) != r:
            return fail('ABSTRACT_TRANSITION_MISSING', action=action)
        for i, (projection_row, update_hex) in enumerate(zip(rows, updates)):
            update = int(update_hex, 16)
            if update.bit_length() > r:
                return fail('ABSTRACT_TRANSITION_WIDTH_INVALID', action=action, row=i)
            lhs = multiply_row(projection_row, matrices[action])
            rhs = multiply_row(update, rows)
            if lhs != rhs:
                return fail('FUTURE_NOT_PRESERVED', action=action, row=i,
                            counterexample_original_state=hex(1 << ((lhs ^ rhs) & -(lhs ^ rhs)).bit_length() - 1))
            count += 1
    theoretical_rank = full_observability_rank(n, matrices, observed, expected_actions)
    if require_minimal and r != theoretical_rank:
        return fail('NON_MINIMAL_PROJECTION',claimed_rank=r,true_rank=theoretical_rank)
    return {'status': 'PASS_EXACT_ALL_STATES', 'n': n, 'rank': r,
            'minimal_predictive_rank': theoretical_rank, 'all_states_covered': str(1 << n),
            'equations_verified': count + 1,
            'proof': 'For GF2 linear maps, exact matrix identities imply all-state and all-future observational equivalence; observability subspace dimension proves minimality.'}
