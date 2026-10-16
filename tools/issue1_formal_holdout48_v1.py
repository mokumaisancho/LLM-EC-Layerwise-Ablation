"""Frozen 48-case successor assay for source-bounded S3/S4 formal logic.

prepare: freeze public inputs and separately commit to gold digest BEFORE native EC scoring.
score: derive gold independently with SymPy and call pinned genuine native EC v2;
       LLM arm remains unscored until actual model output bytes are available.
This is not independent natural-language adjudication, not original A-E.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
from sympy import And, Not, Symbol

HERE=Path(__file__).resolve().parent
EC=HERE/'ec_layerwise_source_policy_authority_v2.py'
EC_BLOB='7da0cd8d876505cafdd5a9811132427e2f441a14'
FLAGS=('authorized','fraud','docs','risk','reviewed')
MODES=('NORMAL','COMPETING','EQUIVALENT','REFRAME')


def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def gitblob(path):
    d=path.read_bytes();return hashlib.sha1(b'blob '+str(len(d)).encode()+b'\0'+d).hexdigest()

def policy():
    return {'schema':'EC_PUBLIC_POLICY_V2','policy_id':'HOLDOUT48_FORMAL_NOT_NL',
            'policy_evidence_ref':'declared:formal-v1',
            'operation_rules':{'PAY':['fact:authorized','not:fact:fraud'],
                               'ESCALATE':['fact:risk'], 'REVIEW':['fact:fraud']},
            'obligation_rules':{'EVIDENCE':{'when':['fact:authorized'],'done_when':['fact:docs']},
                                'FRAUD_REVIEW':{'when':['fact:fraud'],'done_when':['fact:reviewed']}}}

def case(facts,mode):
    task={'schema':'EC_FORMAL_FACTS_V2','source_ref':'declared:case-v1','facts':facts}
    candidates=[{'candidate_id':f'c_{op.lower()}',
                 'semantic_transition':{'operation':op},'evidence_refs':[],
                 'dependencies':[],'claims':[]}
                for op in policy()['operation_rules']]
    groups=[] if mode not in ('COMPETING','EQUIVALENT') else [
        {'group_id':'R01','relation_type':mode,'candidate_ids':['c_pay','c_escalate']}]
    public_s2={'candidates':candidates,'relation_groups':groups,
               'semantic_ir_hash':digest(task),
               'source_refs':['declared:formal-v1','declared:case-v1']}
    return {'task':task,'public_s2':public_s2,
            'framing':{'reframe_required':mode=='REFRAME','reframe_resolved':False}}

def independent_true(expr,facts):
    # Independent implementation: symbolic formula substitution, NOT native EC helper.
    terms=[]
    for token in expr:
        neg=token.startswith('not:fact:')
        assert token.startswith('not:fact:') if neg else token.startswith('fact:')
        name=token.split(':')[-1]
        terms.append(Not(Symbol(name)) if neg else Symbol(name))
    substituted=And(*terms).subs({Symbol(k):v for k,v in facts.items()})
    if substituted not in (True,False):
        return bool(substituted)
    return bool(substituted)

def independent_reference(inp,pol):
    facts=inp['task']['facts']; candidates=inp['public_s2']['candidates']
    selected=[c['candidate_id'] for c in candidates
              if independent_true(pol['operation_rules'][c['semantic_transition']['operation']],facts)]
    unresolved=[oid for oid,r in pol['obligation_rules'].items()
                if independent_true(r['when'],facts) and not independent_true(r['done_when'],facts)]
    conflicts=[]
    for g in inp['public_s2']['relation_groups']:
        if g['relation_type']=='COMPETING' and len(set(g['candidate_ids'])&set(selected))>1:
            conflicts.append(g['group_id'])
    if inp['framing']['reframe_required'] and not inp['framing']['reframe_resolved']:
        label='REFRAME'
    elif unresolved or conflicts:label='CONTINUE'
    elif not selected:label='BLOCKED'
    else:label='CLOSE'
    return {'selected':selected,'closure':label,'unresolved':sorted(unresolved),'conflicts':conflicts}

def make_all():
    pol=policy()
    all_rows=[]
    for bits in itertools.product([False,True],repeat=len(FLAGS)):
        facts=dict(zip(FLAGS,bits))
        for mode in MODES:
            inp=case(facts,mode)
            output=independent_reference(inp,pol)
            rid='H'+hashlib.sha256(canonical(inp)).hexdigest()[:12]
            all_rows.append({'id':rid,'input':inp,'reference':output})
    assert len(all_rows)==128 and len(set(x['id'] for x in all_rows))==128
    selected=[]
    for label in ('BLOCKED','CLOSE','CONTINUE','REFRAME'):
        options=sorted((r for r in all_rows if r['reference']['closure']==label),
                       key=lambda r:hashlib.sha256(('freeze-sample-v1:'+r['id']).encode()).hexdigest())
        assert len(options)>=12,(label,len(options))
        selected.extend(options[:12])
    selected.sort(key=lambda r:r['id'])
    assert len(selected)==48 and len(set(x['id'] for x in selected))==48
    return selected

def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    rows=make_all()
    public={'schema':'ISSUE1_HOLDOUT48_PUBLIC_V1','benchmark_scope':'FORMAL_POLICY_ONLY',
            'policy':policy(),'cases':[{'id':r['id'],'input':r['input']} for r in rows]}
    private={'schema':'ISSUE1_HOLDOUT48_PRIVATE_V1',
             'labels':[{'id':r['id'],'reference':r['reference']} for r in rows]}
    manifest={'schema':'ISSUE1_HOLDOUT48_FROZEN_MANIFEST_V1',
              'public_sha256':digest(public),'private_gold_sha256':digest(private),
              'formal_source_policy_sha256':digest(policy()),
              'native_ec_expected_git_blob':EC_BLOB,
              'n':len(rows),'balance':{'BLOCKED':12,'CLOSE':12,'CONTINUE':12,'REFRAME':12},
              'limits':'No independent NL semantic labels. No real LLM outputs. Public/label generation code exists; only public inputs go to model.'}
    for name,x in [('public.json',public),('private_gold.json',private),('manifest.json',manifest)]:
        (out/name).write_text(json.dumps(x,sort_keys=True,ensure_ascii=False,indent=2)+'\n')
    return manifest

def load(root):
    p,g,m=[json.loads((root/x).read_text()) for x in ('public.json','private_gold.json','manifest.json')]
    assert digest(p)==m['public_sha256'],'PUBLIC_DRIFT'
    assert digest(g)==m['private_gold_sha256'],'GOLD_DRIFT'
    assert digest(p['policy'])==m['formal_source_policy_sha256'],'POLICY_DRIFT'
    assert len(p['cases'])==len(g['labels'])==m['n']==48
    assert [x['id'] for x in p['cases']]==[x['id'] for x in g['labels']]
    return p,g,m

def score(root):
    pub,gold,manifest=load(root)
    assert gitblob(EC)==EC_BLOB,'WRONG_NATIVE_CODE'
    sp=importlib.util.spec_from_file_location('ec_real',EC)
    ec=importlib.util.module_from_spec(sp);sp.loader.exec_module(ec)
    cases=[]; wrong=[]
    for raw,ans in zip(pub['cases'],gold['labels']):
        inp=raw['input'];p=pub['policy'];task=inp['task'];s2=inp['public_s2']
        compiled=ec.compile_source_policy(s2,task,p,pinned_policy_sha256=ec.digest(p),
                                           source_commit='3f435ad4365d846d96264458540efb4848ce3541')
        selected=[k for k,v in compiled['adjudications'].items() if v['status']=='ADMISSIBLE']
        rejected=[k for k,v in compiled['adjudications'].items() if v['status']=='REJECTED']
        selection={'source_s2_sha256':ec.digest(s2),
                   'semantic_truth_independently_verified':False,
                   'selection':{'selected_candidate_ids':selected,'rejected_candidate_ids':rejected}}
        closed=ec.evaluate_policy_closure(compiled,selection,s2,task,p,
                                            pinned_policy_sha256=ec.digest(p),framing=inp['framing'])
        actual={'selected':selected,'closure':closed['closure_diagnostic'],
                'unresolved':closed['unresolved_policy_obligations'],
                'conflicts':closed['competing_selected_groups']}
        correct=actual==ans['reference']
        assert not closed['real_world_close_authorized'] and not compiled['original_phase1_AC_qualified']
        cases.append({'id':raw['id'],'input_sha256':digest(inp),'native':actual,'formal_reference':ans['reference'],'exact':correct})
        if not correct:wrong.append(raw['id'])
    return {'schema':'ISSUE1_HOLDOUT48_NATIVE_EC_SCORE_V1','source_manifest_sha256':digest(manifest),
            'ec_git_blob':EC_BLOB,'n':len(cases),'ec_exact_pass':sum(x['exact'] for x in cases),
            'ec_exact_fail':len(wrong),'fail_ids':wrong,'cases':cases,
            'real_llm_calls':0,'llm_comparison':'NOT_RUN_NO_INFERENCE_ASSET',
            'independent_nl_reference':False,'original_AE_completed':False,'original_AC_promoted':0}

if __name__=='__main__':
    cli=argparse.ArgumentParser()
    cli.add_argument('mode',choices=('prepare','score'))
    cli.add_argument('root',type=Path)
    args=cli.parse_args()
    if args.mode=='prepare':r=prepare(args.root)
    else:
        r=score(args.root)
        (args.root/'native_score.json').write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('cases','labels')}))
