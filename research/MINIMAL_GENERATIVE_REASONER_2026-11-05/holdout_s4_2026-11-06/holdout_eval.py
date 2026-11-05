#!/usr/bin/env python3
"""Prospective *synthetic*, publicly visible S4 signal holdout.

The predictor is a frozen child process seeing only a seven-field public JSON.
The independent reference is a source/obligation ledger. This is NOT a real
independent expert labelled sample, nor an execution of EC-native S4.
"""
from __future__ import annotations
import ast
from collections import defaultdict
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
PRED=HERE/'predictor_frozen.py'
PYTHON_EXECUTABLE=os.environ.get('GEN001_PYTHON_EXECUTABLE',sys.executable)
PROTOCOL='ISSUE1_S4_INTERFACE_INFORMATION_SUCCESSOR_DIAGNOSTIC_V1'
PINNED_UPSTREAM_GIT_BLOB='d7aa6d74946064ffb6b9896c8c9ae94573f11630'


def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(obj):return hashlib.sha256(canonical(obj).encode('utf8')).hexdigest()
def filehash(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_policy_ast(root:Path|None=None):
    """If run inside the full repository, fail if original predict AST drifted."""
    root=root or HERE.parents[2]
    original=root/'tools'/'run_issue1_s4_interface_information_diagnostic_v1.py'
    if not original.exists():return {'status':'NOT_AVAILABLE','original_git_blob':PINNED_UPSTREAM_GIT_BLOB}
    blob=original.read_bytes()
    actual=hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()
    if actual!=PINNED_UPSTREAM_GIT_BLOB:raise RuntimeError('UPSTREAM_PREDICTOR_BLOB_DRIFT')
    def get_ast(path):
        module=ast.parse(path.read_text())
        fn=next(x for x in module.body if isinstance(x,ast.FunctionDef) and x.name=='predict')
        return ast.dump(fn,include_attributes=False)
    if get_ast(PRED)!=get_ast(original):raise RuntimeError('FROZEN_PREDICTOR_AST_DRIFT')
    return {'status':'PASS_PINNED_ORIGINAL_AST','original_git_blob':actual}


def public_projection(ledger):
    """No oracle labels or authoritative missing evidence appear in predictor inputs."""
    groups=[]
    for rel in ledger['candidate_relations']:
        groups.append({'relation_type':rel['kind'],'selected_member_count':len(rel['selected'])})
    return {
        'protocol':PROTOCOL,
        'selected_count':len(ledger['selected_candidates']),
        'rejected_count':ledger['rejected_count'],
        'reframe_required':ledger['reframe_already_applied'],
        'trigger_residual_types':[],
        'relation_groups':groups,
        'required_condition_state':'UNRESOLVED' if ledger['explicit_unresolved'] else 'NOT_EXPLICITLY_UNRESOLVED',
    }


def reference_closure(ledger):
    """Independent obligation-ledger reference, not the public predictor rule."""
    # Enforce an inventory-complete, registered evidence/effects contract.
    if ledger['obligation_inventory_complete'] is not True:
        return 'BLOCKED'
    if ledger['source_evidence_verified'] is not True:
        return 'BLOCKED'
    if ledger['execution_effects_verified'] is not True:
        return 'CONTINUE'
    mandatory=ledger['mandatory_obligations']
    if any(x['proven'] is not True for x in mandatory):
        return 'CONTINUE'
    for rel in ledger['candidate_relations']:
        if rel['kind']=='COMPETING' and len(rel['selected'])>=2:
            return 'CONTINUE'
    return 'CLOSE'


def relation_set(kind):
    if kind=='none':return ['s0'],[]
    if kind=='equivalent':return ['s0','s1'],[{'kind':'EQUIVALENT','selected':['s0','s1']}]
    if kind=='competing':return ['s0','s1'],[{'kind':'COMPETING','selected':['s0','s1']}]
    if kind=='mixed':return ['s0','s1','s2'],[{'kind':'EQUIVALENT','selected':['s0','s1']},{'kind':'COMPETING','selected':['s1','s2']}]
    raise ValueError(kind)


def ledger(kind='none',unresolved=False,reframe=False,rejected=0):
    selected,rels=relation_set(kind)
    return {
        'selected_candidates':selected,
        'rejected_count':rejected,
        'candidate_relations':rels,
        'explicit_unresolved':unresolved,
        'reframe_already_applied':reframe,
        'mandatory_obligations':[{'id':'obligation_A','proven':not unresolved}],
        'obligation_inventory_complete':True,
        'source_evidence_verified':True,
        'execution_effects_verified':True,
    }


def make_cases():
    cases=[]
    for k,unres,reframe,rej in itertools.product(
            ('none','equivalent','competing','mixed'),(False,True),(False,True),(0,1)):
        src=ledger(k,unres,reframe,rej)
        cases.append({'name':f'H-IN-{len(cases):03d}','family':'IN_CONTRACT',
                      'public':public_projection(src),'ledger':src})
    assert len(cases)==32
    # Matched input pairs: the reference MUST disagree for some pairs,
    # while public inputs must remain bit-identical across the two members.
    blockers=['UNVERIFIED_EVIDENCE','INCOMPLETE_INVENTORY','UNTRACKED_OBLIGATION','UNVERIFIED_EFFECT']
    for idx in range(16):
        kind=('none','equivalent')[idx%2]
        src=ledger(kind,False,bool(idx%2),idx//2%2)
        src['mandatory_obligations'].append({'id':'obligation_B','proven':True})
        raw=canonical(src)
        paired=json.loads(raw)
        blocker=blockers[idx%len(blockers)]
        if blocker=='UNVERIFIED_EVIDENCE':paired['source_evidence_verified']=False
        elif blocker=='INCOMPLETE_INVENTORY':paired['obligation_inventory_complete']=False
        elif blocker=='UNTRACKED_OBLIGATION':paired['mandatory_obligations'].append({'id':'obligation_C','proven':False})
        elif blocker=='UNVERIFIED_EFFECT':paired['execution_effects_verified']=False
        pub=public_projection(src)
        assert pub==public_projection(paired)
        cases.append({'name':f'H-PAIR-{idx:02d}-A','family':'BEYOND_CONTRACT',
                      'blocker':'NONE','public':pub,'ledger':src})
        cases.append({'name':f'H-PAIR-{idx:02d}-B','family':'BEYOND_CONTRACT',
                      'blocker':blocker,'public':pub,'ledger':paired})
    assert len(cases)==64
    assert len({c['name'] for c in cases})==64
    assert all(c['name'] not in {f'M{x:03d}' for x in range(1,11)} for c in cases)
    return cases


def run():
    baseline=verify_frozen_policy_ast()
    cases=make_cases()
    labels=[reference_closure(c['ledger']) for c in cases]
    # Seal reference BEFORE running predictor, with a public SHA only.
    frozen_reference_sha=digest([{'name':c['name'],'label':label}
                                 for c,label in zip(cases,labels)])
    # Execute predictor in an isolated -I interpreter; only seven fields on disk.
    with tempfile.TemporaryDirectory(prefix='gen001_s4_holdout_') as tmp:
        predictions=[]
        for c in cases:
            p=Path(tmp)/'public.json'
            p.write_text(canonical(c['public']),encoding='utf8')
            env=subprocess.run([PYTHON_EXECUTABLE,'-I',str(PRED),'--predict-public',str(p)],
                               capture_output=True,text=True,timeout=8,cwd=tmp)
            if env.returncode:raise RuntimeError(f'PREDICTOR_FAIL:{c["name"]}:{env.stderr}')
            prediction=json.loads(env.stdout)
            if set(prediction)!={'closure_class','reason'}:raise RuntimeError('PREDICTOR_SCHEMA_FAIL')
            predictions.append(prediction)
        prediction_hash=digest([{'name':c['name'],'prediction':p}
                                for c,p in zip(cases,predictions)])
    # Only now score sealed predictions against independent ledgers.
    rows=[]
    for c,y,pred in zip(cases,labels,predictions):
        actual=pred['closure_class'];correct=(actual==y)
        rows.append({'id':c['name'],'family':c['family'],'blocker':c.get('blocker'),
                     'public_sha256':digest(c['public']),
                     'reference_label':y,'prediction':actual,
                     'correct':correct,'false_close':actual=='CLOSE' and y!='CLOSE'})
    families={}
    for family in ('IN_CONTRACT','BEYOND_CONTRACT'):
        a=[x for x in rows if x['family']==family]
        families[family]={'cases':len(a),'correct':sum(x['correct'] for x in a),
                          'false_close':sum(x['false_close'] for x in a),
                          'accuracy':sum(x['correct'] for x in a)/len(a)}
    by_hash=defaultdict(list)
    for r in rows:by_hash[r['public_sha256']].append(r)
    ambiguous=[{'public_sha256':key,'case_ids':[r['id'] for r in grp],
                'labels':sorted({r['reference_label'] for r in grp})}
               for key,grp in by_hash.items() if len({r['reference_label'] for r in grp})>1]
    # 16 independently specified causal counterfactual pairs, even if
    # their exact public features coincide across some pairs as well.
    pairs=[]
    for idx in range(16):
        a=next(x for x in rows if x['id']==f'H-PAIR-{idx:02d}-A')
        b=next(x for x in rows if x['id']==f'H-PAIR-{idx:02d}-B')
        assert a['public_sha256']==b['public_sha256']
        assert a['reference_label']=='CLOSE' and b['reference_label']!='CLOSE'
        pairs.append({'pair_id':idx,'blocker':b['blocker'],
                      'same_public_input':True,'truths_differ':True,
                      'A_correct':a['correct'],'B_false_close':b['false_close']})
    # Minimal feature ablation: removing either original new field can
    # change a correct IN-CONTRACT decision.
    from copy import deepcopy
    ablation={}
    for field in ('relation_groups','required_condition_state'):
        target=next(c for c in cases if c['family']=='IN_CONTRACT' and
            ((field=='relation_groups' and c['public']['relation_groups'] and
              any(x['relation_type']=='COMPETING' for x in c['public']['relation_groups']) and
              c['public']['required_condition_state']=='NOT_EXPLICITLY_UNRESOLVED') or
             (field=='required_condition_state' and c['public']['required_condition_state']=='UNRESOLVED' and
              not any(x['relation_type']=='COMPETING' for x in c['public']['relation_groups']))))
        tmp=deepcopy(target['public'])
        if field=='relation_groups':tmp[field]=[]
        else:tmp[field]='NOT_EXPLICITLY_UNRESOLVED'
        with tempfile.TemporaryDirectory(prefix='gen001_ablation_') as d:
            f=Path(d)/'public.json';f.write_text(canonical(tmp))
            q=subprocess.run([PYTHON_EXECUTABLE,'-I',str(PRED),'--predict-public',str(f)],
              capture_output=True,text=True,timeout=8)
            if q.returncode:raise RuntimeError(q.stderr)
            mask=json.loads(q.stdout)
        orig=next(p['closure_class'] for c,p in zip(cases,predictions) if c['name']==target['name'])
        assert orig!=mask['closure_class']
        ablation[field]={'source_case':target['name'],'before':orig,'after_mask':mask['closure_class']}
    assert families['IN_CONTRACT']['correct']==32, families
    assert families['BEYOND_CONTRACT']['false_close']==16,families
    assert len(pairs)==16 and all(p['B_false_close'] for p in pairs)
    assert all(ablation.values())
    result={'protocol':'GEN001_S4_PROSPECTIVE_SYNTHETIC_HOLDOUT_V1',
            'status':'SCOPED_PASS_WITH_OUT_OF_CONTRACT_FAILURE',
            'predictor':{'type':'frozen_existing_rule_copied_unmodified','original_git_blob':PINNED_UPSTREAM_GIT_BLOB,
                         'local_source_sha256':filehash(PRED),'upstream_ast_check':baseline},
            'observations':{'total':len(rows),'families':families,
                            'reference_sha256_sealed_before_prediction':frozen_reference_sha,
                            'prediction_sha256_sealed_before_scoring':prediction_hash,
                            'paired_identical_public_inputs_with_conflicting_truth':len(pairs),
                            'ambiguous_observable_feature_patterns':len(ambiguous),
                            'feature_ablation':ablation},
            'cases':rows,
            'independence':'Novel synthetic holdout cases not in original 10; source/obligation-ledger oracle separate from predictor input. NOT external expert gold or independently collected cases.',
            'scientific_conclusion':'The two added public features suffice for 32 in-contract finite obligation-ledger cases but fail to identify 16 out-of-contract blockers. An enriched S4 contract must expose auditable evidence/inventory/effect completeness (or explicitly abstain); more EC reframe logic cannot recover invisible information.',
            'next_blocker':'Add trusted provenance-bound obligation/evidence/effect-completeness fields or restrict S4 CLOSE to explicitly certified domains; independently test on externally authored unseen tasks before generalization.'}
    (HERE/'HOLDOUT_RESULTS.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2,ensure_ascii=False))
    return result

if __name__=='__main__':run()
