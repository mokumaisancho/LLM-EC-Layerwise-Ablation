#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, subprocess, tarfile, time, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=pathlib.Path('/tmp/function-boundary-s2-v2')
FIXTURE=ROOT/'fixtures'/'function_boundary_s2_v2.json'
OUT=ROOT/'results'/'function_boundary_s2_qwen25_1p5b_runtime.json'
EXPECTED_DIGEST='130f57b09549e260311d69f1b22a56fbfb0a3220880009fd132c1e76e05df14c'
LLAMA_TAG='b11146'; LLAMA_FILE='llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL=f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA='c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
MODEL_REPO='bartowski/Qwen2.5-1.5B-Instruct-GGUF'; MODEL_FILE='Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'
MODEL_URL=f'https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}'
MODEL_SHA='1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'; MODEL_SIZE=986048768

def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def download(url,dest):
 req=urllib.request.Request(url,headers={'User-Agent':'function-boundary-s2-v2/1'})
 with urllib.request.urlopen(req,timeout=240) as r,dest.open('wb') as o:
  while True:
   c=r.read(1024*1024)
   if not c: break
   o.write(c)

def canonical_digest(data):
 subject={'protocol':data['protocol'],'fixture_count':data['fixture_count'],'fixtures':data['fixtures']}
 return hashlib.sha256(json.dumps(subject,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def acquire_runtime():
 arc=WORK/LLAMA_FILE; download(LLAMA_URL,arc)
 if sha256(arc)!=LLAMA_SHA: raise RuntimeError('LLAMA_SHA_MISMATCH')
 target=WORK/'llama'; target.mkdir(parents=True,exist_ok=True)
 with tarfile.open(arc,'r:gz') as tf: tf.extractall(target,filter='data')
 hits=list(target.rglob('llama-server'))
 if not hits: raise RuntimeError('LLAMA_SERVER_NOT_FOUND')
 hits[0].chmod(0o755); return hits[0]

def post_json(url,payload,timeout=180):
 req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)

def grammar_for(ids):
 def choices(xs): return ' | '.join(json.dumps(json.dumps(x)) for x in xs)
 return '\n'.join([
  'root ::= "{" ws "\\\"candidate_ids\\\"" ws ":" ws "[" ws cand (ws "," ws cand)? (ws "," ws cand)? ws "]" ws "}" ws',
  'ws ::= [ \\t\\n\\r]*',
  'cand ::= '+choices(ids),
 ])

def resolve(ids,d):
 return {
  'primary_evidence':d['facts'][ids['primary_fact_id']],
  'semantic_concept':d['concepts'][ids['semantic_concept_id']],
  'key_relation':d['relations'][ids['key_relation_id']],
  'ambiguity':ids['ambiguity'],
  'protected_goal':d['goals'][ids['goal_id']],
 }

def run_arm(server_url,data,arm):
 rows=[]; tp_total=0; emitted_total=0; gold_total=0; exact=0; invalid=0
 system=('You are the candidate-construction stage. Given a frozen semantic state and a visible candidate ontology, emit all semantically admissible candidates needed to preserve the stated goal and evidence. Do not rank or choose a single winner. Exclude candidates that contradict the semantic state, source authority, protected goal, or explicit constraints. Return 1 to 3 unique candidate IDs only in the required JSON object.')
 for fx in data['fixtures']:
  ids=fx['oracle_s1'] if arm=='ORACLE_S1' else fx['actual_s1']
  state=resolve(ids,fx['semantic_dictionary'])
  visible={'semantic_state':state,'candidate_ontology':fx['candidate_ontology']}
  prompt='<|im_start|>system\n'+system+'<|im_end|>\n<|im_start|>user\n'+json.dumps(visible,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'<|im_end|>\n<|im_start|>assistant\n'
  resp=post_json(server_url,{'prompt':prompt,'n_predict':48,'temperature':0,'grammar':grammar_for(list(fx['candidate_ontology'])),'cache_prompt':False})
  raw=str(resp.get('content','')).strip()
  try: parsed=json.loads(raw); pred=parsed.get('candidate_ids',[])
  except Exception: parsed={}; pred=[]
  valid=isinstance(pred,list) and 1<=len(pred)<=3 and len(pred)==len(set(pred)) and all(x in fx['candidate_ontology'] for x in pred)
  pset=set(pred) if valid else set(); gold=set(fx['gold']); tp=len(pset & gold)
  if not valid: invalid+=1
  tp_total+=tp; emitted_total+=len(pset); gold_total+=len(gold); is_exact=valid and pset==gold; exact+=int(is_exact)
  row={'fixture_id':fx['id'],'category':fx['category'],'arm':arm,'semantic_state':state,'candidate_ids':pred,'gold':fx['gold'],'contract_valid':valid,'tp':tp,'recall':tp/len(gold),'precision':tp/len(pset) if pset else 0.0,'exact_set':is_exact,'raw':raw}
  rows.append(row); print('S2_FIXTURE='+json.dumps(row,separators=(',',':')),flush=True)
 recall=tp_total/gold_total; precision=tp_total/emitted_total if emitted_total else 0.0
 return {'arm':arm,'fixture_count':len(rows),'gold_candidate_total':gold_total,'emitted_candidate_total':emitted_total,'true_positive_total':tp_total,'candidate_recall':recall,'candidate_precision':precision,'candidate_f1':(2*recall*precision/(recall+precision)) if recall+precision else 0.0,'exact_set_count':exact,'exact_set_rate':exact/len(rows),'invalid_output_count':invalid,'rows':rows}

def main():
 WORK.mkdir(parents=True,exist_ok=True); OUT.parent.mkdir(parents=True,exist_ok=True)
 data=json.loads(FIXTURE.read_text())
 actual_digest=canonical_digest(data)
 if data.get('status')!='FROZEN_BEFORE_MODEL_RUN' or actual_digest!=EXPECTED_DIGEST or data.get('dataset_digest')!=EXPECTED_DIGEST:
  raise RuntimeError(f'FIXTURE_FREEZE_MISMATCH:{actual_digest}')
 head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 print('S2_STATE=RUNTIME_ACQUIRE',flush=True); server_bin=acquire_runtime()
 model=WORK/MODEL_FILE; print('S2_STATE=MODEL_ACQUIRE',flush=True); download(MODEL_URL,model)
 if model.stat().st_size!=MODEL_SIZE: raise RuntimeError(f'MODEL_SIZE_MISMATCH:{model.stat().st_size}')
 if sha256(model)!=MODEL_SHA: raise RuntimeError('MODEL_SHA_MISMATCH')
 log=(WORK/'llama.log').open('w'); server=subprocess.Popen([str(server_bin),'-m',str(model),'-c','1024','-b','32','-ub','32','--threads','1','--no-warmup','--host','127.0.0.1','--port','18080'],stdout=log,stderr=subprocess.STDOUT,text=True)
 try:
  ready=False
  for _ in range(240):
   if server.poll() is not None: break
   try:
    with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=2) as r:
     if r.status==200: ready=True; break
   except Exception: pass
   time.sleep(1)
  if not ready:
   log.flush(); raise RuntimeError('LLAMA_NOT_READY:'+(WORK/'llama.log').read_text(errors='replace')[-4000:])
  print('S2_STATE=INFERENCE_ORACLE_S1',flush=True); oracle=run_arm('http://127.0.0.1:18080/completion',data,'ORACLE_S1')
  print('S2_STATE=INFERENCE_ACTUAL_S1',flush=True); actual=run_arm('http://127.0.0.1:18080/completion',data,'ACTUAL_S1')
  delta=oracle['candidate_recall']-actual['candidate_recall']
  result={'schema_version':'FUNCTION_BOUNDARY_S2_QWEN25_1P5B_ACTUAL_V1','protocol':'FUNCTION_BOUNDARY_S2_V2','dataset_digest':EXPECTED_DIGEST,'execution_wrapper_commit':head,'model':{'repository':MODEL_REPO,'file':MODEL_FILE,'size_bytes':MODEL_SIZE,'sha256':MODEL_SHA},'runtime':{'llama_cpp_tag':LLAMA_TAG,'llama_cpp_asset_sha256':LLAMA_SHA,'temperature':0,'context_tokens':1024,'github_actions_used':False,'google_drive_used':False},'arms':{'ORACLE_S1':oracle,'ACTUAL_S1':actual},'propagation':{'recall_delta_oracle_minus_actual_s1':delta,'materiality_threshold':0.20,'material':abs(delta)>=0.20}}
  OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); print('S2_TERMINAL='+json.dumps(result,separators=(',',':')),flush=True)
 finally:
  if server.poll() is None: server.terminate()
  log.close()
if __name__=='__main__': main()
