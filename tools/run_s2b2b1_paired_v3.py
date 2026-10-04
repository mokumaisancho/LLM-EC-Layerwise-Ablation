#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json, pathlib, subprocess, tarfile, time, urllib.request

from generate_s2b2b1_schema_synth_holdout import generate
from s2b2b1_schema_synth_core import synthesize
from score_s2b2b1_schema_synth import score_rows

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=pathlib.Path('/tmp/s2b2-b1-v3')
OUT=ROOT/'results'/'function_boundary_s2b2_b1_paired_runtime.json'

PROTOCOL='FUNCTION_BOUNDARY_S2B2_B1_PAIRED_V3'
SEED='04f9b2fff2fde06f2b1be6cfc6030954f59c2f8c'
EXPECTED_DIGEST='dde736e4f37b55567af45726e378291bfa07d44d39ee58e2038804582426e650'
LLAMA_TAG='b11146'
LLAMA_FILE='llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL=f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA='c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
MODEL_REPO='bartowski/Qwen2.5-1.5B-Instruct-GGUF'
MODEL_FILE='Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'
MODEL_URL=f'https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}'
MODEL_SHA='1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'
MODEL_SIZE=986048768
MATERIALITY=0.20

JSON_OBJECT_GRAMMAR=r'''
root ::= ws object ws
object ::= "{" ws "\"proposal_kind\"" ws ":" ws "\"NEW_CLASS\"" ws "," ws "\"action_class\"" ws ":" ws string ws "," ws "\"parameters\"" ws ":" ws strings ws "," ws "\"preconditions\"" ws ":" ws atoms ws "," ws "\"effects\"" ws ":" ws atoms ws "," ws "\"constraints\"" ws ":" ws constraints ws "}"
constraints ::= "{" ws "\"forbidden_effects\"" ws ":" ws atoms ws "}"
atoms ::= "[" ws (atom (ws "," ws atom)*)? ws "]"
atom ::= "{" ws "\"pred\"" ws ":" ws string ws "," ws "\"args\"" ws ":" ws strings ws "}"
strings ::= "[" ws (string (ws "," ws string)*)? ws "]"
string ::= "\"" chars "\""
chars ::= char*
char ::= [^"\\\x00-\x1F] | "\\" escape
escape ::= ["\\/bfnrt] | "u" hex hex hex hex
hex ::= [0-9a-fA-F]
ws ::= [ \t\n\r]*
'''.strip()

def digest(rows): return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def download(url,dest):
    req=urllib.request.Request(url,headers={'User-Agent':'s2b2-b1-v3/1'})
    with urllib.request.urlopen(req,timeout=240) as r,dest.open('wb') as out:
        while True:
            c=r.read(1024*1024)
            if not c: break
            out.write(c)
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
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
def run_preflight():
    p=subprocess.run(['python',str(ROOT/'tools'/'preflight_s2b2b1.py')],cwd=ROOT,text=True,capture_output=True)
    if p.returncode: raise RuntimeError('B1_PREFLIGHT_FAILED:'+(p.stderr or p.stdout))
    x=json.loads(p.stdout)
    if x.get('terminal')!='B1_PREFLIGHT_PASS': raise RuntimeError('B1_PREFLIGHT_NOT_PASS')
    return x

def qwen_predict(fixtures,server_url):
    system=(
      'You are the B1 explicit structured-requirement schema synthesizer. No supplied primitive can satisfy the full requirement. '
      'You are authorized to propose exactly one NEW_CLASS, using only the visible parameter variables and predicate vocabulary. '
      'Construct the minimal schema that exactly matches schema_requirements: no missing or extra preconditions/effects/forbidden-effect constraints. '
      'The action_class surface name is arbitrary and is not scored. Return only one JSON object matching the required schema.'
    )
    preds={}; raw_rows=[]
    for f in fixtures:
        visible=f['visible']
        prompt='<|im_start|>system\n'+system+'<|im_end|>\n<|im_start|>user\n'+json.dumps(visible,sort_keys=True,separators=(',',':'))+'<|im_end|>\n<|im_start|>assistant\n'
        resp=post_json(server_url+'/completion',{'prompt':prompt,'n_predict':384,'temperature':0,'grammar':JSON_OBJECT_GRAMMAR,'cache_prompt':False})
        raw=str(resp.get('content','')).strip(); parsed=None
        try:
            x=json.loads(raw)
            if isinstance(x,dict): parsed=x
        except Exception: pass
        preds[f['id']]=parsed
        row={'fixture_id':f['id'],'raw':raw,'prediction':parsed}
        raw_rows.append(row)
        print('S2B2B1_FIXTURE='+json.dumps(row,separators=(',',':')),flush=True)
    return preds,raw_rows

def main()->int:
    WORK.mkdir(parents=True,exist_ok=True); OUT.parent.mkdir(parents=True,exist_ok=True)
    preflight=run_preflight()
    fixtures=generate(SEED)
    if len(fixtures)!=16 or digest(fixtures)!=EXPECTED_DIGEST: raise RuntimeError('HOLDOUT_MISMATCH')
    det_preds={f['id']:synthesize(f['visible']) for f in fixtures}
    det=score_rows(fixtures,det_preds)
    print('S2B2B1_STATE=STATIC_AND_SCIENTIFIC_PREFLIGHT_PASS',flush=True)
    server_bin=acquire_runtime()
    model=WORK/MODEL_FILE; download(MODEL_URL,model)
    if model.stat().st_size!=MODEL_SIZE: raise RuntimeError('MODEL_SIZE_MISMATCH')
    if sha256(model)!=MODEL_SHA: raise RuntimeError('MODEL_SHA_MISMATCH')
    log_path=WORK/'llama.log'; log=log_path.open('w')
    server=subprocess.Popen([str(server_bin),'-m',str(model),'-c','2048','-b','64','-ub','64','--threads','1','--no-warmup','--host','127.0.0.1','--port','18081'],stdout=log,stderr=subprocess.STDOUT,text=True)
    try:
        ready=False
        for _ in range(240):
            if server.poll() is not None: break
            try:
                with urllib.request.urlopen('http://127.0.0.1:18081/health',timeout=2) as r:
                    if r.status==200: ready=True; break
            except Exception: pass
            time.sleep(1)
        if not ready:
            log.flush(); raise RuntimeError('LLAMA_NOT_READY:'+log_path.read_text(errors='replace')[-3000:])
        qpred,raw_rows=qwen_predict(fixtures,'http://127.0.0.1:18081')
        qwen=score_rows(fixtures,qpred)
        delta=det['valid_schema_proposal_rate']-qwen['valid_schema_proposal_rate']
        terminal='B1_DETERMINISTIC_MATERIAL_ADVANTAGE' if delta>=MATERIALITY else ('B1_LLM_MATERIAL_ADVANTAGE' if -delta>=MATERIALITY else 'B1_NO_MATERIAL_SEPARATION')
        result={
          'schema_version':'FUNCTION_BOUNDARY_S2B2_B1_PAIRED_ACTUAL_V1','protocol':PROTOCOL,'tcc':'S2B2_MVP_TCC_V3','issue':43,
          'holdout_digest':EXPECTED_DIGEST,'fixture_count':16,'family_count':8,'preflight':preflight,
          'frozen_assets':{'core':'3dab663ca2747f102b5c6c3e916119cc0b468708','output_contract':'8ada6bd17b5409e32106afab70692b3cdbf47bef','scorer':'f2ee566eb132362b731d21712d4d601b541e3497','generator':'04f9b2fff2fde06f2b1be6cfc6030954f59c2f8c','manifest':'2372e72231d17ff7e9996199635fa26d5ce52194'},
          'model':{'repository':MODEL_REPO,'file':MODEL_FILE,'size_bytes':MODEL_SIZE,'sha256':MODEL_SHA},
          'runtime':{'llama_cpp_tag':LLAMA_TAG,'llama_cpp_asset_sha256':LLAMA_SHA,'temperature':0,'context_tokens':2048,'grammar':'generic structural JSON only; semantic content not constrained','github_actions_used':False,'google_drive_used':False,'qwen3_4b_used':False},
          'arms':{'deterministic':det,'qwen25_1p5b':qwen},'raw_qwen_rows':raw_rows,
          'paired_delta_deterministic_minus_qwen_valid_rate':delta,'materiality_abs':MATERIALITY,'terminal':terminal,
          'claim_limit':'B1 tests synthesis from explicitly supplied structured schema requirements; it is not operator induction or unconstrained ontology invention.'
        }
        OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print('S2B2B1_TERMINAL='+json.dumps(result,separators=(',',':')),flush=True)
    finally:
        if server.poll() is None: server.terminate()
        log.close()
    return 0
if __name__=='__main__': raise SystemExit(main())
