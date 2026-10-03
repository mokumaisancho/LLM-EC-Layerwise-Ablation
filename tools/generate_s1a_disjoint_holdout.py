#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

PROTOCOL = "FUNCTION_BOUNDARY_S1A_DISJOINT_HOLDOUT_V2"
ALGORITHM_FREEZE_COMMIT = "84c8585e7362976069d2a385b370a20084534b79"

CASES = [
  {
    "family":"temporal_interval_overlap",
    "prompts":[
      "A maintenance window runs 01:00-03:00. The restart occurred at 02:15, while a separate backup completed at 04:00. Represent whether the restart occurred inside the maintenance window.",
      "The approved maintenance interval is from 1am until 3am. A service restart happened at 2:15am; a backup event occurred later at 4am. Ground the interval relation for the restart."
    ],
    "facts":{"P":"service restart occurred at 02:15","D1":"maintenance window is 01:00-03:00","D2":"backup completed at 04:00"},
    "concepts":{"P":"restart lies within the maintenance interval","D1":"restart occurred outside the maintenance interval","D2":"backup timing determines restart validity"},
    "relations":{"P":"{FP} OCCURS_WITHIN {FD1} AND_GROUNDS {CP}","D1":"{FP} OCCURS_AFTER {FD1} AND_GROUNDS {CD1}","D2":"{FD2} DETERMINES {CP}"},
    "goals":{"P":"represent the restart interval status","D1":"summarize the backup completion time"},"ambiguity":"NO"
  },
  {
    "family":"quantified_exception_scope",
    "prompts":[
      "The retention rule covers every project record except temporary scratch files. The item under review is explicitly tagged temporary scratch. Determine whether the general retention rule applies to this item.",
      "All project records are retained, with one stated exception for temporary scratch files. This file carries the temporary-scratch tag. Ground the exception scope."
    ],
    "facts":{"P":"reviewed file is tagged temporary scratch","D1":"general rule retains project records","D2":"scratch files are the explicit exception"},
    "concepts":{"P":"the reviewed file falls under the stated exception","D1":"the reviewed file must follow the general retention rule","D2":"the exception applies to every project record"},
    "relations":{"P":"{FP} MATCHES_EXCEPTION {FD2} AND_GROUNDS {CP}","D1":"{FP} IGNORES_EXCEPTION AND_GROUNDS {CD1}","D2":"{FD1} MAKES {CD2}"},
    "goals":{"P":"determine retention applicability for the reviewed file","D1":"count all retained records"},"ambiguity":"NO"
  },
  {
    "family":"identity_merge_by_key",
    "prompts":[
      "Two customer records use different display names, but both carry immutable customer key K-7741. A third record has another key. Determine whether the first two records denote the same customer entity.",
      "Record A and Record B have different labels yet share the same immutable customer identifier K-7741. Record C uses a different identifier. Ground the entity identity relation for A and B."
    ],
    "facts":{"P":"record A and B share immutable key K-7741","D1":"record A and B have different display names","D2":"record C has a different immutable key"},
    "concepts":{"P":"record A and B identify the same customer entity","D1":"different display names imply different customer entities","D2":"record C identity decides whether A and B match"},
    "relations":{"P":"{FP} ESTABLISHES_IDENTITY {CP}","D1":"{FD1} ESTABLISHES {CD1}","D2":"{FD2} ESTABLISHES {CD2}"},
    "goals":{"P":"resolve whether record A and B are the same entity","D1":"compare record C with every customer"},"ambiguity":"NO"
  },
  {
    "family":"prerequisite_dependency",
    "prompts":[
      "Feature activation requires a completed safety certificate first. The activation request exists, but the certificate is still incomplete. Represent the dependency state rather than the request's presence.",
      "A safety certificate is a prerequisite for enabling the feature. An enable request has been submitted while certification remains unfinished. Ground the prerequisite dependency."
    ],
    "facts":{"P":"safety certificate remains incomplete","D1":"feature activation request exists","D2":"certificate completion is required before activation"},
    "concepts":{"P":"activation prerequisite is not satisfied","D1":"activation is allowed because a request exists","D2":"request submission satisfies certification"},
    "relations":{"P":"{FP} WITH {FD2} GROUNDS {CP}","D1":"{FD1} GROUNDS {CD1}","D2":"{FD1} SATISFIES {CD2}"},
    "goals":{"P":"represent whether feature activation prerequisites are satisfied","D1":"count activation requests"},"ambiguity":"NO"
  },
  {
    "family":"aggregate_vs_instance_scope",
    "prompts":[
      "The fleet's monthly average fuel use decreased, but one vessel consumed more fuel on a single trip. Determine what the aggregate statistic says about the fleet rather than that individual trip.",
      "Across the fleet, average monthly fuel consumption is lower. One specific voyage nevertheless used more fuel than before. Ground the aggregate-level state."
    ],
    "facts":{"P":"fleet monthly average fuel use decreased","D1":"one vessel used more fuel on one trip","D2":"the observation is a single-trip instance"},
    "concepts":{"P":"aggregate fleet fuel use trend is downward","D1":"every vessel trip used less fuel","D2":"single-trip increase reverses the aggregate trend"},
    "relations":{"P":"{FP} GROUNDS_AGGREGATE {CP}","D1":"{FD1} GROUNDS {CD1}","D2":"{FD2} GROUNDS {CD2}"},
    "goals":{"P":"represent the fleet-level fuel trend","D1":"explain the single voyage only"},"ambiguity":"NO"
  },
  {
    "family":"conditional_branch_activation",
    "prompts":[
      "If account risk is HIGH, enhanced review is required; otherwise standard review applies. This account is marked HIGH. Determine which review branch is active.",
      "The workflow selects enhanced review only for HIGH-risk accounts and standard review otherwise. The current account has HIGH risk status. Ground the active branch."
    ],
    "facts":{"P":"current account risk is HIGH","D1":"HIGH risk activates enhanced review","D2":"standard review is the otherwise branch"},
    "concepts":{"P":"enhanced review branch is active","D1":"standard review branch is active","D2":"both branches are simultaneously active"},
    "relations":{"P":"{FP} WITH {FD1} ACTIVATES {CP}","D1":"{FP} ACTIVATES {CD1}","D2":"{FD2} ACTIVATES {CD2}"},
    "goals":{"P":"determine the active review branch","D1":"list all possible review branches"},"ambiguity":"NO"
  },
  {
    "family":"part_whole_attribution",
    "prompts":[
      "A battery module failed inside rack R7, while the rack controller remained healthy. Determine whether the observed failure belongs to the module or to the whole rack controller.",
      "Rack R7 contains a failed battery module, but its controller passes health checks. Ground the failure at the correct component level."
    ],
    "facts":{"P":"battery module inside rack R7 failed","D1":"rack controller remains healthy","D2":"battery module is a component of rack R7"},
    "concepts":{"P":"failure is attributed to the battery module component","D1":"rack controller itself failed","D2":"every component of rack R7 failed"},
    "relations":{"P":"{FP} WITH {FD2} GROUNDS_COMPONENT {CP}","D1":"{FD1} GROUNDS {CD1}","D2":"{FD2} GROUNDS {CD2}"},
    "goals":{"P":"locate the failure at the correct component level","D1":"declare the entire rack failed"},"ambiguity":"NO"
  },
  {
    "family":"measurement_scope_missing",
    "prompts":[
      "The report states 'average latency is 20 ms' but does not say whether the average covers one endpoint, one region, or the entire service. No scope metadata is attached. Represent the missing measurement scope.",
      "A metric says average latency equals 20 ms, with no indication of endpoint, region, or service-wide aggregation scope. Ground whether the measurement scope is resolved."
    ],
    "facts":{"P":"latency average is reported as 20 ms without scope metadata","D1":"endpoint scope is one possible interpretation","D2":"service-wide scope is another possible interpretation"},
    "concepts":{"P":"measurement aggregation scope is unresolved","D1":"the metric definitely refers to one endpoint","D2":"the metric definitely covers the entire service"},
    "relations":{"P":"{FP} INSUFFICIENT_TO_RESOLVE measurement_scope AND_GROUNDS {CP}","D1":"{FP} RESOLVES_TO {CD1}","D2":"{FP} RESOLVES_TO {CD2}"},
    "goals":{"P":"represent whether metric scope is resolved","D1":"assume service-wide scope without metadata"},"ambiguity":"YES"
  }
]


def seed_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16)


def shuffled_ids(rng: random.Random, prefix: str, count: int) -> list[str]:
    ids = [f"c_x{i}" for i in range(1, count+1)] if prefix == "c" else [f"{prefix}{i}" for i in range(1, count+1)]
    rng.shuffle(ids)
    return ids


def make_fixture(rng: random.Random, case: dict, variant: int, seq: int) -> dict:
    fk=list(case["facts"]); ck=list(case["concepts"]); rk=list(case["relations"]); gk=list(case["goals"])
    fm=dict(zip(fk,shuffled_ids(rng,"f",len(fk))))
    cm=dict(zip(ck,shuffled_ids(rng,"c",len(ck))))
    rm=dict(zip(rk,shuffled_ids(rng,"r",len(rk))))
    gm=dict(zip(gk,shuffled_ids(rng,"g",len(gk))))
    fmt={"FP":fm["P"],"FD1":fm["D1"],"FD2":fm["D2"],"CP":cm["P"],"CD1":cm["D1"],"CD2":cm["D2"]}
    return {
      "id":f"J{seq:03d}",
      "family":case["family"],
      "visible":{
        "prompt":case["prompts"][variant],
        "facts":{fm[k]:v for k,v in case["facts"].items()},
        "concepts":{cm[k]:v for k,v in case["concepts"].items()},
        "relations":{rm[k]:v.format(**fmt) for k,v in case["relations"].items()},
        "goals":{gm[k]:v for k,v in case["goals"].items()},
      },
      "oracle":{"primary_fact_id":fm["P"],"semantic_concept_id":cm["P"],"key_relation_id":rm["P"],"ambiguity":case["ambiguity"],"goal_id":gm["P"]},
    }


def generate(seed: str) -> list[dict]:
    rng=random.Random(seed_int(seed))
    order=list(range(len(CASES))); rng.shuffle(order)
    fixtures=[]; seq=1
    for ci in order:
        variants=[0,1]; rng.shuffle(variants)
        for variant in variants:
            fixtures.append(make_fixture(rng, CASES[ci], variant, seq)); seq += 1
    return fixtures


def digest(fixtures: list[dict]) -> str:
    return hashlib.sha256(json.dumps(fixtures,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed",required=True)
    ap.add_argument("--generator-freeze-commit",required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    if args.seed != args.generator_freeze_commit:
        raise SystemExit("seed must equal generator freeze commit")
    fixtures=generate(args.seed)
    out={
      "protocol":PROTOCOL,
      "algorithm_freeze_commit":ALGORITHM_FREEZE_COMMIT,
      "generator_freeze_commit":args.generator_freeze_commit,
      "seed_source":"generator freeze commit SHA",
      "seed":args.seed,
      "fixture_count":len(fixtures),
      "holdout_digest":digest(fixtures),
      "families":[CASES[i]["family"] for i in range(len(CASES))],
      "fixtures":fixtures,
    }
    args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("protocol","algorithm_freeze_commit","generator_freeze_commit","fixture_count","holdout_digest","families")},indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
