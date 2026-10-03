#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

PROTOCOL = "FUNCTION_BOUNDARY_S2B_METADATA_BLIND_HOLDOUT_V2"
CORE_FREEZE_COMMIT = "3ef026d9db6d2fef93c70d15f70fbbff4a98ac00"

SCENARIOS = [
  ("INSUFFICIENT_TO_RESOLVE", {"referent":"custodian","options":["depot_custodian","contract_custodian"]}, [
    ("ask for evidence that distinguishes which custodian was meant", True),
    ("leave the custodian reference unresolved until distinguishing evidence appears", True),
    ("assign the reference to depot_custodian now", False),
    ("assign the reference to contract_custodian now", False),
    ("proceed as though the ambiguity does not matter", False),
    ("drop the ambiguous statement from consideration", False),
  ]),
  ("INSUFFICIENT_TO_RESOLVE", {"referent":"handler","options":["case_handler","shipment_handler"]}, [
    ("seek clarification that separates the two possible handlers", True),
    ("keep handler unresolved pending more context", True),
    ("choose case_handler immediately", False),
    ("choose shipment_handler immediately", False),
    ("continue without resolving who handler denotes", False),
    ("ignore the handler statement", False),
  ]),
  ("ADMISSIBLE_UNDER_CONSTRAINT", {"alternatives":["route_alpha","route_beta"],"constraint":"encryption_required"}, [
    ("keep route_alpha while maintaining the encryption requirement", True),
    ("retain route_beta without weakening required encryption", True),
    ("use route_alpha even if encryption is skipped", False),
    ("use route_beta after removing the encryption requirement", False),
    ("delete the encryption requirement", False),
    ("discard both compliant routes", False),
  ]),
  ("ADMISSIBLE_UNDER_CONSTRAINT", {"alternatives":["review_dual","review_human"],"constraint":"segregation_required"}, [
    ("preserve review_dual while satisfying segregation", True),
    ("keep review_human provided segregation remains intact", True),
    ("select review_dual while bypassing segregation", False),
    ("select review_human after waiving segregation", False),
    ("remove segregation from the decision", False),
    ("reject every option that preserves segregation", False),
  ]),
  ("BLOCKS_INFERENCE", {"trigger":"sensor_flag","proposition":"coolant_leak_confirmed"}, [
    ("leave coolant_leak_confirmed unproven", True),
    ("keep sensor_flag as a reason to inspect, not as proof", True),
    ("declare coolant_leak_confirmed because sensor_flag fired", False),
    ("treat sensor_flag itself as conclusive evidence", False),
    ("ignore sensor_flag completely", False),
    ("escalate the leak as confirmed immediately", False),
  ]),
  ("BLOCKS_INFERENCE", {"trigger":"lint_warning","proposition":"build_failure_confirmed"}, [
    ("keep build_failure_confirmed unconfirmed", True),
    ("retain lint_warning as a review signal rather than proof of failure", True),
    ("confirm build_failure_confirmed from lint_warning alone", False),
    ("treat lint_warning as direct proof of build failure", False),
    ("discard the warning without review", False),
    ("announce a confirmed build failure immediately", False),
  ]),
  ("SUPERSEDES", {"new":"policy_v3","old":"policy_v2"}, [
    ("use policy_v3 as the current policy", True),
    ("keep policy_v2 only as historical context", True),
    ("continue using policy_v2 as current", False),
    ("treat policy_v2 and policy_v3 as equally current", False),
    ("ignore which policy is newer", False),
    ("discard policy_v3", False),
  ]),
  ("SUPERSEDES", {"new":"schedule_friday","old":"schedule_thursday"}, [
    ("apply schedule_friday as the active schedule", True),
    ("retain schedule_thursday as history", True),
    ("apply schedule_thursday as the active schedule", False),
    ("treat both schedules as simultaneously current", False),
    ("ignore the update ordering", False),
    ("throw away schedule_friday", False),
  ]),
]


def seed_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest()[:16],16)


def make_fixture(rng: random.Random, seq: int, op: str, fields: dict, candidate_specs: list[tuple[str,bool]]) -> dict:
    ids=[f"a{i}" for i in range(1,len(candidate_specs)+1)]; rng.shuffle(ids)
    candidates={}; gold=[]
    for cid,(text,is_gold) in zip(ids,candidate_specs):
        candidates[cid]=text
        if is_gold: gold.append(cid)
    relation={"operator":op,**fields}
    return {"id":f"M{seq:03d}","family":op,"relation":relation,"candidates":candidates,"gold":sorted(gold)}


def generate(seed: str) -> list[dict]:
    rng=random.Random(seed_int(seed)); rows=list(SCENARIOS); rng.shuffle(rows)
    return [make_fixture(rng,i,*row) for i,row in enumerate(rows,1)]


def digest(fixtures: list[dict]) -> str:
    return hashlib.sha256(json.dumps(fixtures,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--seed",required=True); ap.add_argument("--generator-freeze-commit",required=True); ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    if args.seed!=args.generator_freeze_commit: raise SystemExit("seed must equal generator freeze commit")
    fixtures=generate(args.seed)
    out={
      "protocol":PROTOCOL,
      "core_freeze_commit":CORE_FREEZE_COMMIT,
      "generator_freeze_commit":args.generator_freeze_commit,
      "seed_source":"generator freeze commit SHA",
      "seed":args.seed,
      "fixture_count":len(fixtures),
      "holdout_digest":digest(fixtures),
      "fixtures":fixtures,
    }
    args.output.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({k:out[k] for k in ("protocol","core_freeze_commit","generator_freeze_commit","fixture_count","holdout_digest")},indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
