#!/usr/bin/env python3
"""GEN001 PoC13: bounded evidence-authority gate; synthetic holdout only."""
import copy, hashlib, itertools, json

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def public(k,u,r,j):
    rel=[]
    if k in ('equivalent','mixed'):rel.append({'relation_type':'EQUIVALENT','selected_member_count':2})
    if k in ('competing','mixed'):rel.append({'relation_type':'COMPETING','selected_member_count':2})
    return {'relation_groups':rel,'required_condition_state':'UNRESOLVED' if u else 'NOT_EXPLICITLY_UNRESOLVED','reframe_required':r,'rejected_count':j}

def old_policy(p):
    return 'CONTINUE' if p['required_condition_state']=='UNRESOLVED' or any(g['relation_type']=='COMPETING' for g in p['relation_groups']) else 'CLOSE'

def registered(scope,extra=False):
    return {'scope':scope,'obligations': ['A','B']+(['C'] if extra else []),'document':'synthetic-v1'}

def authority(src,u=False,block='NONE'):
    h=digest(src)
    proof={o:{'source':h,'verified':not(u and o=='A'),'evidence':digest([h,o])} for o in src['obligations']}
    a={'source':copy.deepcopy(src),'source_digest':h,'external_verified':True,'inventory_complete':True,'proof':proof,'effects_verified':True}
    if block=='EVIDENCE':a['external_verified']=False
    elif block=='INVENTORY':a['inventory_complete']=False
    elif block=='UNTRACKED':a['proof']['C']['verified']=False
    elif block=='EFFECT':a['effects_verified']=False
    elif block!='NONE':raise ValueError(block)
    return a

def check(p,proposal,a):
    def v(status,reason):return {'status':status,'reason':reason}
    if not isinstance(a,dict) or not a.get('external_verified'):return v('BLOCKED','NO_INDEPENDENT_AUTHORITY')
    src=a.get('source')
    if not isinstance(src,dict) or digest(src)!=a.get('source_digest'):return v('BLOCKED','SOURCE_DIGEST_MISMATCH')
    if proposal.get('scope')!=src.get('scope') or proposal.get('source_digest')!=a['source_digest']:return v('BLOCKED','SCOPE_OR_VERSION_CHANGED')
    if a.get('inventory_complete') is not True:return v('BLOCKED','INVENTORY_NOT_CERTIFIED')
    proofs=a.get('proof',{})
    if set(proofs)!=set(src['obligations']):return v('BLOCKED','INVENTORY_COVERAGE_MISMATCH')
    for o in src['obligations']:
        record=proofs[o]
        if record.get('source')!=a['source_digest'] or not isinstance(record.get('evidence'),str) or len(record['evidence'])!=64:return v('BLOCKED','EVIDENCE_PROVENANCE_MISMATCH')
        if record.get('verified') is not True:return v('CONTINUE','UNPROVEN_OBLIGATION')
    if a.get('effects_verified') is not True:return v('CONTINUE','EFFECT_NOT_VERIFIED')
    if p['required_condition_state']=='UNRESOLVED':return v('CONTINUE','EXPLICIT_UNRESOLVED')
    if any(g['relation_type']=='COMPETING' for g in p['relation_groups']):return v('CONTINUE','COMPETING_ALTERNATIVES')
    return v('CLOSE','SCOPED_CERTIFIED')

def expected(p,u,block):
    if block in ('EVIDENCE','INVENTORY'):return 'BLOCKED'
    if block in ('UNTRACKED','EFFECT'):return 'CONTINUE'
    return old_policy(p)

def experiment():
    rows=[]
    def testcase(name,k,u,r,j,b):
        p=public(k,u,r,j);s=registered(name,b=='UNTRACKED');a=authority(s,u,b)
        proposal={'scope':name,'source_digest':digest(s),'claim':'CLOSE','fake_pass':True}
        out=check(p,proposal,a)
        rows.append({'case':name,'family':'BASE' if name.startswith('IN') else 'PAIR','blocker':b,
          'public':p,'expected':expected(p,u,b),'previous':old_policy(p),'actual':out['status']})
    for k,u,r,j in itertools.product(('none','equivalent','competing','mixed'),(False,True),(False,True),(0,1)):
        testcase('IN'+str(len(rows)).zfill(3),k,u,r,j,'NONE')
    blocks=('EVIDENCE','INVENTORY','UNTRACKED','EFFECT')
    for idx in range(16):
        k=('none','equivalent')[idx%2];r=bool(idx%2);j=(idx//2)%2
        testcase('PAIR'+str(idx).zfill(2)+'A',k,False,r,j,'NONE')
        testcase('PAIR'+str(idx).zfill(2)+'B',k,False,r,j,blocks[idx%4])
    assert len(rows)==64
    assert all(z['actual']==z['expected'] for z in rows)
    assert sum(z['previous']=='CLOSE' and z['expected']!='CLOSE' for z in rows)==16
    assert sum(z['actual']=='CLOSE' and z['expected']!='CLOSE' for z in rows)==0
    assert sum(z['actual']=='CLOSE' for z in rows)==24
    for i in range(16):
        left,right=rows[32+2*i:34+2*i]
        assert left['public']==right['public'] and left['expected']!=right['expected']
    p=public('none',False,False,0);s=registered('x');a=authority(s);proposal={'scope':'x','source_digest':digest(s)}
    control={}
    def negative(name,change,decision):
        aa=copy.deepcopy(a);pp=copy.deepcopy(proposal);change(aa,pp)
        got=check(p,pp,aa);assert got['status']==decision,(name,got)
        control[name]=got
    negative('missing_external_authority',lambda a,p:a.update(external_verified=False),'BLOCKED')
    negative('forged_empty_inventory',lambda a,p:a.update(inventory_complete=False,proof={}),'BLOCKED')
    negative('stale_source',lambda a,p:p.update(source_digest='0'*64),'BLOCKED')
    negative('changed_source',lambda a,p:a['source'].update(document='tampered'),'BLOCKED')
    negative('wrong_evidence_origin',lambda a,p:a['proof']['B'].update(source='f'*64),'BLOCKED')
    negative('unknown_effect',lambda a,p:a.update(effects_verified=None),'CONTINUE')
    negative('missing_proof',lambda a,p:a['proof']['A'].update(verified=None),'CONTINUE')
    negative('wrong_scope',lambda a,p:p.update(scope='other'),'BLOCKED')
    negative('self_attestation_without_authority',lambda a,p:(a.update(external_verified=False),p.update(fake_gold=True)),'BLOCKED')
    assert check(p,proposal,a)['status']=='CLOSE'
    return {'protocol':'GEN001_POC13_AUTHORITY_BOUND_CLOSURE_V1','status':'SCOPED_SYNTHETIC_PASS',
      'cases':len(rows),'correct':sum(z['actual']==z['expected'] for z in rows),
      'old_false_close':16,'new_false_close':0,'true_close_retained':24,
      'negative_controls':control,'rows':rows,
      'limitation':'Trusted external authority is a synthetic assumption, not an established real-world certificate.',
      'next_blocker':'Independent authoritative obligation-inventory completeness and execution/evidence attestations'}

if __name__=='__main__':
    print(json.dumps(experiment(),ensure_ascii=False,indent=2))
