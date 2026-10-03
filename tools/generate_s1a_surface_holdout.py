#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

PROTOCOL = "FUNCTION_BOUNDARY_S1A_SURFACE_HOLDOUT_V1"

CASES = [
  {
    "family":"domain_homonym",
    "prompts":[
      "A cargo workflow says the vessel will enter the port selected for unloading. A network note elsewhere discusses an open TCP port. Ground the cargo meaning.",
      "For an unloading decision, the ship is assigned to a port. A separate IT ticket mentions a network port. Identify the maritime semantic state."
    ],
    "facts":{"P":"cargo destination is the unloading port","D1":"IT ticket reports an open TCP port","D2":"workflow is maritime cargo"},
    "concepts":{"P":"harbor location used by a vessel for cargo operations","D1":"network communication endpoint","D2":"meaning of port is unresolved"},
    "relations":{"P":"{FP} GROUNDS {CP}","D1":"{FD1} GROUNDS {CD1}","D2":"{FD2} DOES_NOT_DISAMBIGUATE port"},
    "goals":{"P":"represent the cargo destination semantics","D1":"diagnose network connectivity"},"ambiguity":"NO"
  },
  {
    "family":"near_miss_authority",
    "prompts":[
      "A purchase is within budget, but manager approval is still absent. A supplier is marked preferred. Determine what controls whether the order may be released.",
      "Budget capacity exists for the order, yet required approval has not been granted. Preferred-supplier status is also present. Identify the release authority."
    ],
    "facts":{"P":"manager approval is absent","D1":"budget capacity is available","D2":"supplier status is preferred"},
    "concepts":{"P":"authorization required before releasing an order","D1":"available spending capacity","D2":"supplier preference classification"},
    "relations":{"P":"{FP} CONTROLS order_release","D1":"{FD1} IS_EQUIVALENT_TO {CP}","D2":"{FD2} CONTROLS order_release"},
    "goals":{"P":"determine whether the order can be released","D1":"rank suppliers for sourcing"},"ambiguity":"NO"
  },
  {
    "family":"unresolved_referent",
    "prompts":[
      "The message says 'the reviewer accepted it'. Reviewer may mean the compliance reviewer or the code reviewer, and no identifier or action context resolves which one.",
      "A note states that 'the reviewer approved'. Both compliance and code review roles exist, with nothing in the note selecting one role."
    ],
    "facts":{"P":"text says the reviewer accepted it","D1":"reviewer may mean compliance reviewer","D2":"reviewer may mean code reviewer"},
    "concepts":{"P":"the reviewer referent is unresolved","D1":"compliance review role","D2":"code review role"},
    "relations":{"P":"{FP} INSUFFICIENT_TO_RESOLVE reviewer","D1":"{FP} RESOLVES_TO {CD1}","D2":"{FP} RESOLVES_TO {CD2}"},
    "goals":{"P":"bind the reviewer referent correctly","D1":"continue without clarification"},"ambiguity":"YES"
  },
  {
    "family":"causal_intervention",
    "prompts":[
      "Timeouts correlate with request volume. In a controlled test, changing only retry routing makes the timeouts disappear. A dashboard theme also changed. Identify the strongest causal relation.",
      "Higher load accompanies more timeouts, but an intervention limited to retry routing removes the failures. A visual dashboard setting changed too. Ground the causal evidence."
    ],
    "facts":{"P":"controlled retry-routing intervention removes timeouts","D1":"request volume and timeouts are correlated","D2":"dashboard theme changed"},
    "concepts":{"P":"retry routing is causally implicated","D1":"only correlation is established","D2":"dashboard theme causes timeouts"},
    "relations":{"P":"{FP} SUPPORTS_CAUSAL {CP}","D1":"{FD1} PROVES {CP}","D2":"{FD2} SUPPORTS_CAUSAL {CD2}"},
    "goals":{"P":"identify the evidence-backed cause of timeouts","D1":"redesign the dashboard appearance"},"ambiguity":"NO"
  },
  {
    "family":"representation_gap",
    "prompts":[
      "The incident model allows only user mistakes, while telemetry shows a gateway authentication rejection that the model cannot represent. Keep the investigation objective and represent the observation.",
      "Current variables encode user error only, but logs contain a gateway-side authentication rejection outside that frame. Preserve the explanation goal while adding the missing state."
    ],
    "facts":{"P":"telemetry shows gateway authentication rejection","D1":"current frame represents user error only","D2":"proposal changes the goal to minimize support cost"},
    "concepts":{"P":"gateway-side authentication failure","D1":"user-caused failure","D2":"change of investigation objective"},
    "relations":{"P":"{FP} REQUIRES_REPRESENTATION {CP}","D1":"{FD1} EXPLAINS {FP}","D2":"{FD2} PRESERVES investigation_goal"},
    "goals":{"P":"explain the observed incident","D1":"minimize support cost"},"ambiguity":"NO"
  },
  {
    "family":"source_authority",
    "prompts":[
      "A signed inventory ledger says stock is reserved. An informal chat says it is available. The source registry identifies the signed ledger as current authority.",
      "The verified inventory record marks the item reserved, while an unverified message calls it available. Registry metadata gives authority to the verified record."
    ],
    "facts":{"P":"source registry marks signed ledger as current authority","D1":"signed inventory ledger says reserved","D2":"informal chat says available"},
    "concepts":{"P":"inventory is reserved under current authority","D1":"inventory is available","D2":"authority conflict remains unresolved"},
    "relations":{"P":"{FP} AUTHORIZES {FD1}_OVER_{FD2}","D1":"{FD2} OVERRIDES {FD1}","D2":"{FD1} AND {FD2} ARE_EQUAL_AUTHORITY"},
    "goals":{"P":"derive the authoritative inventory state","D1":"summarize every message equally"},"ambiguity":"NO"
  },
  {
    "family":"domain_near_synonym",
    "prompts":[
      "A project forecast estimates expected completion cost. No invoice has been approved or paid. Interpret the forecast in the financial state.",
      "The program has a forecast for expected total cost, with no approved or issued payment. Ground what the forecast represents."
    ],
    "facts":{"P":"forecast is 2.4 million yen","D1":"invoice approval is absent","D2":"payment issued is false"},
    "concepts":{"P":"estimated future cost","D1":"money authorized for payment","D2":"cash already transferred"},
    "relations":{"P":"{FP} DENOTES {CP}","D1":"{FP} DENOTES {CD1}","D2":"{FD2} MAKES {FP} {CD1}"},
    "goals":{"P":"represent the project financial state","D1":"confirm transferred cash"},"ambiguity":"NO"
  },
  {
    "family":"mandatory_control",
    "prompts":[
      "Two deployment paths are evidence-supported and preserve mandatory encryption. A faster third path bypasses encryption. Identify the constraint that must survive downstream reasoning.",
      "Routes blue and green satisfy the required encryption control; a quicker shortcut skips it. Ground the protected constraint rather than speed."
    ],
    "facts":{"P":"shortcut is faster but bypasses mandatory encryption","D1":"blue path is supported and encryption-preserving","D2":"green path is supported and encryption-preserving"},
    "concepts":{"P":"mandatory encryption is a protected constraint","D1":"fastest path is the protected objective","D2":"only one route may remain represented"},
    "relations":{"P":"{FP} VIOLATES {CP}","D1":"{FP} SATISFIES {CP}","D2":"{FD1} INVALIDATES {FD2}"},
    "goals":{"P":"preserve supported routes without violating encryption","D1":"choose the fastest route immediately"},"ambiguity":"NO"
  },
  {
    "family":"negation_evidence",
    "prompts":[
      "Inspection found no evidence of a coolant leak. A sensor alert exists, but the alert is a review trigger and not proof of a leak.",
      "No coolant leak evidence was found during inspection. An automated sensor flag remains, explicitly not sufficient to prove leakage."
    ],
    "facts":{"P":"inspection found no coolant leak evidence","D1":"sensor alert is present","D2":"sensor alert is not proof"},
    "concepts":{"P":"coolant leak is not supported by current evidence","D1":"coolant leak is confirmed","D2":"leak status cannot be represented"},
    "relations":{"P":"{FD2} BLOCKS_INFERENCE {FD1}_TO_{CD1}","D1":"{FD1} PROVES {CD1}","D2":"{FP} PROVES {CD1}"},
    "goals":{"P":"represent the evidence-supported leak state","D1":"treat every sensor alert as confirmed leakage"},"ambiguity":"NO"
  },
  {
    "family":"freshness_supersession",
    "prompts":[
      "Yesterday the authoritative release record said ENABLED. Today the same authority says DISABLED. An older copied note still says ENABLED. Represent the current release state.",
      "The current authoritative record changed from ENABLED yesterday to DISABLED today; a stale copied message still contains ENABLED. Ground the latest state."
    ],
    "facts":{"P":"authoritative record today says DISABLED","D1":"authoritative record yesterday said ENABLED","D2":"older copied note says ENABLED"},
    "concepts":{"P":"current release state is disabled","D1":"current release state is enabled","D2":"enabled and disabled are equally current"},
    "relations":{"P":"{FP} SUPERSEDES {FD1}","D1":"{FD1} SUPERSEDES {FP}","D2":"{FD2} OVERRIDES {FP}"},
    "goals":{"P":"represent the current authoritative release state","D1":"preserve the oldest release state"},"ambiguity":"NO"
  }
]


def seed_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest()[:16],16)


def shuffled_ids(rng, prefix, count):
    if prefix == "c": ids=[f"c_x{i}" for i in range(1,count+1)]
    else: ids=[f"{prefix}{i}" for i in range(1,count+1)]
    rng.shuffle(ids)
    return ids


def make_fixture(rng, case, variant_index, seq):
    fact_keys=list(case["facts"]); concept_keys=list(case["concepts"]); relation_keys=list(case["relations"]); goal_keys=list(case["goals"])
    fact_ids=shuffled_ids(rng,"f",len(fact_keys)); concept_ids=shuffled_ids(rng,"c",len(concept_keys)); relation_ids=shuffled_ids(rng,"r",len(relation_keys)); goal_ids=shuffled_ids(rng,"g",len(goal_keys))
    fm=dict(zip(fact_keys,fact_ids)); cm=dict(zip(concept_keys,concept_ids)); rm=dict(zip(relation_keys,relation_ids)); gm=dict(zip(goal_keys,goal_ids))
    fmt={"FP":fm["P"],"FD1":fm["D1"],"FD2":fm["D2"],"CP":cm["P"],"CD1":cm["D1"],"CD2":cm["D2"]}
    facts={fm[k]:v for k,v in case["facts"].items()}
    concepts={cm[k]:v for k,v in case["concepts"].items()}
    relations={rm[k]:v.format(**fmt) for k,v in case["relations"].items()}
    goals={gm[k]:v for k,v in case["goals"].items()}
    return {
      "id":f"G{seq:03d}",
      "family":case["family"],
      "visible":{"prompt":case["prompts"][variant_index],"facts":facts,"concepts":concepts,"relations":relations,"goals":goals},
      "oracle":{"primary_fact_id":fm["P"],"semantic_concept_id":cm["P"],"key_relation_id":rm["P"],"ambiguity":case["ambiguity"],"goal_id":gm["P"]}
    }


def generate(seed: str):
    rng=random.Random(seed_int(seed)); out=[]; seq=1
    case_order=list(range(len(CASES))); rng.shuffle(case_order)
    for ci in case_order:
        variants=[0,1]; rng.shuffle(variants)
        for vi in variants:
            out.append(make_fixture(rng,CASES[ci],vi,seq)); seq+=1
    return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seed",required=True); ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    fixtures=generate(args.seed)
    digest=hashlib.sha256(json.dumps(fixtures,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    out={"protocol":PROTOCOL,"seed_source":"generator freeze commit SHA","seed":args.seed,"fixture_count":len(fixtures),"holdout_digest":digest,"fixtures":fixtures}
    args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"protocol":PROTOCOL,"fixture_count":len(fixtures),"holdout_digest":digest,"fixture_order":[f["id"]+":"+f["family"] for f in fixtures]},indent=2))

if __name__=="__main__": main()
