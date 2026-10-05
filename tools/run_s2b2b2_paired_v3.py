#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import tarfile
import time
import urllib.request
from typing import Any

from generate_s2b2b2_operator_holdout import generate
from s2b2b2_enumerative_inducer import induce
from score_s2b2b2_operator_induction import score_rows, typed_atom_universe

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = pathlib.Path('/tmp/s2b2-b2-v3')
OUT = ROOT / 'results' / 'function_boundary_s2b2_b2_paired_runtime.json'

PROTOCOL = 'FUNCTION_BOUNDARY_S2B2_B2_PAIRED_V3'
TCC = 'S2B2_MVP_TCC_V3'
GENERATOR_COMMIT = '78cc047200e8e5338294efcc3ad45039c31755bf'
EXPECTED_DIGEST = '4905b09f7c77cbad0e99a9c4bd98b1fd78a31d369f1019951d5d5864902db077'
EXPECTED_FIXTURES = 16
EXPECTED_FAMILIES = 8
MATERIALITY = 0.20

LLAMA_TAG = 'b11146'
LLAMA_FILE = 'llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL = f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA = 'c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
MODEL_REPO = 'bartowski/Qwen2.5-1.5B-Instruct-GGUF'
MODEL_FILE = 'Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'
MODEL_URL = f'https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}'
MODEL_SHA = '1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'
MODEL_SIZE = 986048768


def canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canon(rows).encode()).hexdigest()


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: pathlib.Path) -> None:
    req = urllib.request.Request(url, headers={'User-Agent': 's2b2-b2-v3/1'})
    with urllib.request.urlopen(req, timeout=240) as r, dest.open('wb') as out:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def acquire_runtime() -> pathlib.Path:
    arc = WORK / LLAMA_FILE
    download(LLAMA_URL, arc)
    if sha256(arc) != LLAMA_SHA:
        raise RuntimeError('LLAMA_SHA_MISMATCH')
    target = WORK / 'llama'
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(arc, 'r:gz') as tf:
        tf.extractall(target, filter='data')
    hits = list(target.rglob('llama-server'))
    if not hits:
        raise RuntimeError('LLAMA_SERVER_NOT_FOUND')
    hits[0].chmod(0o755)
    return hits[0]


def literal(text: str) -> str:
    return json.dumps(text)


def grammar_for(visible: dict[str, Any]) -> str:
    params = [p['name'] for p in visible['parameters']]
    atoms = [
        {'pred': pred, 'args': list(args)}
        for pred, args in typed_atom_universe(visible)
    ]
    atom_literals = ' | '.join(literal(canon(a)) for a in atoms)
    params_literal = literal(canon(params))
    return '\n'.join([
        'root ::= ws "{" ws "\\\"proposal_kind\\\"" ws ":" ws "\\\"INDUCED_OPERATOR\\\"" ws "," ws "\\\"parameters\\\"" ws ":" ws params ws "," ws "\\\"preconditions\\\"" ws ":" ws atoms13 ws "," ws "\\\"add_effects\\\"" ws ":" ws atoms13 ws "," ws "\\\"delete_effects\\\"" ws ":" ws atom1 ws "}" ws',
        'params ::= ' + params_literal,
        'atoms13 ::= "[" ws atom ws "]" | "[" ws atom ws "," ws atom ws "]" | "[" ws atom ws "," ws atom ws "," ws atom ws "]"',
        'atom1 ::= "[" ws atom ws "]"',
        'atom ::= ' + atom_literals,
        'ws ::= [ \\t\\n\\r]*',
    ])


def post_json(url: str, payload: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def run_preflight() -> dict[str, Any]:
    p = subprocess.run(
        ['python3', str(ROOT / 'tools' / 'preflight_s2b2b2.py')],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if p.returncode:
        raise RuntimeError('B2_PREFLIGHT_FAILED:' + (p.stderr or p.stdout))
    x = json.loads(p.stdout)
    if x.get('terminal') != 'B2_PREFLIGHT_PASS':
        raise RuntimeError('B2_PREFLIGHT_NOT_PASS')
    if x.get('holdout_digest') != EXPECTED_DIGEST:
        raise RuntimeError('B2_PREFLIGHT_DIGEST_MISMATCH')
    return x


def qwen_predict(fixtures: list[dict[str, Any]], server_url: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    system = (
        'Infer one reusable symbolic operator from the structured transition examples. '
        'Positive examples are executions of the unknown operator. Negative examples are unchanged because the operator is not applicable. '
        'Use only the visible typed predicate vocabulary and the declared parameter variables. '
        'Return the unique operator consistent with all positive and negative examples. '
        'Do not copy concrete entity names into the schema. Return only the required JSON object.'
    )
    predictions: dict[str, Any] = {}
    raw_rows: list[dict[str, Any]] = []
    for f in fixtures:
        visible = f['visible']
        visible_sha = hashlib.sha256(canon(visible).encode()).hexdigest()
        prompt = (
            '<|im_start|>system\n' + system + '<|im_end|>\n'
            '<|im_start|>user\n' + canon(visible) + '<|im_end|>\n'
            '<|im_start|>assistant\n'
        )
        response = post_json(
            server_url + '/completion',
            {
                'prompt': prompt,
                'n_predict': 384,
                'temperature': 0,
                'grammar': grammar_for(visible),
                'cache_prompt': False,
            },
        )
        raw = str(response.get('content', '')).strip()
        parsed = None
        try:
            x = json.loads(raw)
            if isinstance(x, dict):
                parsed = x
        except Exception:
            pass
        predictions[f['id']] = parsed
        row = {
            'fixture_id': f['id'],
            'visible_sha256': visible_sha,
            'raw': raw,
            'prediction': parsed,
        }
        raw_rows.append(row)
        print('S2B2B2_FIXTURE=' + json.dumps(row, separators=(',', ':')), flush=True)
    return predictions, raw_rows


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    preflight = run_preflight()
    fixtures = generate(GENERATOR_COMMIT)
    if len(fixtures) != EXPECTED_FIXTURES or len({f['family'] for f in fixtures}) != EXPECTED_FAMILIES:
        raise RuntimeError('B2_FIXTURE_COUNT_MISMATCH')
    if digest(fixtures) != EXPECTED_DIGEST:
        raise RuntimeError('B2_HOLDOUT_MISMATCH')

    det_predictions: dict[str, Any] = {}
    search_bound_ids: set[str] = set()
    for f in fixtures:
        r = induce(f['visible'])
        if r.get('status') == 'UNIQUE':
            det_predictions[f['id']] = r['schema']
        else:
            search_bound_ids.add(f['id'])
            det_predictions[f['id']] = None
    deterministic = score_rows(fixtures, det_predictions, search_bound_ids=search_bound_ids)
    if search_bound_ids:
        raise RuntimeError('DETERMINISTIC_SEARCH_BOUND:' + ','.join(sorted(search_bound_ids)))

    print('S2B2B2_STATE=STATIC_AND_SCIENTIFIC_PREFLIGHT_PASS', flush=True)
    server_bin = acquire_runtime()
    model = WORK / MODEL_FILE
    download(MODEL_URL, model)
    if model.stat().st_size != MODEL_SIZE:
        raise RuntimeError('MODEL_SIZE_MISMATCH')
    if sha256(model) != MODEL_SHA:
        raise RuntimeError('MODEL_SHA_MISMATCH')

    log_path = WORK / 'llama.log'
    log = log_path.open('w')
    server = subprocess.Popen(
        [
            str(server_bin), '-m', str(model), '-c', '2048', '-b', '64', '-ub', '64',
            '--threads', '1', '--no-warmup', '--host', '127.0.0.1', '--port', '18082',
        ],
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        ready = False
        for _ in range(240):
            if server.poll() is not None:
                break
            try:
                with urllib.request.urlopen('http://127.0.0.1:18082/health', timeout=2) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            log.flush()
            raise RuntimeError('LLAMA_NOT_READY:' + log_path.read_text(errors='replace')[-3000:])

        qwen_predictions, raw_rows = qwen_predict(fixtures, 'http://127.0.0.1:18082')
        qwen = score_rows(fixtures, qwen_predictions)
        det_rate = float(deterministic['valid_induced_schema_rate'])
        qwen_rate = float(qwen['valid_induced_schema_rate'])
        delta = det_rate - qwen_rate
        if delta >= MATERIALITY:
            terminal = 'B2_DETERMINISTIC_MATERIAL_ADVANTAGE'
        elif -delta >= MATERIALITY:
            terminal = 'B2_LLM_MATERIAL_ADVANTAGE'
        else:
            terminal = 'B2_NO_MATERIAL_SEPARATION'

        result = {
            'schema_version': 'FUNCTION_BOUNDARY_S2B2_B2_PAIRED_ACTUAL_V1',
            'protocol': PROTOCOL,
            'tcc': TCC,
            'issue': 43,
            'holdout_digest': EXPECTED_DIGEST,
            'fixture_count': EXPECTED_FIXTURES,
            'family_count': EXPECTED_FAMILIES,
            'preflight': preflight,
            'frozen_assets': {
                'contract': '96a99c0a58f5063f72b3dfd593c6e14e3a29a96c',
                'inducer': '30d47b6c36a195f986cb26e36d5245e4bbf0d89a',
                'scorer': '9c4ab5f12f33f443d213d8e6854a0461b461ae33',
                'generator': GENERATOR_COMMIT,
                'manifest': 'a01819f5120dd4762817022bdfc1844023541c79',
            },
            'model': {
                'repository': MODEL_REPO,
                'file': MODEL_FILE,
                'size_bytes': MODEL_SIZE,
                'sha256': MODEL_SHA,
            },
            'runtime': {
                'llama_cpp_tag': LLAMA_TAG,
                'llama_cpp_asset_sha256': LLAMA_SHA,
                'temperature': 0,
                'context_tokens': 2048,
                'grammar_policy': 'exact parameter list + typed visible atom vocabulary; semantic atom selection free',
                'github_actions_used': False,
                'google_drive_used': False,
                'qwen3_4b_used': False,
            },
            'arms': {
                'deterministic': deterministic,
                'qwen25_1p5b': qwen,
            },
            'raw_qwen_rows': raw_rows,
            'paired_delta_deterministic_minus_qwen_valid_rate': delta,
            'materiality_abs': MATERIALITY,
            'terminal': terminal,
            'claim_limit': 'Formal operator induction inside the frozen typed symbolic hypothesis space only; not raw-language parsing, world-knowledge invention, or open-ended semantic synthesis.',
        }
        OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print('S2B2B2_TERMINAL=' + json.dumps(result, separators=(',', ':')), flush=True)
    finally:
        if server.poll() is None:
            server.terminate()
        log.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
