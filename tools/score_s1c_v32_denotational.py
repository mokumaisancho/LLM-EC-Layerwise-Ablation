from __future__ import annotations

import itertools
from collections import Counter
from typing import Any

PROTOCOL="S1C_V32_DENOTATIONAL_SCORER_V1"
AUTHORITY="S1C_V31_INDEPENDENT_ORACLE_VALIDATOR_V1"
LOCAL_SLOT_IDS={"S01","S02","S03","S04"}
EVAL_IDS=("Q03","Q05","Q06","Q07")
ALLOWED_POL={"POS","NEG"}
ALLOWED_MOD={"ASSERTED","REQUIRED","POSSIBLE"}


def _fail(reason:str,detail:Any=None)->dict[str,Any]:
    return {"pass":False,"terminal":"S1C_V32_SCORER_FAIL_CLOSED","reason":reason,"detail":detail}


def _ari(gold:list[str],pred:list[str])->float:
    n=len(gold)
    if n!=len(pred) or n<2:return 1.0 if gold==pred else 0.0
    table=Counter(zip(gold,pred));row=Counter(gold);col=Counter(pred)
    c2=lambda x:x*(x-1)//2
    a=sum(c2(v) for v in table.values());b=sum(c2(v) for v in row.values());c=sum(c2(v) for v in col.values());total=c2(n)
    if total==0:return 1.0
    expected=(b*c)/total;maximum=.5*(b+c);denom=maximum-expected
    if denom==0:return 1.0 if a==maximum else 0.0
    return (a-expected)/denom


def _pairwise(gold:list[str],pred:list[str])->float:
    ok=total=0
    for i,j in itertools.combinations(range(len(gold)),2):
        ok+=int((gold[i]==gold[j])==(pred[i]==pred[j]));total+=1
    return ok/total if total else 1.0


def _parse_eval_rows(rows:Any,*,require_unique:bool)->dict[str,tuple[int,int,int]]|None:
    if not isinstance(rows,list) or len(rows)!=4:return None
    out={}
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"probe_id","predicted_after"}:return None
        pid=str(row.get("probe_id") or "");bits=row.get("predicted_after")
        if pid not in EVAL_IDS:return None
        if not isinstance(bits,list) or len(bits)!=3 or any(x not in (0,1) for x in bits):return None
        if require_unique and pid in out:return None
        out[pid]=tuple(int(x) for x in bits)
    if require_unique and set(out)!=set(EVAL_IDS):return None
    return out


def validate_schema_core(task:dict[str,Any],prediction:Any)->dict[str,Any]:
    if not isinstance(prediction,dict):return {"valid":False,"reason":"PREDICTION_NOT_OBJECT"}
    if set(prediction)!={"discovered_slots","heldout_assignments","abstentions"}:return {"valid":False,"reason":"TOP_LEVEL_KEYS_INVALID"}
    v=task["visible"];train_ids={str(x["example_id"]) for x in v["training_examples"]};held_ids={str(x["example_id"]) for x in v["heldout_examples"]}
    type_ids={str(x) for x in v["type_inventory"]};entity_ids={str(eid) for ex in v["heldout_examples"] for eid in ex["entity_registry"]}
    slots=prediction["discovered_slots"];assigns=prediction["heldout_assignments"];abst=prediction["abstentions"]
    if not all(isinstance(x,list) for x in (slots,assigns,abst)):return {"valid":False,"reason":"TOP_LEVEL_LIST_REQUIRED"}
    if not int(v["slot_count_bound"]["min"])<=len(slots)<=int(v["slot_count_bound"]["max"]):return {"valid":False,"reason":"SLOT_COUNT_OUT_OF_SCHEMA_BOUND"}
    for slot in slots:
        if not isinstance(slot,dict) or set(slot)!={"slot_id","arg_types","training_members","evaluation_probe_predictions"}:return {"valid":False,"reason":"SLOT_SHAPE_INVALID"}
        if slot.get("slot_id") not in LOCAL_SLOT_IDS:return {"valid":False,"reason":"SLOT_ID_OUT_OF_SCHEMA_ENUM"}
        types=slot.get("arg_types");members=slot.get("training_members")
        if not isinstance(types,list) or not (1<=len(types)<=2) or any(x not in type_ids for x in types):return {"valid":False,"reason":"ARG_TYPES_SCHEMA_INVALID"}
        if not isinstance(members,list) or not (1<=len(members)<=4) or any(str(x) not in train_ids for x in members):return {"valid":False,"reason":"TRAINING_MEMBERS_SCHEMA_INVALID"}
        if _parse_eval_rows(slot.get("evaluation_probe_predictions"),require_unique=False) is None:return {"valid":False,"reason":"EVAL_PREDICTIONS_SCHEMA_INVALID"}
    for row in assigns:
        if not isinstance(row,dict) or set(row)!={"example_id","slot_id","arguments","polarity","modality"}:return {"valid":False,"reason":"ASSIGNMENT_SHAPE_INVALID"}
        if str(row.get("example_id") or "") not in held_ids:return {"valid":False,"reason":"ASSIGNMENT_HELDOUT_ID_SCHEMA_INVALID"}
        if row.get("slot_id") not in LOCAL_SLOT_IDS:return {"valid":False,"reason":"ASSIGNMENT_SLOT_ID_SCHEMA_INVALID"}
        args=row.get("arguments")
        if not isinstance(args,list) or not (1<=len(args)<=2) or any(str(x) not in entity_ids for x in args):return {"valid":False,"reason":"ASSIGNMENT_ARGUMENT_SCHEMA_INVALID"}
        if row.get("polarity") not in ALLOWED_POL or row.get("modality") not in ALLOWED_MOD:return {"valid":False,"reason":"ASSIGNMENT_PM_SCHEMA_INVALID"}
    for row in abst:
        if not isinstance(row,dict) or set(row)!={"example_id","status"}:return {"valid":False,"reason":"ABSTENTION_SHAPE_INVALID"}
        if str(row.get("example_id") or "") not in held_ids or row.get("status")!="AMBIGUOUS":return {"valid":False,"reason":"ABSTENTION_SCHEMA_INVALID"}
    return {"valid":True}


def validate_semantic_contract(task:dict[str,Any],prediction:dict[str,Any])->dict[str,Any]:
    train_ids={str(x["example_id"]) for x in task["visible"]["training_examples"]}
    held_ids={str(x["example_id"]) for x in task["visible"]["heldout_examples"]}
    slot_ids=[];owner={};slot_types={};slot_eval={}
    for slot in prediction["discovered_slots"]:
        sid=str(slot["slot_id"])
        if sid in slot_ids:return {"valid":False,"reason":"DUPLICATE_DISCOVERED_SLOT_ID"}
        slot_ids.append(sid)
        em=_parse_eval_rows(slot["evaluation_probe_predictions"],require_unique=True)
        if em is None:return {"valid":False,"reason":"EVALUATION_PROBE_COVERAGE_INVALID"}
        slot_types[sid]=tuple(slot["arg_types"]);slot_eval[sid]=em
        for m in slot["training_members"]:
            mid=str(m)
            if mid in owner:return {"valid":False,"reason":"TRAINING_MEMBER_DUPLICATED","member":mid}
            owner[mid]=sid
    missing=sorted(train_ids-set(owner))
    if missing:return {"valid":False,"reason":"TRAINING_MEMBER_MISSING","members":missing}
    byid={}
    for row in prediction["heldout_assignments"]:
        eid=str(row["example_id"])
        if eid in byid:return {"valid":False,"reason":"HELDOUT_ASSIGNMENT_DUPLICATED","example_id":eid}
        if row["slot_id"] not in slot_ids:return {"valid":False,"reason":"ASSIGNMENT_REFERENCES_NONEMITTED_SLOT","example_id":eid}
        byid[eid]=row
    abst_ids=set()
    for row in prediction["abstentions"]:
        eid=str(row["example_id"])
        if eid in abst_ids:return {"valid":False,"reason":"ABSTENTION_DUPLICATED","example_id":eid}
        if eid in byid:return {"valid":False,"reason":"HELDOUT_BOTH_ASSIGNED_AND_ABSTAINED","example_id":eid}
        abst_ids.add(eid)
    covered=set(byid)|abst_ids
    if covered!=held_ids:return {"valid":False,"reason":"HELDOUT_COVERAGE_INVALID","missing":sorted(held_ids-covered),"extra":sorted(covered-held_ids)}
    return {"valid":True,"slot_ids":sorted(slot_ids),"owner":owner,"slot_types":slot_types,"slot_eval":slot_eval,"assign_by_id":byid,"abstain_ids":abst_ids}


def _zero(reason:str,detail:Any=None)->dict[str,Any]:
    return {"pass":True,"terminal":"S1C_V32_SCORE_COMPLETE","schema_core_valid":True,"semantic_output_validity":0.0,
            "prediction_valid":False,"prediction_reason":reason,"prediction_detail":detail,
            "training_partition_adjusted_rand_index":0.0,"training_partition_pairwise_accuracy":0.0,
            "unseen_probe_behavior_accuracy":0.0,"heldout_denotational_assignment_accuracy":0.0,
            "exact_discovery_and_grounding":False,"argument_binding_accuracy":0.0,"polarity_modality_accuracy":0.0,
            "abstention_accuracy":0.0,"slot_coverage":0.0}


def _ref_eval(ref:dict[str,Any])->dict[str,dict[str,tuple[int,int,int]]]:
    out={}
    for key,item in ref["slot_references"].items():
        em=_parse_eval_rows(item["evaluation_probe_expected"],require_unique=True)
        if em is None:raise ValueError("REFERENCE_EVALUATION_PROBE_INVALID")
        out[str(key)]=em
    return out


def _probe_matches(a,b):return sum(int(a.get(k)==b.get(k)) for k in EVAL_IDS)


def score_task(task:dict[str,Any],prediction:Any,reference:dict[str,Any])->dict[str,Any]:
    if reference.get("authority")!=AUTHORITY:return _fail("REFERENCE_AUTHORITY_INVALID")
    if reference.get("task_id")!=task.get("task_id"):return _fail("REFERENCE_TASK_BINDING_MISMATCH")
    core=validate_schema_core(task,prediction)
    if core.get("valid") is not True:return _fail("SCHEMA_CORE_INVALID_ASSAY_EXECUTION",core)
    semantic=validate_semantic_contract(task,prediction)
    if semantic.get("valid") is not True:return _zero(str(semantic.get("reason")),semantic)

    train_ids=sorted(reference["training_gold"]);gold=[reference["training_gold"][x] for x in train_ids];pred=[semantic["owner"][x] for x in train_ids]
    ar=_ari(gold,pred);pw=_pairwise(gold,pred);gold_keys=sorted(reference["slot_references"]);ge=_ref_eval(reference)
    aligns=[]
    for chosen in itertools.permutations(semantic["slot_ids"],len(gold_keys)):
        mapping={sid:g for sid,g in zip(chosen,gold_keys)};score=0
        for sid,g in mapping.items():
            types_ok=semantic["slot_types"][sid]==tuple(reference["slot_references"][g]["arg_types"])
            score+=_probe_matches(semantic["slot_eval"][sid],ge[g]) if types_ok else 0
        aligns.append({"mapping":mapping,"score":score})
    if not aligns:return _fail("NO_ALIGNMENT")
    bestscore=max(x["score"] for x in aligns);best=[x for x in aligns if x["score"]==bestscore]
    vectors=[];details=[]
    for a in best:
        v=[];det={}
        for eid in sorted(reference["heldout"]):
            rr=reference["heldout"][eid]
            if rr["status"]=="AMBIGUOUS":
                ok=eid in semantic["abstain_ids"];v.append(ok);det[eid]={"correct":ok,"status":"AMBIGUOUS"};continue
            row=semantic["assign_by_id"].get(eid)
            if row is None:v.append(False);det[eid]={"correct":False,"reason":"MISSING_ASSIGNMENT"};continue
            den=a["mapping"].get(row["slot_id"])==rr["target_code"];args=list(row["arguments"])==list(rr["arguments"]);pm=row["polarity"]==rr["polarity"] and row["modality"]==rr["modality"]
            ok=den and args and pm;v.append(ok);det[eid]={"correct":ok,"denotation_correct":den,"arguments_correct":args,"polarity_modality_correct":pm}
        vectors.append(tuple(v));details.append(det)
    if len(set(vectors))>1:return _fail("ALIGNMENT_TIE_CHANGES_HELDOUT_CORRECTNESS",{"best_probe_score":bestscore,"vectors":vectors})
    pick=min(range(len(best)),key=lambda i:tuple(sorted(best[i]["mapping"].items())));vec=list(vectors[pick]);det=details[pick]
    unseen=bestscore/(2*len(EVAL_IDS));held=sum(map(int,vec))/len(vec)
    normals=[e for e,r in reference["heldout"].items() if r["status"]=="OK"];amb=[e for e,r in reference["heldout"].items() if r["status"]=="AMBIGUOUS"]
    return {"pass":True,"terminal":"S1C_V32_SCORE_COMPLETE","schema_core_valid":True,"semantic_output_validity":1.0,"prediction_valid":True,"prediction_reason":"VALID",
            "training_partition_adjusted_rand_index":ar,"training_partition_pairwise_accuracy":pw,"unseen_probe_behavior_accuracy":unseen,
            "heldout_denotational_assignment_accuracy":held,"exact_discovery_and_grounding":bool(len(semantic["slot_ids"])==2 and ar==1.0 and unseen==1.0 and held==1.0),
            "argument_binding_accuracy":sum(int(det[e].get("arguments_correct",False)) for e in normals)/len(normals),
            "polarity_modality_accuracy":sum(int(det[e].get("polarity_modality_correct",False)) for e in normals)/len(normals),
            "abstention_accuracy":sum(int(det[e].get("correct",False)) for e in amb)/len(amb),
            "slot_coverage":len(semantic["owner"])/len(train_ids)}


def aggregate(tasks:list[dict[str,Any]],predictions:dict[str,Any],references:dict[str,Any])->dict[str,Any]:
    rows=[]
    for task in tasks:
        tid=str(task["task_id"]);ref=references.get(tid)
        if not isinstance(ref,dict):return _fail("REFERENCE_MISSING",tid)
        row=score_task(task,predictions.get(tid),ref);rows.append({"task_id":tid,**row})
        if row.get("pass") is not True:return {"protocol":PROTOCOL,"pass":False,"terminal":"S1C_V32_SCORER_FAIL_CLOSED","failed_task_id":tid,"rows":rows}
    n=len(rows)
    return {"protocol":PROTOCOL,"pass":True,"terminal":"S1C_V32_SCORE_COMPLETE","task_count":n,
            "primary":{
              "semantic_output_validity_rate":sum(r["semantic_output_validity"] for r in rows)/n,
              "training_partition_adjusted_rand_index":sum(r["training_partition_adjusted_rand_index"] for r in rows)/n,
              "unseen_probe_behavior_accuracy":sum(r["unseen_probe_behavior_accuracy"] for r in rows)/n,
              "heldout_denotational_assignment_accuracy":sum(r["heldout_denotational_assignment_accuracy"] for r in rows)/n,
              "exact_discovery_and_grounding_rate":sum(int(r["exact_discovery_and_grounding"]) for r in rows)/n},
            "secondary":{
              "training_partition_pairwise_accuracy":sum(r["training_partition_pairwise_accuracy"] for r in rows)/n,
              "argument_binding_accuracy":sum(r["argument_binding_accuracy"] for r in rows)/n,
              "polarity_modality_accuracy":sum(r["polarity_modality_accuracy"] for r in rows)/n,
              "abstention_accuracy":sum(r["abstention_accuracy"] for r in rows)/n,
              "slot_coverage":sum(r["slot_coverage"] for r in rows)/n},
            "semantic_invalid_tasks":[{"task_id":r["task_id"],"reason":r["prediction_reason"]} for r in rows if r["semantic_output_validity"]==0.0],
            "rows":rows}


__all__=["PROTOCOL","aggregate","score_task","validate_schema_core","validate_semantic_contract"]
