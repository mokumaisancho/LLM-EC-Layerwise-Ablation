#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from generate_s2b2b2_operator_holdout import generate
from s2b2b2_enumerative_inducer import induce
from score_s2b2b2_operator_induction import preflight_fixture, score_rows, skey, heldout_after, stateset

GENERATOR_COMMIT = '78cc047200e8e5338294efcc3ad45039c31755bf'
EXPECTED_DIGEST = '4905b09f7c77cbad0e99a9c4bd98b1fd78a31d369f1019951d5d5864902db077'
RUNNER_COMMIT = '50b609963b41c696a0295bad84fe351678a186ea'
EXPECTED_QWEN_REASONS = {'SEMANTIC_SIGNATURE_MISMATCH': 12, 'UNUSED_PARAMETER': 2, 'VALID': 2}


def canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def sha_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def fail(detail: str) -> None:
    print(json.dumps({'terminal': 'B2_EVIDENCE_AUDIT_FAIL', 'detail': detail}, indent=2), flush=True)
    raise SystemExit(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--actual', type=Path, required=True)
    args = ap.parse_args()
    actual_bytes = args.actual.read_bytes()
    try:
        actual = json.loads(actual_bytes)
    except Exception as e:
        fail(f'actual JSON parse: {e}')

    if actual.get('schema_version') != 'FUNCTION_BOUNDARY_S2B2_B2_PAIRED_ACTUAL_V1':
        fail('actual schema version')
    if actual.get('terminal') != 'B2_DETERMINISTIC_MATERIAL_ADVANTAGE':
        fail('actual terminal')
    if actual.get('holdout_digest') != EXPECTED_DIGEST:
        fail('actual digest')
    if actual.get('fixture_count') != 16 or actual.get('family_count') != 8:
        fail('actual counts')
    frozen = actual.get('frozen_assets', {})
    if frozen.get('generator') != GENERATOR_COMMIT:
        fail('generator provenance')

    fixtures = generate(GENERATOR_COMMIT)
    if hashlib.sha256(canon(fixtures).encode()).hexdigest() != EXPECTED_DIGEST:
        fail('regenerated digest')
    by_id = {f['id']: f for f in fixtures}

    raw_rows = actual.get('raw_qwen_rows', [])
    if len(raw_rows) != 16 or len({r.get('fixture_id') for r in raw_rows}) != 16:
        fail('raw row completeness')

    qpred: dict[str, Any] = {}
    raw_manifest = []
    visible_hash_match = 0
    raw_parse_match = 0
    identifiable = 0
    heldout_valid_match = 0
    for r in raw_rows:
        fid = r.get('fixture_id')
        if fid not in by_id:
            fail(f'unknown fixture {fid}')
        f = by_id[fid]
        expected_visible_sha = hashlib.sha256(canon(f['visible']).encode()).hexdigest()
        if r.get('visible_sha256') != expected_visible_sha:
            fail(f'visible hash mismatch {fid}')
        visible_hash_match += 1
        raw = r.get('raw')
        if not isinstance(raw, str):
            fail(f'raw missing {fid}')
        try:
            parsed = json.loads(raw)
        except Exception as e:
            fail(f'raw parse {fid}: {e}')
        if canon(parsed) != canon(r.get('prediction')):
            fail(f'raw/prediction mismatch {fid}')
        raw_parse_match += 1
        qpred[fid] = parsed

        pf = preflight_fixture(f)
        if not pf.get('valid') or pf.get('consistent_count') != 1:
            fail(f'identifiability {fid}')
        identifiable += 1
        raw_manifest.append({
            'fixture_id': fid,
            'visible_sha256': expected_visible_sha,
            'raw_sha256': sha_text(raw),
            'prediction_sha256': sha_text(canon(parsed)),
        })

    detpred = {}
    for f in fixtures:
        r = induce(f['visible'])
        if r.get('status') != 'UNIQUE' or r.get('consistent_count') != 1:
            fail(f"deterministic not unique {f['id']}")
        pf = preflight_fixture(f)
        if skey(r['schema']) != skey(pf['oracle']):
            fail(f"deterministic/oracle mismatch {f['id']}")
        detpred[f['id']] = r['schema']

    det = score_rows(fixtures, detpred)
    qwen = score_rows(fixtures, qpred)

    if det.get('valid_total') != 16 or det.get('valid_induced_schema_rate') != 1.0 or det.get('deterministic_search_bound_count') != 0:
        fail('deterministic aggregate')
    if qwen.get('valid_total') != 2 or qwen.get('valid_induced_schema_rate') != 0.125 or qwen.get('invalid_total') != 14:
        fail('qwen aggregate')
    if qwen.get('reason_counts') != EXPECTED_QWEN_REASONS:
        fail('qwen reason counts ' + repr(qwen.get('reason_counts')))
    if abs((det['valid_induced_schema_rate'] - qwen['valid_induced_schema_rate']) - 0.875) > 1e-12:
        fail('paired delta')

    stored_det = actual.get('arms', {}).get('deterministic', {})
    stored_q = actual.get('arms', {}).get('qwen25_1p5b', {})
    for key in ('valid_total','invalid_total','valid_induced_schema_rate','deterministic_search_bound_count'):
        if det.get(key) != stored_det.get(key):
            fail('stored deterministic mismatch ' + key)
        if qwen.get(key) != stored_q.get(key):
            fail('stored qwen mismatch ' + key)
    if qwen.get('reason_counts') != stored_q.get('reason_counts'):
        fail('stored qwen reason mismatch')

    # Recompute the hidden held-out transition independently for every accepted prediction.
    for row in qwen['rows']:
        if not row['valid']:
            continue
        f = by_id[row['fixture_id']]
        ho = heldout_after(row['prediction'], f['visible']['heldout_target'])
        if not ho.get('applicable') or stateset(ho['after']) != stateset(f['oracle']['heldout_after']):
            fail('heldout transition mismatch ' + row['fixture_id'])
        heldout_valid_match += 1
    if heldout_valid_match != 2:
        fail('heldout accepted count')

    out = {
        'schema_version': 'FUNCTION_BOUNDARY_S2B2_B2_INDEPENDENT_POSTRUN_AUDIT_V1',
        'protocol': 'S2B2_MVP_TCC_V3',
        'terminal': 'B2_EVIDENCE_AUDIT_PASS',
        'model_reinference': False,
        'actual_file_sha256': hashlib.sha256(actual_bytes).hexdigest(),
        'runner_commit': RUNNER_COMMIT,
        'generator_commit': GENERATOR_COMMIT,
        'holdout_digest': EXPECTED_DIGEST,
        'fixture_count': 16,
        'identifiable_unique_count': identifiable,
        'visible_hash_match': visible_hash_match,
        'raw_parse_match': raw_parse_match,
        'raw_manifest': sorted(raw_manifest, key=lambda x: x['fixture_id']),
        'deterministic': {
            'valid_total': 16,
            'valid_rate': 1.0,
            'search_bound_count': 0,
            'independent_oracle_match': '16/16',
        },
        'qwen25_1p5b': {
            'valid_total': 2,
            'valid_rate': 0.125,
            'invalid_total': 14,
            'reason_counts': EXPECTED_QWEN_REASONS,
            'valid_heldout_transition_match': '2/2',
        },
        'paired_delta_deterministic_minus_qwen': 0.875,
        'result_overturning_gate_failures': 0,
    }
    print(json.dumps(out, indent=2), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
