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

from tools.generate_s2b2a_composition_holdout import generate
from tools.s2b2a_composition_core import canonical_candidate_set, compose

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = pathlib.Path('/tmp/function-boundary-s2b2a-paired')
OUT = ROOT / 'results' / 'function_boundary_s2b2a_qwen25_1p5b_runtime.json'

PROTOCOL = 'FUNCTION_BOUNDARY_S2B2A_COMPOSITION_PAIRED_V1'
SOURCE_PROTOCOL = 'FUNCTION_BOUNDARY_S2B2A_COMPOSITION_HOLDOUT_V1'
GENERATOR_FREEZE_COMMIT = 'f88e37abf64c10e7e56ce61b5b5c9d6fbb09a075'
EXPECTED_DIGEST = 'a58e978a26f86f41ce9b08e36003e08c4682cd144a3d70a5aa945bd539f0f845'
EXPECTED_FIXTURES = 16

LLAMA_TAG = 'b11146'
LLAMA_FILE = 'llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL = f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA = 'c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
MODEL_REPO = 'bartowski/Qwen2.5-1.5B-Instruct-GGUF'
MODEL_FILE = 'Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'
MODEL_URL = f'https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}'
MODEL_SHA = '1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'
MODEL_SIZE = 986048768


def digest(fixtures: list[dict]) -> str:
    return hashlib.sha256(json.dumps(fixtures, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: pathlib.Path) -> None:
    req = urllib.request.Request(url, headers={'User-Agent': 'function-boundary-s2b2a-paired/1'})
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


def _choices(values: list[str]) -> str:
    return ' | '.join(json.dumps(json.dumps(v)) for v in values)


def grammar_for(visible: dict) -> str:
    actions = sorted({p['action_class'] for p in visible['primitive_actions']})
    params = sorted(visible['domains'])
    if len(params) not in {1, 2}:
        raise RuntimeError('UNSUPPORTED_PARAM_COUNT')

    rules = [
        'root ::= "[" ws candidate ws "]" ws',
        'ws ::= [ \\t\\n\\r]*',
        'action ::= ' + _choices(actions),
    ]
    for i, p in enumerate(params):
        rules.append(f'v{i} ::= ' + _choices(sorted(visible['domains'][p])))

    if len(params) == 1:
        p0 = json.dumps(json.dumps(params[0]))
        rules.append('candidate ::= "{" ws "\\\"action_class\\\"" ws ":" ws action ws "," ws "\\\"bindings\\\"" ws ":" ws "{" ws ' + p0 + ' ws ":" ws v0 ws "}" ws "}"')
    else:
        p0 = json.dumps(json.dumps(params[0])); p1 = json.dumps(json.dumps(params[1]))
        rules.append('candidate ::= "{" ws "\\\"action_class\\\"" ws ":" ws action ws "," ws "\\\"bindings\\\"" ws ":" ws "{" ws ' + p0 + ' ws ":" ws v0 ws "," ws ' + p1 + ' ws ":" ws v1 ws "}" ws "}"')
    return '\n'.join(rules)


def post_json(url: str, payload: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def canonical(candidates: list[dict]) -> list[dict]:
    return canonical_candidate_set(candidates)


def valid_candidate(visible: dict, candidate: dict) -> bool:
    if not isinstance(candidate, dict) or set(candidate) != {'action_class','bindings'}:
        return False
    if candidate['action_class'] not in {p['action_class'] for p in visible['primitive_actions']}:
        return False
    if not isinstance(candidate['bindings'], dict) or set(candidate['bindings']) != set(visible['domains']):
        return False
    return all(candidate['bindings'][k] in visible['domains'][k] for k in visible['domains'])


def score_qwen(fixtures: list[dict], server_url: str) -> dict:
    system = (
        'You are a symbolic candidate-construction stage. The correct candidate instance is intentionally absent from existing_candidates. '
        'Using only the structured relation requirements, current state, parameter domains, and primitive action schemas, construct exactly one authorized candidate instance. '
        'Its preconditions must hold, its effects must satisfy the required effect, and it must not produce a forbidden effect. '
        'Use only a visible primitive action_class and visible domain values. Return only the required JSON array with one candidate object.'
    )
    tp = emitted = gold_total = exact = invalid = fail_open = 0
    rows = []
    fam = defaultdict(lambda:{'fixtures':0,'tp':0,'emitted':0,'gold':0,'exact':0,'invalid':0,'fail_open':0})

    for fixture in fixtures:
        visible = fixture['visible']
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
        raw = str(resp.get('content','')).strip()
        bad = False
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, list) or len(parsed) != 1 or not valid_candidate(visible, parsed[0]):
                bad = True
                parsed = []
        except Exception:
            bad = True
            parsed = []
        invalid += int(bad)

        pred = canonical(parsed)
        gold = canonical(fixture['oracle']['candidates'])
        ps = {json.dumps(x, sort_keys=True, separators=(',', ':')) for x in pred}
        gs = {json.dumps(x, sort_keys=True, separators=(',', ':')) for x in gold}
        hit = len(ps & gs)
        fo = len(ps - gs)
        ex = ps == gs
        tp += hit; emitted += len(ps); gold_total += len(gs); exact += int(ex); fail_open += fo

        b = fam[fixture['family']]
        b['fixtures'] += 1; b['tp'] += hit; b['emitted'] += len(ps); b['gold'] += len(gs); b['exact'] += int(ex); b['invalid'] += int(bad); b['fail_open'] += fo
        row = {'fixture_id':fixture['id'],'family':fixture['family'],'prediction':pred,'oracle':gold,'tp':hit,'exact':ex,'invalid':bad,'fail_open':fo,'raw':raw}
        rows.append(row)
        print('S2B2A_FIXTURE=' + json.dumps(row, ensure_ascii=False, separators=(',', ':')), flush=True)

    recall = tp/gold_total if gold_total else 1.0
    precision = tp/emitted if emitted else 0.0
    family_metrics = {}
    for name,v in sorted(fam.items()):
        r = v['tp']/v['gold'] if v['gold'] else 1.0
        p = v['tp']/v['emitted'] if v['emitted'] else 0.0
        family_metrics[name] = {**v,'recall':r,'precision':p,'f1':2*r*p/(r+p) if r+p else 0.0,'exact_set_rate':v['exact']/v['fixtures']}
    return {
        'candidate_recall': recall,
        'candidate_precision': precision,
        'f1': 2*recall*precision/(recall+precision) if recall+precision else 0.0,
        'exact_set_rate': exact/len(fixtures),
        'true_positive_total': tp,
        'emitted_total': emitted,
        'gold_total': gold_total,
        'invalid_output_count': invalid,
        'forbidden_fail_open_count': fail_open,
        'family_metrics': family_metrics,
        'rows': rows,
    }


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True); OUT.parent.mkdir(parents=True, exist_ok=True)
    fixtures = generate(GENERATOR_FREEZE_COMMIT)
    if len(fixtures) != EXPECTED_FIXTURES or digest(fixtures) != EXPECTED_DIGEST:
        raise RuntimeError('HOLDOUT_MISMATCH')
    det = []
    for f in fixtures:
        pred = canonical(compose(f['visible']))
        gold = canonical(f['oracle']['candidates'])
        if pred != gold:
            raise RuntimeError('DETERMINISTIC_REFERENCE_MISMATCH:' + f['id'])
        det.append({'fixture_id':f['id'],'prediction':pred,'oracle':gold,'exact':True})

    head = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'], text=True).strip()
    print('S2B2A_STATE=RUNTIME_ACQUIRE', flush=True)
    server_bin = acquire_runtime()
    model = WORK / MODEL_FILE
    print('S2B2A_STATE=MODEL_ACQUIRE', flush=True)
    download(MODEL_URL, model)
    if model.stat().st_size != MODEL_SIZE: raise RuntimeError('MODEL_SIZE_MISMATCH')
    if sha256(model) != MODEL_SHA: raise RuntimeError('MODEL_SHA_MISMATCH')

    log_path = WORK / 'llama.log'; log = log_path.open('w')
    server = subprocess.Popen([str(server_bin),'-m',str(model),'-c','1024','-b','32','-ub','32','--threads','1','--no-warmup','--host','127.0.0.1','--port','18080'], stdout=log, stderr=subprocess.STDOUT, text=True)
    try:
        ready=False
        for _ in range(240):
            if server.poll() is not None: break
            try:
                with urllib.request.urlopen('http://127.0.0.1:18080/health', timeout=2) as r:
                    if r.status == 200: ready=True; break
            except Exception: pass
            time.sleep(1)
        if not ready:
            log.flush(); raise RuntimeError('LLAMA_NOT_READY:' + log_path.read_text(errors='replace')[-4000:])
        print('S2B2A_STATE=INFERENCE', flush=True)
        qwen = score_qwen(fixtures, 'http://127.0.0.1:18080')
        result = {
            'schema_version':'FUNCTION_BOUNDARY_S2B2A_COMPOSITION_PAIRED_ACTUAL_V1',
            'protocol':PROTOCOL,
            'source_protocol':SOURCE_PROTOCOL,
            'issue':43,
            'stage':'A_COMPOSITION_FROM_KNOWN_PRIMITIVES',
            'holdout_digest':EXPECTED_DIGEST,
            'fixture_count':len(fixtures),
            'execution_wrapper_commit':head,
            'model':{'repository':MODEL_REPO,'file':MODEL_FILE,'size_bytes':MODEL_SIZE,'sha256':MODEL_SHA},
            'runtime':{'execution_environment':'Render build pipeline','llama_cpp_tag':LLAMA_TAG,'llama_cpp_asset_sha256':LLAMA_SHA,'temperature':0,'context_tokens':1024,'candidate_budget_per_fixture':1,'grammar_constrained_to_visible_primitive_vocabulary':True,'oracle_model_visible':False,'family_model_visible':False,'github_actions_used':False,'google_drive_used':False,'qwen3_4b_used':False},
            'arms':{
                'deterministic_frozen':{'candidate_recall':1.0,'candidate_precision':1.0,'f1':1.0,'exact_set_rate':1.0,'invalid_output_count':0,'forbidden_fail_open_count':0},
                'qwen25_1p5b':qwen,
            },
            'paired_delta_qwen_minus_deterministic':{'recall':qwen['candidate_recall']-1.0,'precision':qwen['candidate_precision']-1.0,'f1':qwen['f1']-1.0,'exact_set_rate':qwen['exact_set_rate']-1.0},
            'claim_limits':['Stage A tests composition/binding from an already supplied symbolic primitive ontology only.','It does not test missing-class/operator invention.','It does not test raw-language relation extraction.','Same frozen 16 fixtures and exactly one-candidate budget are used for both arms.']
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('S2B2A_TERMINAL=' + json.dumps(result, ensure_ascii=False, separators=(',', ':')), flush=True)
    finally:
        if server.poll() is None: server.terminate()
        log.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
