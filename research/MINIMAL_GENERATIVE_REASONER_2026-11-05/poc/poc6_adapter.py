#!/usr/bin/env python3
"""Bounded verified candidate adapter to pinned ECv4.4 semantic framing scoring.
No EC source mutation. No large LLM. GF(2) semantics only.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from poc4_repro import system, quotient
from poc6_checker import verify, raw_fingerprint
from poc5_ecv44_native import SNAP, SOURCE_SHAS, git_blob_hash, framing
from v4.ec_framing_search import search_framing, score_framing


def generate(n, actions):
    M, C = system(n)
    basis, delta, readout = quotient(M, C, actions)
    return {'protocol': 'ABSTRACTION_CANDIDATE_V1', 'domain': 'GF2_LINEAR',
            'n': n, 'actions': list(actions), 'source_sha256': raw_fingerprint(n, M, C),
            'phi_rows_hex': [hex(v) for v in basis],
            'delta_rows_hex': {str(a): [hex(v) for v in delta[a]] for a in actions},
            'output_row_hex': hex(readout), 'rank': len(basis)}


def inject(intent, old_framing, proposal, proof, minimum_gain=0.01):
    # Fail closed on invalid proof BEFORE computing EC semantic scores.
    if proof.get('status') != 'PASS_EXACT_ALL_STATES':
        return {'status': 'REJECT', 'reason': proof.get('reason'), 'candidate': None}
    new = copy.deepcopy(old_framing)
    new['variables'] = {f'z{i}': {'semantic_key': f'gf2_projection_{i}',
                                  'abstraction': 'GF2_LINEAR', 'actionable': True,
                                  'evidence_refs': ['poc6:independent_verifier'],
                                  'projection_mask_hex': hx}
                        for i, hx in enumerate(proposal['phi_rows_hex'])}
    new['edges'] = []
    new['goal_coverage'] = {'predict': list(new['variables'])}
    prior = score_framing(intent, old_framing)
    after = score_framing(intent, new)
    if prior['status'] != 'PASS' or after['status'] != 'PASS':
        return {'status': 'REJECT', 'reason': 'NATIVE_EC_INTENT_GATE_REJECTED'}
    gain = round(after['score'] - prior['score'], 12)
    if gain < minimum_gain:
        return {'status': 'PRESERVE', 'reason': 'NO_MEANINGFUL_IMPROVEMENT', 'score_gain': gain}
    return {'status': 'REVISE_VERIFIED_ABSTRACTION', 'score_gain': gain,
            'previous_variables': len(old_framing['variables']), 'new_variables': len(new['variables']),
            'proof_status': proof['status'], 'candidate_protocol': proposal['protocol']}


def run():
    hashes = {path: git_blob_hash((SNAP / path).read_bytes()) for path in SOURCE_SHAS}
    assert hashes == SOURCE_SHAS
    intent = {'original_intent': 'Find the smallest adequate predictive coordinates',
              'success_conditions': ['predict'], 'protected_invariants': ['preserve_future'],
              'prohibited_substitutions': ['invalid_replacement']}
    all_results = []
    for n in (6, 8, 128):
        for actions in ((0, 1), (0, 1, 2)):
            M, C = system(n)
            proposal = generate(n, actions)
            proof = verify(proposal, n, M, C, actions)
            assert proof['status'] == 'PASS_EXACT_ALL_STATES'
            before_native = search_framing(intent, framing(n))
            assert before_native['status'] == 'CLOSE'
            candidate_out = inject(intent, framing(n), proposal, proof)
            expected = 'REVISE_VERIFIED_ABSTRACTION' if n >= 8 and len(actions) == 2 else 'PRESERVE'
            assert candidate_out['status'] == expected, (n, actions, candidate_out)
            if len(actions) == 2:
                # Invalid phi, delta, source digest, and scope must all fail closed.
                mutants = {}
                def attempt(label, variant, check_actions=actions):
                    result = verify(variant, n, M, C, check_actions)
                    assert result['status'] == 'FAIL', (label, result)
                    sent = inject(intent, framing(n), variant, result)
                    assert sent['status'] == 'REJECT'
                    mutants[label] = result['reason']
                bad = copy.deepcopy(proposal)
                bad['phi_rows_hex'][0] = hex(int(bad['phi_rows_hex'][0], 16) ^ 1)
                attempt('wrong_projection', bad)
                bad = copy.deepcopy(proposal)
                bad['delta_rows_hex']['0'][0] = hex(int(bad['delta_rows_hex']['0'][0], 16) ^ 1)
                attempt('wrong_transition', bad)
                bad = copy.deepcopy(proposal)
                bad['source_sha256'] = '0' * 64
                attempt('wrong_provenance', bad)
                attempt('newly_permitted_probe', proposal, (0, 1, 2))
            else:
                mutants = {}
            all_results.append({'n': n, 'actions': list(actions),
                                'derived_rank': proposal['rank'], 'proof': proof,
                                'ec_without_candidate': before_native['status'],
                                'adapter_with_verified_candidate': candidate_out,
                                'faults': mutants})
    report = {'id': 'GEN001_POC6_PROOF_BEARING_ECV44_ADAPTER_V1',
              'status': 'PASS_SCOPED_ADAPTER_PROTOTYPE', 'cases': all_results,
              'source_commit': 'd5ec423968f1c9242c590e5e77ccfd92d1f59eb2',
              'EC_source_blobs': hashes,
              'scope': 'Known GF2 linear original model; offline adapter calls the two native EC framing modules without source modification; not integrated into EC control plane.',
              'limitations': ['No general nonlinear discovery','No EC SUITE and no production acceptance',
                              'Input matrices given, not inferred from raw observations',
                              'Representation memory score is only EC metadata proxy, no full runtime cost measured'],
              'next_blocker': 'Implement the typed adapter against actual ECv4.4 S3/S4 inputs and real nonlinear transition source; run the actual SUITE and assess output preservation under changing task scope.'}
    (ROOT / 'results6.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    r = run()
    print(r['status'])
    for x in r['cases']:
        print(x['n'], x['actions'], 'rank', x['derived_rank'],
              x['adapter_with_verified_candidate']['status'], 'faults', x['faults'])
