#!/usr/bin/env python3
"""GEN001 POC7: executable baseline of Angluin L* active automata learning.

This module uses the published L* observation-table method; it is an INDEPENDENT
reference implementation, NOT an AALpy library execution. The separate
AALpy-native driver is provided for reproducibility when AALpy is installed.

Learner sees only a resettable membership (input-word -> output) interface.
A verifier has access to the target transition implementation; the learner
never sees its source, hidden coordinates, or state count.
"""
from __future__ import annotations
import collections
import hashlib
import itertools
import json
import random
import sys
import time
from pathlib import Path


def bitdot(mask:int, state:int)->int:
    return (mask & state).bit_count() & 1


def linear_system(n):
    mask=(1<<n)-1
    A=[mask, mask^2]+[1<<i for i in range(2,n)]
    B=[2^(mask^3),3]+[1<<i for i in range(2,n)]
    def mulrow(row,mat):
        z=0
        while row:
            lsb=row & -row
            z ^= mat[lsb.bit_length()-1]
            row ^= lsb
        return z
    def mm(left,right):return [mulrow(r,right) for r in left]
    assert mm(A,B)==[1<<i for i in range(n)]
    def native(a):
        pair={0:[2,1],1:[3,1],2:[5,2]}[a]
        tail=([1<<(i+1) for i in range(2,n-1)]+[4]) if a==2 else [1<<i for i in range(2,n)]
        return pair+tail
    matrices={a:mm(mm(B,native(a)),A) for a in (0,1,2)}
    return matrices,A[0]


class LinearSUL:
    def __init__(self,n,initial,actions,extended_reset=False):
        self.n=n;self.initial=initial;self.actions=tuple(actions)
        self.M,self.C=linear_system(n)
        if extended_reset: assert 3 in actions
    def reset(self): return self.initial
    def step(self,x,a):
        if a==3: # new explicit action, changes the contract: reset all original coordinates
            return 0
        return sum(bitdot(mask,x)<<i for i,mask in enumerate(self.M[a]))
    def output(self,x):return bitdot(self.C,x)
    def title(self):return 'poc4_linear'


class NonlinearScrambledSUL:
    """Known-to-verifier nonlinear bijection from 128 dense source bits to 2 q-bits plus hidden bits.
    The learner gets only reset(), step(), and output(), never transform().
    """
    def __init__(self,n=128,initial=0,actions=(0,1)):
        assert n>=4
        self.n=n;self.initial=initial;self.actions=tuple(actions)
        self.mask=(1<<n)-1
    def reset(self):return self.initial
    def to_latent(self,x):
        z0=x.bit_count() & 1
        z1=((x & (self.mask^2)).bit_count() & 1) ^ (z0 & ((x>>2)&1))
        return (z0|(z1<<1)),(x>>2)
    def from_latent(self,z,h):
        z0,z1=z&1,(z>>1)&1
        hp=h.bit_count() & 1
        x0=z1^(z0&(h&1))^hp
        x1=z0^x0^hp
        x=(h<<2)|(x1<<1)|x0
        assert self.to_latent(x)==(z,h)
        return x
    def output(self,x):return self.to_latent(x)[0]&1
    def step(self,x,a):
        z,h=self.to_latent(x)
        if a==0:z=(z+1)&3
        elif a==1:z=((z&1)^((z>>1)&1))|((z>>1)<<1)
        elif a==2:
            z ^= (h&1)
            h=(h>>1)|((z&1)<<(self.n-3))
        else:raise ValueError(a)
        return self.from_latent(z,h)
    def title(self):return 'nonlinear_scrambled'


class MembershipOracle:
    def __init__(self,system):
        self.system=system;self.queries=0;self.executed_actions=0
        self.cache={}
    def __call__(self,word):
        word=tuple(word)
        if word not in self.cache:
            x=self.system.reset()
            for a in word:x=self.system.step(x,a)
            self.cache[word]=self.system.output(x)
            self.queries+=1
            self.executed_actions+=len(word)
        return self.cache[word]


class Hypothesis:
    def __init__(self,initial,transitions,outputs):
        self.initial=initial
        self.transitions=transitions
        self.outputs=outputs
    def run(self,word):
        state=self.initial
        for a in word:state=self.transitions[state][a]
        return self.outputs[state]
    @property
    def size(self):return len(self.outputs)
    def serialize(self):
        return {'states':self.size,'initial':self.initial,'outputs':self.outputs,
                'transitions':{str(i):{str(a):s for a,s in trans.items()}
                               for i,trans in self.transitions.items()}}


class LStar:
    def __init__(self,alphabet,member):
        self.alphabet=tuple(alphabet);self.member=member
        self.S={()};self.E={()};self.refinements=0
        self.consistency_splits=0;self.closure_additions=0
        self.cex=[]
    def row(self,s):
        return tuple(self.member(s+e) for e in sorted(self.E,key=lambda x:(len(x),x)))
    def build(self):
        assert () in self.E
        keys=sorted(self.S,key=lambda x:(len(x),x))
        rows={s:self.row(s) for s in keys}
        row_to_id={v:i for i,v in enumerate(sorted(set(rows.values())))}
        output_idx=sorted(self.E,key=lambda x:(len(x),x)).index(())
        rep={row_to_id[v]:s for s,v in rows.items() if rows[s]==v}
        trans={}
        out={}
        for id,s in sorted(rep.items()):
            trans[id]={a:row_to_id[self.row(s+(a,))] for a in self.alphabet}
            out[id]=rows[s][output_idx]
        return Hypothesis(row_to_id[rows[()]],trans,out)
    def learn(self,eq_oracle,max_rounds=200):
        for round_i in range(max_rounds):
            while True:
                # Enforce closure.
                rows={self.row(s):s for s in self.S}
                missing=next((s+(a,) for s in sorted(self.S,key=lambda x:(len(x),x))
                              for a in self.alphabet if self.row(s+(a,)) not in rows),None)
                if missing is not None:
                    self.S.add(missing);self.closure_additions+=1
                    continue
                # Enforce consistency.
                rs=collections.defaultdict(list)
                for s in sorted(self.S,key=lambda x:(len(x),x)):rs[self.row(s)].append(s)
                inconsistency=None
                for group in rs.values():
                    for s1,s2 in itertools.combinations(group,2):
                        for a in self.alphabet:
                            for e in sorted(self.E,key=lambda x:(len(x),x)):
                                if self.member(s1+(a,)+e)!=self.member(s2+(a,)+e):
                                    inconsistency=(a,)+e
                                    break
                            if inconsistency is not None:break
                        if inconsistency is not None:break
                    if inconsistency is not None:break
                if inconsistency is not None:
                    assert inconsistency not in self.E
                    self.E.add(inconsistency);self.consistency_splits+=1
                    continue
                break
            hypothesis=self.build()
            cex=eq_oracle(hypothesis)
            self.refinements+=1
            if cex is None:return hypothesis,True
            self.cex.append(cex)
            for i in range(len(cex)+1):self.S.add(cex[:i])
        return hypothesis,False


def blackbox_eq(system,membership,alphabet,seed=20261105,num_tests=2000,max_depth=20):
    rng=random.Random(seed);calls=0
    def query(h):
        nonlocal calls
        calls+=1
        # Include deterministic coverage for short prefixes.
        for k in range(min(4,max_depth)+1):
            for w in itertools.product(alphabet,repeat=k):
                if membership(w)!=h.run(w):return w
        for _ in range(num_tests):
            length=rng.randint(0,max_depth)
            w=tuple(rng.choice(alphabet) for __ in range(length))
            if membership(w)!=h.run(w):return w
        return None
    return query,lambda:calls


def independent_equivalence(system,hypothesis,limit=100000):
    """Exact product BFS from the *specific reset* state, not global-state equivalence.
    Stops with UNKNOWN if budget exceeded. Does not inspect learner's observation table.
    """
    queue=collections.deque([(system.reset(),hypothesis.initial,())])
    visited={(system.reset(),hypothesis.initial)}
    while queue:
        x,y,w=queue.popleft()
        if system.output(x)!=hypothesis.outputs[y]:
            return {'status':'FAIL','counterexample':w,'product_states_visited':len(visited)}
        for a in system.actions:
            xx=system.step(x,a)
            yy=hypothesis.transitions[y][a]
            if (xx,yy) not in visited:
                if len(visited)>=limit:
                    return {'status':'UNKNOWN_BUDGET','product_states_visited':len(visited)}
                visited.add((xx,yy));queue.append((xx,yy,w+(a,)))
    return {'status':'PASS_EXACT_REACHABLE','product_states_visited':len(visited)}


def reachable_minimal_reference(system,limit=100000):
    """Exact independent reachable automaton minimization; only for manageable reachable systems."""
    queue=collections.deque([system.reset()]);seen={system.reset()}
    while queue:
        x=queue.popleft()
        for a in system.actions:
            xx=system.step(x,a)
            if xx not in seen:
                if len(seen)>=limit:return {'status':'UNKNOWN_BUDGET','reachable_count':len(seen)}
                seen.add(xx);queue.append(xx)
    states=sorted(seen)
    labels={x:system.output(x) for x in states}
    while True:
        signatures={x:(system.output(x),tuple(labels[system.step(x,a)] for a in system.actions)) for x in states}
        key_to_id={k:i for i,k in enumerate(sorted(set(signatures.values())))}
        newer={x:key_to_id[signatures[x]] for x in states}
        if all((labels[x]==labels[y])==(newer[x]==newer[y]) for x in states for y in states):
            return {'status':'PASS_EXACT_REACHABLE','reachable_count':len(states),'minimal_classes':len(set(newer.values()))}
        labels=newer


def eval_case(label,system,seed=20261105,queries=2000,depth=20,oracle='blackbox',max_rounds=100,limit=50000):
    m=MembershipOracle(system)
    if oracle=='blackbox':eq,rounds=blackbox_eq(system,m,system.actions,seed=seed,num_tests=queries,max_depth=depth)
    elif oracle=='exact':
        count=[0]
        def eq(h):
            count[0]+=1
            report=independent_equivalence(system,h,limit=limit)
            if report['status']=='UNKNOWN_BUDGET':raise RuntimeError('EQ_BUDGET')
            return report.get('counterexample')
        rounds=lambda:count[0]
    else:raise AssertionError(oracle)
    start=time.perf_counter()
    learned,stopped=LStar(system.actions,m).learn(eq,max_rounds=max_rounds)
    elapsed=time.perf_counter()-start
    checker=independent_equivalence(system,learned,limit=limit)
    truth=reachable_minimal_reference(system,limit=limit)
    return {'name':label,'system':system.title(),'source_width_bits':system.n,
            'action_alphabet':list(system.actions),'reset_x_hex':hex(system.initial),
            'learner':'Independent published Angluin L* observation-table method (AALpy was not importable)',
            'eq_oracle':oracle,'learned_states':learned.size,'model':learned.serialize(),
            'learning_terminated':stopped,'membership_queries_unique':m.queries,
            'membership_simulated_steps':m.executed_actions,'eq_oracle_calls':rounds(),
            'runtime_seconds':elapsed,'independent_product_check':checker,
            'independent_reachable_minimal':truth,
            'learner_fitness': 'PASS_EXACT' if checker['status']=='PASS_EXACT_REACHABLE' and truth['status']=='PASS_EXACT_REACHABLE' and learned.size==truth['minimal_classes'] else 'FAIL_OR_UNKNOWN'}


def run_all():
    cases=[
        ('poc4_zero_reset',LinearSUL(8,0,(0,1))),
        ('poc4_nonzero_reset',LinearSUL(8,1,(0,1))),
        ('poc4_reachable_4_with_explicit_reset_action',LinearSUL(8,1,(0,1,3),extended_reset=True)),
        ('nonlinear_128_invertible_scrambled_reset',NonlinearScrambledSUL(128,initial=0,actions=(0,1))),
        ('poc4_probe_enabled_6bits',LinearSUL(6,1,(0,1,2))),
    ]
    report={'id':'GEN001_POC7_ACTIVE_AUTOMATA_LEARNING_FALLBACK_V1','scope':'Published Angluin L* method implemented standalone because AALpy package retrieval blocked; not claimed as AALpy software execution.','results':[], 'warnings':[]}
    for label,sul in cases:
        t=eval_case(label,sul,oracle='blackbox',queries=1500,depth=18,limit=50000)
        report['results'].append(t)
        print(label,'learned',t['learned_states'],'indep',t['independent_reachable_minimal'],'check',t['independent_product_check'],'queries',t['membership_queries_unique'],flush=True)
    # Negative control: an equivalence oracle that only checks the empty word
    # can accept an incorrect one-state hypothesis. Independent exact validator catches it.
    sul=NonlinearScrambledSUL(128,initial=0,actions=(0,1))
    m=MembershipOracle(sul)
    learner=LStar(sul.actions,m)
    bad,closed=learner.learn(lambda hypothesis:None)
    wrong=independent_equivalence(sul,bad)
    assert wrong['status']=='FAIL'
    report['false_pass_control']={'bogus_eq_oracle':'always accepts','trained_states':bad.size,
                                  'bogus_learner_stopped':closed,'independent_check':wrong}
    assert report['results'][0]['learned_states']==1
    assert report['results'][1]['independent_reachable_minimal']['minimal_classes']==3
    assert report['results'][2]['independent_reachable_minimal']['minimal_classes']==4
    assert report['results'][3]['independent_reachable_minimal']['minimal_classes']==4
    Path(__file__).with_name('POC7_LOCAL_RESULTS.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report

if __name__=='__main__':run_all()
