#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import tarfile
import time
import urllib.request
from collections import defaultdict

from generate_s2b2b1_schema_holdout import generate, digest
from s2b2b1_schema_synth_core import synthesize
from s2b2b1_schema_validator import validate_proposal

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=pathlib.Path('/tmp/function-boundary-s2b2b1-paired')
OUT=ROOT/'results'/'function_boundary_s2b2b1_qwen25_1p5b_runtime.json'
PROTOCOL='FUNCTION_BOUNDARY_S2B2B1_STRUCTURED_SCHEMA_PAIRED_V1'
GENERATOR_FREEZE_COMMIT='adbf16f2a8493fa328e142ae2b6962ed89f022c0'
EXPECTED_DIGEST='fb1cb2373edc3f95433541a1c7dd72b936e0e04b28e6ff79d738a64643b0b082'
EXPECTED_FIXTURES=16

LLAMA_TAG='b11146'
LLAMA_FILE='llama-b11146-bin-ubuntu-x64.tar.gz'
LLAMA_URL=f'https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}'
LLAMA_SHA='c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410'
MODEL_REPO='bartowski/Qwen2.5-1.5B-Instruct-GGUF'
MODEL_FILE='Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'
MODEL_URL=f'https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}'
MODEL_SHA='1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370'
MODEL_SIZE=986048768


def sha256(path:pathlib.Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def download(url:str,dest:pathlib.Path)->None:
    req=urllib.request.Request(url,headers={'User-Agent':'function-boundary-s2b2b1-paired/1'})
    with urllib.request.urlopen(req,timeout=240) as r,dest.open('wb') as out:
        while True:
            chunk=r.read(1024*1024)
            if not chunk: break
            out.write(chunk)


def acquire_runtime()->pathlib.Path:
    archive=WORK/LLAMA_FILE; download(LLAMA_URL,archive)
    if sha256(archive)!=LLAMA_SHA: raise RuntimeError('LLAMA_SHA_MISMATCH')
    target=WORK/'llama'; target.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive,'r:gz') as tf: tf.extractall(target,filter='data')
    hits=list(target.rglob('llama-server'))
    if not hits: raise RuntimeError('LLAMA_SERVER_NOT_FOUND')
    hits[0].chmod(0o755); return hits[0]


def choices(values:list[str])->str:
    return ' | '.join(json.dumps(json.dumps(v)) for v in values)


def grammar_for(v:dict)->str:
    params=v['parameters']; unary=sorted(p for p,a in v['predicate_vocab'].items() if a==1); binary=sorted(p for p,a in v['predicate_vocab'].items() if a==2)
    rules=[
      'root ::= "{" ws "\\\"proposal_kind\\\"" ws ":" ws "\\\"NEW_CLASS\\\"" ws "," ws "\\\"action_class\\\"" ws ":" ws "\\\"PROPOSED_NEW_CLASS\\\"" ws "," ws "\\\"parameters\\\"" ws ":" ws params ws "," ws "\\\"preconditions\\\"" ws ":" ws pres ws "," ws "\\\"effects\\\"" ws ":" ws effs ws "," ws "\\\"bindings\\\"" ws ":" ws binds ws "}" ws',
      'ws ::= [ \\t\\n\\r]*',
      'upred ::= '+choices(unary),
    ]
    if len(params)==1:
        p=json.dumps(json.dumps(params[0])); vals=choices(sorted(v['domains'][params[0]]))
        rules += [
          'params ::= "[" ws '+p+' ws "]"',
          'atom1 ::= "{" ws "\\\"pred\\\"" ws ":" ws upred ws "," ws "\\\"args\\\"" ws ":" ws "[" ws '+p+' ws "]" ws "}"',
          'pres ::= "[" ws atom1 ws "]"',
          'effs ::= "[" ws atom1 ws "]"',
          'v0 ::= '+vals,
          'binds ::= "{" ws '+p+' ws ":" ws v0 ws "}"',
        ]
    elif len(params)==2:
        pa,pb=params; paq=json.dumps(json.dumps(pa)); pbq=json.dumps(json.dumps(pb))
        rules += [
          'bpred ::= '+choices(binary),
          'param ::= '+choices(params),
          'params ::= "[" ws '+paq+' ws "," ws '+pbq+' ws "]"',
          'atom1 ::= "{" ws "\\\"pred\\\"" ws ":" ws upred ws "," ws "\\\"args\\\"" ws ":" ws "[" ws param ws "]" ws "}"',
          'atom2 ::= "{" ws "\\\"pred\\\"" ws ":" ws bpred ws "," ws "\\\"args\\\"" ws ":" ws "[" ws param ws "," ws param ws "]" ws "}"',
          'pres ::= "[" ws atom1 ws "," ws atom1 ws "]"',
          'effs ::= "[" ws atom2 ws "]"',
          'va ::= '+choices(sorted(v['domains'][pa])),
          'vb ::= '+choices(sorted(v['domains'][pb])),
          'binds ::= "{" ws '+paq+' ws ":" ws va ws "," ws '+pbq+' ws ":" ws vb ws "}"',
        ]
    else: raise RuntimeError('UNSUPPORTED_PARAM_COUNT')
    return '\n'.join(rules)


def post_json(url:str,payload:dict,timeout:int=180)->dict:
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)


def score_qwen(fixtures:list[dict],server_url:str)->dict:
    system=(
      'You are a symbolic action-schema synthesis stage. No existing primitive action can satisfy the structured target. '
      'Propose exactly one new action schema using only the visible parameter names, predicates, and domain values. '
      'Its instantiated preconditions must include every required precondition and be satisfied by current state. '
      'Its instantiated effects must include every required effect and no forbidden effect. '
      'Return only the required JSON object.'
    )
    valid=exact=invalid=forbidden=0; rows=[]; fam=defaultdict(lambda:{'fixtures':0,'valid':0,'exact':0,'invalid':0,'forbidden':0})
    for f in fixtures:
        v=f['visible']
        prompt='<|im_start|>system\n'+system+'<|im_end|>\n<|im_start|>user\n'+json.dumps(v,sort_keys=True,separators=(',',':'))+'<|im_end|>\n<|im_start|>assistant\n'
        resp=post_json(server_url+'/completion',{'prompt':prompt,'n_predict':256,'temperature':0,'grammar':grammar_for(v),'cache_prompt':False})
        raw=str(resp.get('content','')).strip(); bad=False
        try: proposal=json.loads(raw)
        except Exception: proposal=None; bad=True
        validation=validate_proposal(f,proposal) if not bad else {'valid':False,'exact_canonical':False,'reasons':['INVALID_JSON']}
        is_valid=bool(validation.get('valid')); is_exact=bool(validation.get('exact_canonical'))
        invalid += int(bad); valid += int(is_valid); exact += int(is_exact); forbidden += int('FORBIDDEN_EFFECT_PRESENT' in validation.get('reasons',[]))
        b=fam[f['family']]; b['fixtures']+=1; b['valid']+=int(is_valid); b['exact']+=int(is_exact); b['invalid']+=int(bad); b['forbidden']+=int('FORBIDDEN_EFFECT_PRESENT' in validation.get('reasons',[]))
        row={'fixture_id':f['id'],'family':f['family'],'proposal':proposal,'valid':is_valid,'exact_canonical':is_exact,'reasons':validation.get('reasons',[]),'raw':raw}
        rows.append(row); print('S2B2B1_FIXTURE='+json.dumps(row,separators=(',',':')),flush=True)
    return {'valid_proposal_rate':valid/len(fixtures),'exact_canonical_schema_rate':exact/len(fixtures),'invalid_output_count':invalid,'forbidden_effect_count':forbidden,'per_family':{k:{**x,'valid_rate':x['valid']/x['fixtures'],'exact_rate':x['exact']/x['fixtures']} for k,x in sorted(fam.items())},'rows':rows}


def main()->int:
    WORK.mkdir(parents=True,exist_ok=True); OUT.parent.mkdir(parents=True,exist_ok=True)
    fixtures=generate(GENERATOR_FREEZE_COMMIT)
    if len(fixtures)!=EXPECTED_FIXTURES or digest(fixtures)!=EXPECTED_DIGEST: raise RuntimeError('HOLDOUT_MISMATCH')
    for f in fixtures:
        proposals=synthesize(f['visible'])
        if len(proposals)!=1: raise RuntimeError('DETERMINISTIC_PROPOSAL_COUNT_MISMATCH:'+f['id'])
        check=validate_proposal(f,proposals[0])
        if not check['valid'] or not check['exact_canonical']: raise RuntimeError('DETERMINISTIC_REFERENCE_MISMATCH:'+f['id'])
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    print('S2B2B1_STATE=RUNTIME_ACQUIRE',flush=True); server_bin=acquire_runtime()
    model=WORK/MODEL_FILE; print('S2B2B1_STATE=MODEL_ACQUIRE',flush=True); download(MODEL_URL,model)
    if model.stat().st_size!=MODEL_SIZE: raise RuntimeError('MODEL_SIZE_MISMATCH')
    if sha256(model)!=MODEL_SHA: raise RuntimeError('MODEL_SHA_MISMATCH')
    log_path=WORK/'llama.log'; log=log_path.open('w')
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
        if not ready: log.flush(); raise RuntimeError('LLAMA_NOT_READY:'+log_path.read_text(errors='replace')[-4000:])
        print('S2B2B1_STATE=INFERENCE',flush=True); qwen=score_qwen(fixtures,'http://127.0.0.1:18080')
        result={'schema_version':'FUNCTION_BOUNDARY_S2B2B1_STRUCTURED_SCHEMA_PAIRED_ACTUAL_V1','protocol':PROTOCOL,'issue':43,'stage':'B1_STRUCTURED_REQUIREMENTS_TO_NOVEL_SCHEMA','holdout_digest':EXPECTED_DIGEST,'fixture_count':len(fixtures),'execution_wrapper_commit':head,'model':{'repository':MODEL_REPO,'file':MODEL_FILE,'size_bytes':MODEL_SIZE,'sha256':MODEL_SHA},'runtime':{'execution_environment':'Render build pipeline','llama_cpp_tag':LLAMA_TAG,'llama_cpp_asset_sha256':LLAMA_SHA,'temperature':0,'context_tokens':1024,'oracle_model_visible':False,'family_model_visible':False,'github_actions_used':False,'google_drive_used':False,'qwen3_4b_used':False},'arms':{'deterministic_synth':{'valid_proposal_rate':1.0,'exact_canonical_schema_rate':1.0,'invalid_output_count':0,'forbidden_effect_count':0},'qwen25_1p5b':qwen},'paired_delta_qwen_minus_deterministic':{'valid_proposal_rate':qwen['valid_proposal_rate']-1.0,'exact_canonical_schema_rate':qwen['exact_canonical_schema_rate']-1.0},'claim_limits':['B1 supplies explicit structured preconditions/effects/constraints.','This does not test missing causal semantics or raw-language operator induction.','No post-freeze predictor/fixture/prompt/grammar/scorer change is authorized.']}
        OUT.write_text(json.dumps(result,indent=2)+'\n'); print('S2B2B1_TERMINAL='+json.dumps(result,separators=(',',':')),flush=True)
    finally:
        if server.poll() is None: server.terminate()
        log.close()
    return 0

if __name__=='__main__': raise SystemExit(main())
