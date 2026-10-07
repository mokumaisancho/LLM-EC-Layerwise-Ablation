from __future__ import annotations
import argparse,hashlib,itertools,json
from pathlib import Path
from typing import Any

PROTOCOL="S1C_V3_INDEPENDENT_POSTRUN_AUDIT_V1"
EXPECTED_RUNTIME="FUNCTION_BOUNDARY_S1C_V3_PAIRED_V1"
TRUTH=json.loads(Path(__file__).resolve().with_name("s1c_v3_reference_truth_tables.json").read_text(encoding="utf-8"))

def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"))
def sha(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def raw_sha(s): return hashlib.sha256(s.encode()).hexdigest()

def fail(reason,detail=None):
    return {"protocol":PROTOCOL,"pass":False,"terminal":"S1C_V3_POSTRUN_AUDIT_FAIL_CLOSED","reason":reason,"detail":detail,"model_reinference":False}

def candidates(obs):
    out=set()
    for rid,table in TRUTH.items():
        if all(table.get("".join(map(str,o["before"])))=="".join(map(str,o["after"])) for o in obs):
            out.add(int(rid))
    return out

def parse_shape(task,pred):
    train={x["example_id"] for x in task["visible"]["training_examples"]}; held={x["example_id"] for x in task["visible"]["heldout_examples"]}
    if not isinstance(pred,dict) or set(pred)!={"discovered_slots","heldout_assignments","abstentions"}: return None
    slots=pred["discovered_slots"]; assigns=pred["heldout_assignments"]; abst=pred["abstentions"]
    if not all(isinstance(x,list) for x in (slots,assigns,abst)) or not (1<=len(slots)<=4): return None
    owner={}; sm={}; st={}
    for s in slots:
        if not isinstance(s,dict) or set(s)!={"slot_id","arg_types","training_members"}: return None
        sid=s.get("slot_id")
        if not isinstance(sid,str) or not sid or sid in sm: return None
        if not isinstance(s.get("arg_types"),list) or not isinstance(s.get("training_members"),list) or not s["training_members"]: return None
        members=[]
        for mid in map(str,s["training_members"]):
            if mid not in train or mid in owner: return None
            owner[mid]=sid; members.append(mid)
        sm[sid]=members; st[sid]=tuple(map(str,s["arg_types"]))
    if set(owner)!=train: return None
    amap={}
    for a in assigns:
        if not isinstance(a,dict) or set(a)!={"example_id","slot_id","arguments","polarity","modality"}: return None
        eid=str(a.get("example_id"))
        if eid not in held or eid in amap or a.get("slot_id") not in sm: return None
        amap[eid]=a
    abstain=set()
    for a in abst:
        if not isinstance(a,dict) or set(a)!={"example_id","status"} or a.get("status")!="AMBIGUOUS": return None
        eid=str(a.get("example_id"))
        if eid not in held or eid in abstain or eid in amap: return None
        abstain.add(eid)
    if set(amap)|abstain != held: return None
    return owner,sm,st,amap,abstain

def recompute_task(task,pred,ref):
    shape=parse_shape(task,pred)
    if shape is None:
        return {"prediction_valid":False,"partition":0.0,"heldout":0.0,"exact":False,"slot_purity":0.0,"slot_coverage":0.0,"abstention":0.0}
    owner,sm,st,amap,abstain=shape
    byid={x["example_id"]:x for x in task["visible"]["training_examples"]}
    align={}
    pure=0
    for sid,members in sm.items():
        obs=[o for mid in members for o in byid[mid]["behavior_observations"]]
        c=candidates(obs)
        if len(c)==1:
            align[sid]=(next(iter(c)),st[sid]); pure+=len(members)
    gold={eid:(int(v["rule"]),tuple(v["arg_types"])) for eid,v in ref["training_semantics"].items()}
    ids=sorted(owner)
    total=good=0
    for a,b in itertools.combinations(ids,2):
        good+=int((owner[a]==owner[b])==(gold[a]==gold[b])); total+=1
    partition=good/total if total else 1.0
    hc=0; abn=abd=0
    for eid,r in ref["heldout_semantics"].items():
        if r["status"]=="AMBIGUOUS":
            abd+=1; ok=eid in abstain; abn+=int(ok); hc+=int(ok); continue
        a=amap.get(eid)
        if not a: continue
        key=align.get(a["slot_id"])
        exp=(int(r["rule"]),tuple(r["arg_types"]))
        ok=(key==exp and list(a.get("arguments",[]))==list(r["arguments"]) and a.get("polarity")==r["polarity"] and a.get("modality")==r["modality"])
        hc+=int(ok)
    held=hc/len(ref["heldout_semantics"])
    exact=(partition==1.0 and held==1.0 and pure==len(ids) and len(align)==len(sm))
    return {"prediction_valid":True,"partition":partition,"heldout":held,"exact":exact,"slot_purity":pure/len(ids),"slot_coverage":len(owner)/len(ids),"abstention":abn/abd if abd else None}

def aggregate(tasks,preds,refs):
    rows=[]
    for t in tasks:
        tid=t["task_id"]; rows.append({"task_id":tid,**recompute_task(t,preds.get(tid),refs[tid])})
    n=len(rows)
    return {"primary":{
      "training_partition_pairwise_accuracy":sum(r["partition"] for r in rows)/n,
      "heldout_denotational_assignment_accuracy":sum(r["heldout"] for r in rows)/n,
      "exact_discovery_and_grounding_rate":sum(int(r["exact"]) for r in rows)/n},
      "secondary":{
       "slot_purity":sum(r["slot_purity"] for r in rows)/n,
       "slot_coverage":sum(r["slot_coverage"] for r in rows)/n,
       "abstention_accuracy":sum(r["abstention"] for r in rows if r["abstention"] is not None)/max(1,sum(r["abstention"] is not None for r in rows))},
      "rows":rows}

def common_prefix(strings,min_len=24):
    if not strings: return ""
    p=strings[0]
    for s in strings[1:]:
        i=0; m=min(len(p),len(s))
        while i<m and p[i]==s[i]: i+=1
        p=p[:i]
        if len(p)<min_len: break
    return p

def audit(runtime,corpus,oracle_validation):
    if runtime.get("protocol")!=EXPECTED_RUNTIME: return fail("RUNTIME_PROTOCOL_MISMATCH")
    if oracle_validation.get("terminal")!="S1C_V3_ORACLE_VALIDATION_PASS" or oracle_validation.get("pass") is not True: return fail("ORACLE_VALIDATION_NOT_PASS")
    tasks=corpus["tasks"]; refs=oracle_validation["references"]; tids={t["task_id"] for t in tasks}
    if runtime.get("dataset_digest")!=corpus.get("dataset_digest"): return fail("DATASET_DIGEST_MISMATCH")
    rows=runtime.get("raw_qwen_rows")
    if not isinstance(rows,list) or len(rows)!=len(tasks): return fail("RAW_ROW_COUNT_MISMATCH")
    qpred={}; invalid_raw=[]; seen=set()
    for row in rows:
        tid=row.get("task_id")
        if tid not in tids or tid in seen: return fail("RAW_TASK_ID_INVALID_OR_DUPLICATE",tid)
        seen.add(tid); raw=row.get("raw")
        if not isinstance(raw,str) or raw_sha(raw)!=row.get("raw_sha256"): return fail("RAW_HASH_MISMATCH",tid)
        task=next(t for t in tasks if t["task_id"]==tid)
        vh=sha(task["visible"])
        if row.get("visible_sha256")!=vh or runtime.get("visible_hashes",{}).get(tid)!=vh: return fail("VISIBLE_HASH_MISMATCH",tid)
        parsed=None
        try:
            x=json.loads(raw)
            if isinstance(x,dict): parsed=x
        except Exception: pass
        if parsed!=row.get("prediction"): return fail("RAW_REPARSE_MISMATCH",tid)
        if parsed is None: invalid_raw.append(raw)
        qpred[tid]=parsed
    invalid_rate=len(invalid_raw)/len(tasks)
    if invalid_rate>=0.25:
        p=common_prefix(invalid_raw)
        return fail("PARSER_FAILURE_RATE_GTE_0P25",{"invalid_rate":invalid_rate,"common_prefix":p[:160]})
    if len(invalid_raw)>=2:
        p=common_prefix(invalid_raw)
        if len(p)>=24: return fail("COMMON_PREFIX_TRUNCATION",{"prefix":p[:160],"count":len(invalid_raw)})
    dpred=runtime.get("deterministic_predictions")
    if not isinstance(dpred,dict) or set(dpred)!=tids: return fail("DETERMINISTIC_PREDICTION_COVERAGE")
    det=aggregate(tasks,dpred,refs); q=aggregate(tasks,qpred,refs)
    arms=runtime.get("arms") or {}
    for name,recomputed in (("deterministic",det),("qwen25_1p5b",q)):
        stored=arms.get(name) or {}
        if stored.get("primary")!=recomputed["primary"] or stored.get("secondary")!=recomputed["secondary"]:
            return fail("METRIC_RECOMPUTATION_MISMATCH",name)
    return {"protocol":PROTOCOL,"pass":True,"terminal":"S1C_V3_POSTRUN_AUDIT_PASS","invalid_qwen_rate":invalid_rate,
            "deterministic":det,"qwen25_1p5b":q,"result_overturning_gate_failures":0,"model_reinference":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("runtime",type=Path); ap.add_argument("corpus",type=Path); ap.add_argument("oracle",type=Path); ap.add_argument("--output",type=Path); args=ap.parse_args()
    runtime=json.loads(args.runtime.read_text(encoding="utf-8")); corpus=json.loads(args.corpus.read_text(encoding="utf-8")); oracle=json.loads(args.oracle.read_text(encoding="utf-8")); out=audit(runtime,corpus,oracle)
    if args.output: args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out.get(k) for k in ("protocol","pass","terminal","reason","invalid_qwen_rate")},indent=2)); raise SystemExit(0 if out.get("pass") else 3)