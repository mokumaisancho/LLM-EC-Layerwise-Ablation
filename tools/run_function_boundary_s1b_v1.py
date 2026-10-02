#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'fixtures'/'function_boundary_s1b_v1.json'
SOURCE=ROOT/'vendor'/'ecv44'/'poc07_epistemic_cache.py'
OUT=ROOT/'results'/'function_boundary_s1b_ec_actual_2026-10-03.json'
EXPECTED_SOURCE_BLOB='838ef8f679a4c7c6226312fca4c693bcd3822bb8'
EXPECTED_DATASET_DIGEST='38e10530d0645bc73418fcfd61f5137d1da53ffd27e7324a2eb0a615a4e082b3'
EC_REPO='mokumaisancho/GPT-EC-Closure-Engine'
EC_COMMIT='d5ec423968f1c9242c590e5e77ccfd92d1f59eb2'

def git_blob_sha(b:bytes)->str:
 return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def canon_digest(data:dict)->str:
 subject={'protocol':data['protocol'],'fixture_count':data['fixture_count'],'fixtures':data['fixtures']}
 return hashlib.sha256(json.dumps(subject,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def load_module():
 actual=git_blob_sha(SOURCE.read_bytes())
 if actual!=EXPECTED_SOURCE_BLOB: raise RuntimeError(f'EC_SOURCE_BLOB_MISMATCH:{actual}')
 spec=importlib.util.spec_from_file_location('poc07_epistemic_cache',SOURCE)
 mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
 return mod,actual

def scope(mod, raw):
 return mod.Scope(**dict(raw or {}))

def execute_fixture(mod, fx):
 valid=set(fx['valid_sources']); cache=mod.EpistemicCache(source_validator=lambda ref: ref in valid)
 for st in fx['steps']:
  op=st['op']
  if op=='add_memory':
   cache.add_memory(st['item_id'],st['payload'],claim_key=st['claim_key'],scope=scope(mod,st.get('scope')),verified=st['verified'],authority=st['authority'],source_refs=st.get('source_refs',[]),ttl=st.get('ttl'))
  elif op=='add_learning':
   cache.add_learning(st['item_id'],st['payload'],claim_key=st['claim_key'],scope=scope(mod,st.get('scope')),source_refs=st.get('source_refs',[]),ttl=st.get('ttl'))
  elif op=='relate': cache.relate(st['left'],st['relation'],st['right'])
  elif op=='revoke': cache.revoke(st['item_id'])
  else: raise RuntimeError('UNKNOWN_STEP:'+op)
 q=fx['query']; d=cache.retrieve(scope(mod,q.get('scope')),kind=q.get('kind'),limit=q.get('limit',5),now_seq=q.get('now_seq'))
 return {'status':d.status,'selected_ids':[x.item_id for x in d.selected],'reasons':list(d.reasons),'requires_revalidation':d.requires_revalidation,'examined_candidates':d.examined_candidates}

def main():
 data=json.loads(FIXTURE.read_text())
 if data.get('status')!='FROZEN_BEFORE_EXECUTION': raise RuntimeError('FIXTURE_NOT_FROZEN')
 digest=canon_digest(data)
 if data.get('dataset_digest')!=EXPECTED_DATASET_DIGEST or digest!=EXPECTED_DATASET_DIGEST: raise RuntimeError(f'DATASET_DIGEST_MISMATCH:{digest}')
 mod,source_blob=load_module(); rows=[]; correct=0; fail_open=0
 for fx in data['fixtures']:
  actual=execute_fixture(mod,fx); oracle=fx['oracle']; ok=(actual['status']==oracle['status'] and actual['selected_ids']==oracle['selected_ids'] and actual['reasons']==oracle['reasons'])
  if ok: correct+=1
  if oracle['status']=='FALLBACK_SOURCE' and actual['status']=='USE_CACHE': fail_open+=1
  row={'fixture_id':fx['id'],'category':fx['category'],'actual':actual,'oracle':oracle,'correct':ok}; rows.append(row); print('S1B_ROW='+json.dumps(row,separators=(',',':')),flush=True)
 n=len(rows); acc=correct/n; passed=acc>=float(data['acceptance']['minimum_accuracy']) and fail_open<=int(data['acceptance']['fail_open_allowed'])
 head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 result={'schema_version':'FUNCTION_BOUNDARY_S1B_EC_ACTUAL_V1','protocol':data['protocol'],'dataset_digest':digest,'execution_wrapper_commit':head,'ec_source':{'repo':EC_REPO,'commit':EC_COMMIT,'path':'02_experiments/metacognition_vnext/poc07_epistemic_cache/epistemic_cache.py','git_blob_sha':source_blob},'fixture_count':n,'correct':correct,'accuracy':acc,'fail_open_count':fail_open,'acceptance':data['acceptance'],'pass':passed,'rows':rows,'scope_boundary':{'externalized':['structured evidence source validation','freshness/supersession','conflict abstention','revocation propagation','expiry','scope-specific retrieval'],'not_externalized_by_this_assay':['raw-language parsing','negation interpretation from text','arbitrary semantic relation extraction','novel candidate generation']},'github_actions_used':False,'google_drive_used':False}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); print('S1B_TERMINAL='+json.dumps(result,separators=(',',':')),flush=True)
if __name__=='__main__': main()
