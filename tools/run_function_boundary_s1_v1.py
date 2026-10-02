#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, subprocess, tarfile, time, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=pathlib.Path('/tmp/function-boundary-s1-v1')
FIXTURE=ROOT/'fixtures'/'function_boundary_s1_v1.json'
OUT=ROOT/'results'/'function_boundary_s1_qwen25_1p5b_runtime.json'
EXPECTED_DIGEST='4d15e1b89c6382a8a5252558525db55cccc700096ad5c92e97d384c9d59cd190'
LLAMA_TAG='b11146'
LLAMA_FILE='llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL=f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA='c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
MODEL_REPO='bartowski/Qwen2.5-1.5B-Instruct-GGUF'
MODEL_FILE='Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'
MODEL_URL=f'https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}'
MODEL_SHA='1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'
MODEL_SIZE=986048768
FIELDS=['primary_fact_id','semantic_concept_id','key_relation_id','ambiguity','goal_id']

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def download(url,dest):
    req=urllib.request.Request(url,headers={'User-Agent':'function-boundary-s1-v1/1'})
    with urllib.request.urlopen(req,timeout=240) as r,dest.open('wb') as o:
        while True:
            c=r.read(1024*1024)
            if not c: break
            o.write(c)

def canonical_digest(data):
    subject={'protocol':data['protocol'],'fixture_count':data['fixture_count'],'fixtures':data['fixtures']}
    b=json.dumps(subject,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return hashlib.sha256(b).hexdigest()

def acquire_runtime():
    arc=WORK/LLAMA_FILE; download(LLAMA_URL,arc)
    if sha256(arc)!=LLAMA_SHA: raise RuntimeError('LLAMA_SHA_MISMATCH')
    target=WORK/'llama'; target.mkdir(parents=True,exist_ok=True)
    with tarfile.open(arc,'r:gz') as tf: tf.extractall(target,filter='data')
    hits=list(target.rglob('llama-server'))
    if not hits: raise RuntimeError('LLAMA_SERVER_NOT_FOUND')
    hits[0].chmod(0o755); return hits[0]

def q(s): return json.dumps(str(s),ensure_ascii=False)
def alts(values): return ' | '.join(q(json.dumps(v)) for v in values)
def grammar_for(v):
    facts=list(v['facts']); concepts=list(v['concepts']); rels=list(v['relations']); goals=list(v['goals'])
    # GBNF terminals include JSON-quoted strings, e.g. terminal text is \"f1\".
    def choices(xs): return ' | '.join(json.dumps(json.dumps(x)) for x in xs)
    return '\n'.join([
      'root ::= "{" ws "\\\"primary_fact_id\\\"" ws ":" ws fact ws "," ws "\\\"semantic_concept_id\\\"" ws ":" ws concept ws "," ws "\\\"key_relation_id\\\"" ws ":" ws rel ws "," ws "\\\"ambiguity\\\"" ws ":" ws amb ws "," ws "\\\"goal_id\\\"" ws ":" ws goal ws "}" ws',
      'ws ::= [ \\t\\n\\r]*',
      'fact ::= '+choices(facts),
      'concept ::= '+choices(concepts),
      'rel ::= '+choices(rels),
      'amb ::= "\\\"YES\\\"" | "\\\"NO\\\""',
      'goal ::= '+choices(goals),
    ])

def post_json(url,payload,timeout=180):
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)

def main():
    WORK.mkdir(parents=True,exist_ok=True); OUT.parent.mkdir(parents=True,exist_ok=True)
    data=json.loads(FIXTURE.read_text())
    actual_digest=canonical_digest(data)
    if data.get('status')!='FROZEN_BEFORE_MODEL_RUN' or actual_digest!=EXPECTED_DIGEST or data.get('dataset_digest')!=EXPECTED_DIGEST:
        raise RuntimeError(f'FIXTURE_FREEZE_MISMATCH:{actual_digest}')
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    print('S1_STATE=RUNTIME_ACQUIRE',flush=True)
    server_bin=acquire_runtime()
    model=WORK/MODEL_FILE
    print('S1_STATE=MODEL_ACQUIRE',flush=True)
    download(MODEL_URL,model)
    if model.stat().st_size!=MODEL_SIZE: raise RuntimeError(f'MODEL_SIZE_MISMATCH:{model.stat().st_size}')
    if sha256(model)!=MODEL_SHA: raise RuntimeError('MODEL_SHA_MISMATCH')
    log=(WORK/'llama.log').open('w')
    server=subprocess.Popen([str(server_bin),'-m',str(model),'-c','1024','-b','32','-ub','32','--threads','1','--no-warmup','--host','127.0.0.1','--port','18080'],stdout=log,stderr=subprocess.STDOUT,text=True)
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
        system=('You are a semantic-grounding stage. Use only the supplied visible task. Select the single primary evidence fact, the best matching domain concept, the key semantic relation, whether the meaning/referent remains ambiguous, and the protected goal. IDs and option descriptions are supplied in the task. Do not invent IDs. Return only the required JSON object.')
        rows=[]; field_correct={f:0 for f in FIELDS}; exact=0
        print('S1_STATE=INFERENCE',flush=True)
        for fx in data['fixtures']:
            visible=fx['visible']; oracle=fx['oracle']
            prompt='<|im_start|>system\n'+system+'<|im_end|>\n<|im_start|>user\n'+json.dumps(visible,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'<|im_end|>\n<|im_start|>assistant\n'
            resp=post_json('http://127.0.0.1:18080/completion',{'prompt':prompt,'n_predict':128,'temperature':0,'grammar':grammar_for(visible),'cache_prompt':False})
            raw=str(resp.get('content','')).strip()
            try: parsed=json.loads(raw)
            except Exception: parsed={}
            correct={f:parsed.get(f)==oracle[f] for f in FIELDS}
            for f in FIELDS: field_correct[f]+=int(correct[f])
            is_exact=all(correct.values()); exact+=int(is_exact)
            row={'fixture_id':fx['id'],'category':fx['category'],'parsed':parsed,'oracle':oracle,'field_correct':correct,'exact_match':is_exact,'raw':raw}
            rows.append(row); print('S1_FIXTURE='+json.dumps(row,separators=(',',':')),flush=True)
        total=len(rows)*len(FIELDS)
        result={
          'schema_version':'FUNCTION_BOUNDARY_S1_QWEN25_1P5B_ACTUAL_V1','protocol':'FUNCTION_BOUNDARY_S1_V1','dataset_digest':EXPECTED_DIGEST,
          'execution_wrapper_commit':head,'model':{'repository':MODEL_REPO,'file':MODEL_FILE,'size_bytes':MODEL_SIZE,'sha256':MODEL_SHA},
          'runtime':{'llama_cpp_tag':LLAMA_TAG,'llama_cpp_asset_sha256':LLAMA_SHA,'temperature':0,'context_tokens':1024,'github_actions_used':False,'google_drive_used':False},
          'fixture_count':len(rows),'field_decisions':total,'field_correct_total':sum(field_correct.values()),'primary_score':sum(field_correct.values())/total,
          'fixture_exact_match_count':exact,'fixture_exact_match_rate':exact/len(rows),'per_dimension_accuracy':{f:field_correct[f]/len(rows) for f in FIELDS},'rows':rows
        }
        OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print('S1_TERMINAL='+json.dumps(result,separators=(',',':')),flush=True)
    finally:
        if server.poll() is None: server.terminate()
        log.close()
if __name__=='__main__': main()
