#!/usr/bin/env python3
"""Use official AALpy 2.0 L* against the same black-box fixture as the local fallback.

Prerequisites: pip install aalpy==2.0.0. The present sandbox cannot access PyPI;
this driver is provided but HAS NOT BEEN EXECUTED with AALpy in this session.
Learner sees only (reset, input, current output), never underlying coordinates.
"""
import json
import random
from pathlib import Path
from poc7_lstar_fallback import LinearSUL, NonlinearScrambledSUL, independent_equivalence, reachable_minimal_reference, Hypothesis

try:
    from aalpy.base import SUL
    from aalpy.oracles import StatePrefixEqOracle
    from aalpy.learning_algs import run_Lstar
except ImportError as exc:
    raise SystemExit('NATIVE_AALPY_NOT_RUN: install aalpy==2.0.0 (package unavailable in current sandbox)') from exc


class BlackBoxSUL(SUL):
    def __init__(self, target):
        super().__init__()
        self.target=target
        self.state=None
    def pre(self):self.state=self.target.reset()
    def post(self):pass
    def step(self,letter):
        if letter is not None:self.state=self.target.step(self.state,letter)
        return bool(self.target.output(self.state))


def convert_dfa(model, alphabet):
    states=list(model.states)
    index={state:i for i,state in enumerate(states)}
    transitions={index[s]:{a:index[s.transitions[a]] for a in alphabet} for s in states}
    outputs={index[s]:int(bool(s.is_accepting)) for s in states}
    return Hypothesis(index[model.initial_state],transitions,outputs)


def main():
    random.seed(20261105)
    configs=[
        ('poc4_zero_reset',LinearSUL(8,0,(0,1))),
        ('poc4_nonzero_reset',LinearSUL(8,1,(0,1))),
        ('poc4_reachable_four_states',LinearSUL(8,1,(0,1,3),extended_reset=True)),
        ('nonlinear_scrambled_128',NonlinearScrambledSUL(128,initial=0,actions=(0,1))),
        ('probe_reaches_40_states',LinearSUL(12,4,(0,1,2)))
    ]
    results=[]
    for name,target in configs:
        sul=BlackBoxSUL(target)
        eq=StatePrefixEqOracle(list(target.actions),sul,walks_per_state=150,walk_len=32)
        model,info=run_Lstar(list(target.actions),sul,eq,'dfa',cex_processing=None,
                             return_data=True,print_level=0,max_learning_rounds=100)
        equivalent=convert_dfa(model,target.actions)
        exact=independent_equivalence(target,equivalent,limit=50000)
        ref=reachable_minimal_reference(target,limit=50000)
        result={'name':name,'learned_states':len(model.states),'learning_metadata':info,
                'independent_exact':exact,'minimal_reachable':ref,
                'result':'PASS_EXACT' if exact['status']=='PASS_EXACT_REACHABLE' and len(model.states)==ref['minimal_classes'] else 'FAIL_OR_UNKNOWN'}
        results.append(result)
        print(name,result['result'],'states',result['learned_states'])
    output={'id':'GEN001_POC7_AALPY_NATIVE_V1','library':'AALpy 2.0.0','results':results}
    Path(__file__).with_name('POC7_AALPY_NATIVE_RESULTS.json').write_text(json.dumps(output,indent=2,ensure_ascii=False,default=str)+'\n')


if __name__=='__main__':main()
