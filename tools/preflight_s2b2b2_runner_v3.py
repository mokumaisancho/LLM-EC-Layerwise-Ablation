#!/usr/bin/env python3
from __future__ import annotations

import importlib
import inspect
import json
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
sys.path.insert(0, str(TOOLS))

RUNNER_COMMIT = '50b609963b41c696a0295bad84fe351678a186ea'
RUNNER_PATH = 'tools/run_s2b2b2_paired_v3.py'
EXPECTED_DIGEST = '4905b09f7c77cbad0e99a9c4bd98b1fd78a31d369f1019951d5d5864902db077'
GENERATOR_COMMIT = '78cc047200e8e5338294efcc3ad45039c31755bf'


def fail(detail: str) -> None:
    print(json.dumps({'terminal': 'B2_RUNNER_PREFLIGHT_FAILED', 'detail': detail}, indent=2), flush=True)
    raise SystemExit(2)


def git_show(commit: str, path: str) -> bytes:
    p = subprocess.run(['git', 'show', f'{commit}:{path}'], cwd=ROOT, capture_output=True)
    if p.returncode:
        fail(f'git show failed {commit}:{path}')
    return p.stdout


def main() -> int:
    try:
        py_compile.compile(str(ROOT / RUNNER_PATH), doraise=True)
    except Exception as e:
        fail(f'runner py_compile: {e}')

    if (ROOT / RUNNER_PATH).read_bytes() != git_show(RUNNER_COMMIT, RUNNER_PATH):
        fail('frozen runner drift')

    p = subprocess.run(['python3', str(TOOLS / 'preflight_s2b2b2.py')], cwd=ROOT, text=True, capture_output=True)
    if p.returncode:
        fail('scientific preflight: ' + (p.stderr or p.stdout))
    try:
        scientific = json.loads(p.stdout)
    except Exception as e:
        fail(f'scientific preflight JSON: {e}')
    if scientific.get('terminal') != 'B2_PREFLIGHT_PASS' or scientific.get('holdout_digest') != EXPECTED_DIGEST:
        fail('scientific preflight terminal/digest mismatch')

    runner = importlib.import_module('run_s2b2b2_paired_v3')
    generator = importlib.import_module('generate_s2b2b2_operator_holdout')
    source = inspect.getsource(runner.qwen_predict)
    if "['oracle']" in source or '["oracle"]' in source or "['family']" in source or '["family"]' in source:
        fail('qwen_predict references hidden fixture fields')

    fixtures = generator.generate(GENERATOR_COMMIT)
    if len(fixtures) != 16:
        fail('fixture count drift')
    for f in fixtures:
        grammar = runner.grammar_for(f['visible'])
        params = [p['name'] for p in f['visible']['parameters']]
        for pvar in params:
            if pvar not in grammar:
                fail(f"{f['id']} grammar missing parameter {pvar}")
        entity_values = set()
        for ex in f['visible']['positive_examples'] + f['visible']['negative_examples'] + [f['visible']['heldout_target']]:
            entity_values.update(ex['binding'].values())
        if any(value in grammar for value in entity_values):
            fail(f"{f['id']} grammar leaks concrete binding entity")
        if 'oracle' in grammar or 'heldout_after' in grammar or f['family'] in grammar:
            fail(f"{f['id']} grammar leaks hidden metadata")

    out = {
        'terminal': 'B2_RUNNER_PREFLIGHT_PASS',
        'protocol': 'S2B2_MVP_TCC_V3',
        'runner_commit': RUNNER_COMMIT,
        'holdout_digest': EXPECTED_DIGEST,
        'scientific_preflight': 'B2_PREFLIGHT_PASS',
        'fixture_count': 16,
        'runner_hidden_field_reference': False,
        'grammar_concrete_entity_leakage': 0,
        'model_inference': False,
    }
    print(json.dumps(out, indent=2), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
