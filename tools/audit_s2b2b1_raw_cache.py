#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'results/function_boundary_s2b2_b1_qwen_raw_cache_2026-10-05.json'
SEM=ROOT/'results/function_boundary_s2b2_b1_qwen_semantic_cache_2026-10-05.json'
raw=json.loads(RAW.read_text()); sem=json.loads(SEM.read_text())
if raw.get('fixture_count')!=16 or len(raw.get('rows',[]))!=16: raise SystemExit('RAW_COUNT_FAIL')
if raw.get('holdout_digest')!=sem.get('holdout_digest'): raise SystemExit('DIGEST_FAIL')
rmap={r['fixture_id']:r for r in raw['rows']}; smap={r['fixture_id']:r for r in sem['rows']}
if set(rmap)!=set(smap) or len(rmap)!=16: raise SystemExit('ID_COVERAGE_FAIL')
for fid,r in rmap.items():
    if hashlib.sha256(r['raw'].encode()).hexdigest()!=r['raw_sha256']: raise SystemExit('RAW_SHA_FAIL:'+fid)
    if json.loads(r['raw'])!=r['prediction']: raise SystemExit('RAW_PARSE_FAIL:'+fid)
    if r['prediction']!=smap[fid]['prediction']: raise SystemExit('SEMANTIC_CACHE_FAIL:'+fid)
    if r['render_log_id']!=smap[fid]['render_log_id']: raise SystemExit('LOG_ID_FAIL:'+fid)
print(json.dumps({'terminal':'B1_RAW_CACHE_INTEGRITY_PASS','fixture_count':16,'holdout_digest':raw['holdout_digest'],'raw_cache_sha256':hashlib.sha256(RAW.read_bytes()).hexdigest(),'semantic_cache_sha256':hashlib.sha256(SEM.read_bytes()).hexdigest(),'model_inference':False},indent=2))
