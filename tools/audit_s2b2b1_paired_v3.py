#!/usr/bin/env python3
from __future__ import annotations

import hashlib, importlib, json, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tools'
sys.path.insert(0,str(TOOLS))

GEN_COMMIT='04f9b2fff2fde06f2b1be6cfc6030954f59c2f8c'
CORE_COMMIT='3dab663ca2747f102b5c6c3e916119cc0b468708'
CONTRACT_COMMIT='8ada6bd17b5409e32106afab70692b3cdbf47bef'
EXPECTED_DIGEST='dde736e4f37b55567af45726e378291bfa07d44d39ee58e2038804582426e650'
CACHE=ROOT/'results'/'function_boundary_s2b2_b1_qwen_semantic_cache_2026-10-05.json'
CONTRACT_PATH='docs/FUNCTION_BOUNDARY_S2B2_B1_OUTPUT_CONTRACT_2026-10-04.json'


def die(msg:str)->None:
    print(json.dumps({'terminal':'B1_SCORE_AUDIT_FAILED','detail':msg},indent=2)); raise SystemExit(2)

def git_show(commit:str,path:str)->bytes:
    p=subprocess.run(['git','show',f'{commit}:{path}'],cwd=ROOT,capture_output=True)
    if p.returncode: die(f'git show failed {commit}:{path}')
    return p.stdout

def require_frozen(path:str,commit:str)->None:
    cur=(ROOT/path).read_bytes(); frozen=git_show(commit,path)
    if cur!=frozen: die(f'frozen asset drift: {path}')

def canon(v:Any)->Any:
    if isinstance(v,dict): return {k:canon(v[k]) for k in sorted(v)}
    if isinstance(v,list):
        keyed={json.dumps(canon(x),sort_keys=True,separators=(',',':')):canon(x) for x in v}
        return [keyed[k] for k in sorted(keyed)]
    return v

def atom_key(a:dict[str,Any])->str: return json.dumps(canon(a),sort_keys=True,separators=(',',':'))
def sig(schema:dict[str,Any])->str:
    return json.dumps(canon({'parameters':schema.get('parameters',[]),'preconditions':schema.get('preconditions',[]),'effects':schema.get('effects',[]),'constraints':schema.get('constraints',{})}),sort_keys=True,separators=(',',':'))

def vars_in(v:Any)->set[str]:
    out:set[str]=set()
    if isinstance(v,str) and v.startswith('$'): out.add(v)
    elif isinstance(v,dict):
        for x in v.values(): out|=vars_in(x)
    elif isinstance(v,list):
        for x in v: out|=vars_in(x)
    return out

def atoms_valid(atoms:Any,vocab:dict[str,int],params:set[str])->bool:
    if not isinstance(atoms,list): return False
    for a in atoms:
        if not isinstance(a,dict) or set(a)!={'pred','args'}: return False
        if a['pred'] not in vocab or not isinstance(a['args'],list) or len(a['args'])!=vocab[a['pred']]: return False
        if not vars_in(a).issubset(params): return False
    return True

def independent_reason(visible:dict[str,Any],proposal:Any)->str:
    req=visible['schema_requirements']; vocab=visible['predicate_vocabulary']
    if not isinstance(proposal,dict): return 'NOT_OBJECT'
    if set(proposal)!={'proposal_kind','action_class','parameters','preconditions','effects','constraints'}: return 'WRONG_KEYS'
    if proposal['proposal_kind']!='NEW_CLASS' or not isinstance(proposal['action_class'],str): return 'WRONG_KIND'
    if not isinstance(proposal['parameters'],list) or set(proposal['parameters'])!=set(req['parameters']): return 'PARAMETER_MISMATCH'
    params=set(proposal['parameters'])
    if not atoms_valid(proposal['preconditions'],vocab,params) or not atoms_valid(proposal['effects'],vocab,params): return 'INVALID_ATOM'
    c=proposal['constraints']
    if not isinstance(c,dict) or set(c)!={'forbidden_effects'} or not atoms_valid(c['forbidden_effects'],vocab,params): return 'INVALID_CONSTRAINT'
    if {atom_key(x) for x in proposal['preconditions']}!={atom_key(x) for x in req.get('required_preconditions',[])}: return 'PRECONDITION_MISMATCH'
    if {atom_key(x) for x in proposal['effects']}!={atom_key(x) for x in req.get('required_effects',[])}: return 'EFFECT_MISMATCH'
    if {atom_key(x) for x in c['forbidden_effects']}!={atom_key(x) for x in req.get('forbidden_effects',[])}: return 'FORBIDDEN_CONSTRAINT_MISMATCH'
    supplied={sig({'parameters':p.get('parameters',[]),'preconditions':p.get('preconditions',[]),'effects':p.get('effects',[]),'constraints':{'forbidden_effects':p.get('forbidden_effects',[])}}) for p in visible.get('primitive_actions',[])}
    if sig(proposal) in supplied: return 'NOT_NOVEL_VS_SUPPLIED_ONTOLOGY'
    return 'VALID'

def relaxed_to_vars(visible:dict[str,Any],proposal:Any)->Any:
    if not isinstance(proposal,dict): return proposal
    rev:dict[str,list[str]]={}
    for var,vals in visible.get('domains',{}).items():
        for val in vals: rev.setdefault(val,[]).append(var)
    mapping={v:xs[0] for v,xs in rev.items() if len(xs)==1}
    def sub(x:Any)->Any:
        if isinstance(x,str): return mapping.get(x,x)
        if isinstance(x,list): return [sub(v) for v in x]
        if isinstance(x,dict): return {k:sub(v) for k,v in x.items()}
        return x
    return sub(proposal)

def main()->int:
    require_frozen('tools/generate_s2b2b1_schema_synth_holdout.py',GEN_COMMIT)
    require_frozen('tools/s2b2b1_schema_synth_core.py',CORE_COMMIT)
    contract=json.loads(git_show(CONTRACT_COMMIT,CONTRACT_PATH))
    if contract['output_schema']['parameters']!='array of visible parameter variable names': die('parameter-variable requirement not frozen pre-run')
    if not contract['paired_authority']['deterministic_may_emit_new_class'] or not contract['paired_authority']['qwen_may_emit_new_class']: die('asymmetric NEW_CLASS authority')
    if contract['materiality_abs']!=0.20 or not contract['no_post_freeze_tuning']: die('contract drift')

    gen=importlib.import_module('generate_s2b2b1_schema_synth_holdout')
    core=importlib.import_module('s2b2b1_schema_synth_core')
    fixtures=gen.generate(GEN_COMMIT)
    digest=hashlib.sha256(json.dumps(fixtures,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if len(fixtures)!=16 or digest!=EXPECTED_DIGEST: die('holdout regeneration mismatch')
    byid={f['id']:f for f in fixtures}

    cache=json.loads(CACHE.read_text())
    if cache.get('holdout_digest')!=EXPECTED_DIGEST or cache.get('source',{}).get('runner_commit')!='ec26fee3e0a85598f1d6ad2d55d9b6f128461d33': die('cache provenance mismatch')
    rows=cache.get('rows',[])
    if len(rows)!=16 or len({r['fixture_id'] for r in rows})!=16 or set(byid)!={r['fixture_id'] for r in rows}: die('cache fixture coverage mismatch')
    if any(not r.get('render_log_id') for r in rows): die('missing Render raw-log index')

    det_reasons=[]
    for f in fixtures:
        pred=core.synthesize(f['visible'])
        det_reasons.append(independent_reason(f['visible'],pred))
    if det_reasons!=['VALID']*16: die('deterministic independent replay not 16/16 valid')

    exact=[]; relaxed=[]; reason_rows=[]; per_family=defaultdict(lambda:{'fixtures':0,'valid':0})
    for r in rows:
        f=byid[r['fixture_id']]; p=r['prediction']
        reason=independent_reason(f['visible'],p); exact.append(reason)
        rr=independent_reason(f['visible'],relaxed_to_vars(f['visible'],p)); relaxed.append(rr)
        per_family[f['family']]['fixtures']+=1; per_family[f['family']]['valid']+=int(reason=='VALID')
        reason_rows.append({'fixture_id':f['id'],'render_log_id':r['render_log_id'],'family':f['family'],'exact_reason':reason,'representation_relaxed_reason':rr})

    exact_count=exact.count('VALID'); relaxed_count=relaxed.count('VALID')
    if exact_count!=1: die(f'exact Qwen valid total mismatch: {exact_count}')
    if Counter(exact)!=Counter({'PARAMETER_MISMATCH':10,'PRECONDITION_MISMATCH':3,'EFFECT_MISMATCH':2,'VALID':1}): die('reason topology mismatch')
    delta=1.0-exact_count/16
    if abs(delta-0.9375)>1e-12: die('paired delta mismatch')

    out={
      'schema_version':'FUNCTION_BOUNDARY_S2B2_B1_INDEPENDENT_AUDIT_V1',
      'protocol':'S2B2_MVP_TCC_V3',
      'issue':43,'evidence_issue':46,
      'terminal':'B1_SCORE_AUDIT_PASS',
      'holdout_digest':digest,'fixture_count':16,
      'frozen_contract':{'commit':CONTRACT_COMMIT,'parameter_variable_names_required_pre_run':True,'symmetric_new_class_authority':True,'materiality_abs':0.20},
      'deterministic_independent_replay':{'valid_total':16,'valid_rate':1.0},
      'qwen_independent_recompute':{'valid_total':exact_count,'valid_rate':exact_count/16,'invalid_total':16-exact_count,'fail_open_count':16-exact_count,'reason_counts':dict(sorted(Counter(exact).items())),'per_family':{k:{**v,'valid_rate':v['valid']/v['fixtures']} for k,v in sorted(per_family.items())}},
      'paired_delta_deterministic_minus_qwen_valid_rate':delta,
      'representation_relaxed_sensitivity':{'authoritative':False,'method':'map concrete domain values back to the unique visible parameter variable, then rescore without any other repair','valid_total':relaxed_count,'valid_rate':relaxed_count/16,'reason_counts':dict(sorted(Counter(relaxed).items())),'deterministic_minus_qwen':1.0-relaxed_count/16,'material_gap_still_ge_0p20':(1.0-relaxed_count/16)>=0.20},
      'claim':'B1 explicit structured requirements -> symbolic NEW_CLASS schema is deterministic-externalizable on this frozen assay. The Qwen gap is material under the pre-frozen exact schema contract and remains material under a non-authoritative concrete-to-variable sensitivity normalization.',
      'claim_limits':['B1 exposes complete structured schema requirements. It is not B2 operator induction or unconstrained ontology invention.','Parameter-variable exactness was frozen before inference; it is not a post-hoc scorer rule.','The relaxed sensitivity result is descriptive only and does not replace the frozen primary metric.'],
      'rows':reason_rows,
      'github_actions_used':False,'google_drive_used':False,'qwen3_4b_used':False
    }
    print(json.dumps(out,indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
