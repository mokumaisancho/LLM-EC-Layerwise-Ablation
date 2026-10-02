#!/usr/bin/env python3
from __future__ import annotations

import asyncio
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

from websockets.asyncio.client import connect

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = pathlib.Path('/tmp/phase1-rpc-controller')
PORT = int(os.environ.get('PORT', '10000'))
TOKEN = os.environ['RPC_TUNNEL_TOKEN']
WORKER_URLS = [os.environ['RPC_WORKER_1'], os.environ['RPC_WORKER_2']]
LOCAL_RPC_PORTS = [50052, 50053]

EXPECTED_DATASET_DIGEST = '8bfce027bdc82a34b78e9b1a87f7812d907db34c164f50a9a996bd41b3b824d6'
BASE_RESEARCH_COMMIT = '8ad9b312b560731e93c95a5e54a50f13705b91a0'

LLAMA_TAG = 'b11146'
LLAMA_FILE = 'llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL = f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA256 = 'c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'

MODEL_REPO = 'bartowski/Qwen2.5-1.5B-Instruct-GGUF'
MODEL_REV = 'main'
MODEL_FILE = 'Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'
MODEL_URL = f'https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REV}/{MODEL_FILE}'
MODEL_SHA256 = '1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'
MODEL = WORK / MODEL_FILE

STATE = {'status':'BOOTING','phase':'INIT','result':None,'error':None}
LOCK = threading.Lock()
BRIDGES_READY = threading.Event()


def set_state(**kwargs):
    with LOCK:
        STATE.update(kwargs)
    print('ASSAY_STATE=' + json.dumps(STATE, ensure_ascii=False, separators=(',', ':')), flush=True)


def sha256(path: pathlib.Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, path: pathlib.Path):
    req=urllib.request.Request(url,headers={'User-Agent':'phase1-rpc-controller/1'})
    with urllib.request.urlopen(req,timeout=180) as src,path.open('wb') as out:
        while True:
            chunk=src.read(1024*1024)
            if not chunk: break
            out.write(chunk)


def acquire_runtime() -> pathlib.Path:
    archive=WORK/LLAMA_FILE
    download(LLAMA_URL,archive)
    actual=sha256(archive)
    if actual!=LLAMA_SHA256: raise RuntimeError(f'LLAMA_SHA_MISMATCH:{actual}')
    target=WORK/'llama'; target.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive,'r:gz') as tf: tf.extractall(target,filter='data')
    matches=list(target.rglob('llama-server'))
    if not matches: raise RuntimeError('LLAMA_SERVER_NOT_FOUND')
    matches[0].chmod(0o755)
    return matches[0]


async def bridge_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, worker_url: str):
    ws_url = worker_url.rstrip('/') + '/' + TOKEN
    try:
        async with connect(ws_url, max_size=None, compression=None, ping_interval=20, ping_timeout=20) as ws:
            print(f'RPC_BRIDGE_CONNECTED worker={worker_url}', flush=True)

            async def tcp_to_ws():
                while True:
                    data=await reader.read(65536)
                    if not data: break
                    await ws.send(data)

            async def ws_to_tcp():
                async for message in ws:
                    if isinstance(message,str): raise RuntimeError('TEXT_FRAME_NOT_ALLOWED')
                    writer.write(message); await writer.drain()

            tasks=[asyncio.create_task(tcp_to_ws()),asyncio.create_task(ws_to_tcp())]
            done,pending=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
            for task in pending: task.cancel()
            for task in done:
                exc=task.exception()
                if exc: raise exc
    finally:
        writer.close()
        await writer.wait_closed()


async def bridges_main():
    servers=[]
    for port,worker in zip(LOCAL_RPC_PORTS,WORKER_URLS):
        server=await asyncio.start_server(
            lambda r,w,worker=worker: bridge_connection(r,w,worker),
            '127.0.0.1',port,
        )
        servers.append(server)
    BRIDGES_READY.set()
    print('RPC_BRIDGES_READY ' + ','.join(f'127.0.0.1:{p}' for p in LOCAL_RPC_PORTS), flush=True)
    await asyncio.gather(*(s.serve_forever() for s in servers))


def start_bridges():
    asyncio.run(bridges_main())


def post_json(url: str,payload: dict,timeout: int=180):
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as resp: return json.load(resp)


def run_assay():
    llama=None; log=None
    try:
        WORK.mkdir(parents=True,exist_ok=True)
        execution_head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()

        set_state(status='RUNNING',phase='BRIDGE_START')
        threading.Thread(target=start_bridges,daemon=True).start()
        if not BRIDGES_READY.wait(10): raise RuntimeError('RPC_BRIDGES_NOT_READY')

        set_state(phase='RUNTIME_ACQUIRE')
        llama_server=acquire_runtime()

        set_state(phase='MODEL_ACQUIRE')
        download(MODEL_URL,MODEL)
        actual_size=MODEL.stat().st_size
        actual_sha=sha256(MODEL)
        if actual_sha!=MODEL_SHA256: raise RuntimeError(f'MODEL_SHA_MISMATCH:{actual_sha}')
        print(f'MODEL_VERIFIED size={actual_size} sha={actual_sha}',flush=True)

        set_state(phase='FIXTURE_GENERATE')
        generated=json.loads(subprocess.check_output(['python3','tools/generate_phase1_measurement_v2_canonical.py'],cwd=ROOT,text=True))
        if generated.get('dataset_digest')!=EXPECTED_DATASET_DIGEST:
            raise RuntimeError(f"DATASET_DIGEST_MISMATCH:{generated.get('dataset_digest')}")
        subprocess.run(['python3','tools/generate_phase1_v2_s3_states.py'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)

        set_state(phase='LLAMA_RPC_START')
        log=(WORK/'llama.log').open('w')
        cmd=[
            str(llama_server),'-m',str(MODEL),'-c','768','-b','32','-ub','32','--threads','1','--no-warmup',
            '-ngl','99','--rpc',','.join(f'127.0.0.1:{p}' for p in LOCAL_RPC_PORTS),
            '--host','127.0.0.1','--port','18080'
        ]
        print('LLAMA_CMD='+' '.join(cmd),flush=True)
        llama=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,text=True)
        ready=False
        for _ in range(240):
            if llama.poll() is not None: break
            try:
                with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=2) as resp:
                    if resp.status==200: ready=True; break
            except Exception: pass
            time.sleep(1)
        if not ready:
            log.flush(); tail=(WORK/'llama.log').read_text(errors='replace')[-10000:]
            raise RuntimeError('LLAMA_RPC_NOT_READY:'+tail)

        set_state(phase='INFERENCE')
        root=ROOT/'fixtures/phase1_v2/generated'
        system=('You are the reframing-control stage of a reasoning system. Use only the supplied semantic state. '
                'Decide whether the problem model itself must be revised. Reframing means adding, removing, splitting, '
                'merging, or reabstracting state variables to preserve the stated intent and account for evidence. '
                'Merely choosing or rejecting an action is not itself reframing. Return exactly YES or NO.')
        grammar='root ::= "YES" | "NO"'
        rows=[]
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            state=json.loads((d/'upstream/s3_semantic_state.json').read_text())
            visible={k:v for k,v in state.items() if k not in {'content_hash','artifact_id','source_refs'}}
            prompt=('<|im_start|>system\n'+system+'<|im_end|>\n<|im_start|>user\nsemantic_state:\n'+
                    json.dumps(visible,ensure_ascii=False,sort_keys=True,separators=(',',':'))+
                    '<|im_end|>\n<|im_start|>assistant\n')
            response=post_json('http://127.0.0.1:18080/completion',{'prompt':prompt,'n_predict':2,'temperature':0,'grammar':grammar,'cache_prompt':False})
            raw=str(response.get('content','')).strip().upper()
            pred=True if raw.startswith('YES') else False if raw.startswith('NO') else None
            gold=bool(json.loads((d/'hidden/evaluation.json').read_text())['reframe_required'])
            row={'fixture_id':d.name,'prediction':pred,'gold':gold,'correct':pred==gold,'raw':raw,'upstream_state_hash':state.get('content_hash')}
            rows.append(row); print('ASSAY_FIXTURE='+json.dumps(row,separators=(',',':')),flush=True)

        correct=sum(int(r['correct']) for r in rows)
        result={'schema_version':'PHASE1_QWEN25_1P5B_REFRAME_RPC_ACTUAL_V1','assay':'PHASE1_V2_S3_REFRAME_FIXED_STATE_V1',
                'fixture_generation':'phase1_v2','dataset_digest':EXPECTED_DATASET_DIGEST,
                'model_repo':MODEL_REPO,'model_revision':MODEL_REV,'model_file':MODEL_FILE,'model_size_bytes':actual_size,'model_sha256':MODEL_SHA256,
                'llama_cpp_tag':LLAMA_TAG,'llama_cpp_asset_sha256':LLAMA_SHA256,'base_research_commit':BASE_RESEARCH_COMMIT,
                'execution_wrapper_commit':execution_head,'rpc_workers':len(WORKER_URLS),'fixture_count':len(rows),'correct':correct,'accuracy':correct/len(rows),
                'rows':rows,'temperature':0,'grammar':'YES|NO','oracle_labels_model_visible':False,'google_drive_used':False,'github_actions_used':False}
        set_state(status='PASS',phase='EXIT',result=result,error=None)
    except Exception as exc:
        if log:
            try: log.flush()
            except Exception: pass
        set_state(status='FAIL',phase='EXIT',result=None,error=f'{type(exc).__name__}:{exc}')
    finally:
        if llama is not None and llama.poll() is None: llama.terminate()
        if log: log.close()


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        with LOCK: body=json.dumps(dict(STATE),ensure_ascii=False).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass


def main():
    threading.Thread(target=run_assay,daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0',PORT),H).serve_forever()

if __name__=='__main__': main()
