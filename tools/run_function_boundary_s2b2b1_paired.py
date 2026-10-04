#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PIN='6f686a8c458f7e7c74c5c5e6b378493cb423399a'
PUBLIC_REPO='https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation.git'

def run(*args:str): return subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
def fail(detail:str):
    print(json.dumps({'terminal':'B1_AUDIT_ADAPTER_FAILED','detail':detail},indent=2),flush=True); raise SystemExit(2)

p=run('git','fetch','--no-tags',PUBLIC_REPO,'main')
if p.returncode: fail('public main fetch: '+(p.stderr or p.stdout).strip())
p=run('git','cat-file','-e',PIN+'^{commit}')
if p.returncode: fail('audit commit unavailable')
p=run('git','checkout','--detach',PIN)
if p.returncode: fail('checkout audit commit: '+(p.stderr or p.stdout).strip())
if run('git','rev-parse','HEAD').stdout.strip()!=PIN: fail('HEAD not audit commit')
print(json.dumps({'terminal':'B1_AUDIT_ADAPTER_PASS','pinned_commit':PIN,'model_inference':False},indent=2),flush=True)
os.execv(sys.executable,[sys.executable,'tools/audit_s2b2b1_paired_v3.py'])
