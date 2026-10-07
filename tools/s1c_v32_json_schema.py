from __future__ import annotations

import itertools
import json
from typing import Any

PROTOCOL = "S1C_V32_JSON_SCHEMA_V1"
LOCAL_SLOT_IDS = ("S01","S02")
EVAL_PROBE_IDS = ("Q03","Q05","Q06","Q07")


def _enum(values):
    return {"type":"string","enum":list(values)}

def _bits():
    return {"type":"array","minItems":3,"maxItems":3,"items":{"type":"integer","enum":[0,1]}}

def _eval_rows():
    return {
        "type":"array","minItems":4,"maxItems":4,
        "prefixItems":[
            {"type":"object","additionalProperties":False,"required":["probe_id","predicted_after"],
             "properties":{"probe_id":{"const":pid},"predicted_after":_bits()}}
            for pid in EVAL_PROBE_IDS
        ],
        "items":False,
    }

def _slot(task, sid, members):
    types=list(task["visible"]["type_inventory"])
    return {
        "type":"object","additionalProperties":False,
        "required":["slot_id","arg_types","training_members","evaluation_probe_predictions"],
        "properties":{
            "slot_id":{"const":sid},
            "arg_types":{"type":"array","minItems":1,"maxItems":2,"items":_enum(types)},
            "training_members":{"type":"array","minItems":2,"maxItems":2,
                "prefixItems":[{"const":members[0]},{"const":members[1]}],"items":False},
            "evaluation_probe_predictions":_eval_rows(),
        },
    }

def _assignment(task,eid):
    entities=sorted({str(k) for ex in task["visible"]["heldout_examples"] for k in ex["entity_registry"]})
    return {
      "type":"object","additionalProperties":False,
      "required":["example_id","slot_id","arguments","polarity","modality"],
      "properties":{
        "example_id":{"const":eid},"slot_id":_enum(LOCAL_SLOT_IDS),
        "arguments":{"type":"array","minItems":1,"maxItems":2,"items":_enum(entities)},
        "polarity":_enum(("POS","NEG")),"modality":_enum(("ASSERTED","REQUIRED","POSSIBLE")),
      },
    }

def _abstention(eid):
    return {"type":"object","additionalProperties":False,"required":["example_id","status"],
            "properties":{"example_id":{"const":eid},"status":{"const":"AMBIGUOUS"}}}

def _fixed_array(items):
    return {"type":"array","minItems":len(items),"maxItems":len(items),"prefixItems":items,"items":False}

def schema_for(task:dict[str,Any])->dict[str,Any]:
    train=sorted(str(x["example_id"]) for x in task["visible"]["training_examples"])
    held=sorted(str(x["example_id"]) for x in task["visible"]["heldout_examples"])
    if len(train)!=4 or len(held)!=3:
        raise ValueError("V32_EXPECTS_4_TRAIN_3_HELDOUT")

    pairings=[
      ((train[0],train[1]),(train[2],train[3])),
      ((train[0],train[2]),(train[1],train[3])),
      ((train[0],train[3]),(train[1],train[2])),
    ]
    discovered_alts=[]
    for a,b in pairings:
        discovered_alts.append(_fixed_array([_slot(task,"S01",a),_slot(task,"S02",b)]))
        discovered_alts.append(_fixed_array([_slot(task,"S01",b),_slot(task,"S02",a)]))

    decision_alts=[]
    for mask in range(8):
        assign_ids=[held[i] for i in range(3) if mask&(1<<i)]
        abstain_ids=[held[i] for i in range(3) if not mask&(1<<i)]
        decision_alts.append({
          "properties":{
            "heldout_assignments":_fixed_array([_assignment(task,eid) for eid in assign_ids]),
            "abstentions":_fixed_array([_abstention(eid) for eid in abstain_ids]),
          }
        })

    return {
      "type":"object","additionalProperties":False,
      "required":["discovered_slots","heldout_assignments","abstentions"],
      "properties":{
        "discovered_slots":{"oneOf":discovered_alts},
        "heldout_assignments":{"type":"array"},
        "abstentions":{"type":"array"},
      },
      "allOf":[{"oneOf":decision_alts}],
    }

def canonical_positive(task):
    tr=sorted(str(x["example_id"]) for x in task["visible"]["training_examples"])
    held=sorted(str(x["example_id"]) for x in task["visible"]["heldout_examples"])
    types=list(task["visible"]["type_inventory"])
    args=sorted(task["visible"]["heldout_examples"][0]["entity_registry"])
    probes=[{"probe_id":p,"predicted_after":[0,0,0]} for p in EVAL_PROBE_IDS]
    return {
      "discovered_slots":[
        {"slot_id":"S01","arg_types":types,"training_members":[tr[0],tr[1]],"evaluation_probe_predictions":probes},
        {"slot_id":"S02","arg_types":types,"training_members":[tr[2],tr[3]],"evaluation_probe_predictions":probes},
      ],
      "heldout_assignments":[
        {"example_id":held[0],"slot_id":"S01","arguments":args,"polarity":"POS","modality":"ASSERTED"},
        {"example_id":held[1],"slot_id":"S02","arguments":args,"polarity":"POS","modality":"ASSERTED"},
      ],
      "abstentions":[{"example_id":held[2],"status":"AMBIGUOUS"}],
    }

def static_contract_check(task):
    s=schema_for(task)
    encoded=json.dumps(s,separators=(",",":"))
    c=canonical_positive(task)
    failures=[]
    if encoded.count('"oneOf"')<2: failures.append("ONEOF_PARTITION_OR_COVERAGE_MISSING")
    if '"prefixItems"' not in encoded: failures.append("POSITIONAL_CONSTRAINT_MISSING")
    if '"S03"' in encoded or '"S04"' in encoded: failures.append("EXTRA_SLOT_ID_AUTHORITY")
    if any(pid not in encoded for pid in EVAL_PROBE_IDS): failures.append("EVAL_PROBE_LITERAL_MISSING")
    if len(c["discovered_slots"])!=2 or any(len(x["training_members"])!=2 for x in c["discovered_slots"]): failures.append("CANONICAL_PARTITION_INVALID")
    dup=json.loads(json.dumps(c)); dup["discovered_slots"][1]["training_members"]=list(dup["discovered_slots"][0]["training_members"])
    missing=json.loads(json.dumps(c)); missing["discovered_slots"][0]["evaluation_probe_predictions"]=missing["discovered_slots"][0]["evaluation_probe_predictions"][:3]
    return {
      "protocol":PROTOCOL,"pass":not failures,"failures":failures,"schema":s,
      "canonical_positive":c,
      "negative_examples":{
        "duplicate_training_members":dup,
        "missing_eval_probe":missing,
      },
      "runtime_validation_required":True,
      "scientific_change":"NONE_OUTPUT_AUTHORITY_ONLY",
    }

__all__=["PROTOCOL","LOCAL_SLOT_IDS","EVAL_PROBE_IDS","schema_for","canonical_positive","static_contract_check"]
