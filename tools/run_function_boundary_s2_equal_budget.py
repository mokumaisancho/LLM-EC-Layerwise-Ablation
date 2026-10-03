#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math, pathlib, re, subprocess, tarfile, time, urllib.request
from collections import Counter

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=pathlib.Path('/tmp/function-boundary-s2-equal-budget')
FIXTURE=ROOT/'fixtures'/'function_boundary_s2_v2.json'
OUT=ROOT/'results'/'function_boundary_s2_equal_budget_runtime.json'
EXPECTED_DIGEST='130f57b09549e260311d69f1b22a56fbfb0a3220880009fd132c1e76e05df14c'
LLAMA_TAG='b11146'; LLAMA_FILE='llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL=f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA='c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
MODEL_REPO='bartowski/Qwen2.5-1.5B-Instruct-GGUF'; MODEL_FILE='Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'
MODEL_URL=f'https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}'
MODEL_SHA='1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'; MODEL_SIZE=986048768
BUDGETS=(1,2,3)
STOPWORDS={'a','an','and','are','as','at','be','because','but','by','for','from','has','have','in','is','it','of','on','or','that','the','their','there','this','to','under','until','was','were','which','with','without','already','only','every','both','all','more','one','than','into','around','during','current'}
TOKEN_RE=re.compile(r'[a-z0-9]+'); ID_RE=re.compile(r'f\d+|c_[a-z0-9_]+|g\d+',re.I)

def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def download(url,dest):
 req=urllib.request.Request(url,headers={'User-Agent':'function-boundary-s2-equal-budget/1'})
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

def grammar_for_exact(ids,k):
 def choices(xs): return ' | '.join(json.dumps(json.dumps(x)) for x in xs)
 inner='cand' + ''.join(' ws "," ws cand' for _ in range(k-1))
 return '\n'.join([
  f'root ::= "{{" ws "\\\"candidate_ids\\\"" ws ":" ws "[" ws {inner} ws "]" ws "}}" ws',
  'ws ::= [ \\t\\n\\r]*',
  'cand ::= '+choices(ids),
 ])

def resolve(ids,d):
 return {'primary_evidence':d['facts'][ids['primary_fact_id']],'semantic_concept':d['concepts'][ids['semantic_concept_id']],'key_relation':d['relations'][ids['key_relation_id']],'ambiguity':ids['ambiguity'],'protected_goal':d['goals'][ids['goal_id']]}

def norm_text(text): return re.sub(r'\s+',' ',text.lower().replace('_',' ').replace('-',' ')).strip()
def tokens(text): return [t for t in TOKEN_RE.findall(norm_text(text)) if t not in STOPWORDS]
def char3(text):
 s=norm_text(text); return Counter(s[i:i+3] for i in range(max(0,len(s)-2)))
def cosine(a,b):
 if not a or not b:return 0.0
 dot=sum(v*b.get(k,0.0) for k,v in a.items()); na=math.sqrt(sum(v*v for v in a.values())); nb=math.sqrt(sum(v*v for v in b.values()))
 return dot/(na*nb) if na and nb else 0.0

def resolve_selected_semantics(fx):
 s1=fx['oracle_s1']; d=fx['semantic_dictionary']; parts=[]; seen=set()
 def add(x):
  if x not in seen: seen.add(x); parts.append(x)
 for group,key in [('facts',s1['primary_fact_id']),('concepts',s1['semantic_concept_id']),('relations',s1['key_relation_id']),('goals',s1['goal_id'])]: add(d[group][key])
 rel=d['relations'][s1['key_relation_id']]
 for ref in ID_RE.findall(rel):
  for group in ('facts','concepts','goals'):
   for key,val in d[group].items():
    if key.lower()==ref.lower(): add(val); break
 add(f"ambiguity {s1['ambiguity']}")
 return ' | '.join(parts)

def deterministic_ranking(fx):
 query=resolve_selected_semantics(fx); docs=fx['candidate_ontology']; doc_tf={k:Counter(tokens(v)) for k,v in docs.items()}; n=len(doc_tf); df=Counter()
 for tf in doc_tf.values():
  for term in tf: df[term]+=1
 idf={term:math.log((n+1)/(freq+1))+1.0 for term,freq in df.items()}; qtf=Counter(tokens(query)); qv={term:count*idf.get(term,math.log(n+1)+1.0) for term,count in qtf.items()}; q3=char3(query); scored=[]
 for cid,text in docs.items():
  dv={term:count*idf.get(term,math.log(n+1)+1.0) for term,count in doc_tf[cid].items()}; ts=cosine(qv,dv); cs=cosine(q3,char3(text)); scored.append((cid,0.70*ts+0.30*cs))
 return [cid for cid,_ in sorted(scored,key=lambda x:(-x[1],x[0]))]

def metrics(rows,k):
 tp=emitted=gold_total=exact=invalid=0
 for row in rows:
  pred=row['candidate_ids']; valid=row['contract_valid']; pset=set(pred) if valid else set(); gold=set(row['gold']); hit=len(pset&gold)
  tp+=hit; emitted+=len(pset); gold_total+=len(gold); exact+=int(valid and pset==gold); invalid+=int(not valid)
 recall=tp/gold_total; precision=tp/emitted if emitted else 0.0
 return {'k':k,'fixture_count':len(rows),'candidate_recall':recall,'candidate_precision':precision,'candidate_f1':2*recall*precision/(recall+precision) if recall+precision else 0.0,'true_positive_total':tp,'emitted_candidate_total':emitted,'gold_candidate_total':gold_total,'exact_set_count':exact,'exact_set_rate':exact/len(rows),'invalid_output_count':invalid,'rows':rows}

def run_deterministic(data,k):
 rows=[]
 for fx in data['fixtures']:
  pred=deterministic_ranking(fx)[:k]
  rows.append({'fixture_id':fx['id'],'candidate_ids':pred,'gold':fx['gold'],'contract_valid':len(pred)==k and len(pred)==len(set(pred))})
 return metrics(rows,k)

def run_qwen(server_url,data,k):
 rows=[]
 system=(f'You are a fixed-budget semantic candidate retrieval stage. Given a frozen semantic state and visible candidate ontology, return exactly {k} unique candidate IDs that best preserve the stated goal and evidence and least contradict the semantic state. This is a fixed-budget retrieval assay, so return exactly {k} IDs even when fewer candidates seem ideal. Return only the required JSON object.')
 for fx in data['fixtures']:
  state=resolve(fx['oracle_s1'],fx['semantic_dictionary']); visible={'semantic_state':state,'candidate_ontology':fx['candidate_ontology']}
  prompt='<|im_start|>system\n'+system+'<|im_end|>\n<|im_start|>user\n'+json.dumps(visible,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'<|im_end|>\n<|im_start|>assistant\n'
  resp=post_json(server_url,{'prompt':prompt,'n_predict':48,'temperature':0,'grammar':grammar_for_exact(list(fx['candidate_ontology']),k),'cache_prompt':False}); raw=str(resp.get('content','')).strip()
  try: parsed=json.loads(raw); pred=parsed.get('candidate_ids',[])
  except Exception: pred=[]
  valid=isinstance(pred,list) and len(pred)==k and len(pred)==len(set(pred)) and all(x in fx['candidate_ontology'] for x in pred)
  rows.append({'fixture_id':fx['id'],'candidate_ids':pred,'gold':fx['gold'],'contract_valid':valid,'raw':raw})
  print('S2_EQUAL_QWEN='+json.dumps({'k':k,**rows[-1]},separators=(',',':')),flush=True)
 return metrics(rows,k)

def main():
 WORK.mkdir(parents=True,exist_ok=True); OUT.parent.mkdir(parents=True,exist_ok=True); data=json.loads(FIXTURE.read_text())
 actual_digest=canonical_digest(data)
 if data.get('status')!='FROZEN_BEFORE_MODEL_RUN' or actual_digest!=EXPECTED_DIGEST or data.get('dataset_digest')!=EXPECTED_DIGEST: raise RuntimeError(f'FIXTURE_FREEZE_MISMATCH:{actual_digest}')
 head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 deterministic={str(k):run_deterministic(data,k) for k in BUDGETS}
 print('S2_EQUAL_STATE=RUNTIME_ACQUIRE',flush=True); server_bin=acquire_runtime(); model=WORK/MODEL_FILE; print('S2_EQUAL_STATE=MODEL_ACQUIRE',flush=True); download(MODEL_URL,model)
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
  if not ready: log.flush(); raise RuntimeError('LLAMA_NOT_READY:'+(WORK/'llama.log').read_text(errors='replace')[-4000:])
  qwen={}
  for k in BUDGETS:
   print(f'S2_EQUAL_STATE=QWEN_K{k}',flush=True); qwen[str(k)]=run_qwen('http://127.0.0.1:18080/completion',data,k)
  comparison={str(k):{'deterministic_minus_qwen_recall':deterministic[str(k)]['candidate_recall']-qwen[str(k)]['candidate_recall'],'deterministic_minus_qwen_precision':deterministic[str(k)]['candidate_precision']-qwen[str(k)]['candidate_precision'],'deterministic_minus_qwen_f1':deterministic[str(k)]['candidate_f1']-qwen[str(k)]['candidate_f1']} for k in BUDGETS}
  result={'schema_version':'FUNCTION_BOUNDARY_S2A_EQUAL_BUDGET_ACTUAL_V1','protocol':'FUNCTION_BOUNDARY_S2A_EQUAL_BUDGET_V1','source_protocol':'FUNCTION_BOUNDARY_S2_V2','dataset_digest':EXPECTED_DIGEST,'execution_wrapper_commit':head,'arm':'ORACLE_S1_ONLY','candidate_budgets':list(BUDGETS),'model':{'repository':MODEL_REPO,'file':MODEL_FILE,'size_bytes':MODEL_SIZE,'sha256':MODEL_SHA},'runtime':{'llama_cpp_tag':LLAMA_TAG,'llama_cpp_asset_sha256':LLAMA_SHA,'temperature':0,'context_tokens':1024,'github_actions_used':False,'google_drive_used':False},'deterministic':deterministic,'qwen25_1p5b':qwen,'same_k_comparison':comparison,'claim_limit':'This is a fixed-budget retrieval comparison, not the original variable-cardinality all-admissible set-construction task.'}
  OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); print('S2_EQUAL_TERMINAL='+json.dumps(result,separators=(',',':')),flush=True)
 finally:
  if server.poll() is None: server.terminate()
  log.close()
if __name__=='__main__': main()
