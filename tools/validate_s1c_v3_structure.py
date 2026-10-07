from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

PROTOCOL="S1C_V3_STRUCTURAL_NOVELTY_GATE_V1"

PRIOR_VECTORS=[
 {"id":"S1A_GRAPH_GROUNDING","visible_slot_inventory":True,"unknown_partition":False,"behavior_supervision":"GRAPH_OR_TYPED_SYMBOLS","output_target":"KNOWN_SEMANTIC_IR","partial_probe_partition_induction":False},
 {"id":"S2A_KNOWN_PRIMITIVE_COMPOSITION","visible_slot_inventory":True,"unknown_partition":False,"behavior_supervision":"KNOWN_PRIMITIVES","output_target":"COMPOSED_OPERATOR","partial_probe_partition_induction":False},
 {"id":"S2B1_SCHEMA_SYNTHESIS","visible_slot_inventory":True,"unknown_partition":False,"behavior_supervision":"SCHEMA_REQUIREMENTS","output_target":"NEW_SCHEMA","partial_probe_partition_induction":False},
 {"id":"S2B2_OPERATOR_INDUCTION","visible_slot_inventory":True,"unknown_partition":False,"behavior_supervision":"POS_NEG_STATE_TRANSITIONS","output_target":"NEW_OPERATOR","partial_probe_partition_induction":False},
 {"id":"S1C_R_RAW_GROUNDING","visible_slot_inventory":True,"unknown_partition":False,"behavior_supervision":"TYPED_IR_DEMONSTRATIONS","output_target":"KNOWN_SEMANTIC_IR","partial_probe_partition_induction":False},
 {"id":"S1C_V2_INVALID","visible_slot_inventory":False,"unknown_partition":True,"behavior_supervision":"IDENTICAL_SLOT_SIGNATURE","output_target":"DISCOVERED_LOCAL_SLOT","partial_probe_partition_induction":False},
]

def derive(task:dict[str,Any])->dict[str,Any]:
    v=task["visible"]
    train=v.get("training_examples",[])
    held=v.get("heldout_examples",[])
    observations=[ex.get("behavior_observations") for ex in train]
    has_partial=bool(observations) and all(isinstance(x,list) and len(x)==2 for x in observations)
    probe_sets=[]
    bundles=[]
    for obs in observations:
        if not isinstance(obs,list): continue
        probe_sets.append(tuple(o.get("probe_id") for o in obs))
        bundles.append(json.dumps(obs,sort_keys=True,separators=(",",":")))
    held_behavior=any("behavior_observations" in ex for ex in held)
    visible_keys=set(v)
    serialized=json.dumps(v,sort_keys=True).lower()
    known_slot_keys=any(k in serialized for k in ('"opaque_semantic_inventory"','"semantic_inventory"','"predicate_inventory"','"schema_requirements"','"supplied_primitive_ontology"'))
    typed_demo=any("typed_ir" in ex for ex in train if isinstance(ex,dict))
    vector={
      "visible_slot_inventory":known_slot_keys,
      "unknown_partition":not known_slot_keys and len(train)>0,
      "behavior_supervision":"DISTINCT_PARTIAL_TRANSITION_PROBES" if has_partial and len(set(probe_sets))==len(probe_sets) and len(set(bundles))==len(bundles) else ("TYPED_IR_DEMONSTRATIONS" if typed_demo else "OTHER"),
      "output_target":"DISCOVERED_LOCAL_SLOT",
      "partial_probe_partition_induction":has_partial and len(set(probe_sets))==len(probe_sets)==len(train),
      "heldout_behavior_visible":held_behavior,
      "training_count":len(train),
      "heldout_count":len(held),
      "has_ambiguity_case":any("unresolved between" in str(ex.get("raw_text","")).lower() for ex in held),
      "visible_top_keys":sorted(visible_keys),
    }
    return vector

def same_core(a,b):
    keys=("visible_slot_inventory","unknown_partition","behavior_supervision","output_target","partial_probe_partition_induction")
    return all(a.get(k)==b.get(k) for k in keys)

def evaluate(tasks:list[dict[str,Any]])->dict[str,Any]:
    failures=[]; rows=[]
    for task in tasks:
        vec=derive(task)
        collisions=[p["id"] for p in PRIOR_VECTORS if same_core(vec,p)]
        ok=(
          vec["visible_slot_inventory"] is False
          and vec["unknown_partition"] is True
          and vec["behavior_supervision"]=="DISTINCT_PARTIAL_TRANSITION_PROBES"
          and vec["partial_probe_partition_induction"] is True
          and vec["heldout_behavior_visible"] is False
          and vec["training_count"]==4
          and vec["heldout_count"]==3
          and vec["has_ambiguity_case"] is True
          and not collisions
        )
        rows.append({"task_id":task["task_id"],"derived_vector":vec,"prior_core_collisions":collisions,"pass":ok})
        if not ok: failures.append({"task_id":task["task_id"],"gate":"STRUCTURAL_NOVELTY_FAIL","vector":vec,"collisions":collisions})
    return {"protocol":PROTOCOL,"pass":not failures,"terminal":"S1C_V3_STRUCTURAL_NOVELTY_PASS" if not failures else "S1C_V3_STRUCTURAL_NOVELTY_FAIL_CLOSED","failure_count":len(failures),"failures":failures,"rows":rows}

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("corpus",type=Path); ap.add_argument("--output",type=Path); args=ap.parse_args()
    corpus=json.loads(args.corpus.read_text(encoding="utf-8")); out=evaluate(corpus["tasks"])
    if args.output: args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("protocol","pass","terminal","failure_count")},indent=2)); raise SystemExit(0 if out["pass"] else 3)