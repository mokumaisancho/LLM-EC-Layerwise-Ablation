#!/usr/bin/env python3
"""Run unmodified, SHA-pinned ECv4.4 framing source on dimension-shift fixtures.
The two v4 source files are verified byte-for-byte against GitHub blob SHAs.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SNAP = Path(os.environ.get('ECV44_SRC', str(ROOT / 'ecv44_snapshot'))).resolve()
if not (SNAP / 'v4/ec_framing_search.py').is_file():
    raise SystemExit('Set ECV44_SRC to the pinned EC repository 01_repo/src directory')
sys.path.insert(0, str(SNAP))
from v4.ec_framing_search import search_framing, score_framing
from v4.ec_residual_detector import detect_residuals

SOURCE_SHAS = {
    'v4/ec_residual_detector.py': 'db2786573417348b243ca9d54f3a21d631427943',
    'v4/ec_framing_search.py': 'dfc4c56e9bfdeffb3bd1f4aa699d9172c78fa7d5',
}


def git_blob_hash(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def framing(n):
    variables = {f'x{i}': {'semantic_key': f'x{i}', 'abstraction': 'INPUT_BIT',
                          'evidence_refs': [f'given:x{i}'], 'actionable': True}
                 for i in range(n)}
    return {'framing_revision_id': 1, 'variables': variables,
            'goal_coverage': {'predict': list(variables)}, 'edges': []}


def run():
    hashes = {}
    for path, want in SOURCE_SHAS.items():
        found = git_blob_hash((SNAP / path).read_bytes())
        assert found == want, (path, want, found)
        hashes[path] = {'observed_git_blob_sha': found, 'match': True}

    intent = {'original_intent': 'Discover a sufficient and minimal predictive state',
              'success_conditions': ['predict'], 'protected_invariants': ['preserve_future'],
              'prohibited_substitutions': ['incorrect_projection']}
    old = framing(128)
    reduced = {'framing_revision_id': 1, 'variables': {
        'z0': {'semantic_key': 'parity_all', 'abstraction': 'GF2_LINEAR_OBSERVABLE',
               'evidence_refs': ['poc4:certificate'], 'actionable': True,
               'projection_mask_hex': hex((1 << 128) - 1)},
        'z1': {'semantic_key': 'parity_except_x1', 'abstraction': 'GF2_LINEAR_OBSERVABLE',
               'evidence_refs': ['poc4:certificate'], 'actionable': True,
               'projection_mask_hex': hex(((1 << 128) - 1) ^ 2)}},
        'goal_coverage': {'predict': ['z0', 'z1']}, 'edges': []}

    old_res = detect_residuals(intent, old)
    old_search = search_framing(intent, old)
    reduced_score = score_framing(intent, reduced)
    old_score = score_framing(intent, old)
    assert old_res['status'] == 'CLEAN'
    assert old_search['status'] == 'CLOSE'
    assert old_search['selected_operation'] is None
    assert reduced_score['score'] > old_score['score']
    # Explicit mismatch creates a REABSTRACT candidate, but its single-field
    # label change is score-neutral. Hence the current threshold rejects it.
    with_hint = framing(128)
    with_hint['variables']['x0']['required_abstraction'] = 'GF2_LINEAR_OBSERVABLE'
    hinted_result = search_framing(intent, with_hint)
    assert hinted_result['status'] == 'PRESERVE'
    assert hinted_result['reason'] == 'NO_MEANINGFUL_IMPROVEMENT'
    assert any(x['operation']['op'] == 'REABSTRACT' for x in hinted_result['evaluated'])

    # Fault control: score validates goal coverage/evidence presence but does
    # not check the mathematical future-preservation property of a projection.
    bad = json.loads(json.dumps(reduced))
    bad['variables']['z0']['projection_mask_hex'] = hex(1)  # broken even for present output
    bad_score = score_framing(intent, bad)
    witness_x = 2
    assert ((int(reduced['variables']['z0']['projection_mask_hex'], 16) & witness_x).bit_count() & 1) != ((int(bad['variables']['z0']['projection_mask_hex'], 16) & witness_x).bit_count() & 1)
    assert bad_score['status'] == 'PASS' and bad_score['score'] == reduced_score['score']

    # Existing hard intent invariants still reject explicit distortion.
    violates = json.loads(json.dumps(reduced))
    violates['violated_invariants'] = ['preserve_future']
    reject = score_framing(intent, violates)
    assert reject['status'] == 'REJECT' and reject['reason'] == 'INTENT_DISTORTION'

    report = {
        'id': 'GEN001_POC5_ECV44_NATIVE_FUTURE_PROJECTION_GAP_V1',
        'status': 'PASS_GAP_REPRODUCED_PINNED_NATIVE_SOURCE',
        'source_repo': 'mokumaisancho/GPT-EC-Closure-Engine',
        'source_commit': 'd5ec423968f1c9242c590e5e77ccfd92d1f59eb2',
        'verified_source_blobs': hashes,
        'setup': {'variables_before': 128, 'proposed_exact_GF2_projection_variables': 2,
                  'note': 'The 2-coordinate projection is a proposal established in separate POC4; EC never derives it'},
        'tests': [
            {'id': 'no_residual_discovers_no_projection', 'native_residual': old_res['status'],
             'native_search': old_search['status'], 'selected_operation': old_search['selected_operation'], 'pass': True},
            {'id': 'externally_supplied_projection_score_better',
             'old_score': old_score['score'], 'new_score': reduced_score['score'],
             'score_gain': round(reduced_score['score']-old_score['score'], 12), 'pass': True},
            {'id': 'provided_reabstract_hint_cannot_pass_score_gate',
             'native_search': hinted_result['status'], 'reason': hinted_result['reason'],
             'ops_tested': [x['operation']['op'] for x in hinted_result['evaluated']], 'pass': True},
            {'id': 'mathematically_invalid_coordinate_not_rejected_by_framing_score',
             'native_score_status': bad_score['status'], 'invalid_score': bad_score['score'],
             'matches_valid_score': bad_score['score'] == reduced_score['score'],
             'explicit_bad_projection_witness': {'state': witness_x, 'correct_observation': 1, 'bad_projection_first_bit': 0}, 'pass': True,
             'note': 'Not a defect against the old ECv4.4 goal; it proves novel quotient-certification is absent.'},
            {'id': 'existing_intent_protection_still_rejects_explicit_violation',
             'native_score_status': reject['status'], 'reason': reject['reason'], 'pass': True},
        ],
        'root_cause': 'Existing ECv4.4 residual triggers are semantic metadata checks. REABSTRACT only updates an abstraction string; no candidate expression for phi/delta or future-preservation verification is generated. Complexity score does not drive candidate search when residuals are CLEAN.',
        'single_blocker': 'Add a separate evidence-bearing candidate generator for mathematically meaningful phi/delta, together with proof/counterexample, and feed its verified candidate into ECv4.4 without changing the existing closure authority.',
        'limitations': ['Only exact pinned ECv4.4 framing_search and residual_detector modules executed, not whole runtime control plane',
                       'Synthetic framed variables and native score not independent truth ground',
                       'No native integration or full SUITE regression performed']
    }
    (ROOT / 'results5.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    r = run()
    print(r['status'])
    for t in r['tests']:
        print(t['id'], 'PASS' if t['pass'] else 'FAIL', {k: v for k, v in t.items() if k not in ('id', 'pass')})
