#!/usr/bin/env python3
"""Rehydrate source-bound formal benchmark without storing raw data in GitHub.

Source-frozen V1 dataset; this V2 tool changes ONLY verification, not samples.
Mechanical gold is reconstructible from public policy. This is NOT an
independent natural-language gold or valid full LLM/EC replacement experiment.

Security model: script and pinned SHA constants must be obtained from a trusted
Git commit. An adversary able to edit both the script and the Git commit can
subvert this audit; same-repository constants are NOT external attestations.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

SCRIPT_BLOB = '2eb9b49bdfd8d0e42d497218ee4c9d66cd46e4a7'
MANIFEST_BLOB = '74ee6317c96835a2abd9cb5e33bc968b3fa496fa'
SOURCE_MANIFEST_DIGEST = '4a0f5ffb84dc8370ac890bceddf8f88c405e4b65c8672ddedbd310abbab976be'
PUBLIC_DIGEST = 'ab9e382a62f0722b27aa5161adefc8f1c6e3bb7dca68662de7184722c441b276'
GOLD_DIGEST = '0a01e5781dc062ebb43fc055ac3b3550f3eeea3f816e9ec248ef26c64531484c'
POLICY_DIGEST = 'fd1703572172641287906613ad970d6104656128a5000cce76873c4502974b96'
EC_SOURCE_BLOB = '7da0cd8d876505cafdd5a9811132427e2f441a14'
SAVED_SCORE_FILE_SHA256 = 'ca9c934e26a347ad8bb816931da43626ace34c953e5a3defd070165a42604239'  # Old local original replay only
MODEL_FORBIDDEN_KEYS = {'gold','oracle','oracle_constraints','answer','answers',
                       'expected','reference','formal_reference','correct',
                       'correct_label','label','labels','prediction',
                       'score','private_gold','private'}
ALLOWED_CLASSES = ('BLOCKED', 'CLOSE', 'CONTINUE', 'REFRAME')

class VerificationError(ValueError):
    pass

def require(ok: bool, reason: str):
    if not ok:
        raise VerificationError(reason)

def canonical(value: Any) -> bytes:
    try:
        return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',', ':'),allow_nan=False).encode()
    except (ValueError, TypeError) as exc:
        raise VerificationError('NONCANONICAL_DATA') from exc

def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()

def blob(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def parse_json(path: Path) -> Any:
    def reject_dupes(pairs):
        d={}
        for k,v in pairs:
            require(k not in d,'DUPLICATE_JSON_KEY:'+k)
            d[k]=v
        return d
    return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=reject_dupes)

def public_free(value, location='$'):
    if isinstance(value, dict):
        for k,v in value.items():
            require(isinstance(k,str) and k.lower() not in MODEL_FORBIDDEN_KEYS,
                    'PREDICTOR_GOLD_KEY:'+location+'.'+str(k))
            public_free(v,location+'.'+k)
    elif isinstance(value, list):
        for i,v in enumerate(value):public_free(v,location+'['+str(i)+']')
    else:
        require(type(value) in (str,bool,int,float,type(None)),
                'INVALID_MODEL_VISIBLE_TYPE:'+location)

def load_pinned_generator(source: Path):
    require(source.exists(),'GENERATOR_NOT_FOUND')
    require(blob(source)==SCRIPT_BLOB,'GENERATOR_GIT_BLOB_MISMATCH')
    spec=importlib.util.spec_from_file_location('holdout48_v1_pinned',source)
    require(spec is not None and spec.loader is not None,'GENERATOR_IMPORT_UNAVAILABLE')
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def rehydrate(source: Path, manifest_path: Path):
    require(manifest_path.exists(),'MANIFEST_NOT_FOUND')
    require(blob(manifest_path)==MANIFEST_BLOB,'MANIFEST_GIT_BLOB_MISMATCH')
    manifest=parse_json(manifest_path)
    require(sha(manifest)==SOURCE_MANIFEST_DIGEST,'MANIFEST_CANONICAL_ROOT_MISMATCH')
    require(manifest.get('native_ec_expected_git_blob')==EC_SOURCE_BLOB,
            'NATIVE_EC_EXPECTED_BLOB_DRIFT')
    for k,v in [('public_sha256',PUBLIC_DIGEST),('private_gold_sha256',GOLD_DIGEST),
                ('formal_source_policy_sha256',POLICY_DIGEST),('n',48)]:
        require(manifest.get(k)==v,'PINNED_MANIFEST_FIELD_MISMATCH:'+k)
    generator=load_pinned_generator(source)
    rows=generator.make_all()
    require(len(rows)==48 and len(set(r['id'] for r in rows))==48,
            'FIXTURE_IDS_OR_N_CHANGED')
    public={'schema':'ISSUE1_HOLDOUT48_PUBLIC_V1',
            'benchmark_scope':'FORMAL_POLICY_ONLY','policy':generator.policy(),
            'cases':[{'id':r['id'],'input':r['input']} for r in rows]}
    private={'schema':'ISSUE1_HOLDOUT48_PRIVATE_V1',
             'labels':[{'id':r['id'],'reference':r['reference']} for r in rows]}
    public_free(public)
    require(sha(public)==PUBLIC_DIGEST,'PUBLIC_REHYDRATION_MISMATCH')
    require(sha(private)==GOLD_DIGEST,'GOLD_REHYDRATION_MISMATCH')
    require(sha(generator.policy())==POLICY_DIGEST,'POLICY_REHYDRATION_MISMATCH')
    counts={x:0 for x in ALLOWED_CLASSES}
    for x in private['labels']:
        cls=x['reference']['closure']
        require(cls in counts,'UNKNOWN_ORACLE_CLASS')
        counts[cls]+=1
    require(counts=={k:12 for k in ALLOWED_CLASSES},'HOLDOUT_NOT_BALANCED')
    return public,private,manifest

def check_saved_score(score_path: Path, public:dict, gold:dict, manifest:dict):
    """Audit recorded native output without rerunning EC; not a new model test."""
    require(hashlib.sha256(score_path.read_bytes()).hexdigest()==SAVED_SCORE_FILE_SHA256,
            'SAVED_SCORE_SHA256_MISMATCH')
    r=parse_json(score_path)
    require(r.get('schema')=='ISSUE1_HOLDOUT48_NATIVE_EC_SCORE_V1',
            'SAVED_SCORE_SCHEMA_MISMATCH')
    require(r.get('source_manifest_sha256')==SOURCE_MANIFEST_DIGEST,
            'SCORE_MANIFEST_UNBOUND')
    require(r.get('ec_git_blob')==EC_SOURCE_BLOB,'SCORE_NATIVE_SOURCE_UNBOUND')
    require(r.get('n')==48 and len(r.get('cases',[]))==48,'SCORE_CASE_COUNT_INVALID')
    require([x['id'] for x in r['cases']]==[x['id'] for x in public['cases']]==
            [x['id'] for x in gold['labels']],'SCORE_ORDER_OR_ID_MISMATCH')
    for row,in_row,ref in zip(r['cases'],public['cases'],gold['labels']):
        require(row.get('input_sha256')==sha(in_row['input']),
                'SCORE_INPUT_SHA_MISMATCH:'+row['id'])
        require(row.get('formal_reference')==ref['reference'],
                'SCORE_GOLD_MISMATCH:'+row['id'])
        require(row.get('exact') is (row.get('native')==ref['reference']),
                'SCORE_CORRECTNESS_TAMPER:'+row['id'])
    actual_count=sum(x['native']==y['reference'] for x,y in zip(r['cases'],gold['labels']))
    require(actual_count==48 and r.get('ec_exact_pass')==48 and
            r.get('ec_exact_fail')==0 and r.get('fail_ids')==[],
            'SAVED_SCORE_NOT_FROZEN_48_OF_48')
    require(r.get('real_llm_calls')==0 and r.get('independent_nl_reference') is False,
            'FALSE_SCIENTIFIC_QUALIFICATION')
    return {'recorded_native_count':actual_count,'recorded_native_cases':48,
            'independently_recomputed_from_source':True,
            'native_ec_reexecuted_in_this_audit':False}

def run(source:Path,manifest_path:Path,recorded_score:Path|None=None,public_output:Path|None=None,
        native_path:Path|None=None):
    public,private,manifest=rehydrate(source,manifest_path)
    check=None
    if recorded_score is not None:
        check=check_saved_score(recorded_score,public,private,manifest)
    ec_source_verified=False
    if native_path is not None:
        require(blob(native_path)==EC_SOURCE_BLOB,'NATIVE_EC_SOURCE_GIT_BLOB_MISMATCH')
        ec_source_verified=True
    if public_output is not None:
        require(not public_output.exists(),'REFUSE_TO_OVERWRITE_PUBLIC')
        public_output.parent.mkdir(parents=True,exist_ok=True)
        public_output.write_bytes(json.dumps(public,sort_keys=True,ensure_ascii=False,indent=2).encode()+b'\n')
    return {'schema':'ISSUE1_REHYDRATE_AUDIT_V2',
            'source':'EXACT_GIT_BLOB_VERIFIED_RECONSTRUCTION',
            'raw_input_files_in_git_required':False,
            'public_cases':48,'counts_by_class':{x:12 for x in ALLOWED_CLASSES},
            'public_sha256':sha(public),'mechanical_gold_sha256':sha(private),
            'policy_sha256':sha(public['policy']),
            'manifest_root_sha256':sha(manifest),
            'source_generator_git_blob':SCRIPT_BLOB,
            'native_source_verified_this_run':ec_source_verified,
            'recorded_score_replay':check,
            'gold_generation_method':'SAME_AUTHORED_FORMAL_POLICY_SYMBOLIC_ALGORITHM',
            'llm_correctness_judged_by_llm':False,
            'semantic_gold_independent':False,
            'full_s1_s4_non_degradation_demonstrated':False,
            'new_real_llm_inference':0,
            'new_native_ec_inference':0,
            'original_science_ac_promoted':0,
            'dataset_is_unseen_semantic_holdout':False,
            'result':'RECONSTRUCTABLE_BUT_NOT_INDEPENDENT_SEMANTIC_EVALUATION'}

def cli():
    ap=argparse.ArgumentParser()
    ap.add_argument('--generator',type=Path,required=True)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--score',type=Path)
    ap.add_argument('--emit-public',type=Path)
    ap.add_argument('--native-source',type=Path)
    ap.add_argument('--receipt',type=Path)
    a=ap.parse_args()
    result=run(a.generator,a.manifest,a.score,a.emit_public,a.native_source)
    data=json.dumps(result,sort_keys=True,indent=2)+'\n'
    if a.receipt:
        require(not a.receipt.exists(),'REFUSE_TO_OVERWRITE_RECEIPT')
        a.receipt.write_text(data)
    print(data,end='')
if __name__=='__main__':
    try:cli()
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        print('VERIFICATION_REJECTED:'+str(exc),file=sys.stderr)
        raise SystemExit(3)
