#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='1dcc5a122631232e92977eba6516b42a6cf1244c'
PUBLIC_REPO='https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation.git'
def run(*args:str): return subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
def fail(detail:str): print(json.dumps({'terminal':'B2_PREFLIGHT_ADAPTER_FAILED','detail':detail},indent=2),flush=True); raise SystemExit(2)
p=run('git','fetch','--no-tags',PUBLIC_REPO,'main')
if p.returncode: fail('fetch: '+(p.stderr or p.stdout).strip())
if run('git','cat-file','-e',PIN+'^{commit}').returncode: fail('preflight commit unavailable')
p=run('git','checkout','--detach',PIN)
if p.returncode: fail('checkout: '+(p.stderr or p.stdout).strip())
if run('git','rev-parse','HEAD').stdout.strip()!=PIN: fail('HEAD mismatch')
p=subprocess.run([sys.executable,'tools/preflight_s2b2b2.py'],cwd=ROOT,text=True,capture_output=True)
print(p.stdout,flush=True)
if p.returncode: fail('B2 preflight: '+(p.stderr or p.stdout).strip())
try: terminal=json.loads(p.stdout).get('terminal')
except Exception as e: fail(f'preflight JSON parse: {e}')
if terminal!='B2_PREFLIGHT_PASS': fail('unexpected preflight terminal '+str(terminal))
print(json.dumps({'terminal':'B2_PREFLIGHT_ADAPTER_PASS','pinned_commit':PIN,'model_inference':False},indent=2),flush=True)
