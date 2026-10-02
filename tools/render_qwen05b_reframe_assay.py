#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import tarfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = pathlib.Path('/tmp/phase1-capacity-assay')

BASE_RESEARCH_COMMIT = '8ad9b312b560731e93c95a5e54a50f13705b91a0'
EXPECTED_DATASET_DIGEST = '8bfce027bdc82a34b78e9b1a87f7812d907db34c164f50a9a996bd41b3b824d6'

LLAMA_TAG = 'b11146'
LLAMA_FILE = 'llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL = f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA256 = 'c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'

MODEL_REPO = os.environ.get('ASSAY_MODEL_REPO', 'bartowski/Qwen2.5-0.5B-Instruct-GGUF')
MODEL_REV = os.environ.get('ASSAY_MODEL_REV', '21ef23001f314d0895bd8439b08157c2d4cd9bb7')
MODEL_FILE = os.environ.get('ASSAY_MODEL_FILE', 'Qwen2.5-0.5B-Instruct-Q4_K_M.gguf')
MODEL_SHA256 = os.environ.get('ASSAY_MODEL_SHA256', '6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653')
MODEL_SIZE_EXPECTED = int(os.environ.get('ASSAY_MODEL_SIZE_BYTES', '0') or '0')
MODEL = WORK / MODEL_FILE
MODEL_URL = f'https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REV}/{MODEL_FILE}'
CAPACITY_LABEL = os.environ.get('ASSAY_CAPACITY_LABEL', '0.5B')

STATE = {'status': 'BOOTING', 'phase': 'INIT', 'result': None, 'error': None}
LOCK = threading.Lock()


def set_state(**kwargs):
    with LOCK:
        STATE.update(kwargs)
    print('ASSAY_STATE=' + json.dumps(STATE, ensure_ascii=False, separators=(',', ':')), flush=True)


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: pathlib.Path):
    req = urllib.request.Request(url, headers={'User-Agent': 'phase1-capacity-assay/1'})
    with urllib.request.urlopen(req, timeout=180) as src, dest.open('wb') as out:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def acquire_runtime() -> pathlib.Path:
    archive = WORK / LLAMA_FILE
    download(LLAMA_URL, archive)
    actual = sha256(archive)
    if actual != LLAMA_SHA256:
        raise RuntimeError(f'LLAMA_SHA_MISMATCH:{actual}')
    target = WORK / 'llama'
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, 'r:gz') as tf:
        tf.extractall(target, filter='data')
    matches = list(target.rglob('llama-server'))
    if not matches:
        raise RuntimeError('LLAMA_SERVER_NOT_FOUND')
    matches[0].chmod(0o755)
    return matches[0]


def post_json(url: str, payload: dict, timeout: int = 180):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def run_assay():
    server = None
    server_log = None
    try:
        WORK.mkdir(parents=True, exist_ok=True)
        execution_head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()

        set_state(status='RUNNING', phase='RUNTIME_ACQUIRE')
        llama_server = acquire_runtime()

        set_state(phase='MODEL_ACQUIRE')
        download(MODEL_URL, MODEL)
        actual_size = MODEL.stat().st_size
        if MODEL_SIZE_EXPECTED and actual_size != MODEL_SIZE_EXPECTED:
            raise RuntimeError(f'MODEL_SIZE_MISMATCH:{actual_size}')
        actual_model_sha = sha256(MODEL)
        if actual_model_sha != MODEL_SHA256:
            raise RuntimeError(f'MODEL_SHA_MISMATCH:{actual_model_sha}')

        set_state(phase='FIXTURE_GENERATE')
        generated = subprocess.check_output(
            ['python3', 'tools/generate_phase1_measurement_v2_canonical.py'], cwd=ROOT, text=True
        )
        actual_digest = json.loads(generated).get('dataset_digest')
        if actual_digest != EXPECTED_DATASET_DIGEST:
            raise RuntimeError(f'DATASET_DIGEST_MISMATCH:{actual_digest}')
        subprocess.run(
            ['python3', 'tools/generate_phase1_v2_s3_states.py'], cwd=ROOT,
            check=True, stdout=subprocess.DEVNULL,
        )

        set_state(phase='LLAMA_START')
        server_log = (WORK / 'llama.log').open('w')
        server = subprocess.Popen(
            [
                str(llama_server), '-m', str(MODEL),
                '-c', '768', '-b', '32', '-ub', '32',
                '--threads', '1', '--no-warmup',
                '--host', '127.0.0.1', '--port', '18080',
            ],
            stdout=server_log, stderr=subprocess.STDOUT, text=True,
        )
        ready = False
        for _ in range(240):
            if server.poll() is not None:
                break
            try:
                with urllib.request.urlopen('http://127.0.0.1:18080/health', timeout=2) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            server_log.flush()
            tail = (WORK / 'llama.log').read_text(errors='replace')[-6000:]
            raise RuntimeError('LLAMA_SERVER_NOT_READY:' + tail)

        set_state(phase='INFERENCE')
        root = ROOT / 'fixtures/phase1_v2/generated'
        system = (
            'You are the reframing-control stage of a reasoning system. Use only the supplied semantic state. '
            'Decide whether the problem model itself must be revised. Reframing means adding, removing, splitting, '
            'merging, or reabstracting state variables to preserve the stated intent and account for evidence. '
            'Merely choosing or rejecting an action is not itself reframing. Return exactly YES or NO.'
        )
        grammar = 'root ::= "YES" | "NO"'
        rows = []
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            state = json.loads((d / 'upstream/s3_semantic_state.json').read_text())
            visible = {k: v for k, v in state.items() if k not in {'content_hash', 'artifact_id', 'source_refs'}}
            prompt = (
                '<|im_start|>system\n' + system + '<|im_end|>\n'
                '<|im_start|>user\nsemantic_state:\n' +
                json.dumps(visible, ensure_ascii=False, sort_keys=True, separators=(',', ':')) +
                '<|im_end|>\n<|im_start|>assistant\n'
            )
            response = post_json(
                'http://127.0.0.1:18080/completion',
                {'prompt': prompt, 'n_predict': 2, 'temperature': 0, 'grammar': grammar, 'cache_prompt': False},
            )
            raw = str(response.get('content', '')).strip().upper()
            pred = True if raw.startswith('YES') else False if raw.startswith('NO') else None
            hidden = json.loads((d / 'hidden/evaluation.json').read_text())
            gold = bool(hidden['reframe_required'])
            row = {
                'fixture_id': d.name,
                'prediction': pred,
                'gold': gold,
                'correct': pred == gold,
                'raw': raw,
                'upstream_state_hash': state.get('content_hash'),
            }
            rows.append(row)
            print('ASSAY_FIXTURE=' + json.dumps(row, separators=(',', ':')), flush=True)

        correct = sum(int(r['correct']) for r in rows)
        result = {
            'schema_version': 'PHASE1_QWEN_CAPACITY_REFRAME_ACTUAL_V1',
            'assay': 'PHASE1_V2_S3_REFRAME_FIXED_STATE_V1',
            'capacity_label': CAPACITY_LABEL,
            'fixture_generation': 'phase1_v2',
            'dataset_digest': EXPECTED_DATASET_DIGEST,
            'model_repo': MODEL_REPO,
            'model_revision': MODEL_REV,
            'model_file': MODEL_FILE,
            'model_size_bytes': actual_size,
            'model_sha256': MODEL_SHA256,
            'llama_cpp_tag': LLAMA_TAG,
            'llama_cpp_asset': LLAMA_FILE,
            'llama_cpp_asset_sha256': LLAMA_SHA256,
            'base_research_commit': BASE_RESEARCH_COMMIT,
            'execution_wrapper_commit': execution_head,
            'fixture_count': len(rows),
            'correct': correct,
            'accuracy': correct / len(rows),
            'rows': rows,
            'temperature': 0,
            'grammar': 'YES|NO',
            'oracle_labels_model_visible': False,
            'google_drive_used': False,
            'github_actions_used': False,
        }
        set_state(status='PASS', phase='EXIT', result=result, error=None)
    except Exception as exc:
        set_state(status='FAIL', phase='EXIT', result=None, error=f'{type(exc).__name__}:{exc}')
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
        if server_log is not None:
            server_log.close()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        with LOCK:
            body = json.dumps(dict(STATE), ensure_ascii=False).encode('utf-8')
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
