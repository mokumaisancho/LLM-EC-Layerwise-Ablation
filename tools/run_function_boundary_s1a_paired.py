#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import tarfile
import time
import urllib.request
from collections import defaultdict

from tools.generate_s1a_disjoint_holdout import generate, digest
from tools.s1a_predictor_core import FIELDS, score as score_deterministic

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = pathlib.Path('/tmp/function-boundary-s1a-paired')
OUT = ROOT / 'results' / 'function_boundary_s1a_disjoint_qwen25_1p5b_runtime.json'

PROTOCOL = 'FUNCTION_BOUNDARY_S1A_DISJOINT_PAIRED_V1'
SOURCE_PROTOCOL = 'FUNCTION_BOUNDARY_S1A_DISJOINT_HOLDOUT_V2'
GENERATOR_FREEZE_COMMIT = '8d8a333ebc17e73ee04a43baf3a3976c865d621f'
EXPECTED_DIGEST = '3192d093d3f2162f94e22e8a2e30ea5dbb691cfc42a7913492435d511d506b9a'
EXPECTED_FIXTURES = 16
EXPECTED_DET_PRIMARY = 0.7375
EXPECTED_DET_EXACT = 0.3125

LLAMA_TAG = 'b11146'
LLAMA_FILE = 'llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL = f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA = 'c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
MODEL_REPO = 'bartowski/Qwen2.5-1.5B-Instruct-GGUF'
MODEL_FILE = 'Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'
MODEL_URL = f'https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}'
MODEL_SHA = '1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'
MODEL_SIZE = 986048768


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: pathlib.Path) -> None:
    req = urllib.request.Request(url, headers={'User-Agent': 'function-boundary-s1a-paired/1'})
    with urllib.request.urlopen(req, timeout=240) as r, dest.open('wb') as out:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def acquire_runtime() -> pathlib.Path:
    archive = WORK / LLAMA_FILE
    download(LLAMA_URL, archive)
    if sha256(archive) != LLAMA_SHA:
        raise RuntimeError('LLAMA_SHA_MISMATCH')
    target = WORK / 'llama'
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, 'r:gz') as tf:
        tf.extractall(target, filter='data')
    hits = list(target.rglob('llama-server'))
    if not hits:
        raise RuntimeError('LLAMA_SERVER_NOT_FOUND')
    hits[0].chmod(0o755)
    return hits[0]


def grammar_for(visible: dict) -> str:
    facts = list(visible['facts'])
    concepts = list(visible['concepts'])
    relations = list(visible['relations'])
    goals = list(visible['goals'])

    def choices(values: list[str]) -> str:
        return ' | '.join(json.dumps(json.dumps(v)) for v in values)

    return '\n'.join([
        'root ::= "{" ws "\\\"primary_fact_id\\\"" ws ":" ws fact ws "," ws "\\\"semantic_concept_id\\\"" ws ":" ws concept ws "," ws "\\\"key_relation_id\\\"" ws ":" ws rel ws "," ws "\\\"ambiguity\\\"" ws ":" ws amb ws "," ws "\\\"goal_id\\\"" ws ":" ws goal ws "}" ws',
        'ws ::= [ \\t\\n\\r]*',
        'fact ::= ' + choices(facts),
        'concept ::= ' + choices(concepts),
        'rel ::= ' + choices(relations),
        'amb ::= "\\\"YES\\\"" | "\\\"NO\\\""',
        'goal ::= ' + choices(goals),
    ])


def post_json(url: str, payload: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def score_qwen(fixtures: list[dict], server_url: str) -> dict:
    system = (
        'You are a semantic-grounding stage. Use only the supplied visible task. '
        'Select the single primary evidence fact, the best matching domain concept, '
        'the key semantic relation, whether the meaning/referent remains ambiguous, '
        'and the protected goal. IDs and option descriptions are supplied in the task. '
        'Do not invent IDs. Return only the required JSON object.'
    )
    rows = []
    field_correct = {f: 0 for f in FIELDS}
    exact = 0
    invalid = 0
    family_counts = defaultdict(lambda: {'fixtures': 0, 'correct_fields': 0, 'field_decisions': 0, 'exact': 0})

    for fixture in fixtures:
        visible = fixture['visible']
        oracle = fixture['oracle']
        prompt = (
            '<|im_start|>system\n' + system + '<|im_end|>\n'
            '<|im_start|>user\n' + json.dumps(visible, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '<|im_end|>\n'
            '<|im_start|>assistant\n'
        )
        resp = post_json(server_url + '/completion', {
            'prompt': prompt,
            'n_predict': 128,
            'temperature': 0,
            'grammar': grammar_for(visible),
            'cache_prompt': False,
        })
        raw = str(resp.get('content', '')).strip()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {}
            invalid += 1
        correct = {f: parsed.get(f) == oracle[f] for f in FIELDS}
        for f in FIELDS:
            field_correct[f] += int(correct[f])
        is_exact = all(correct.values())
        exact += int(is_exact)
        family = fixture['family']
        bucket = family_counts[family]
        bucket['fixtures'] += 1
        bucket['correct_fields'] += sum(correct.values())
        bucket['field_decisions'] += len(FIELDS)
        bucket['exact'] += int(is_exact)
        row = {
            'fixture_id': fixture['id'],
            'family': family,
            'prediction': {f: parsed.get(f) for f in FIELDS},
            'oracle': oracle,
            'field_correct': correct,
            'correct_fields': sum(correct.values()),
            'exact_match': is_exact,
            'raw': raw,
        }
        rows.append(row)
        print('S1A_FIXTURE=' + json.dumps(row, ensure_ascii=False, separators=(',', ':')), flush=True)

    total = len(rows) * len(FIELDS)
    return {
        'field_correct_total': sum(field_correct.values()),
        'field_decisions': total,
        'primary_score': sum(field_correct.values()) / total,
        'fixture_exact_match_count': exact,
        'fixture_exact_match_rate': exact / len(rows),
        'per_dimension_accuracy': {f: field_correct[f] / len(rows) for f in FIELDS},
        'per_family': {
            family: {
                **v,
                'primary_score': v['correct_fields'] / v['field_decisions'],
                'exact_rate': v['exact'] / v['fixtures'],
            }
            for family, v in sorted(family_counts.items())
        },
        'invalid_output_count': invalid,
        'rows': rows,
    }


def paired_compare(det: dict, qwen: dict) -> dict:
    drows = {r['fixture_id']: r for r in det['rows']}
    qrows = {r['fixture_id']: r for r in qwen['rows']}
    discordance = {f: {'both_correct': 0, 'det_only': 0, 'qwen_only': 0, 'both_wrong': 0} for f in FIELDS}
    fixture_exact = {'both_exact': 0, 'det_only_exact': 0, 'qwen_only_exact': 0, 'both_nonexact': 0}
    for fid in sorted(drows):
        dr = drows[fid]
        qr = qrows[fid]
        for f in FIELDS:
            dc = dr['prediction'][f] == dr['oracle'][f]
            qc = qr['prediction'][f] == qr['oracle'][f]
            key = 'both_correct' if dc and qc else 'det_only' if dc else 'qwen_only' if qc else 'both_wrong'
            discordance[f][key] += 1
        de = bool(dr['exact_match'])
        qe = bool(qr['exact_match'])
        key = 'both_exact' if de and qe else 'det_only_exact' if de else 'qwen_only_exact' if qe else 'both_nonexact'
        fixture_exact[key] += 1
    return {
        'qwen_minus_deterministic_primary': qwen['primary_score'] - det['primary_score'],
        'qwen_minus_deterministic_exact': qwen['fixture_exact_match_rate'] - det['fixture_exact_match_rate'],
        'per_dimension_delta_qwen_minus_deterministic': {
            f: qwen['per_dimension_accuracy'][f] - det['per_dimension_accuracy'][f] for f in FIELDS
        },
        'field_decision_discordance': discordance,
        'fixture_exact_discordance': fixture_exact,
    }


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    fixtures = generate(GENERATOR_FREEZE_COMMIT)
    actual_digest = digest(fixtures)
    if len(fixtures) != EXPECTED_FIXTURES or actual_digest != EXPECTED_DIGEST:
        raise RuntimeError(f'HOLDOUT_MISMATCH:{len(fixtures)}:{actual_digest}')

    det = score_deterministic(fixtures)
    if abs(det['primary_score'] - EXPECTED_DET_PRIMARY) > 1e-12 or abs(det['fixture_exact_match_rate'] - EXPECTED_DET_EXACT) > 1e-12:
        raise RuntimeError('DETERMINISTIC_REFERENCE_MISMATCH')

    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    print('S1A_STATE=RUNTIME_ACQUIRE', flush=True)
    server_bin = acquire_runtime()
    model = WORK / MODEL_FILE
    print('S1A_STATE=MODEL_ACQUIRE', flush=True)
    download(MODEL_URL, model)
    if model.stat().st_size != MODEL_SIZE:
        raise RuntimeError(f'MODEL_SIZE_MISMATCH:{model.stat().st_size}')
    if sha256(model) != MODEL_SHA:
        raise RuntimeError('MODEL_SHA_MISMATCH')

    log_path = WORK / 'llama.log'
    log = log_path.open('w')
    server = subprocess.Popen([
        str(server_bin), '-m', str(model), '-c', '1024', '-b', '32', '-ub', '32', '--threads', '1',
        '--no-warmup', '--host', '127.0.0.1', '--port', '18080'
    ], stdout=log, stderr=subprocess.STDOUT, text=True)
    try:
        ready = False
        for _ in range(240):
            if server.poll() is not None:
                break
            try:
                with urllib.request.urlopen('http://127.0.0.1:18080/health', timeout=2) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            log.flush()
            raise RuntimeError('LLAMA_NOT_READY:' + log_path.read_text(errors='replace')[-4000:])

        print('S1A_STATE=INFERENCE', flush=True)
        qwen = score_qwen(fixtures, 'http://127.0.0.1:18080')
        comparison = paired_compare(det, qwen)
        result = {
            'schema_version': 'FUNCTION_BOUNDARY_S1A_DISJOINT_PAIRED_ACTUAL_V1',
            'protocol': PROTOCOL,
            'source_protocol': SOURCE_PROTOCOL,
            'generator_freeze_commit': GENERATOR_FREEZE_COMMIT,
            'holdout_digest': EXPECTED_DIGEST,
            'fixture_count': len(fixtures),
            'execution_wrapper_commit': head,
            'model': {
                'repository': MODEL_REPO,
                'file': MODEL_FILE,
                'size_bytes': MODEL_SIZE,
                'sha256': MODEL_SHA,
            },
            'runtime': {
                'execution_environment': 'Render build pipeline',
                'llama_cpp_tag': LLAMA_TAG,
                'llama_cpp_asset_sha256': LLAMA_SHA,
                'temperature': 0,
                'context_tokens': 1024,
                'grammar_constrained_to_visible_ids': True,
                'oracle_fields_model_visible': False,
                'family_model_visible': False,
                'github_actions_used': False,
                'google_drive_used': False,
                'qwen3_4b_used': False,
            },
            'arms': {
                'deterministic_frozen': det,
                'qwen25_1p5b': qwen,
            },
            'paired_comparison': comparison,
            'claim_limits': [
                'Same 16 fixtures and same five-field output contract are used for both arms.',
                'The holdout is synthetic and structurally disjoint from the earlier ten-family diagnostic, not a natural-corpus benchmark.',
                'Both arms receive an already supplied semantic dictionary; this does not test ontology induction or unconstrained semantic invention.',
                'No predictor, fixture, prompt, grammar, threshold, or scoring change is authorized after this wrapper commit.',
            ],
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('S1A_TERMINAL=' + json.dumps(result, ensure_ascii=False, separators=(',', ':')), flush=True)
    finally:
        if server.poll() is None:
            server.terminate()
        log.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
