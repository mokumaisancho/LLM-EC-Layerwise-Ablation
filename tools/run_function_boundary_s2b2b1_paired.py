#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REPO = 'https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation.git'
LIVE_RESULT_URL = 'https://function-boundary-s2b2b1-paired-temp.onrender.com/'
ACTUAL = Path('/tmp/s2b2_b2_actual.json')
AUDIT_OUT = ROOT / 'results' / 'function_boundary_s2b2_b2_paired_runtime.json'
AUDIT_COMMIT = '074aaec9c0e719cde71506232a8c60b8e3793882'
FROZEN = [
    ('30d47b6c36a195f986cb26e36d5245e4bbf0d89a', 'tools/s2b2b2_enumerative_inducer.py'),
    ('9c4ab5f12f33f443d213d8e6854a0461b461ae33', 'tools/score_s2b2b2_operator_induction.py'),
    ('78cc047200e8e5338294efcc3ad45039c31755bf', 'tools/generate_s2b2b2_operator_holdout.py'),
    (AUDIT_COMMIT, 'tools/audit_s2b2b2_paired_v3.py'),
]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def fail(detail: str) -> None:
    print(json.dumps({'terminal': 'B2_POSTRUN_AUDIT_ADAPTER_FAILED', 'detail': detail}, indent=2), flush=True)
    raise SystemExit(2)


# Capture the already-completed live result before this deployment can replace it.
try:
    req = urllib.request.Request(LIVE_RESULT_URL, headers={'User-Agent': 's2b2-b2-audit/1'})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
except Exception as e:
    fail(f'live result fetch: {e}')
try:
    doc = json.loads(body)
except Exception as e:
    fail(f'live result JSON: {e}')
if doc.get('schema_version') != 'FUNCTION_BOUNDARY_S2B2_B2_PAIRED_ACTUAL_V1' or doc.get('terminal') != 'B2_DETERMINISTIC_MATERIAL_ADVANTAGE':
    fail('live endpoint is not the completed B2 paired result')
ACTUAL.write_bytes(body)

p = run('git', 'fetch', '--no-tags', PUBLIC_REPO, 'main')
if p.returncode:
    fail('fetch: ' + (p.stderr or p.stdout).strip())
for commit, path in FROZEN:
    if run('git', 'cat-file', '-e', commit + '^{commit}').returncode:
        fail('required commit unavailable: ' + commit)
    p = run('git', 'checkout', commit, '--', path)
    if p.returncode:
        fail('checkout ' + path + ': ' + (p.stderr or p.stdout).strip())

p = subprocess.run(
    [sys.executable, 'tools/audit_s2b2b2_paired_v3.py', '--actual', str(ACTUAL)],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
print(p.stdout, flush=True)
if p.returncode:
    fail('B2 postrun audit: ' + (p.stderr or p.stdout).strip())
try:
    audit = json.loads(p.stdout)
except Exception as e:
    fail(f'audit JSON: {e}')
if audit.get('terminal') != 'B2_EVIDENCE_AUDIT_PASS':
    fail('unexpected audit terminal: ' + str(audit.get('terminal')))

AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
AUDIT_OUT.write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'terminal':'B2_POSTRUN_AUDIT_ADAPTER_PASS','model_reinference':False,'actual_file_sha256':audit['actual_file_sha256']}, indent=2), flush=True)
