#!/usr/bin/env python3
"""D04/D05: source-pinned REAL third-party annotated natural-language QA audit.

Publisher: AllenAI StrategyQA evaluator, official *representative* 10-case sample.
Uses independent publisher-authored natural-language questions, gold answers and
decompositions; existing publisher example predictions are NOT model inference.
Reports structural and answer metrics separately. Gold stays in scorer only.
NEVER promotes these diagnostics to general semantic S3/S4 or root AC 18/18.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

PROTOCOL="ISSUE1_EXTERNAL_STRATEGYQA_SOURCE_AUDIT_V1"
PUBLISHER="allenai/strategyqa-evaluator"
COMMIT="49b88ed2b2f1b57385c13e8a0699dee1d227f83e"
SOURCES={
    "gold_small.json":"31a98479a79d44d2a94ca0684e876411566ee21d",
    "predictions_small.json":"7464a3d0e685a7679c7dfc6d58e8629c2a691426",
}
ORIGIN="https://raw.githubusercontent.com/"+PUBLISHER+"/"+COMMIT+"/"

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def fetch(name:str)->bytes:
    with urllib.request.urlopen(ORIGIN+name,timeout=12) as response:
        return response.read()

def checked_source(name:str,read=fetch):
    if name not in SOURCES:
        raise ValueError("D04_UPSTREAM_PATH_NOT_ALLOWED")
    data=read(name)
    if git_blob(data)!=SOURCES[name]:
        raise ValueError("D04_EXTERNAL_SOURCE_GIT_BLOB_DRIFT:"+name)
    return json.loads(data)

def public_inputs_from_gold(gold):
    """Public predictor *input only*: label/decomposition/evidence omitted."""
    return [{"qid":case["qid"],"question":case["question"]} for case in gold]

def audit(read=fetch):
    gold=checked_source("gold_small.json",read)
    predictions=checked_source("predictions_small.json",read)
    if type(gold) is not list or len(gold)!=10 or type(predictions) is not dict:
        raise ValueError("D04_THIRD_PARTY_CASE_SCHEMA_INVALID")
    ids=[]
    by_case=[]
    for row in gold:
        if type(row) is not dict or set(row)!={"qid","question","answer","decomposition","evidence"}:
            raise ValueError("D04_GOLD_RECORD_SCHEMA_DRIFT")
        qid=row["qid"]
        if type(qid) is not str or not qid or type(row["question"]) is not str or not row["question"]:
            raise ValueError("D04_GOLD_QUESTION_MISSING")
        if type(row["answer"]) is not bool:
            raise ValueError("D04_GOLD_ANSWER_TYPE_INVALID")
        steps=row["decomposition"]
        if type(steps) is not list or not steps or not all(type(x) is str and x for x in steps):
            raise ValueError("D05_PUBLISHED_DECOMPOSITION_SCHEMA_INVALID")
        if type(row["evidence"]) is not list or not row["evidence"]:
            raise ValueError("D05_PUBLISHED_EVIDENCE_MISSING")
        ids.append(qid)
    if len(set(ids))!=10 or set(predictions)!=set(ids):
        raise ValueError("D04_DUPLICATE_OR_UNMATCHED_QIDS")
    public=public_inputs_from_gold(gold)
    if any(set(x)!={"qid","question"} for x in public):
        raise ValueError("D04_PREDICTOR_INPUT_CONTAINS_GOLD")
    answer_right=0
    exact_decomp=0
    gold_total_steps=0
    prediction_total_steps=0
    for row in gold:
        pred=predictions[row["qid"]]
        if type(pred) is not dict or set(pred)!={"answer","decomposition","paragraphs"}:
            raise ValueError("D04_PREDICTION_SCHEMA_DRIFT")
        if type(pred["answer"]) is not bool:
            raise ValueError("D04_PREDICTION_ANSWER_TYPE_INVALID")
        ps=pred["decomposition"]
        if type(ps) is not list or not all(type(x) is str for x in ps):
            raise ValueError("D05_PREDICTION_DECOMPOSITION_INVALID")
        same_answer=pred["answer"]==row["answer"]
        same_decomposition=ps==row["decomposition"]
        answer_right+=int(same_answer)
        exact_decomp+=int(same_decomposition)
        gold_total_steps+=len(row["decomposition"])
        prediction_total_steps+=len(ps)
        by_case.append({
            "qid":row["qid"],
            "published_gold_steps":len(row["decomposition"]),
            "published_example_prediction_steps":len(ps),
            "published_example_answer_correct":same_answer,
            "verbatim_decomposition_identical":same_decomposition,
        })
    if (answer_right,gold_total_steps,prediction_total_steps,exact_decomp)!=(8,34,20,0):
        raise ValueError("D04_UNEXPECTED_OFFICIAL_EXAMPLE_AUDIT_VALUES")
    return {
        "protocol":PROTOCOL,
        "status":"VERIFIED_EXTERNAL_HUMAN_NL_DECOMPOSITION_EXAMPLE_SCOPED_ONLY",
        "published_by":PUBLISHER,
        "publisher_commit":COMMIT,
        "published_git_blobs":dict(SOURCES),
        "third_party_natural_language_question_count":10,
        "published_gold_decomposition_steps":gold_total_steps,
        "published_example_prediction_steps":prediction_total_steps,
        "published_example_answer_correct":answer_right,
        "published_example_exact_decomposition_count":exact_decomp,
        "publisher_gold_true_count":sum(x["answer"] for x in gold),
        "published_example_is_not_real_LLM_inference":True,
        "alternate_valid_decompositions_possible":True,
        "textual_decomposition_mismatch_is_not_proof_of_failed_S4":True,
        "human_annotated_public_gold_is_visible_not_hidden":True,
        "publisher_test_is_only_representative_sample":True,
        "training_contamination_or_unseenness_independently_proven":False,
        "true_S3_candidatewise_natural_language_admissibility_evaluated":False,
        "true_S4_exhaustive_real_world_obligations_evaluated":False,
        "full_original_A_B_C_D_E_measured":False,
        "original_root_scientific_AC_pass_raised":False,
        "predictor_input_contract_keys":["qid","question"],
        "per_case":by_case,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        result=audit()
        if a.out:
            if a.out.is_symlink(): raise ValueError("D04_SYMLINK_OUTPUT")
            a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        print(json.dumps({k:result[k] for k in (
            "status","third_party_natural_language_question_count",
            "published_example_answer_correct",
            "true_S3_candidatewise_natural_language_admissibility_evaluated",
            "true_S4_exhaustive_real_world_obligations_evaluated")}))
        return 0
    except Exception as e:
        print(json.dumps({"status":"INTEGRITY_FAIL_CLOSED",
                          "error":type(e).__name__+":"+str(e)[:200]}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
