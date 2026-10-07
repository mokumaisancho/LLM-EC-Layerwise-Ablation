from __future__ import annotations
import argparse,itertools,json,hashlib,re
from pathlib import Path
from typing import Any

AUTHORITY="S1C_V3_INDEPENDENT_ORACLE_VALIDATOR_V1"
TRUTH=json.loads(Path(__file__).resolve().with_name("s1c_v3_reference_truth_tables.json").read_text(encoding="utf-8"))
CONTRACT=json.loads((Path(__file__).resolve().parents[1]/"docs"/"S1C_V3_DENOTATIONAL_DISCOVERY_CONTRACT_2026-10-07.json").read_text(encoding="utf-8"))

# Independent phrase/reference specification. Generator is not imported.
SPEC={
 "V301":{"arg_types":["T01","T02"],0:["couples with","binds alongside","links together with"],1:["decouples from","breaks coupling with","separates cleanly from"]},
 "V302":{"arg_types":["T01"],0:["reserves","holds in reserve","may be set aside"],2:["unreserves","releases reservation on","is freed from reservation"]},
 "V303":{"arg_types":["T01","T02"],1:["hands control to","passes control toward","transfers control to"],2:["takes control back from","recovers control from","reclaims control from"]},
 "V304":{"arg_types":["T01"],3:["reveals","makes visible","shows openly"],4:["conceals","masks from view","is not kept hidden"]},
 "V305":{"arg_types":["T01","T02"],3:["mounts on","attaches as a mount to","is mounted onto"],5:["unmounts from","removes the mount from","is detached as a mount from"]},
 "V306":{"arg_types":["T01"],4:["subscribes","enrolls for updates","must opt into updates"],5:["unsubscribes","leaves the update feed","opts out of updates"]},
 "V307":{"arg_types":["T01","T02"],6:["pairs with","forms a pair with","is paired to"],7:["unpairs from","dissolves the pair with","is no longer paired with"]},
 "V308":{"arg_types":["T01"],6:["marks","places a mark on","labels as marked"],8:["unmarks","clears the mark on","removes the mark"]},
}
PRIOR_STRUCTURES=[
 {"stage":"RAW_LANGUAGE_GROUNDING","visible_slot_inventory":True,"training_examples":"DEMONSTRATIONS","behavior_supervision":"TYPED_IR"},
 {"stage":"OPERATOR_INDUCTION","visible_slot_inventory":True,"behavior_supervision":"STATE_TRANSITIONS","heldout_transfer":"OPERATOR_SCHEMA"},
 {"stage":"SCHEMA_SYNTHESIS","visible_slot_inventory":True,"behavior_supervision":"TYPED_EXAMPLES","heldout_transfer":"SCHEMA"},
 {"stage":"GRAPH_GROUNDING","visible_slot_inventory":True,"behavior_supervision":"GRAPH_LABELS","heldout_transfer":"GRAPH_IR"},
]

def norm(s:str)->str:
    return " ".join(s.lower().split())

def infer_rules(tid:str,text:str)->set[int]:
    low=norm(text); found=set()
    for k,phrases in SPEC[tid].items():
        if k=="arg_types": continue
        for p in phrases:
            cue=norm(p)
            if re.search(r"(?<!\w)"+re.escape(cue)+r"(?!\w)", low):
                found.add(int(k)); break
    return found

def expected_pm(text:str)->tuple[str,str]:
    low=norm(text)
    polarity="NEG" if " not " in f" {low} " else "POS"
    if " must " in f" {low} ": modality="REQUIRED"
    elif " may " in f" {low} ": modality="POSSIBLE"
    else: modality="ASSERTED"
    return polarity,modality

def obs_candidates(obs:list[dict[str,Any]])->set[int]:
    out=set()
    for rid,table in TRUTH.items():
        if all(table.get("".join(map(str,o["before"])))=="".join(map(str,o["after"])) for o in obs):
            out.add(int(rid))
    return out

def eq_pattern(vals:list[Any])->tuple[bool,...]:
    return tuple(vals[i]==vals[j] for i,j in itertools.combinations(range(len(vals)),2))

def gold_pattern(rules:list[int])->tuple[bool,...]:
    return tuple(rules[i]==rules[j] for i,j in itertools.combinations(range(len(rules)),2))

def validate_task(task:dict[str,Any])->tuple[dict[str,Any],list[dict[str,Any]]]:
    tid=task["task_id"]; failures=[]; v=task["visible"]
    if tid not in SPEC: failures.append({"gate":"TASK_SPEC_UNKNOWN"})
    expected_types=SPEC[tid]["arg_types"]
    if task.get("structural_descriptor")!=CONTRACT["corpus"]["structural_descriptor"] and isinstance(CONTRACT["corpus"]["structural_descriptor"],dict):
        failures.append({"gate":"STRUCTURAL_DESCRIPTOR_MISMATCH"})
    # current contract stores descriptor as string; require exact V3 vector fields instead.
    sd=task.get("structural_descriptor") or {}
    required={"stage":"SEMANTIC_PARTITION_DISCOVERY","visible_slot_inventory":False,"behavior_supervision":"DISTINCT_PARTIAL_TRANSITION_PROBES","heldout_behavior_visible":False,"heldout_transfer":"RAW_LANGUAGE_TO_DISCOVERED_LOCAL_SLOT","ambiguity_case":True}
    if not all(sd.get(k)==val for k,val in required.items()):
        failures.append({"gate":"STRUCTURAL_DESCRIPTOR_INVALID"})
    if any(all(sd.get(k)==val for k,val in p.items()) for p in PRIOR_STRUCTURES):
        failures.append({"gate":"STRUCTURAL_HOLDOUT_REUSE"})

    ser=json.dumps(v,sort_keys=True).lower()
    for forbidden in ('"rule"','"denotation"','"family"','"slot_id"','"oracle"','"semantic_gloss"'):
        if forbidden in ser: failures.append({"gate":"VISIBLE_FORBIDDEN_KEY","key":forbidden})

    train=v["training_examples"]
    if len(train)!=4: failures.append({"gate":"TRAIN_COUNT"})
    rules=[]; bundles=[]; probes=[]; afterseq=[]
    reference_train={}
    for ex in train:
        rs=infer_rules(tid,ex["raw_text"])
        if len(rs)!=1:
            failures.append({"gate":"TRAIN_RAW_TEXT_DENOTATION_NONUNIQUE","id":ex["example_id"],"rules":sorted(rs)}); continue
        rule=next(iter(rs)); rules.append(rule)
        obs=ex.get("behavior_observations")
        if not isinstance(obs,list) or len(obs)!=2:
            failures.append({"gate":"TRAIN_BEHAVIOR_OBSERVATION_COUNT","id":ex["example_id"]}); continue
        cand=obs_candidates(obs)
        if rule not in cand:
            failures.append({"gate":"TRAIN_BEHAVIOR_CONTRADICTS_TEXT","id":ex["example_id"],"text_rule":rule,"candidates":sorted(cand)})
        if len(cand)<2:
            failures.append({"gate":"SINGLE_EXAMPLE_RULE_IDENTIFIED","id":ex["example_id"],"candidates":sorted(cand)})
        bundles.append(hashlib.sha256(json.dumps(obs,sort_keys=True,separators=(",",":")).encode()).hexdigest())
        probes.append(tuple(o["probe_id"] for o in obs))
        afterseq.append(tuple(tuple(o["after"]) for o in obs))
        types=[ex["entity_registry"][eid]["type"] for eid in sorted(ex["entity_registry"])]
        if types!=expected_types: failures.append({"gate":"TRAIN_ARG_TYPES","id":ex["example_id"],"actual":types,"expected":expected_types})
        reference_train[ex["example_id"]]={"rule":rule,"arg_types":expected_types}
    if len(rules)==4:
        gp=gold_pattern(rules)
        if len(set(bundles))!=4: failures.append({"gate":"VISIBLE_EXACT_BEHAVIOR_BUNDLE_REUSE"})
        if len(set(probes))!=4: failures.append({"gate":"VISIBLE_EXACT_PROBE_SET_REUSE"})
        for name,vals in (("bundle",bundles),("probe_set",probes),("after_sequence",afterseq)):
            if eq_pattern(vals)==gp: failures.append({"gate":"VISIBLE_PARTITION_LABEL_EQUIVALENT_FEATURE","feature":name})
        groups={}
        for ex,rule in zip(train,rules): groups.setdefault(rule,[]).append(ex)
        if sorted(len(x) for x in groups.values())!=[2,2]: failures.append({"gate":"TEXT_DERIVED_PARTITION_SHAPE"})
        else:
            for rule,rows in groups.items():
                merged=[o for ex in rows for o in ex["behavior_observations"]]
                c=obs_candidates(merged)
                if c!={rule}: failures.append({"gate":"CORRECT_PAIR_DENOTATION_NOT_UNIQUE","rule":rule,"candidates":sorted(c)})
        valids=[]
        for pairing in [((0,1),(2,3)),((0,2),(1,3)),((0,3),(1,2))]:
            pair_rules=[]; ok=True
            for pair in pairing:
                merged=[]
                for i in pair: merged.extend(train[i]["behavior_observations"])
                c=obs_candidates(merged)
                if len(c)!=1: ok=False; break
                pair_rules.append(next(iter(c)))
            if ok and pair_rules[0]!=pair_rules[1]: valids.append((pairing,pair_rules))
        if len(valids)!=1: failures.append({"gate":"NON_IDENTIFIABLE_PARTITION","valid_partitions":valids})

    held=v["heldout_examples"]
    if len(held)!=3: failures.append({"gate":"HELDOUT_COUNT"})
    reference_held={}
    ambiguity_count=0
    for ex in held:
        if "behavior_observations" in ex: failures.append({"gate":"HELDOUT_BEHAVIOR_LEAKAGE","id":ex["example_id"]})
        rs=infer_rules(tid,ex["raw_text"])
        if "unresolved between" in norm(ex["raw_text"]):
            ambiguity_count+=1
            if len(rs)!=2: failures.append({"gate":"AMBIGUOUS_DOES_NOT_REFERENCE_BOTH_SLOTS","id":ex["example_id"],"rules":sorted(rs)})
            reference_held[ex["example_id"]]={"status":"AMBIGUOUS"}
            continue
        if len(rs)!=1:
            failures.append({"gate":"HELDOUT_RAW_TEXT_DENOTATION_NONUNIQUE","id":ex["example_id"],"rules":sorted(rs)}); continue
        rule=next(iter(rs)); pol,mod=expected_pm(ex["raw_text"])
        types=[ex["entity_registry"][eid]["type"] for eid in sorted(ex["entity_registry"])]
        if types!=expected_types: failures.append({"gate":"HELDOUT_ARG_TYPES","id":ex["example_id"]})
        reference_held[ex["example_id"]]={"status":"OK","rule":rule,"arg_types":expected_types,"arguments":sorted(ex["entity_registry"]),"polarity":pol,"modality":mod}
    if ambiguity_count!=1: failures.append({"gate":"AMBIGUITY_COVERAGE","count":ambiguity_count})
    ref={"authority":AUTHORITY,"training_semantics":reference_train,"heldout_semantics":reference_held}
    return ref,failures

def validate_corpus(corpus:dict[str,Any])->dict[str,Any]:
    refs={}; failures=[]
    tasks=corpus.get("tasks",[])
    if len(tasks)!=8: failures.append({"gate":"TASK_COUNT","actual":len(tasks)})
    for task in tasks:
        ref,fs=validate_task(task); refs[task["task_id"]]=ref
        failures.extend({"task_id":task["task_id"],**f} for f in fs)
    return {"protocol":"S1C_V3_INDEPENDENT_ORACLE_VALIDATION_V1","pass":not failures,
            "terminal":"S1C_V3_ORACLE_VALIDATION_PASS" if not failures else "S1C_V3_ORACLE_VALIDATION_FAIL_CLOSED",
            "failure_count":len(failures),"failures":failures,"references":refs}

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("corpus",type=Path); ap.add_argument("--output",type=Path); args=ap.parse_args()
    corpus=json.loads(args.corpus.read_text(encoding="utf-8")); out=validate_corpus(corpus)
    if args.output: args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("protocol","pass","terminal","failure_count")},indent=2))
    if not out["pass"]:
        print(json.dumps(out["failures"],indent=2)); raise SystemExit(3)