#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import threading
import time
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = pathlib.Path('/tmp/qwen05b-assay')
MODEL = WORK / 'Qwen2.5-0.5B-Instruct-Q4_K_M.gguf'
MODEL_URL = 'https://huggingface.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/21ef23001f314d0895bd8439b08157c2d4cd9bb7/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf'
MODEL_SHA = '6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653'
MODEL_REV = '21ef23001f314d0895bd8439b08157c2d4cd9bb7'
BASE_RESEARCH_COMMIT = '8ad9b312b560731e93c95a5e54a50f13705b91a0'
EXPECTED_DATASET_DIGEST = '8bfce027bdc82a34b78e9b1a87f7812d907db34c164f50a9a996bd41b3b824d6'
STATE = {'status': 'BOOTING', 'phase': 'INIT', 'result': None, 'error': None}
LOCK = threading.Lock()


def set_state(**kwargs):
    with LOCK:
        STATE.update(kwargs)
    print('ASSAY_STATE=' + json.dumps(STATE, ensure_ascii=False, separators=(',', ':')), flush=True)


def download(url: str, dest: pathlib.Path):
    req = urllib.request.Request(url, headers={'User-Agent': 'phase1-qwen05b-assay/1'})
    with urllib.request.urlopen(req, timeout=120) as src, dest.open('wb') as out:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def find_llama_server() -> pathlib.Path:
    api = json.load(urllib.request.urlopen('https://api.github.com/repos/ggml-org/llama.cpp/releases/latest', timeout=30))
    assets = [a for a in api['assets'] if 'bin-ubuntu-x64.zip' in a['name'] and 'vulkan' not in a['name'].lower()]
    if not assets:
        raise RuntimeError('NO_LLAMA_UBUNTU_X64_ASSET')
    z = WORK / 'llama.zip'
    download(assets[0]['browser_download_url'], z)
    target = WORK / 'llama'
    with zipfile.ZipFile(z) as archive:
        archive.extractall(target)
    matches = list(target.rglob('llama-server'))
    if not matches:
        raise RuntimeError('LLAMA_SERVER_NOT_FOUND')
    matches[0].chmod(0o755)
    return matches[0]


def post_json(url: str, payload: dict, timeout: int = 120):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def run_assay():
    server = None
    try:
        WORK.mkdir(parents=True, exist_ok=True)
        set_state(status='RUNNING', phase='PRECHECK')
        head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()

        set_state(phase='RUNTIME_ACQUIRE')
        llama_server = find_llama_server()

        set_state(phase='MODEL_ACQUIRE')
        download(MODEL_URL, MODEL)
        actual_sha = sha256(MODEL)
        if actual_sha != MODEL_SHA:
            raise RuntimeError(f'MODEL_SHA_MISMATCH:{actual_sha}')

        set_state(phase='FIXTURE_GENERATE')
        generated = subprocess.check_output(['python3', 'tools/generate_phase1_measurement_v2_canonical.py'], cwd=ROOT, text=True)
        generated_doc = json.loads(generated)
        actual_digest = generated_doc.get('dataset_digest')
        if actual_digest != EXPECTED_DATASET_DIGEST:
            raise RuntimeError(f'DATASET_DIGEST_MISMATCH:{actual_digest}')
        subprocess.run(['python3', 'tools/generate_phase1_v2_s3_states.py'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)

        set_state(phase='LLAMA_START')
        server_log = (WORK / 'llama.log').open('w')
        server = subprocess.Popen([
            str(llama_server), '-m', str(MODEL), '-c', '1024', '-b', '64', '-ub', '64',
            '--threads', '1', '--host', '127.0.0.1', '--port', '18080'
        ], stdout=server_log, stderr=subprocess.STDOUT, text=True)
        ready = False
        for _ in range(180):
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
            tail = (WORK / 'llama.log').read_text(errors='replace')[-4000:]
            raise RuntimeError('LLAMA_SERVER_NOT_READY:' + tail)

        set_state(phase='INFERENCE')
        fixture_root = ROOT / 'fixtures/phase1_v2/generated'
        system = (
            'You are the reframing-control stage of a reasoning system. Use only the supplied semantic state. '
            'Decide whether the problem model itself must be revised. Reframing means adding, removing, splitting, '
            'merging, or reabstracting state variables to preserve the stated intent and account for evidence. '
            'Merely choosing or rejecting an action is not itself reframing. Return exactly YES or NO.'
        )
        grammar = 'root ::= "YES" | "NO"'
        rows = []
        for d in sorted(p for p in fixture_root.iterdir() if p.is_dir()):
            state = json.loads((d / 'upstream/s3_semantic_state.json').read_text())
            hidden = json.loads((d / 'hidden/evaluation.json').read_text())
            visible = {k: v for k, v in state.items() if k not in {'content_hash', 'artifact_id', 'source_refs'}}
            user = 'semantic_state:\n' + json.dumps(visible, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            prompt = '<|im_start|>system\n' + system + '<|im_end|>\n<|im_start|>user\n' + user + '<|im_end|>\n<|im_start|>assistant\n'
            out = post_json('http://127.0.0.1:18080/completion', {
                'prompt': prompt, 'n_predict': 2, 'temperature': 0, 'grammar': grammar, 'cache_prompt': False
            })
            raw = str(out.get('content', '')).strip().upper()
            pred = True if raw.startswith('YES') else False if raw.startswith('NO') else None
            gold = bool(hidden['reframe_required'])
            rows.append({'fixture_id': d.name, 'prediction': pred, 'gold': gold, 'correct': pred == gold, 'raw': raw})

        correct = sum(int(r['correct']) for r in rows)
        result = {
            'schema_version': 'PHASE1_QWEN25_0P5B_REFRAME_ACTUAL_V1',
            'assay': 'PHASE1_V2_S3_REFRAME_FIXED_STATE_V1',
            'fixture_generation': 'phase1_v2',
            'dataset_digest': EXPECTED_DATASET_DIGEST,
            'model_repo': 'bartowski/Qwen2.5-0.5B-Instruct-GGUF',
            'model_revision': MODEL_REV,
            'model_file': MODEL.name,
            'model_sha256': MODEL_SHA,
            'base_research_commit': BASE_RESEARCH_COMMIT,
            'execution_head': head,
            'fixture_count': len(rows),
            'correct': correct,
            'accuracy': correct / len(rows),
            'rows': rows,
            'temperature': 0,
            'grammar': 'YES|NO',
            'oracle_labels_model_visible': False,
            'google_drive_used': False,
            'github_actions_used': False
        }
        set_state(status='PASS', phase='EXIT', result=result)
    except Exception as exc:
        set_state(status='FAIL', phase='EXIT', error=f'{type(exc).__name__}:{exc}')
    finally:
        if server is not None and server.poll() is None:
            server.terminate()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        with LOCK:
            payload = dict(STATE)
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def main():
    port = int(os.environ.get('PORT', '10000'))
    threading.Thread(target=run_assay, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()


if __name__ == '__main__':
    main()
