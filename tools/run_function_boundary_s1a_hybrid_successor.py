#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tarfile
import time
import urllib.request
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.generate_s1a_hybrid_successor import generate, digest
from tools.s1a_predictor_core import FIELDS, score as score_deterministic

WORK = pathlib.Path('/tmp/function-boundary-s1a-hybrid-successor')
OUT = ROOT / 'results' / 'function_boundary_s1a_hybrid_successor_runtime.json'

PROTOCOL = 'FUNCTION_BOUNDARY_S1A_HYBRID_SUCCESSOR_THREE_ARM_V1'
SOURCE_PROTOCOL = 'FUNCTION_BOUNDARY_S1A_HYBRID_SUCCESSOR_V1'
ROUTE_FREEZE_COMMIT = 'b9fc26809da58ed25572454f3de5a09e99930b6a'
GENERATOR_FREEZE_COMMIT = 'd38cda27c906fa8c92b070c97821da3f0143e6ed'
EXPECTED_DIGEST = '8cf95fa3e9fc44c5ad155ac38b551aaa497f8fa82133cb5ef0f39e9d97a55404'
EXPECTED_FIXTURES = 16
MATERIALITY_THRESHOLD = 0.20

LLAMA_TAG = 'b11146'
LLAMA_FILE = 'llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL = f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA = 'c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
MODEL_REPO = 'bartowski/Qwen2.5-1.5B-Instruct-GGUF'
MODEL_FILE = 'Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'
MODEL_URL = f'https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}'
MODEL_SHA = '1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'
MODEL_SIZE = 986048768

HYBRID_ROUTE = {
    'primary_fact_id': 'qwen25_1p5b',
    'semantic_concept_id': 'deterministic_frozen',
    'key_relation_id': 'deterministic_frozen',
    'ambiguity': 'deterministic_frozen',
    'goal_id': 'deterministic_frozen',
}


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: pathlib.Path) -> None:
    req = urllib.request.Request(url, headers={'User-Agent': 'function-boundary-s1a-hybrid-successor/1'})
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
    def choices(values: list[str]) -> str:
        return ' | '.join(json.dumps(json.dumps(v)) for v in values)
    return '\n'.join([
        'root ::= "{" ws "\\\"primary_fact_id\\\"" ws ":" ws fact ws "," ws "\\\"semantic_concept_id\\\"" ws ":" ws concept ws "," ws "\\\"key_relation_id\\\"" ws ":" ws rel ws "," ws "\\\"ambiguity\\\"" ws ":" ws amb ws "," ws "\\\"goal_id\\\"" ws ":" ws goal ws "}" ws',
        'ws ::= [ \\t\\n\\r]*',
        'fact ::= ' + choices(list(visible['facts'])),
        'concept ::= ' + choices(list(visible['concepts'])),
        'rel ::= ' + choices(list(visible['relations'])),
        'amb ::= "\\\"YES\\\"" | "\\\"NO\\\""',
        'goal ::= ' + choices(list(visible['goals'])),
    ])


def post_json(url: str, payload: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def score_rows(fixtures: list[dict], predictions: dict[str, dict]) -> dict:
    correct_total = 0
    exact = 0
    dims = {f: 0 for f in FIELDS}
    rows = []
    per_family = defaultdict(lambda: {'fixtures':0,'correct_fields':0,'field_decisions':0,'exact':0})
    for fx in fixtures:
        pred = {f: predictions[fx['id']].get(f) for f in FIELDS}
        oracle = fx['oracle']
        hits = {f: pred[f] == oracle[f] for f in FIELDS}
        n = sum(hits.values())
        correct_total += n
        exact += int(n == len(FIELDS))
        for f in FIELDS:
            dims[f] += int(hits[f])
        b = per_family[fx['family']]
        b['fixtures'] += 1; b['correct_fields'] += n; b['field_decisions'] += len(FIELDS); b['exact'] += int(n == len(FIELDS))
        rows.append({'fixture_id':fx['id'],'family':fx['family'],'prediction':pred,'oracle':oracle,'field_correct':hits,'correct_fields':n,'exact_match':n == len(FIELDS)})
    total = len(fixtures) * len(FIELDS)
    return {
        'field_correct_total': correct_total,
        'field_decisions': total,
        'primary_score': correct_total / total,
        'fixture_exact_match_count': exact,
        'fixture_exact_match_rate': exact / len(fixtures),
        'per_dimension_accuracy': {f:dims[f]/len(fixtures) for f in FIELDS},
        'per_family': {k:{**v,'primary_score':v['correct_fields']/v['field_decisions'],'exact_rate':v['exact']/v['fixtures']} for k,v in sorted(per_family.items())},
        'rows': rows,
    }


def run_qwen(fixtures: list[dict], server_url: str) -> tuple[dict, dict[str, dict]]:
    system = (
        'You are a semantic-grounding stage. Use only the supplied visible task. '
        'Select the single primary evidence fact, the best matching domain concept, '
        'the key semantic relation, whether the meaning/referent remains ambiguous, '
        'and the protected goal. IDs and option descriptions are supplied in the task. '
        'Do not invent IDs. Return only the required JSON object.'
    )
    predictions = {}
    invalid = 0
    for fx in fixtures:
        visible = fx['visible']
        prompt = '<|im_start|>system\n' + system + '<|im_end|>\n<|im_start|>user\n' + json.dumps(visible, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '<|im_end|>\n<|im_start|>assistant\n'
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
        predictions[fx['id']] = {f: parsed.get(f) for f in FIELDS}
        print('HYBRID_QWEN_FIXTURE=' + json.dumps({'fixture_id':fx['id'],'prediction':predictions[fx['id']]}, separators=(',', ':')), flush=True)
    scored = score_rows(fixtures, predictions)
    scored['invalid_output_count'] = invalid
    return scored, predictions


def row_predictions(scored: dict) -> dict[str, dict]:
    return {r['fixture_id']: r['prediction'] for r in scored['rows']}


def build_hybrid(det: dict, qwen_predictions: dict[str, dict]) -> dict[str, dict]:
    det_predictions = row_predictions(det)
    out = {}
    for fid in det_predictions:
        out[fid] = {
            'primary_fact_id': qwen_predictions[fid]['primary_fact_id'],
            'semantic_concept_id': det_predictions[fid]['semantic_concept_id'],
            'key_relation_id': det_predictions[fid]['key_relation_id'],
            'ambiguity': det_predictions[fid]['ambiguity'],
            'goal_id': det_predictions[fid]['goal_id'],
        }
    return out


def arm_summary(arm: dict) -> dict:
    return {
        'primary_score': arm['primary_score'],
        'fixture_exact_match_rate': arm['fixture_exact_match_rate'],
        'per_dimension_accuracy': arm['per_dimension_accuracy'],
    }


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fixtures = generate(GENERATOR_FREEZE_COMMIT)
    actual_digest = digest(fixtures)
    if len(fixtures) != EXPECTED_FIXTURES or actual_digest != EXPECTED_DIGEST:
        raise RuntimeError(f'HOLDOUT_MISMATCH:{len(fixtures)}:{actual_digest}')

    head = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'], text=True).strip()
    print('HYBRID_STATE=FIXTURE_VERIFIED', flush=True)
    det = score_deterministic(fixtures)

    print('HYBRID_STATE=RUNTIME_ACQUIRE', flush=True)
    server_bin = acquire_runtime()
    model = WORK / MODEL_FILE
    print('HYBRID_STATE=MODEL_ACQUIRE', flush=True)
    download(MODEL_URL, model)
    if model.stat().st_size != MODEL_SIZE:
        raise RuntimeError(f'MODEL_SIZE_MISMATCH:{model.stat().st_size}')
    if sha256(model) != MODEL_SHA:
        raise RuntimeError('MODEL_SHA_MISMATCH')

    log_path = WORK / 'llama.log'
    log = log_path.open('w')
    server = subprocess.Popen([str(server_bin),'-m',str(model),'-c','1024','-b','32','-ub','32','--threads','1','--no-warmup','--host','127.0.0.1','--port','18080'], stdout=log, stderr=subprocess.STDOUT, text=True)
    try:
        ready = False
        for _ in range(240):
            if server.poll() is not None:
                break
            try:
                with urllib.request.urlopen('http://127.0.0.1:18080/health', timeout=2) as r:
                    if r.status == 200:
                        ready = True; break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            log.flush(); raise RuntimeError('LLAMA_NOT_READY:' + log_path.read_text(errors='replace')[-4000:])

        print('HYBRID_STATE=QWEN_INFERENCE', flush=True)
        qwen, qwen_predictions = run_qwen(fixtures, 'http://127.0.0.1:18080')
        hybrid_predictions = build_hybrid(det, qwen_predictions)
        hybrid = score_rows(fixtures, hybrid_predictions)

        best_single_primary = max(det['primary_score'], qwen['primary_score'])
        best_single_exact = max(det['fixture_exact_match_rate'], qwen['fixture_exact_match_rate'])
        result = {
            'schema_version':'FUNCTION_BOUNDARY_S1A_HYBRID_SUCCESSOR_ACTUAL_V1',
            'protocol':PROTOCOL,
            'source_protocol':SOURCE_PROTOCOL,
            'route_freeze_commit':ROUTE_FREEZE_COMMIT,
            'generator_freeze_commit':GENERATOR_FREEZE_COMMIT,
            'holdout_digest':EXPECTED_DIGEST,
            'fixture_count':len(fixtures),
            'execution_wrapper_commit':head,
            'hybrid_route':HYBRID_ROUTE,
            'model':{'repository':MODEL_REPO,'file':MODEL_FILE,'size_bytes':MODEL_SIZE,'sha256':MODEL_SHA},
            'runtime':{'execution_environment':'Render build pipeline','llama_cpp_tag':LLAMA_TAG,'llama_cpp_asset_sha256':LLAMA_SHA,'temperature':0,'context_tokens':1024,'grammar_constrained_to_visible_ids':True,'oracle_fields_model_visible':False,'family_model_visible':False,'github_actions_used':False,'google_drive_used':False,'qwen3_4b_used':False},
            'arms':{'deterministic_frozen':det,'qwen25_1p5b':qwen,'frozen_hybrid':hybrid},
            'comparison':{
                'summaries':{'deterministic_frozen':arm_summary(det),'qwen25_1p5b':arm_summary(qwen),'frozen_hybrid':arm_summary(hybrid)},
                'hybrid_minus_best_single_primary':hybrid['primary_score'] - best_single_primary,
                'hybrid_minus_best_single_exact':hybrid['fixture_exact_match_rate'] - best_single_exact,
                'hybrid_primary_material_vs_best_single':abs(hybrid['primary_score'] - best_single_primary) >= MATERIALITY_THRESHOLD,
                'materiality_threshold':MATERIALITY_THRESHOLD
            },
            'claim_limits':[
                'Routing was frozen before successor generator creation.',
                'Generator and digest were frozen before any scoring.',
                'Fresh synthetic families do not reuse the prior S1A structural families, but this is not a natural-corpus benchmark.',
                'Scope is supplied-dictionary grounding only; ontology induction, missing-candidate invention, and open-ended synthesis remain untested.'
            ]
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('HYBRID_TERMINAL=' + json.dumps(result, ensure_ascii=False, separators=(',', ':')), flush=True)
    finally:
        if server.poll() is None:
            server.terminate()
        log.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
