#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = '922f57643074cde3a2653e02a6b9de111deebff0'
RUNNER_COMMIT = '50b609963b41c696a0295bad84fe351678a186ea'
PUBLIC_REPO = 'https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation.git'
FILES = [
    'docs/FUNCTION_BOUNDARY_S2B2_B2_OPERATOR_INDUCTION_CONTRACT_2026-10-05.json',
    'fixtures/function_boundary_s2b2_b1_schema_synth_manifest_2026-10-04.json',
    'fixtures/function_boundary_s2b2_b2_operator_manifest_2026-10-05.json',
    'tools/s2b2b2_enumerative_inducer.py',
    'tools/score_s2b2b2_operator_induction.py',
    'tools/generate_s2b2b2_operator_holdout.py',
    'tools/preflight_s2b2b2.py',
    'tools/run_s2b2b2_paired_v3.py',
    'tools/preflight_s2b2b2_runner_v3.py',
]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def fail(detail: str) -> None:
    print(json.dumps({'terminal': 'B2_EXECUTION_ADAPTER_FAILED', 'detail': detail}, indent=2), flush=True)
    raise SystemExit(2)


p = run('git', 'fetch', '--no-tags', PUBLIC_REPO, 'main')
if p.returncode:
    fail('fetch: ' + (p.stderr or p.stdout).strip())
for commit in (PIN, RUNNER_COMMIT):
    if run('git', 'cat-file', '-e', commit + '^{commit}').returncode:
        fail('required commit unavailable: ' + commit)
p = run('git', 'checkout', PIN, '--', *FILES)
if p.returncode:
    fail('pinned file checkout: ' + (p.stderr or p.stdout).strip())

p = subprocess.run([sys.executable, 'tools/preflight_s2b2b2_runner_v3.py'], cwd=ROOT, text=True, capture_output=True)
print(p.stdout, flush=True)
if p.returncode:
    fail('runner preflight: ' + (p.stderr or p.stdout).strip())
try:
    gate = json.loads(p.stdout)
except Exception as e:
    fail(f'runner preflight JSON: {e}')
if gate.get('terminal') != 'B2_RUNNER_PREFLIGHT_PASS':
    fail('unexpected runner preflight terminal: ' + str(gate.get('terminal')))

print(json.dumps({'terminal': 'B2_EXECUTION_ADAPTER_PASS', 'pinned_commit': PIN, 'runner_commit': RUNNER_COMMIT}, indent=2), flush=True)
raise SystemExit(subprocess.call([sys.executable, 'tools/run_s2b2b2_paired_v3.py'], cwd=ROOT))
