#!/usr/bin/env python3
"""Reproduction: preregistered C6 source-aware P4 GF(2) cost benchmark.
Source formulas transcribed from GitHub blob 706da2229bbe7a244e899729221170149bc6d014.
Comparison frozen in commit a455aa81a2afc4cabc76fb77822c8c86141f45f8.
"""
from __future__ import annotations
import gc, json, platform, random, statistics, sys, time, hashlib
from pathlib import Path

N=128; ACTIONS=(0,1); HORIZONS=(1,16,256,2048); STREAMS=8; REPEATS=7; SEED=20261107
MAX_MEM=2*1024*1024

# Pinned original P4 functions faithfully transcribed.
def dot(row,state): return (row & state).bit_count() & 1
def eval_rows(rows,state): return sum(dot(row,state)<<i for i,row in enumerate(rows))
def mul_row(row,matrix):
    v=0
    while row:
        bit=row&-row; v ^= matrix[bit.bit_length()-1]; row ^= bit
    return v
def mul(a,b):return [mul_row(row,b) for row in a]
def system(n):
    allbits=(1<<n)-1
    A=[allbits, allbits ^ 2]+[1<<i for i in range(2,n)]
    B=[2 ^ (allbits ^ 3),3]+[1<<i for i in range(2,n)]
    assert mul(A,B)==[1<<i for i in range(n)]
    def native(action):
        pair={0:[2,1],1:[3,1]}[action]
        return pair+[1<<i for i in range(2,n)]
    return {a:mul(mul(B,native(a)),A) for a in ACTIONS}, A[0]
def quotient(matrices,observed_row,actions):
    pivots={}
    def add(row):
        while row:
            p=row.bit_length()-1
            if p in pivots:row ^= pivots[p]
            else:pivots[p]=row;return True
        return False
    add(observed_row)
    while True:
        prev=len(pivots); snapshot=list(pivots.values())
        for row in snapshot:
            for a in actions:add(mul_row(row,matrices[a]))
        if len(pivots)==prev:break
    basis=[pivots[p] for p in sorted(pivots,reverse=True)]
    def coeff(row):
        encoded=0
        for j,b in enumerate(basis):
            if (row>>(b.bit_length()-1))&1:row^=b;encoded^=1<<j
        assert row==0
        return encoded
    updates={a:[coeff(mul_row(b,matrices[a])) for b in basis] for a in actions}
    readout=coeff(observed_row)
    for a in actions:
        for b,update in zip(basis,updates[a]):
            assert mul_row(b,matrices[a])==mul_row(update,basis)
    return basis,updates,readout

# Exact direct raw-state comparators: same GF(2) linear map with no quotient.
def make_columns(rows):
    return [eval_rows(rows,1<<j) for j in range(N)]
def column_step(columns,x):
    y=0
    while x:
        bit=x&-x;y^=columns[bit.bit_length()-1];x^=bit
    return y
def make_lut(columns):
    result=[]
    for block in range(N//8):
        table=[0]*256
        for i in range(1,256):
            low=i&-i;table[i]=table[i^low]^columns[8*block+low.bit_length()-1]
        result.append(table)
    return result
def lut_step(tables,x):
    y=0
    for table in tables:
        y^=table[x&255];x>>=8
    return y

def build_raw_row(m,o): return m
def build_raw_col(m,o): return {a:make_columns(m[a]) for a in ACTIONS}
def build_raw_lut(m,o): return {a:make_lut(make_columns(m[a])) for a in ACTIONS}
def build_quotient(m,o): return quotient(m,o,ACTIONS)
BUILD={'raw_row_parity':build_raw_row,'raw_column_xor':build_raw_col,'raw_byte_lut':build_raw_lut,'projected_2bit':build_quotient}

def independent_certification(m,o,candidate):
    basis,updates,readout=candidate
    if len(basis)!=2:return {'status':'REJECT','reason':'wrong_quotient_dimension'}
    # Independently construct the *observable* dual row span from scratch.
    reached={o};todo=[o]
    for row in todo:
        for a in ACTIONS:
            rr=mul_row(row,m[a]);
            if rr not in reached:reached.add(rr);todo.append(rr)
            if len(reached)>128*128:return {'status':'HOLD','reason':'span_budget'}
    def rank(rows):
        pivots={}
        for row in rows:
            while row:
                p=row.bit_length()-1
                if p in pivots:row^=pivots[p]
                else:pivots[p]=row;break
        return len(pivots)
    exact_rank=rank(reached)
    if exact_rank!=2:return {'status':'REJECT','reason':'independent_observable_rank','rank':exact_rank}
    for j in range(N):
        raw=1<<j;old=eval_rows(basis,raw)
        if dot(o,raw)!=dot(readout,old):return {'status':'REJECT','reason':'output','witness_basis_bit':j}
        for a in ACTIONS:
            next_phi=eval_rows(basis,eval_rows(m[a],raw))
            next_delta=eval_rows(updates[a],old)
            if next_phi!=next_delta:return {'status':'REJECT','reason':'transition','witness_basis_bit':j,'action':a}
    return {'status':'PASS_EXACT_GF2','independent_observable_rank':exact_rank,'checked_basis_states':N,'checked_transition_edges':N*len(ACTIONS),'proof':'GF2 linear maps agree on complete 128-vector basis, so they agree on every raw x'}

def deep_size(obj,seen=None):
    if seen is None:seen=set()
    i=id(obj)
    if i in seen:return 0
    seen.add(i);v=sys.getsizeof(obj)
    if isinstance(obj,dict):
        for k,z in obj.items():v+=deep_size(k,seen)+deep_size(z,seen)
    elif isinstance(obj,(list,tuple,set)):
        for x in obj:v+=deep_size(x,seen)
    return v

def execute(name,method,starts,streams,num):
    total=0
    if name=='projected_2bit':
        basis,updates,readout=method
        for x,actions in zip(starts,streams):
            q=eval_rows(basis,x)
            for a in actions[:num]:
                q=eval_rows(updates[a],q)
                total+=dot(readout,q)
    else:
        for x,actions in zip(starts,streams):
            for a in actions[:num]:
                if name=='raw_row_parity':x=eval_rows(method[a],x)
                elif name=='raw_column_xor':x=column_step(method[a],x)
                elif name=='raw_byte_lut':x=lut_step(method[a],x)
                else:raise ValueError(name)
                total+=dot(OBSERVED,x)
    return total

def safe_median(x):return statistics.median(x)
def run():
    global OBSERVED
    gc.disable()
    t=time.perf_counter_ns();source,OBSERVED=system(N);source_build_ns=time.perf_counter_ns()-t
    starts_rng=random.Random(SEED)
    starts=[starts_rng.getrandbits(N) for _ in range(STREAMS)]
    streams=[[starts_rng.getrandbits(1) for _ in range(max(HORIZONS))] for _ in range(STREAMS)]
    name_order=list(BUILD)
    setup_samples={name:[] for name in BUILD};methods={}
    # Warmup precomputation independently, then repeated timing with all methods.
    for name,fn in BUILD.items():methods[name]=fn(source,OBSERVED)
    for rep in range(REPEATS):
        for name in name_order[rep%4:]+name_order[:rep%4]:
            fn=BUILD[name];t=time.perf_counter_ns();built=fn(source,OBSERVED);elapsed=time.perf_counter_ns()-t
            setup_samples[name].append(elapsed);methods[name]=built
    cert_samples=[];cert=None
    for _ in range(REPEATS):
        t=time.perf_counter_ns();chk=independent_certification(source,OBSERVED,methods['projected_2bit']);dur=time.perf_counter_ns()-t
        cert_samples.append(dur);cert=chk
        assert chk['status']=='PASS_EXACT_GF2',chk
    # negative: changing one quotient delta row must be caught by independent checker
    basis,updates,readout=methods['projected_2bit'];mutated_updates={a:updates[a].copy() for a in ACTIONS};mutated_updates[0][0]^=1
    negative=independent_certification(source,OBSERVED,(basis,mutated_updates,readout));assert negative['status']=='REJECT',negative
    table_sizes={name:deep_size(v) for name,v in methods.items()}
    # Note memory is Python object-size estimate, not peak RSS, and excludes common source.
    admissible=[name for name in name_order if table_sizes[name]<=MAX_MEM]
    if 'raw_column_xor' not in admissible or 'projected_2bit' not in admissible:raise RuntimeError('MEMORY_BUDGET_CONFLICT')
    # Validate every per-step observed value, not just aggregated checksums.
    correctness_checks=0
    for x0,actions in zip(starts,streams):
        raw_states={name:x0 for name in name_order if name!='projected_2bit'}
        q=eval_rows(basis,x0)
        for a in actions:
            expected=eval_rows(source[a],raw_states['raw_row_parity']);raw_states['raw_row_parity']=expected
            for name in ('raw_column_xor','raw_byte_lut'):
                nxt=column_step(methods[name][a],raw_states[name]) if name=='raw_column_xor' else lut_step(methods[name][a],raw_states[name]);raw_states[name]=nxt
                assert nxt==expected,(name,'wrong raw state')
            q=eval_rows(updates[a],q);reference=dot(OBSERVED,expected)
            assert dot(readout,q)==reference,('quotient mismatch',a)
            correctness_checks+=1
    samples={str(num):{name:[] for name in BUILD} for num in HORIZONS}
    checksums={}
    for num in HORIZONS:
        for i in range(REPEATS+1):
            order=name_order[i%4:]+name_order[:i%4]
            for name in order:
                t=time.perf_counter_ns();checksum=execute(name,methods[name],starts,streams,num);elapsed=time.perf_counter_ns()-t
                if i>0:samples[str(num)][name].append(elapsed)
                checksums.setdefault(str(num),{})[name]=checksum
        assert len(set(checksums[str(num)].values()))==1,(num,checksums[str(num)])
    total={};fastest={}
    for num in HORIZONS:
        k=str(num);total[k]={}
        for name in BUILD:
            build_ns=safe_median(setup_samples[name]);exec_ns=safe_median(samples[k][name]);verify_ns=safe_median(cert_samples) if name=='projected_2bit' else 0
            total[k][name]={'build_median_ns':build_ns,'execute_median_ns':exec_ns,'independent_certification_median_ns':verify_ns,'total_ns':build_ns+exec_ns+verify_ns}
        available=[n for n in ('raw_column_xor','raw_byte_lut') if n in admissible]
        fastest[k]=min(available,key=lambda n:total[k][n]['total_ns'])
    n='2048';best=fastest[n];proj=total[n]['projected_2bit']['total_ns'];baseline=total[n][best]['total_ns'];ratio=proj/baseline
    verdict='PASS_SCOPED_COST_MARGIN' if ratio<=0.9 else 'FAIL_SCOPED_COST_MARGIN'
    return {
      'protocol':'GEN001_C6_COST_BENCHMARK_V1','status':verdict,'date':'2026-11-07',
      'pre_registration_commit':'a455aa81a2afc4cabc76fb77822c8c86141f45f8',
      'original_source_git_blob':'706da2229bbe7a244e899729221170149bc6d014',
      'platform':{'python':platform.python_version(),'implementation':platform.python_implementation(),'machine':platform.machine(),'platform':platform.platform(),'clock':'perf_counter_ns'},
      'fixed_scope':{'n':N,'actions':ACTIONS,'streams':STREAMS,'seed':SEED,'horizons':HORIZONS,'repetitions':REPEATS,'max_method_specific_table_memory_bytes':MAX_MEM,'observed_output':'1bit after each source action','cache':'no output-word cache','common_source_build_ns_one_observation':source_build_ns},
      'correctness':{'output_checks_per_method':correctness_checks,'source_raw_to_optimized_exact':True,'quotient_future_preserving':True,'independent_gf2_certificate':cert,'mutation_control':negative,'checksums':checksums},
      'method_specific_python_object_memory_bytes':table_sizes,
      'admissible_methods':admissible,
      'setup_samples_ns':setup_samples,'certificate_samples_ns':cert_samples,'execution_samples_ns':samples,'inclusive_median_estimates_by_horizon':total,
      'fastest_admissible_raw_by_horizon':fastest,
      'main_comparison':{'horizon_steps_per_stream':2048,'best_no_projection_method':best,'quotient_over_best_raw_total_cost_ratio':ratio,'speedup_best_raw_over_quotient':baseline/proj,'quotient_total_ns':proj,'best_raw_total_ns':baseline,'ten_percent_margin_met':ratio<=0.9},
      'limits':['Synthetic, source-aware GF2; no black-box arbitrary phi','Python benchmark on one host, not compiled native kernel','Common source matrix construction excluded equally from comparative totals; measured separately once','Method-specific build includes LUT/columns or quotient generation. Quotient independent certification included, direct raw code correctness check not charged as runtime certification','Python recursive sys.getsizeof estimates footprint, not RSS or allocated peak','No source-discovery cost: known source model provided to both sides; C6 for unknown-domain discovery remains open','Only 8 streams, uniform actions; repeated-run medians do not guarantee physical deployment speedup','Comparisons exclude operational integration and robust confidence intervals']
    }

if __name__=='__main__':
    res=run()
    path=Path('/mnt/data/gen001_c6/C6_FAIR_COST_OBSERVED_2026-11-07.json')
    path.write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
    summary={'status':res['status'],'main_comparison':res['main_comparison'],'table_bytes':res['method_specific_python_object_memory_bytes'],'verification':res['correctness']['independent_gf2_certificate'],'mutation':res['correctness']['mutation_control'],'source_build_ns':res['fixed_scope']['common_source_build_ns_one_observation'],'by_horizon':{k:{v:round(d['total_ns']/1e6,4) for v,d in x.items()} for k,x in res['inclusive_median_estimates_by_horizon'].items()}}
    print(json.dumps(summary,ensure_ascii=False,indent=2))
