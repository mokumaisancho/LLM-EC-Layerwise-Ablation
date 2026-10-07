from __future__ import annotations
import argparse, itertools, json, hashlib
from pathlib import Path
from typing import Any

PROTOCOL="S1C_V3_CORPUS_GENERATOR_V1"
STATES=list(itertools.product((0,1), repeat=3))

def r0(s): a,b,c=s; return (1,b,c)
def r1(s): a,b,c=s; return (0,b,c)
def r2(s): a,b,c=s; return (a,1,c)
def r3(s): a,b,c=s; return (a,0,c)
def r4(s): a,b,c=s; return (a,b,1)
def r5(s): a,b,c=s; return (a,b,0)
def r6(s): a,b,c=s; return (1-a,b,c)
def r7(s): a,b,c=s; return (a,1-b,c)
def r8(s): a,b,c=s; return (a,b,1-c)
RULES=[r0,r1,r2,r3,r4,r5,r6,r7,r8]

STRUCTURE={
 "stage":"SEMANTIC_PARTITION_DISCOVERY",
 "visible_slot_inventory":False,
 "training_examples":4,
 "unknown_partition_classes":True,
 "behavior_supervision":"DISTINCT_PARTIAL_TRANSITION_PROBES",
 "per_example_probe_count":2,
 "heldout_behavior_visible":False,
 "heldout_transfer":"RAW_LANGUAGE_TO_DISCOVERED_LOCAL_SLOT",
 "ambiguity_case":True,
}

TASKS=[
 {"id":"V301","family":"coupling","arg_types":["T01","T02"],"rules":[0,1],"probe_sets":[[0,1],[2,6],[0,2],[0,3]],
  "a_train":["couples with","binds alongside"],"a_held":"links together with",
  "b_train":["decouples from","breaks coupling with"],"b_held":"separates cleanly from"},
 {"id":"V302","family":"reservation","arg_types":["T01"],"rules":[0,2],"probe_sets":[[0,1],[2,6],[0,4],[2,3]],
  "a_train":["reserves","holds in reserve"],"a_held":"may be set aside","a_modality":"POSSIBLE",
  "b_train":["unreserves","releases reservation on"],"b_held":"is freed from reservation"},
 {"id":"V303","family":"handoff","arg_types":["T01","T02"],"rules":[1,2],"probe_sets":[[0,1],[0,2],[0,4],[2,3]],
  "a_train":["hands control to","passes control toward"],"a_held":"transfers control to",
  "b_train":["takes control back from","recovers control from"],"b_held":"reclaims control from"},
 {"id":"V304","family":"visibility","arg_types":["T01"],"rules":[3,4],"probe_sets":[[0,1],[0,4],[0,2],[0,7]],
  "a_train":["reveals","makes visible"],"a_held":"shows openly",
  "b_train":["conceals","masks from view"],"b_held":"is not kept hidden","b_polarity":"NEG"},
 {"id":"V305","family":"mounting","arg_types":["T01","T02"],"rules":[3,5],"probe_sets":[[0,1],[0,4],[0,6],[1,3]],
  "a_train":["mounts on","attaches as a mount to"],"a_held":"is mounted onto",
  "b_train":["unmounts from","removes the mount from"],"b_held":"is detached as a mount from"},
 {"id":"V306","family":"subscription","arg_types":["T01"],"rules":[4,5],"probe_sets":[[0,1],[0,2],[0,4],[0,6]],
  "a_train":["subscribes","enrolls for updates"],"a_held":"must opt into updates","a_modality":"REQUIRED",
  "b_train":["unsubscribes","leaves the update feed"],"b_held":"opts out of updates"},
 {"id":"V307","family":"pairing","arg_types":["T01","T02"],"rules":[6,7],"probe_sets":[[0,1],[2,4],[0,4],[2,3]],
  "a_train":["pairs with","forms a pair with"],"a_held":"is paired to",
  "b_train":["unpairs from","dissolves the pair with"],"b_held":"is no longer paired with"},
 {"id":"V308","family":"marking","arg_types":["T01"],"rules":[6,8],"probe_sets":[[0,1],[2,4],[0,2],[0,3]],
  "a_train":["marks","places a mark on"],"a_held":"labels as marked",
  "b_train":["unmarks","clears the mark on"],"b_held":"removes the mark"},
]

def observations(rule:int, probe_set:list[int])->list[dict[str,Any]]:
    return [{"probe_id":f"Q{i:02d}","before":list(STATES[i]),"after":list(RULES[rule](STATES[i]))} for i in probe_set]

def registry(prefix:str,arg_types:list[str])->dict[str,Any]:
    out={"E01":{"type":arg_types[0],"surface_forms":[f"{prefix} item"]}}
    if len(arg_types)==2:
        out["E02"]={"type":arg_types[1],"surface_forms":[f"{prefix} zone"]}
    return out

def sentence(prefix:str,phrase:str,arg_types:list[str])->str:
    if len(arg_types)==1:
        return f"{prefix} item {phrase}."
    return f"{prefix} item {phrase} {prefix} zone."

def task_from_spec(spec:dict[str,Any])->dict[str,Any]:
    tid=spec["id"]; types=list(spec["arg_types"]); ra,rb=spec["rules"]; ps=spec["probe_sets"]
    training=[]
    rows=[
      ("A1",spec["a_train"][0],ra,ps[0]),
      ("A2",spec["a_train"][1],ra,ps[1]),
      ("B1",spec["b_train"][0],rb,ps[2]),
      ("B2",spec["b_train"][1],rb,ps[3]),
    ]
    for suffix,phrase,rule,subset in rows:
        prefix=f"{tid}{suffix}"
        training.append({"example_id":f"{tid}T{len(training)+1:02d}","raw_text":sentence(prefix,phrase,types),"entity_registry":registry(prefix,types),"behavior_observations":observations(rule,list(subset))})
    held=[]
    for side,phrase in (("A",spec["a_held"]),("B",spec["b_held"])):
        idx=1 if side=="A" else 2; prefix=f"{tid}H{idx}"
        held.append({"example_id":f"{tid}H{idx:02d}","raw_text":sentence(prefix,phrase,types),"entity_registry":registry(prefix,types)})
    prefix=f"{tid}H3"
    amb=f"The evidence is unresolved between: {sentence(prefix,spec['a_held'],types)[:-1]} OR {sentence(prefix,spec['b_held'],types)}"
    held.append({"example_id":f"{tid}H03","raw_text":amb,"entity_registry":registry(prefix,types)})
    return {"task_id":tid,"family":spec["family"],"structural_descriptor":dict(STRUCTURE),
            "visible":{"type_inventory":sorted(set(types)),"training_examples":training,"heldout_examples":held,"slot_count_bound":{"min":1,"max":4}}}

def generate()->list[dict[str,Any]]:
    return [task_from_spec(s) for s in TASKS]

def digest(tasks)->str:
    return hashlib.sha256(json.dumps(tasks,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def build_corpus():
    tasks=generate()
    return {"protocol":PROTOCOL,"task_count":len(tasks),"training_count":sum(len(t["visible"]["training_examples"]) for t in tasks),
            "heldout_count":sum(len(t["visible"]["heldout_examples"]) for t in tasks),"dataset_digest":digest(tasks),"tasks":tasks}

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    out=build_corpus(); args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("protocol","task_count","training_count","heldout_count","dataset_digest")},indent=2))