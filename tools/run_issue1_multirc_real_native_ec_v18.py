#!/usr/bin/env python3
"""Actual source-pinned EC S3/S4 implementation on published MultiRC cases.

This is genuinely executed native EC source, with deterministic public-only
lexical predicates, NOT independent source-qualified natural-language meaning.
Never interpret finite-question CLOSE as real-world S4 task closure.
"""
from __future__ import annotations
import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path
from tools.issue1_ecv4_local_plugin_v1 import evaluate as execute_native_plugin, file_blob

PROTOCOL="ISSUE1_MULTIRC_REAL_NATIVE_EC_LEXICAL_SOURCE_BRIDGE_V18"
SAMPLE_COUNT=32
CORPUS_URL=("https://raw.githubusercontent.com/soujanyarbhat/aNswER_multirc/"
            "41d06bd291026f42fc3a44cbd021cc6f6f84d9bd/dataset/devData.json")
CORPUS_SHA="847cbabd9de66ab7f37a3e7a2a1849ef51c9b1e5"
PLUGIN_BLOB="ee17492c71ba28ca8d1681edd8e5a56fb3e33db1"
S2_INPUT_SCHEMA=frozenset({"question_id","passage","question","options"})
EC_SOURCE_COMMIT="3f435ad4365d846d96264458540efb4848ce3541"

def gh_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(item):
    return json.dumps(item,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode()

def normalize(value):
    value=re.sub(r"<[^>]*>"," ",value)
    value=re.sub(r"&nbsp;|&#160;"," ",value,flags=re.I)
    value=re.sub("[^a-z0-9]+"," ",value.lower()).strip()
    return " "+re.sub(r"\s+"," ",value)+" "

def source_cases(raw):
    if gh_blob(raw)!=CORPUS_SHA:
        raise ValueError("G0_MULTIRC_SOURCE_PIN_MISMATCH")
    obj=json.loads(raw)
    if set(obj)!={"data"}:
        raise ValueError("G1_WRONG_SOURCE_SCHEMA")
    public,golds=[],[]
    for pi,p in enumerate(obj["data"]):
        body=p["paragraph"]
        for qi,q in enumerate(body["questions"]):
            cid=f"{pi}/{qi}"
            options=[]
            labels={}
            for ai,answer in enumerate(q["answers"]):
                key=f"{cid}/{ai}"
                if type(answer["isAnswer"]) is not bool:
                    raise ValueError("G0_BAD_PUBLISHED_GOLD")
                labels[key]=answer["isAnswer"]
                options.append({"candidate_id":key,"text":answer["text"]})
            if not options:
                raise ValueError("G0_EMPTY_INPUT_CANDIDATES")
            public.append({"question_id":cid,"passage":body["text"],
                           "question":q["question"],"options":options})
            golds.append({"question_id":cid,"labels":labels})
    if len(public)!=953 or sum(len(x["options"]) for x in public)!=4848:
        raise ValueError("G0_PUBLISHED_MULTIRC_CASECOUNT_CHANGED")
    return public,golds

def make_public_ec_input(case):
    if not isinstance(case,dict) or set(case)!=S2_INPUT_SCHEMA:
        raise ValueError("G5_GOLD_OR_OTHER_PRIVATE_FIELD_IN_PUBLIC_CASE")
    caseid=case["question_id"]
    paragraph=normalize(case["passage"])
    operations={}
    facts={"active":True,"all_candidates_decided":True}
    candidates=[]
    for n,item in enumerate(case["options"]):
        if set(item)!={"candidate_id","text"}:
            raise ValueError("G5_PRIVATE_LABEL_IN_PUBLIC_OPTION")
        cid=item["candidate_id"]
        op=f"op{n}"
        key=f"visible_{n}"
        operations[op]=[f"fact:{key}"]
        facts[key]=normalize(item["text"]).strip()+" " in paragraph
        candidates.append({
            "candidate_id":cid,
            "semantic_transition":{"operation":op},
            "evidence_refs":[f"policy:multirc:{caseid}"],
            "dependencies":[],"claims":[],
        })
    policy={
        "schema":"EC_PUBLIC_POLICY_V2",
        "policy_id":f"research-multirc-lexical:{caseid}",
        "policy_evidence_ref":f"policy:multirc:{caseid}",
        "operation_rules":operations,
        "obligation_rules":{
            "all_choices_processed":{
                "when":["fact:active"],"done_when":["fact:all_candidates_decided"],
            }
        },
    }
    task={
        "schema":"EC_FORMAL_FACTS_V2",
        "source_ref":f"task:multirc:{caseid}",
        "facts":facts,
    }
    return candidates,policy,task

def run_one(ec_root:Path,case):
    candidates,policy,task=make_public_ec_input(case)
    from tools.issue1_ecv4_local_plugin_v1 import module, SOURCES
    policy_lib=module(ec_root/SOURCES["policy"][0],"bounded_multirc_policy")
    public_s2={
        "candidates":candidates,
        "relation_groups":[],
        "semantic_ir_hash":policy_lib.digest(task),
        "source_refs":[policy["policy_evidence_ref"],task["source_ref"]],
    }
    started=time.perf_counter()
    actual=execute_native_plugin(
        ec_root,public_s2,task,policy,policy_lib.digest(policy),
        {"reframe_required":False,"reframe_resolved":False})
    duration=time.perf_counter()-started
    if actual["original_MVP_AC_pass_from_plugin"] or actual["real_world_close_authorized"]:
        raise ValueError("G11_FALSE_SCIENTIFIC_AC_PROMOTION")
    if len(actual["s3_selected"])+len(actual["s3_rejected"])!=len(candidates):
        raise ValueError("G7_NATIVE_S3_PARTITION_INCOMPLETE")
    picked=set(actual["s3_selected"])
    dropped=set(actual["s3_rejected"])
    original={x["candidate_id"] for x in candidates}
    if picked&dropped or picked|dropped!=original:
        raise ValueError("G7_NATIVE_S3_DUPLICATE_OR_OMISSION")
    return {
        "question_id":case["question_id"],
        "input_sha256":sha(canonical(case)),
        "native_policy_sha256":actual["S4_derived_required_conditions"] and
                               policy_lib.digest(policy),
        "selected_candidate_ids":actual["s3_selected"],
        "s4_formal_diagnostic":actual["s4_diagnostic"],
        "s4_policy_condition_inventory":list(actual["s4_policy_obligations"]),
        "native_source_commit":actual["EC_source_commit"],
        "elapsed_ms":round(duration*1000,2),
    }

def execute(ec_root:Path,plugin_source:Path,*,count=SAMPLE_COUNT):
    if count!=SAMPLE_COUNT:
        raise ValueError("G0_SAMPLED_COUNT_NOT_PREDECLARED")
    if file_blob(plugin_source)!=PLUGIN_BLOB:
        raise ValueError("G0_PLUGIN_CODE_NOT_PINNED")
    import os
    if os.environ.get("PYTHONDONTWRITEBYTECODE")!="1":
        raise ValueError("G0_NO_LOCAL_PYTHON_CACHE_ALLOWED")
    with urllib.request.urlopen(CORPUS_URL,timeout=25) as response:
        raw=response.read()
    public,gold=source_cases(raw)
    rows=[]
    TP=FP=FN=TN=0
    exact=closed=closed_inexact=multi=0
    start=time.perf_counter()
    for p,g in zip(public[:count],gold[:count]):
        row=run_one(ec_root,p)
        sel=set(row["selected_candidate_ids"])
        actual={cid for cid,true in g["labels"].items() if true}
        if set(g["labels"])!={x["candidate_id"] for x in p["options"]}:
            raise ValueError("G7_DIFFERENT_GOLD_CANDIDATES")
        multi+=int(len(actual)>1)
        same=sel==actual
        exact+=int(same)
        for cid in g["labels"]:
            positive=cid in sel
            correct=g["labels"][cid]
            if positive and correct:TP+=1
            elif positive:FP+=1
            elif correct:FN+=1
            else:TN+=1
        is_close=row["s4_formal_diagnostic"]=="CLOSE"
        closed+=int(is_close)
        closed_inexact+=int(is_close and not same)
        rows.append(row)
    return {
        "schema":PROTOCOL,
        "sample_plan":{
            "algorithm":"first_32_questions_in_publisher_frozen_index_order",
            "count":SAMPLE_COUNT,"chosen_without_gold_label_filter":True,
            "publisher_data_original_public_dev":True,
            "heldout_unseen_proven":False,
        },
        "source":{"mirror_corpus_git_blob":CORPUS_SHA,
                  "native_EC_commit":EC_SOURCE_COMMIT,
                  "research_plugin_git_blob":PLUGIN_BLOB,
                  "raw_source_SHA256":sha(raw)},
        "actual_native_execution":{
            "real_ec_s3_s4_invocations":len(rows),
            "case_count_with_multiple_published_correct_answers":multi,
            "TP":TP,"FP":FP,"FN":FN,"TN":TN,
            "exact_candidate_sets":exact,
            "candidate_micro_F1":2*TP/(2*TP+FP+FN),
            "formal_question_close":closed,
            "formal_close_with_wrong_published_answer_set":closed_inexact,
            "formally_closed_wrong_is_NOT_scientific_S4_false_closure":True,
            "elapsed_ms_total":round((time.perf_counter()-start)*1000,2),
            "raw_prediction_receipts":rows,
        },
        "qualification":{
            "real_native_ec_modules_executed":True,
            "predictions_derived_from_public_input_only":True,
            "semantic_feature_extractor":"CONTIGUOUS_LEXICAL_MATCH_ONLY",
            "independent_natural_language_S3_semantics_proven":False,
            "independent_real_task_S4_obligation_completeness_proven":False,
            "LLM_model_inference_run":False,
            "true_original_four_layer_AE_proven":False,
            "original_scientific_AC_score":2,
        }
    }
