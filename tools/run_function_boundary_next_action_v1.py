#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib, json, os, pathlib, subprocess, sys, tarfile, time, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=pathlib.Path('/tmp/function-boundary-next-action-v1')
FIXTURE=ROOT/'fixtures'/'function_boundary_next_action_v1.json'
OUT=ROOT/'results'/'function_boundary_next_action_runtime.json'
EXPECTED_DIGEST='db22a68721e4adc17fd9020adf383cc41d20b66c63cfcb504ca6b6545ca39b6a'
EC_COMMIT='d5ec423968f1c9242c590e5e77ccfd92d1f59eb2'
EC_FILES={
 'ec_next_action_authority.py':'89806d27da266de9bb8a9541129fc47722dea36c',
 'ec_dynamic_frontier.py':'3cb8eb34c49d90edf2b2fd9bf10f47bb52d38147',
 'v4/ec_issue_definition_gate.py':'cfa5085cde33cd4629583392adcc7ed088ad10b1',
 'v4/ec_equation_contract.py':'16962f1eecfb3822395fd24c9d12f092f07a3d9f',
 'v4/ec_execution_semantics.py':'29814179c19bee3154807be475516173bbe841ef',
 'v4/ec_variable_space_revision.py':'1c1a41a510271ac121cc4c629937296daffef861'
}
LLAMA_TAG='b11146'; LLAMA_FILE='llama-b11146-bin-ubuntu-x64.tar.gz'; LLAMA_SHA='c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
LLAMA_URL=f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
MODEL_REPO='bartowski/Qwen2.5-1.5B-Instruct-GGUF'; MODEL_FILE='Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'; MODEL_SIZE=986048768
MODEL_SHA='1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'; MODEL_URL=f'https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}'
STATUSES=['EXECUTE','BLOCKED','NO_OPEN_WORK','REFRAME','FAIL_CLOSED']
REASONS=['NONE','ALL_REMAINING_WORK_BLOCKED','NO_OPEN_WORK','PRIOR_ART_GATE_PASS_REQUIRED','EC_PLAN_AUTHORITY_INVALID','WORK_CANNOT_BE_BOTH_COMPLETE_AND_BLOCKED','ISSUE_DEFINITION_REFRAME']

def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def git_blob_sha(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'function-boundary-next-action-v1/1'})
 with urllib.request.urlopen(req,timeout=240) as r: return r.read()

def download(url,dest):
 b=get(url); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(b); return b

def canonical_digest(data):
 subject={'protocol':data['protocol'],'fixture_count':data['fixture_count'],'fixtures':data['fixtures']}
 return hashlib.sha256(json.dumps(subject,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def acquire_ec():
 base=ROOT/'vendor'/'ecv44'
 observed={}
 for rel,expected in EC_FILES.items():
  p=base/rel
  if not p.exists(): raise RuntimeError(f'EC_VENDOR_MISSING:{rel}')
  b=p.read_bytes(); actual=git_blob_sha(b); observed[rel]=actual
  if actual!=expected: raise RuntimeError(f'EC_BLOB_MISMATCH:{rel}:{actual}:{expected}')
 sys.path.insert(0,str(base)); importlib.invalidate_caches()
 ena=importlib.import_module('ec_next_action_authority'); df=importlib.import_module('ec_dynamic_frontier')
 return ena,df,observed

def acquire_runtime():
 arc=WORK/LLAMA_FILE; download(LLAMA_URL,arc)
 if sha256(arc)!=LLAMA_SHA: raise RuntimeError('LLAMA_SHA_MISMATCH')
 target=WORK/'llama'; target.mkdir(parents=True,exist_ok=True)
 with tarfile.open(arc,'r:gz') as tf: tf.extractall(target,filter='data')
 hits=list(target.rglob('llama-server'))
 if not hits: raise RuntimeError('LLAMA_SERVER_NOT_FOUND')
 hits[0].chmod(0o755); return hits[0]

def normalize_ec(ena,df,fx):
 plan=fx['plan']; done=fx.get('completed_work_ids') or []; blocked=fx.get('blocked_work') or {}; kwargs={}
 visible_dynamic=None
 if fx.get('dynamic_spec'):
  s=fx['dynamic_spec']; ctx={'protocol':df.PROTOCOL,'plan_digest':df.plan_digest(plan),'state_revision':s['state_revision'],'dependency_graph':s['dependency_graph'],'issue_state':s['issue_state'],'completed_work_ids':sorted(done),'blocked_work':blocked,'observation_ref':f"auth:{s['state_revision']}"}
  ctx['state_digest']=df.state_digest(ctx); visible_dynamic=ctx
  def authority(ref,digest,revision): return ref==f'auth:{revision}' and digest==ctx['state_digest']
  kwargs={'dynamic_context':ctx,'dynamic_state_authority':authority}
 try:
  out=ena.select_next_action(plan,completed_work_ids=done,blocked_work=blocked,**kwargs); status=out['status']; work=out.get('work_id') or 'NONE'
  reason='NONE'
  if status=='BLOCKED': reason='ALL_REMAINING_WORK_BLOCKED'
  elif status=='NO_OPEN_WORK': reason='NO_OPEN_WORK'
  elif status=='REFRAME': reason='ISSUE_DEFINITION_REFRAME'
  return {'status':status,'work_id':work,'reason_code':reason},out,visible_dynamic
 except Exception as e:
  msg=str(e); reason=msg.split(':',1)[0] if msg.startswith('PRIOR_ART_GATE_PASS_REQUIRED:') else msg
  return {'status':'FAIL_CLOSED','work_id':'NONE','reason_code':reason},{'exception_type':type(e).__name__,'exception':msg},visible_dynamic

def post_json(url,payload,timeout=180):
 req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)

def choices(xs): return ' | '.join(json.dumps(json.dumps(x)) for x in xs)
def grammar_for(work_ids):
 return '\n'.join([
  'root ::= "{" ws "\\\"status\\\"" ws ":" ws status ws "," ws "\\\"work_id\\\"" ws ":" ws work ws "," ws "\\\"reason_code\\\"" ws ":" ws reason ws "}" ws',
  'ws ::= [ \\t\\n\\r]*','status ::= '+choices(STATUSES),'work ::= '+choices(sorted(set(work_ids+['NONE']))),'reason ::= '+choices(REASONS)
 ])

def all_work_ids(plan):
 out=[]
 for issue in plan.get('issues',[]):
  for w in issue.get('work',[]): out.append(w if isinstance(w,str) else w.get('work_id',''))
 return [x for x in out if x]

def run_llm(server_url,data,ec_rows):
 policy=data['policy_contract']
 system=('You are the next-action authority. Apply the supplied policy exactly, not what seems pragmatically fluent. Return exactly one governed decision. '
         'Important: blocker=true outranks nonblocker even when its numeric priority is worse; lower numeric P value wins within the same blocker class; ties use lexicographic issue_id. '
         'Within an issue use PRIOR_ART if present, then REPAIR, REGRESSION, EVIDENCE. Skip explicitly blocked current work and consider another actionable issue. '
         'Accepted architectural limitations are not actionable. After PRIOR_ART is completed, prior_art_gate must be PASS or fail closed. Invalid plan authority and completed/blocked conflicts fail closed. '
         'With dynamic state, only dependency-ready issues may execute and an authority-bound Pareto-dominant blocker/criticality/urgency issue may override the static choice. '
         'Insufficient governed issue definition returns REFRAME. If only blocked work remains return BLOCKED; if nothing remains return NO_OPEN_WORK. Use NONE work_id unless EXECUTE.')
 rows=[]
 for fx,erow in zip(data['fixtures'],ec_rows):
  visible={'policy_contract':policy,'plan':fx['plan'],'completed_work_ids':fx.get('completed_work_ids') or [],'blocked_work':fx.get('blocked_work') or {}}
  if erow.get('dynamic_context') is not None: visible['dynamic_context']=erow['dynamic_context']
  prompt='<|im_start|>system\n'+system+'<|im_end|>\n<|im_start|>user\n'+json.dumps(visible,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'<|im_end|>\n<|im_start|>assistant\n'
  resp=post_json(server_url,{'prompt':prompt,'n_predict':64,'temperature':0,'grammar':grammar_for(all_work_ids(fx['plan'])),'cache_prompt':False})
  raw=str(resp.get('content','')).strip()
  try: pred=json.loads(raw)
  except Exception: pred={}
  gold=fx['oracle']; decision_ok=pred.get('status')==gold['status'] and pred.get('work_id')==gold['work_id']; reason_ok=pred.get('reason_code')==gold['reason_code']
  row={'fixture_id':fx['id'],'category':fx['category'],'prediction':pred,'oracle':gold,'decision_correct':decision_ok,'reason_correct':reason_ok,'raw':raw}
  rows.append(row); print('NA_LLM='+json.dumps(row,separators=(',',':')),flush=True)
 return rows

def summarize(rows):
 n=len(rows); dec=sum(int(r['decision_correct']) for r in rows); reason=sum(int(r['reason_correct']) for r in rows)
 fail=[r for r in rows if r['oracle']['status'] in {'FAIL_CLOSED','REFRAME'}]; fc=sum(int(r['prediction'].get('status')==r['oracle']['status']) for r in fail)
 return {'fixture_count':n,'decision_correct':dec,'decision_accuracy':dec/n,'reason_correct':reason,'reason_accuracy':reason/n,'fail_closed_fixture_count':len(fail),'fail_closed_status_correct':fc,'fail_closed_accuracy':fc/len(fail) if fail else None,'rows':rows}

def main():
 WORK.mkdir(parents=True,exist_ok=True); OUT.parent.mkdir(parents=True,exist_ok=True); data=json.loads(FIXTURE.read_text())
 actual_digest=canonical_digest(data)
 if data.get('status')!='FROZEN_BEFORE_MODEL_RUN' or data.get('dataset_digest')!=EXPECTED_DIGEST or actual_digest!=EXPECTED_DIGEST: raise RuntimeError(f'FIXTURE_FREEZE_MISMATCH:{actual_digest}')
 head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 print('NA_STATE=EC_ACQUIRE',flush=True); ena,df,ec_blobs=acquire_ec()
 ec_rows=[]
 for fx in data['fixtures']:
  pred,raw,dyn=normalize_ec(ena,df,fx); gold=fx['oracle']; row={'fixture_id':fx['id'],'category':fx['category'],'prediction':pred,'oracle':gold,'decision_correct':pred['status']==gold['status'] and pred['work_id']==gold['work_id'],'reason_correct':pred['reason_code']==gold['reason_code'],'raw_ec':raw,'dynamic_context':dyn}
  ec_rows.append(row); print('NA_EC='+json.dumps({k:v for k,v in row.items() if k!='raw_ec'},separators=(',',':')),flush=True)
 print('NA_STATE=RUNTIME_ACQUIRE',flush=True); server_bin=acquire_runtime(); model=WORK/MODEL_FILE
 print('NA_STATE=MODEL_ACQUIRE',flush=True); download(MODEL_URL,model)
 if model.stat().st_size!=MODEL_SIZE or sha256(model)!=MODEL_SHA: raise RuntimeError('MODEL_INTEGRITY_FAILED')
 log=(WORK/'llama.log').open('w'); server=subprocess.Popen([str(server_bin),'-m',str(model),'-c','2048','-b','32','-ub','32','--threads','1','--no-warmup','--host','127.0.0.1','--port','18080'],stdout=log,stderr=subprocess.STDOUT,text=True)
 try:
  ready=False
  for _ in range(240):
   if server.poll() is not None: break
   try:
    with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=2) as r:
     if r.status==200: ready=True; break
   except Exception: pass
   time.sleep(1)
  if not ready: log.flush(); raise RuntimeError('LLAMA_NOT_READY:'+(WORK/'llama.log').read_text(errors='replace')[-4000:])
  print('NA_STATE=LLM_INFERENCE',flush=True); llm_rows=run_llm('http://127.0.0.1:18080/completion',data,ec_rows)
  ec_summary=summarize(ec_rows); llm_summary=summarize(llm_rows); gap=ec_summary['decision_accuracy']-llm_summary['decision_accuracy']
  result={'schema_version':'FUNCTION_BOUNDARY_NEXT_ACTION_ACTUAL_V1','protocol':'FUNCTION_BOUNDARY_NEXT_ACTION_V1','dataset_digest':EXPECTED_DIGEST,'execution_wrapper_commit':head,'ec':{'repo':'mokumaisancho/GPT-EC-Closure-Engine','commit':EC_COMMIT,'blob_shas':ec_blobs,'source_mode':'EXACT_VENDORED_GIT_BLOBS','protocol':'EC_NEXT_ACTION_V1','summary':ec_summary},'llm':{'model_repo':MODEL_REPO,'model_file':MODEL_FILE,'model_size_bytes':MODEL_SIZE,'model_sha256':MODEL_SHA,'llama_cpp_tag':LLAMA_TAG,'temperature':0,'summary':llm_summary},'comparison':{'ec_minus_llm_decision_accuracy':gap,'materiality_threshold':0.20,'material':abs(gap)>=0.20},'github_actions_used':False,'google_drive_used':False}
  OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); print('NA_TERMINAL='+json.dumps(result,separators=(',',':')),flush=True)
 finally:
  if server.poll() is None: server.terminate()
  log.close()
if __name__=='__main__': main()
