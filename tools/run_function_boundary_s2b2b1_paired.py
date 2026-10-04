#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='ea4fd8065ec5c9f1f65a5e39e0d9deee302d22c9'
PUBLIC_REPO='https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation.git'
def run(*args:str): return subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
def fail(detail:str): print(json.dumps({'terminal':'B1_EVIDENCE_AUDIT_ADAPTER_FAILED','detail':detail},indent=2),flush=True); raise SystemExit(2)
p=run('git','fetch','--no-tags',PUBLIC_REPO,'main')
if p.returncode: fail('fetch: '+(p.stderr or p.stdout).strip())
if run('git','cat-file','-e',PIN+'^{commit}').returncode: fail('audit commit unavailable')
p=run('git','checkout','--detach',PIN)
if p.returncode: fail('checkout: '+(p.stderr or p.stdout).strip())
if run('git','rev-parse','HEAD').stdout.strip()!=PIN: fail('HEAD mismatch')
for script,expected in [('tools/audit_s2b2b1_raw_cache.py','B1_RAW_CACHE_INTEGRITY_PASS'),('tools/audit_s2b2b1_paired_v3.py','B1_SCORE_AUDIT_PASS')]:
    p=subprocess.run([sys.executable,script],cwd=ROOT,text=True,capture_output=True)
    print(p.stdout,flush=True)
    if p.returncode: fail(script+': '+(p.stderr or p.stdout).strip())
    try: term=json.loads(p.stdout).get('terminal')
    except Exception as e: fail(f'{script} JSON parse: {e}')
    if term!=expected: fail(f'{script} terminal {term} != {expected}')
print(json.dumps({'terminal':'B1_EVIDENCE_AUDIT_PASS','pinned_commit':PIN,'model_inference':False},indent=2),flush=True)
