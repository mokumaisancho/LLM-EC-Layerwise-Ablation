#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib, json, pathlib, subprocess, sys, tarfile, time, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=pathlib.Path('/tmp/function-boundary-next-action-v2')
FIXTURE=ROOT/'fixtures'/'function_boundary_next_action_v1.json'
CONTRACT=ROOT/'docs'/'NEXT_ACTION_V2_CONTRACT_2026-10-03.json'
OUT=ROOT/'results'/'function_boundary_next_action_v2_runtime.json'
FIXTURE_BLOB='12faa9a4cacf0c91694d25f1ccce45e093d95e44'
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

def git_blob_sha(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'function-boundary-next-action-v2/1'})
 with urllib.request.urlopen(req,timeout=240) as r:return r.read()
def download(url,dest):
 b=get(url);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b);return b

def acquire_ec():
 base=ROOT/'vendor'/'ecv44'; observed={}
 for rel,expected in EC_FILES.items():
  b=(base/rel).read_bytes(); actual=git_blob_sha(b); observed[rel]=actual
  if actual!=expected: raise RuntimeError(f'EC_BLOB_MISMATCH:{rel}:{actual}:{expected}')
 sys.path.insert(0,str(base));importlib.invalidate_caches()
 return importlib.import_module('ec_next_action_authority'),importlib.import_module('ec_dynamic_frontier'),observed

def acquire_runtime():
 arc=WORK/LLAMA_FILE;download(LLAMA_URL,arc)
 if sha256(arc)!=LLAMA_SHA:raise RuntimeError('LLAMA_SHA_MISMATCH')
 target=WORK/'llama';target.mkdir(parents=True,exist_ok=True)
 with tarfile.open(arc,'r:gz') as tf:tf.extractall(target,filter='data')
 hits=list(target.rglob('llama-server'))
 if not hits:raise RuntimeError('LLAMA_SERVER_NOT_FOUND')
 hits[0].chmod(0o755);return hits[0]

def normalize_ec(ena,df,fx):
 plan=fx['plan'];done=fx.get('completed_work_ids') or [];blocked=fx.get('blocked_work') or {};kwargs={};visible_dynamic=None
 if fx.get('dynamic_spec'):
  s=fx['dynamic_spec'];ctx={'protocol':df.PROTOCOL,'plan_digest':df.plan_digest(plan),'state_revision':s['state_revision'],'dependency_graph':s['dependency_graph'],'issue_state':s['issue_state'],'completed_work_ids':sorted(done),'blocked_work':blocked,'observation_ref':f"auth:{s['state_revision']}"};ctx['state_digest']=df.state_digest(ctx);visible_dynamic=ctx
  def authority(ref,digest,revision):return ref==f'auth:{revision}' and digest==ctx['state_digest']
  kwargs={'dynamic_context':ctx,'dynamic_state_authority':authority}
 try:
  out=ena.select_next_action(plan,completed_work_ids=done,blocked_work=blocked,**kwargs);status=out['status'];work=out.get('work_id') or 'NONE';reason='NONE'
  if status=='BLOCKED':reason='ALL_REMAINING_WORK_BLOCKED'
  elif status=='NO_OPEN_WORK':reason='NO_OPEN_WORK'
  elif status=='REFRAME':reason='ISSUE_DEFINITION_REFRAME'
  return {'status':status,'work_id':work,'reason_code':reason},visible_dynamic
 except Exception as e:
  msg=str(e);reason=msg.split(':',1)[0] if msg.startswith('PRIOR_ART_GATE_PASS_REQUIRED:') else msg
  return {'status':'FAIL_CLOSED','work_id':'NONE','reason_code':reason},visible_dynamic

def post_json(url,payload,timeout=180):
 req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
def q(s):return json.dumps(json.dumps(s))
def grammar_for(work_ids):
 work=' | '.join(q(x) for x in sorted(set(work_ids)))
 fail=' | '.join(q(x) for x in ['PRIOR_ART_GATE_PASS_REQUIRED','EC_PLAN_AUTHORITY_INVALID','WORK_CANNOT_BE_BOTH_COMPLETE_AND_BLOCKED'])
 return '\n'.join([
  'root ::= execute | blocked | noopen | reframe | failclosed',
  'ws ::= [ \\t\\n\\r]*',
  'execute ::= "{" ws "\\\"status\\\"" ws ":" ws '+q('EXECUTE')+' ws "," ws "\\\"work_id\\\"" ws ":" ws work ws "," ws "\\\"reason_code\\\"" ws ":" ws '+q('NONE')+' ws "}" ws',
  'blocked ::= "{" ws "\\\"status\\\"" ws ":" ws '+q('BLOCKED')+' ws "," ws "\\\"work_id\\\"" ws ":" ws '+q('NONE')+' ws "," ws "\\\"reason_code\\\"" ws ":" ws '+q('ALL_REMAINING_WORK_BLOCKED')+' ws "}" ws',
  'noopen ::= "{" ws "\\\"status\\\"" ws ":" ws '+q('NO_OPEN_WORK')+' ws "," ws "\\\"work_id\\\"" ws ":" ws '+q('NONE')+' ws "," ws "\\\"reason_code\\\"" ws ":" ws '+q('NO_OPEN_WORK')+' ws "}" ws',
  'reframe ::= "{" ws "\\\"status\\\"" ws ":" ws '+q('REFRAME')+' ws "," ws "\\\"work_id\\\"" ws ":" ws '+q('NONE')+' ws "," ws "\\\"reason_code\\\"" ws ":" ws '+q('ISSUE_DEFINITION_REFRAME')+' ws "}" ws',
  'failclosed ::= "{" ws "\\\"status\\\"" ws ":" ws '+q('FAIL_CLOSED')+' ws "," ws "\\\"work_id\\\"" ws ":" ws '+q('NONE')+' ws "," ws "\\\"reason_code\\\"" ws ":" ws failreason ws "}" ws',
  'work ::= '+work,'failreason ::= '+fail])
def work_ids(plan):
 return [w if isinstance(w,str) else w.get('work_id','') for i in plan.get('issues',[]) for w in i.get('work',[]) if (w if isinstance(w,str) else w.get('work_id',''))]

def run_llm(server_url,fixture,contract,ec_rows):
 system=('You are the deterministic next-action authority. Apply only the supplied control contract. '
 'ISSUE-DEFINITION GATE ACTIVATION: apply the gate only when an issue contains action_class OR issue_contract. If neither key exists, the gate is NOT_APPLICABLE for legacy compatibility and must not cause REFRAME. If the gate applies and is non-PASS, return REFRAME before selection. '
 'Static selection: blocker=true first; then lower numeric P priority; then lexicographic issue_id. Within the selected issue use PRIOR_ART if present, then REPAIR, REGRESSION, EVIDENCE. '
 'Skip an explicitly blocked current work item and consider another actionable issue. Accepted architectural limitations are never actionable. After PRIOR_ART completion, prior_art_gate must be PASS or FAIL_CLOSED. Invalid plan authority and completed+blocked conflicts FAIL_CLOSED. '
 'With dynamic state, only dependency-ready issues may execute; preserve static choice unless another ready issue Pareto-dominates on blocker, dependency criticality, urgency. If only blocked work remains return BLOCKED; if no work remains return NO_OPEN_WORK. Return one JSON decision only.')
 rows=[]
 for fx,erow in zip(fixture['fixtures'],ec_rows):
  visible={'policy_contract_v2':contract['policy_corrections'],'base_policy_contract':fixture['policy_contract'],'plan':fx['plan'],'completed_work_ids':fx.get('completed_work_ids') or [],'blocked_work':fx.get('blocked_work') or {}}
  if erow['dynamic_context'] is not None:visible['dynamic_context']=erow['dynamic_context']
  prompt='<|im_start|>system\n'+system+'<|im_end|>\n<|im_start|>user\n'+json.dumps(visible,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'<|im_end|>\n<|im_start|>assistant\n'
  resp=post_json(server_url,{'prompt':prompt,'n_predict':64,'temperature':0,'grammar':grammar_for(work_ids(fx['plan'])),'cache_prompt':False});raw=str(resp.get('content','')).strip()
  try:pred=json.loads(raw)
  except Exception:pred={}
  gold=fx['oracle'];row={'fixture_id':fx['id'],'category':fx['category'],'prediction':pred,'oracle':gold,'decision_correct':pred.get('status')==gold['status'] and pred.get('work_id')==gold['work_id'],'reason_correct':pred.get('reason_code')==gold['reason_code'],'raw':raw};rows.append(row);print('NAV2_LLM='+json.dumps(row,separators=(',',':')),flush=True)
 return rows

def summary(rows):
 n=len(rows);d=sum(r['decision_correct'] for r in rows);rr=sum(r['reason_correct'] for r in rows);fc=[r for r in rows if r['oracle']['status'] in {'FAIL_CLOSED','REFRAME'}];f=sum(r['prediction'].get('status')==r['oracle']['status'] for r in fc)
 return {'fixture_count':n,'decision_correct':d,'decision_accuracy':d/n,'reason_correct':rr,'reason_accuracy':rr/n,'fail_closed_fixture_count':len(fc),'fail_closed_status_correct':f,'fail_closed_accuracy':f/len(fc) if fc else None,'rows':rows}

def main():
 WORK.mkdir(parents=True,exist_ok=True);OUT.parent.mkdir(parents=True,exist_ok=True)
 if git_blob_sha(FIXTURE.read_bytes())!=FIXTURE_BLOB:raise RuntimeError('FIXTURE_BLOB_CHANGED')
 fixture=json.loads(FIXTURE.read_text());contract=json.loads(CONTRACT.read_text())
 if contract.get('status')!='FROZEN_BEFORE_MODEL_RUN' or contract.get('fixture_oracle_mutation') is not False:raise RuntimeError('V2_CONTRACT_NOT_FROZEN')
 head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip();print('NAV2_STATE=EC_PRECHECK',flush=True);ena,df,blobs=acquire_ec();ec_rows=[]
 for fx in fixture['fixtures']:
  pred,dyn=normalize_ec(ena,df,fx);gold=fx['oracle'];row={'fixture_id':fx['id'],'category':fx['category'],'prediction':pred,'oracle':gold,'decision_correct':pred['status']==gold['status'] and pred['work_id']==gold['work_id'],'reason_correct':pred['reason_code']==gold['reason_code'],'dynamic_context':dyn};ec_rows.append(row);print('NAV2_EC='+json.dumps(row,separators=(',',':')),flush=True)
 if sum(r['decision_correct'] and r['reason_correct'] for r in ec_rows)!=17:raise RuntimeError('EC_ORACLE_PRECHECK_NOT_17_OF_17')
 print('NAV2_STATE=RUNTIME_ACQUIRE',flush=True);server_bin=acquire_runtime();model=WORK/MODEL_FILE;print('NAV2_STATE=MODEL_ACQUIRE',flush=True);download(MODEL_URL,model)
 if model.stat().st_size!=MODEL_SIZE or sha256(model)!=MODEL_SHA:raise RuntimeError('MODEL_INTEGRITY_FAILED')
 log=(WORK/'llama.log').open('w');server=subprocess.Popen([str(server_bin),'-m',str(model),'-c','2048','-b','32','-ub','32','--threads','1','--no-warmup','--host','127.0.0.1','--port','18081'],stdout=log,stderr=subprocess.STDOUT,text=True)
 try:
  ready=False
  for _ in range(240):
   if server.poll() is not None:break
   try:
    with urllib.request.urlopen('http://127.0.0.1:18081/health',timeout=2) as r:
     if r.status==200:ready=True;break
   except Exception:pass
   time.sleep(1)
  if not ready:raise RuntimeError('LLAMA_NOT_READY')
  print('NAV2_STATE=LLM_INFERENCE',flush=True);llm_rows=run_llm('http://127.0.0.1:18081/completion',fixture,contract,ec_rows);es=summary(ec_rows);ls=summary(llm_rows);gap=es['decision_accuracy']-ls['decision_accuracy'];result={'schema_version':'FUNCTION_BOUNDARY_NEXT_ACTION_ACTUAL_V2','protocol':'FUNCTION_BOUNDARY_NEXT_ACTION_V2','fixture_blob_sha':FIXTURE_BLOB,'execution_wrapper_commit':head,'ec':{'repo':'mokumaisancho/GPT-EC-Closure-Engine','commit':EC_COMMIT,'blob_shas':blobs,'source_mode':'EXACT_VENDORED_GIT_BLOBS','summary':es},'llm':{'model_repo':MODEL_REPO,'model_file':MODEL_FILE,'model_sha256':MODEL_SHA,'llama_cpp_tag':LLAMA_TAG,'temperature':0,'summary':ls},'comparison':{'ec_minus_llm_decision_accuracy':gap,'materiality_threshold':0.2,'material':abs(gap)>=0.2},'v1_defect_excluded':True,'github_actions_used':False,'google_drive_used':False};OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('NAV2_TERMINAL='+json.dumps(result,separators=(',',':')),flush=True)
 finally:
  if server.poll() is None:server.terminate()
  log.close()
if __name__=='__main__':main()
