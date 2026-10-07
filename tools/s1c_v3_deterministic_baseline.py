from __future__ import annotations
import itertools,json,math,re
from collections import Counter
from pathlib import Path
from typing import Any

PROTOCOL="S1C_V3_DETERMINISTIC_DISCOVERY_V1"
TRUTH=json.loads(Path(__file__).resolve().with_name("s1c_v3_reference_truth_tables.json").read_text(encoding="utf-8"))
TOKEN_RE=re.compile(r"[a-z0-9<>]+",re.I)
STOP={"a","an","and","are","as","at","be","been","being","by","for","from","has","have","in","is","it","of","on","or","that","the","their","there","this","to","was","were","which","with","while"}

def norm(s): return re.sub(r"\s+"," ",s.lower().replace("_"," ").replace("-"," ")).strip()
def tokens(s): return [x for x in TOKEN_RE.findall(norm(s)) if x not in STOP]
def char3(s):
    s=norm(s); return Counter(s[i:i+3] for i in range(max(0,len(s)-2)))
def cosine(a,b):
    if not a or not b:return 0.0
    dot=sum(v*b.get(k,0.0) for k,v in a.items()); na=math.sqrt(sum(v*v for v in a.values())); nb=math.sqrt(sum(v*v for v in b.values()))
    return dot/(na*nb) if na and nb else 0.0
def similarities(query,docs):
    all_docs=docs+[query]; tfs=[Counter(tokens(x)) for x in all_docs]; df=Counter()
    for row in tfs:
        for term in row: df[term]+=1
    n=len(all_docs); idf={k:math.log((n+1)/(v+1))+1 for k,v in df.items()}
    q={k:v*idf[k] for k,v in tfs[-1].items()}; q3=char3(query); out=[]
    for text,row in zip(docs,tfs[:-1]):
        d={k:v*idf[k] for k,v in row.items()}
        out.append(0.70*cosine(q,d)+0.30*cosine(q3,char3(text)))
    return out

def obs_candidates(obs):
    out=set()
    for rid,table in TRUTH.items():
        if all(table.get("".join(map(str,o["before"])))=="".join(map(str,o["after"])) for o in obs): out.add(int(rid))
    return out

def discover_partition(train):
    pairings=[((0,1),(2,3)),((0,2),(1,3)),((0,3),(1,2))]
    valid=[]
    for pairing in pairings:
        rules=[]; ok=True
        for pair in pairing:
            obs=[]
            for i in pair: obs.extend(train[i]["behavior_observations"])
            c=obs_candidates(obs)
            if len(c)!=1:ok=False;break
            rules.append(next(iter(c)))
        if ok and rules[0]!=rules[1]: valid.append((pairing,rules))
    if len(valid)!=1:return None
    pairing,rules=valid[0]
    groups=[]
    for pair,rule in zip(pairing,rules):
        members=sorted(train[i]["example_id"] for i in pair)
        groups.append((members,rule,pair))
    groups.sort(key=lambda x:x[0])
    return groups

def mask_entities(text,registry):
    out=text
    reps=[]
    for eid,item in registry.items():
        typ=item.get("type")
        for form in item.get("surface_forms",[]): reps.append((len(str(form)),str(form),f"<{typ}>"))
    for _,form,repl in sorted(reps,key=lambda x:(-x[0],x[1].lower())):
        out=re.sub(re.escape(form),repl,out,flags=re.I)
    return norm(out)

def arg_types_for(ex):
    return [ex["entity_registry"][eid]["type"] for eid in sorted(ex["entity_registry"])]

def bind_args(text,registry,arg_types):
    low=text.lower(); bytype={}
    for eid,item in registry.items():
        poss=[low.find(str(f).lower()) for f in item.get("surface_forms",[]) if str(f) and low.find(str(f).lower())>=0]
        if poss: bytype.setdefault(item["type"],[]).append((min(poss),eid))
    for t in bytype: bytype[t].sort()
    args=[]; used=set()
    for t in arg_types:
        pool=[eid for _,eid in bytype.get(t,[]) if eid not in used]
        if not pool:return None
        args.append(pool[0]);used.add(pool[0])
    return args

def polarity_modality(text):
    low=norm(text)
    pol="NEG" if re.search(r"\b(not|no|never|cannot|does not|do not|isn't|isnt)\b",low) else "POS"
    if re.search(r"\b(must|required|requires|shall|needs to|need to)\b",low): mod="REQUIRED"
    elif re.search(r"\b(may|might|could|possible|possibly)\b",low): mod="POSSIBLE"
    else: mod="ASSERTED"
    return pol,mod

def ambiguous(text):
    low=norm(text)
    return "unresolved between" in low or "unclear whether" in low or ("either" in low and " or " in f" {low} ")

def predict(task):
    v=task["visible"]; train=v["training_examples"]; held=v["heldout_examples"]
    groups=discover_partition(train)
    if groups is None:
        return {"discovered_slots":[{"slot_id":"S01","arg_types":[],"training_members":[x["example_id"] for x in train]}],"heldout_assignments":[],"abstentions":[{"example_id":x["example_id"],"status":"AMBIGUOUS"} for x in held]}
    slots=[]; docs=[]; slot_types={}
    for i,(members,_rule,pair) in enumerate(groups,1):
        sid=f"S{i:02d}"; types=arg_types_for(train[pair[0]])
        slots.append({"slot_id":sid,"arg_types":types,"training_members":members}); slot_types[sid]=types
        docs.append(" ".join(mask_entities(train[j]["raw_text"],train[j]["entity_registry"]) for j in pair))
    assigns=[]; abst=[]
    sids=[s["slot_id"] for s in slots]
    for ex in held:
        eid=ex["example_id"]; raw=ex["raw_text"]
        if ambiguous(raw):
            abst.append({"example_id":eid,"status":"AMBIGUOUS"});continue
        q=mask_entities(raw,ex["entity_registry"]); scores=similarities(q,docs); ranked=sorted(zip(scores,sids),key=lambda x:(-x[0],x[1]))
        if not ranked or ranked[0][0]<=0 or (len(ranked)>1 and abs(ranked[0][0]-ranked[1][0])<=1e-12):
            abst.append({"example_id":eid,"status":"AMBIGUOUS"});continue
        sid=ranked[0][1]; args=bind_args(raw,ex["entity_registry"],slot_types[sid])
        if args is None:
            abst.append({"example_id":eid,"status":"AMBIGUOUS"});continue
        pol,mod=polarity_modality(raw)
        assigns.append({"example_id":eid,"slot_id":sid,"arguments":args,"polarity":pol,"modality":mod})
    return {"discovered_slots":slots,"heldout_assignments":sorted(assigns,key=lambda x:x["example_id"]),"abstentions":sorted(abst,key=lambda x:x["example_id"])}

def manifest():
    return {"protocol":PROTOCOL,"oracle_visible":False,"family_visible":False,"canonical_slot_visible":False,
            "partition_method":"enumerate all 3 pairings; accept only unique pairing where each pair's union of partial behavior observations identifies one distinct transition rule",
            "heldout_method":"entity-masked lexical retrieval to discovered slot member texts","post_result_tuning":False}