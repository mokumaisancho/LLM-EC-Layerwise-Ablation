#!/usr/bin/env python3
"""GEN001 POC7 extension: query budget, reachable-state scope, and amortized cost."""
import json
import random
import statistics
import time
from pathlib import Path
from poc7_lstar_fallback import (
    LinearSUL, NonlinearScrambledSUL, MembershipOracle, LStar,
    blackbox_eq, independent_equivalence, reachable_minimal_reference, eval_case, run_all
)


def runtime_benchmark(system, hypothesis, loops=150000, repetitions=7):
    sequence=[(i*6364136223846793005 >> 8)&1 for i in range(loops)]
    original=[];learned=[]
    for _ in range(repetitions):
        x=system.reset(); checksum=0
        tic=time.perf_counter()
        for a in sequence:
            x=system.step(x,a)
            checksum+=system.output(x)
        original.append(time.perf_counter()-tic)
        y=hypothesis.initial; other=0
        tic=time.perf_counter()
        for a in sequence:
            y=hypothesis.transitions[y][a]
            other+=hypothesis.outputs[y]
        learned.append(time.perf_counter()-tic)
        assert checksum==other
    raw=statistics.median(original);simple=statistics.median(learned)
    return {'iterations':loops, 'repetitions':repetitions,
            'original_median_seconds':raw,'learned_median_seconds':simple,
            'observed_speedup_python_microbenchmark':raw/simple,
            'mean_saved_seconds_per_step':(raw-simple)/loops,
            'benchmark_warning':'Python implementation microbenchmark, not real deployment, does not include learning/proof costs'}


def run():
    source_results=Path(__file__).with_name('POC7_LOCAL_RESULTS.json')
    if not source_results.is_file():
        run_all()
    base=json.loads(source_results.read_text())
    output={'id':'GEN001_POC7_BLACKBOX_LEARNER_EXTENDED_V1',
            'scope':'Independent Angluin L* fallback using black-box queries. Native AALpy package NOT_RUN because installation blocked by network.',
            'budget_experiments':[], 'hidden_state_scaling':[],
            'seed_replicates':[], 'performance':None}
    # Fully reproduce a specific false-completion scenario. Learning may return
    # without counterexample though the model is wrong: independent checker prevents PASS.
    for budget in (0,5,50,200,1500):
        case=eval_case('hidden_probe_n12',LinearSUL(12,4,(0,1,2)),oracle='blackbox',queries=budget,depth=32)
        output['budget_experiments'].append({k:case[k] for k in ('learned_states','learning_terminated',
            'membership_queries_unique','eq_oracle_calls','independent_product_check','independent_reachable_minimal','learner_fitness')} | {'random_walk_tests_per_round':budget})
    assert output['budget_experiments'][0]['learner_fitness']=='FAIL_OR_UNKNOWN'
    assert all(x['learner_fitness']=='PASS_EXACT' for x in output['budget_experiments'][1:])

    # The exact reference is a SEPARATE checker. It is aware of the original
    # state transition, whereas learner only learns reset-action-output.
    for n in (6,8,12,16,32,64,128):
        target=LinearSUL(n,4,(0,1,2))
        truth=reachable_minimal_reference(target,limit=10000)
        assert truth['status']=='PASS_EXACT_REACHABLE'
        output['hidden_state_scaling'].append({'source_bits':n,'reachable_original_states':truth['reachable_count'],
                                               'minimal_predictive_states_reachable':truth['minimal_classes']})
    for seed in (7,42,20261105,20261106,99999):
        for label,sul in [('nonlinear_128',NonlinearScrambledSUL(128,initial=0,actions=(0,1))),
                          ('probe_n12',LinearSUL(12,4,(0,1,2)))]:
            res=eval_case(label,sul,seed=seed,oracle='blackbox',queries=1000,depth=32)
            output['seed_replicates'].append({'seed':seed,'case':label,'learned_states':res['learned_states'],
                                             'min_truth':res['independent_reachable_minimal']['minimal_classes'],
                                             'status':res['learner_fitness'],
                                             'member_queries':res['membership_queries_unique']})
    assert all(x['status']=='PASS_EXACT' for x in output['seed_replicates'])
    system=NonlinearScrambledSUL(128,initial=0,actions=(0,1))
    mq=MembershipOracle(system)
    eq,_=blackbox_eq(system,mq,system.actions,seed=20261105,num_tests=1500,max_depth=18)
    t0=time.perf_counter()
    hyp,terminated=LStar(system.actions,mq).learn(eq)
    training_wall=time.perf_counter()-t0
    verify=independent_equivalence(system,hyp)
    assert terminated and verify['status']=='PASS_EXACT_REACHABLE' and hyp.size==4
    perf=runtime_benchmark(system,hyp)
    perf['learning_time_seconds_this_run']=training_wall
    perf['unique_learning_queries']=mq.queries
    perf['learning_system_steps']=mq.executed_actions
    perf['amortized_break_even_steps_estimate']=round(training_wall/perf['mean_saved_seconds_per_step']) if perf['mean_saved_seconds_per_step']>0 else None
    perf['cost_caveat']='Break-even excludes verifier, encoding of API, environmental costs, repeated deployments and Python interpreter differences.'
    output['performance']=perf
    Path(__file__).with_name('POC7_EXTENDED_RESULTS.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('budget_experiments','hidden_state_scaling','seed_replicates')},indent=2))
    print('BUDGET',[(a['random_walk_tests_per_round'],a['learned_states'],a['learner_fitness']) for a in output['budget_experiments']])
    print('SCALING',[(a['source_bits'],a['minimal_predictive_states_reachable']) for a in output['hidden_state_scaling']])
    print('SEEDS',len(output['seed_replicates']), 'PASS',sum(x['status']=='PASS_EXACT' for x in output['seed_replicates']))
    return output


if __name__=='__main__':run()
