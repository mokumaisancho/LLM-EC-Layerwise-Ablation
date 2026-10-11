#!/usr/bin/env python3
"""D04/D05 published MultiRC natural-language S3 diagnostic + bounded S4 gate.

Source: preexisting public development labels in third-party research mirror.
No LLM, original EC S3 semantic proof, or blinded gold certification implied.
A lexical-only baseline sees *public input only*; scoring receives gold later.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

PROTOCOL="ISSUE1_PUBLISHED_MULTIRC_NL_S3_S4_V17"
PUBLISHER="CogComp/multirc"
SOURCE_REPO="soujanyarbhat/aNswER_multirc"
SOURCE_COMMIT="41d06bd291026f42fc3a44cbd021cc6f6f84d9bd"
SOURCE_PATH="dataset/devData.json"
SOURCE_BLOB="847cbabd9de66ab7f37a3e7a2a1849ef51c9b1e5"
SOURCE_URL=("https://raw.githubusercontent.com/"+SOURCE_REPO+"/"+
            SOURCE_COMMIT+"/"+SOURCE_PATH)

def git_blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def read_public_publisher_copy():
    with urllib.request.urlopen(SOURCE_URL,timeout=30) as response:
        return response.read()

def source_rows(raw:bytes):
    if git_blob(raw)!=SOURCE_BLOB:
        raise ValueError("D04_OFFICIAL_DERIVED_COPY_BLOB_DRIFT")
    obj=json.loads(raw)
    if type(obj) is not dict or set(obj)!={"data"}:
        raise ValueError("D04_SOURCE_SCHEMA")
    public,gold=[],[]
    for pi,paragraph in enumerate(obj["data"]):
        body=paragraph["paragraph"]
        for qi,q in enumerate(body["questions"]):
            cid=f"{pi}/{qi}"
            answers=q["answers"]
            if not answers:
                raise ValueError("D04_EMPTY_CANDIDATE_SET")
            case={"question_id":cid,"passage":body["text"],
                  "question":q["question"],"options":[]}
            labels={}
            for ai,answer in enumerate(answers):
                aid=f"{cid}/{ai}"
                if (type(answer["isAnswer"]) is not bool or
                    not isinstance(answer["text"],str)):
                    raise ValueError("D04_INVALID_GOLD")
                case["options"].append({
                    "candidate_id":aid,"text":answer["text"]})
                labels[aid]=answer["isAnswer"]
            public.append(case)
            gold.append({"question_id":cid,"labels":labels})
    if len(public)!=953 or sum(len(x["options"]) for x in public)!=4848:
        raise ValueError("D04_EXPECTED_PUBLISHER_SOURCE_SIZE_CHANGED")
    if any("isAnswer" in json.dumps(case) for case in public):
        raise ValueError("GOLD_LEAKAGE")
    return public,gold

def normalize(text:str)->str:
    text=re.sub(r"<[^>]*>"," ",text)
    text=re.sub(r"&nbsp;|&#160;"," ",text,flags=re.I)
    text=re.sub("[^a-z0-9]+"," ",text.lower()).strip()
    return " "+re.sub(r"\\s+"," ",text)+" "

def literal_public_only_predict(case):
    if set(case)!={"question_id","passage","question","options"}:
        raise ValueError("D04_MODEL_PUBLIC_ONLY_INTERFACE")
    p=normalize(case["passage"])
    predictions=[]
    for opt in case["options"]:
        if set(opt)!={"candidate_id","text"}:
            raise ValueError("D04_MODEL_ORACLE_GOLD_INPUT")
        phrase=normalize(opt["text"]).strip()+" "
        # Exactly the predeclared untuned contiguous lexical baseline.
        predictions.append({"candidate_id":opt["candidate_id"],
                            "select":phrase in p})
    return {"question_id":case["question_id"],"decisions":predictions}

def s4_formal_completion(case,pred):
    """Closed-world QUESTION SUBMISSION only: all choices must be decided."""
    if case["question_id"]!=pred.get("question_id"):
        raise ValueError("D05_UPSTREAM_ID_DRIFT")
    original=[x["candidate_id"] for x in case["options"]]
    decisions=pred.get("decisions")
    if not isinstance(decisions,list):
        raise ValueError("D05_DECISIONS_NOT_ARRAY")
    ids=[x["candidate_id"] for x in decisions]
    if (len(set(original))!=len(original) or
        len(ids)!=len(original) or len(set(ids))!=len(ids) or
        set(ids)!=set(original) or
        any(type(x["select"]) is not bool for x in decisions)):
        raise ValueError("D05_INCOMPLETE_DUPLICATE_OR_FORGED_DECISION")
    return {"all_option_decisions_accounted_for":True,
            "formal_question_submission_allowed":True,
            "real_world_task_closure_authorized":False}

def score(public,gold,predictions):
    if len(public)!=len(gold) or len(gold)!=len(predictions):
        raise ValueError("D04_MISMATCHED_ROWS")
    tally=dict(tp=0,fp=0,fn=0,tn=0,exact=0,multi_gold=0,zero_gold=0,
               all_choices_decided=0)
    for case,g,p in zip(public,gold,predictions):
        if case["question_id"]!=g["question_id"]:
            raise ValueError("D04_GOLD_SOURCE_NOT_SAME_CASE")
        required=g["labels"]
        result=s4_formal_completion(case,p)
        tally["all_choices_decided"]+=int(
            result["all_option_decisions_accounted_for"])
        got={x["candidate_id"]:x["select"] for x in p["decisions"]}
        if set(got)!=set(required):
            raise ValueError("D04_S3_SELECTION_NOT_SAME_CANDIDATE_SET")
        truth={x for x,y in required.items() if y}
        selected={x for x,y in got.items() if y}
        tally["exact"]+=int(truth==selected)
        tally["multi_gold"]+=int(len(truth)>1)
        tally["zero_gold"]+=int(len(truth)==0)
        for cid in required:
            a=got[cid]
            b=required[cid]
            tally["tp" if a and b else
                  "fp" if a and not b else
                  "fn" if not a and b else "tn"]+=1
    t=tally
    return {
        "questions":len(public),
        "answer_options":sum(len(x["options"]) for x in public),
        "true_option_labels":t["tp"]+t["fn"],
        "selected_by_public_literal_baseline":t["tp"]+t["fp"],
        "true_positives":t["tp"],"false_positives":t["fp"],
        "false_negatives":t["fn"],"true_negatives":t["tn"],
        "question_exact_selected_set_matches":t["exact"],
        "exact_set_rate":t["exact"]/len(public),
        "candidate_micro_precision":t["tp"]/(t["tp"]+t["fp"]),
        "candidate_micro_recall":t["tp"]/(t["tp"]+t["fn"]),
        "candidate_micro_F1":2*t["tp"]/(2*t["tp"]+t["fp"]+t["fn"]),
        "questions_with_multiple_correct_candidates":t["multi_gold"],
        "questions_with_zero_correct_candidates":t["zero_gold"],
        "formal_s4_question_submission_preconditions_met":
             t["all_choices_decided"],
        "real_world_task_closures_authorized":0,
    }

def evaluate(raw:bytes):
    public,gold=source_rows(raw)
    preds=[literal_public_only_predict(x) for x in public]
    result=score(public,gold,preds)
    expected=(953,4848,653,3,838,796,1237,1977,89)
    got=(result["questions"],result["answer_options"],
         result["questions_with_multiple_correct_candidates"],
         result["questions_with_zero_correct_candidates"],
         result["true_positives"],result["false_positives"],
         result["false_negatives"],result["true_negatives"],
         result["question_exact_selected_set_matches"])
    if got!=expected:
        raise ValueError("D04_BASELINE_RESULT_NOT_REPRODUCIBLE")
    return {
      "protocol":PROTOCOL,
      "data":{"original_benchmark":PUBLISHER,
              "publisher_mirror":SOURCE_REPO,
              "source_commit":SOURCE_COMMIT,
              "source_path":SOURCE_PATH,
              "source_git_blob":SOURCE_BLOB,
              "public_development_gold_not_unseen":True,
              "raw_publisher_text_republished":False},
      "S3":result,
      "S4_scope":{
          "only_all_official_question_answer_choices_decided":True,
          "real_world_task_termination_unproven":True,
          "not_original_false_closure_rate":True},
      "predictor":{"type":"UNTUNED_LEXICAL_DIAGNOSTIC_NOT_LLM_OR_EC",
                   "model_gold_access":False,
                   "s3_real_semantic_capability_proven":False},
      "scientific_boundary":{
          "independent_publisher_annotated_multiselect_source_available":True,
          "blind_unseen_holdout_proven":False,
          "real_ec_nl_s3_semantic_admissibility_qualified":False,
          "independent_real_task_s4_obligations_qualified":False,
          "root_original_scientific_AC_pass":2,
          "A_B_C_D_E_real_causal_run":False},
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    try:
        raw=read_public_publisher_copy()
        result=evaluate(raw)
        if args.out:
            if args.out.is_symlink():
                raise ValueError("D04_SYMLINK_OUTPUT")
            args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        print(json.dumps({"status":"SCOPED_NL_S3_SET_DIAGNOSTIC_DONE",
                          "questions":result["S3"]["questions"],
                          "multi_gold":result["S3"]["questions_with_multiple_correct_candidates"],
                          "exact":result["S3"]["question_exact_selected_set_matches"],
                          "root_scientific_AC":2}))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"FAIL_CLOSED",
                          "error":type(exc).__name__+":"+str(exc)[:240]}))
        return 3
if __name__=="__main__":
    raise SystemExit(main())
