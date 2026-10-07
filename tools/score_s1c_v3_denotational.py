from __future__ import annotations
import itertools, json
from pathlib import Path
from typing import Any

PROTOCOL="S1C_V3_INDEPENDENT_DENOTATIONAL_SCORER_V1"
ALLOWED_POLARITY={"POS","NEG"}
ALLOWED_MODALITY={"ASSERTED","REQUIRED","POSSIBLE"}
TRUTH=json.loads(Path(__file__).resolve().with_name("s1c_v3_reference_truth_tables.json").read_text(encoding="utf-8"))

def obs_candidates(observations:list[dict[str,Any]])->set[int]:
    out=set()
    for rid,table in TRUTH.items():
        ok=True
        for o in observations:
            before="".join(map(str,o["before"]))
            after="".join(map(str,o["after"]))
            if table.get(before)!=after:
                ok=False; break
        if ok: out.add(int(rid))
    return out

def _visible_ids(task):
    v=task["visible"]
    return ({str(x["example_id"]) for x in v["training_examples"]},
            {str(x["example_id"]) for x in v["heldout_examples"]})

def validate_prediction(task,pred):
    train_ids,held_ids=_visible_ids(task)
    if not isinstance(pred,dict):
        return {"valid":False,"reason":"NOT_OBJECT"}
    if set(pred)!={"discovered_slots","heldout_assignments","abstentions"}:
        return {"valid":False,"reason":"WRONG_KEYS"}
    slots=pred["discovered_slots"]; assigns=pred["heldout_assignments"]; abst=pred["abstentions"]
    if not all(isinstance(x,list) for x in (slots,assigns,abst)):
        return {"valid":False,"reason":"TOP_LEVEL_NOT_LISTS"}
    if not (1<=len(slots)<=4):
        return {"valid":False,"reason":"SLOT_COUNT_OUT_OF_BOUND"}
    owner={}; slot_members={}; slot_types={}
    for s in slots:
        if not isinstance(s,dict) or set(s)!={"slot_id","arg_types","training_members"}:
            return {"valid":False,"reason":"INVALID_SLOT_SHAPE"}
        sid=s["slot_id"]
        if not isinstance(sid,str) or not sid or sid in slot_members:
            return {"valid":False,"reason":"INVALID_OR_DUPLICATE_SLOT_ID"}
        types=s["arg_types"]; members=s["training_members"]
        if not isinstance(types,list) or not all(isinstance(x,str) and x for x in types):
            return {"valid":False,"reason":"INVALID_ARG_TYPES"}
        if not isinstance(members,list) or not members:
            return {"valid":False,"reason":"INVALID_MEMBERS"}
        sm=[]
        for x in members:
            mid=str(x)
            if mid not in train_ids or mid in owner:
                return {"valid":False,"reason":"MEMBER_UNKNOWN_OR_DUPLICATE"}
            owner[mid]=sid; sm.append(mid)
        slot_members[sid]=sm; slot_types[sid]=tuple(types)
    if set(owner)!=train_ids:
        return {"valid":False,"reason":"TRAIN_PARTITION_INCOMPLETE"}
    assignment={}
    for a in assigns:
        if not isinstance(a,dict) or set(a)!={"example_id","slot_id","arguments","polarity","modality"}:
            return {"valid":False,"reason":"INVALID_ASSIGNMENT_SHAPE"}
        eid=str(a["example_id"])
        if eid not in held_ids or eid in assignment:
            return {"valid":False,"reason":"HELDOUT_ASSIGNMENT_UNKNOWN_OR_DUPLICATE"}
        if a["slot_id"] not in slot_members:
            return {"valid":False,"reason":"UNKNOWN_SLOT"}
        if not isinstance(a["arguments"],list) or not all(isinstance(x,str) for x in a["arguments"]):
            return {"valid":False,"reason":"INVALID_ARGUMENTS"}
        if a["polarity"] not in ALLOWED_POLARITY or a["modality"] not in ALLOWED_MODALITY:
            return {"valid":False,"reason":"INVALID_POLARITY_MODALITY"}
        assignment[eid]=a
    abstain=set()
    for a in abst:
        if not isinstance(a,dict) or set(a)!={"example_id","status"} or a.get("status")!="AMBIGUOUS":
            return {"valid":False,"reason":"INVALID_ABSTENTION"}
        eid=str(a["example_id"])
        if eid not in held_ids or eid in abstain or eid in assignment:
            return {"valid":False,"reason":"ABSTENTION_UNKNOWN_DUPLICATE_OR_CONFLICT"}
        abstain.add(eid)
    if set(assignment)|abstain != held_ids:
        return {"valid":False,"reason":"HELDOUT_COVERAGE_INCOMPLETE"}
    return {"valid":True,"reason":"VALID","owner":owner,"slot_members":slot_members,"slot_types":slot_types,"assignment":assignment,"abstain":abstain}

def align_slots(task,shape):
    by_id={str(x["example_id"]):x for x in task["visible"]["training_examples"]}
    alignment={}; details={}
    for sid,members in shape["slot_members"].items():
        merged=[]
        for mid in members:
            merged.extend(by_id[mid]["behavior_observations"])
        c=obs_candidates(merged)
        if len(c)!=1:
            details[sid]={"aligned":False,"reason":"DENOTATION_NOT_UNIQUE","candidate_rules":sorted(c)}
            continue
        rule=next(iter(c))
        alignment[sid]=(rule,shape["slot_types"][sid])
        details[sid]={"aligned":True,"rule":rule,"arg_types":list(shape["slot_types"][sid]),"truth_table":TRUTH[str(rule)]}
    return alignment,details

def pairwise_accuracy(ids,owner,gold_key):
    good=total=0
    for a,b in itertools.combinations(sorted(ids),2):
        good += int((owner[a]==owner[b]) == (gold_key[a]==gold_key[b]))
        total += 1
    return (good/total if total else 1.0,good,total)

def zero(reason):
    return {"pass":True,"terminal":"S1C_V3_SCORE_COMPLETE","prediction_valid":False,"prediction_reason":reason,
            "training_partition_pairwise_accuracy":0.0,"heldout_denotational_assignment_accuracy":0.0,
            "exact_discovery_and_grounding":False,"argument_binding_accuracy":0.0,
            "polarity_modality_accuracy":0.0,"abstention_accuracy":0.0,"slot_purity":0.0,"slot_coverage":0.0}

def score_task(task,pred,reference):
    if reference.get("authority")!="S1C_V3_INDEPENDENT_ORACLE_VALIDATOR_V1":
        return {"pass":False,"terminal":"S1C_V3_SCORER_FAIL_CLOSED","reason":"REFERENCE_AUTHORITY_INVALID"}
    shape=validate_prediction(task,pred)
    if not shape["valid"]: return zero(shape["reason"])
    train_ids,held_ids=_visible_ids(task)
    gold={str(k):(int(v["rule"]),tuple(v["arg_types"])) for k,v in reference["training_semantics"].items()}
    if set(gold)!=train_ids:
        return {"pass":False,"terminal":"S1C_V3_SCORER_FAIL_CLOSED","reason":"TRAIN_REFERENCE_COVERAGE_MISMATCH"}
    pair,pn,pd=pairwise_accuracy(train_ids,shape["owner"],gold)
    alignment,detail=align_slots(task,shape)
    pure=sum(len(shape["slot_members"][sid]) for sid in alignment)
    purity=pure/len(train_ids)
    coverage=len(shape["owner"])/len(train_ids)

    held_correct=arg_num=arg_den=pm_num=pm_den=ab_num=ab_den=0
    rows=[]
    for eid in sorted(held_ids):
        ref=reference["heldout_semantics"][eid]
        if ref["status"]=="AMBIGUOUS":
            ab_den+=1; ok=eid in shape["abstain"]; ab_num+=int(ok); held_correct+=int(ok)
            rows.append({"example_id":eid,"correct":ok,"reason":"AMBIGUOUS" if ok else "ABSTENTION_FAIL"}); continue
        row=shape["assignment"].get(eid)
        if row is None:
            rows.append({"example_id":eid,"correct":False,"reason":"MISSING_ASSIGNMENT"}); continue
        key=alignment.get(row["slot_id"])
        expected=(int(ref["rule"]),tuple(ref["arg_types"]))
        den_ok=(key==expected)
        args_ok=list(row["arguments"])==list(ref["arguments"])
        pm_ok=row["polarity"]==ref["polarity"] and row["modality"]==ref["modality"]
        arg_den+=1; arg_num+=int(args_ok); pm_den+=1; pm_num+=int(pm_ok)
        ok=den_ok and args_ok and pm_ok; held_correct+=int(ok)
        rows.append({"example_id":eid,"correct":ok,"denotation_correct":den_ok,"arguments_correct":args_ok,"polarity_modality_correct":pm_ok})
    held_acc=held_correct/len(held_ids) if held_ids else 1.0
    exact=(pair==1.0 and held_acc==1.0 and purity==1.0 and coverage==1.0 and len(alignment)==len(shape["slot_members"]))
    return {"pass":True,"terminal":"S1C_V3_SCORE_COMPLETE","prediction_valid":True,"prediction_reason":"VALID",
            "training_partition_pairwise_accuracy":pair,"training_partition_pairwise_correct":pn,"training_partition_pairwise_total":pd,
            "heldout_denotational_assignment_accuracy":held_acc,"heldout_correct":held_correct,"heldout_total":len(held_ids),
            "exact_discovery_and_grounding":exact,"argument_binding_accuracy":arg_num/arg_den if arg_den else None,
            "polarity_modality_accuracy":pm_num/pm_den if pm_den else None,
            "abstention_accuracy":ab_num/ab_den if ab_den else None,"slot_purity":purity,"slot_coverage":coverage,
            "slot_alignment":detail,"heldout_rows":rows}

def aggregate(tasks,predictions,references):
    rows=[]
    for task in tasks:
        tid=task["task_id"]; rows.append({"task_id":tid,**score_task(task,predictions.get(tid),references[tid])})
    if any(r.get("pass") is not True for r in rows):
        return {"protocol":PROTOCOL,"pass":False,"terminal":"S1C_V3_SCORER_FAIL_CLOSED","rows":rows}
    n=len(rows)
    def avg(k): return sum(float(r[k]) for r in rows)/n if n else 0.0
    abst=[r["abstention_accuracy"] for r in rows if r["abstention_accuracy"] is not None]
    return {"protocol":PROTOCOL,"pass":True,"terminal":"S1C_V3_SCORE_COMPLETE","task_count":n,
            "primary":{"training_partition_pairwise_accuracy":avg("training_partition_pairwise_accuracy"),
                       "heldout_denotational_assignment_accuracy":avg("heldout_denotational_assignment_accuracy"),
                       "exact_discovery_and_grounding_rate":sum(int(r["exact_discovery_and_grounding"]) for r in rows)/n if n else 0.0},
            "secondary":{"slot_purity":avg("slot_purity"),"slot_coverage":avg("slot_coverage"),
                         "abstention_accuracy":sum(abst)/len(abst) if abst else None},
            "rows":rows}