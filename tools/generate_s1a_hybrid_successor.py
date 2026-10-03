#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

PROTOCOL = "FUNCTION_BOUNDARY_S1A_HYBRID_SUCCESSOR_V1"
ROUTE_FREEZE_COMMIT = "b9fc26809da58ed25572454f3de5a09e99930b6a"

CASES = [
  {
    "family":"directed_graph_reachability",
    "prompts":[
      "A directed dependency graph contains A→B and B→C, with no reverse edges. Determine whether C is reachable from A through the graph.",
      "The graph has directed links from A to B and from B to C. Reverse links are absent. Ground the reachability state from A toward C."
    ],
    "facts":{"P":"directed edges A to B and B to C exist","D1":"there is no direct A to C edge","D2":"reverse edges C to B and B to A are absent"},
    "concepts":{"P":"C is reachable from A by a directed path","D1":"C is unreachable because no direct edge exists","D2":"A is reachable from C"},
    "relations":{"P":"{FP} ESTABLISHES_TRANSITIVE_PATH {CP}","D1":"{FD1} ESTABLISHES {CD1}","D2":"{FD2} ESTABLISHES {CD2}"},
    "goals":{"P":"represent directed reachability from A to C","D1":"list only direct graph edges"},
    "ambiguity":"NO"
  },
  {
    "family":"set_intersection_membership",
    "prompts":[
      "Item X belongs to set Red and set Large. Item Y belongs only to Red. Determine whether X is in the intersection Red∩Large.",
      "Membership records place X in both Red and Large, while Y appears only in Red. Ground X's membership in the intersection of the two sets."
    ],
    "facts":{"P":"X is a member of both Red and Large","D1":"Y is a member of Red only","D2":"X is not listed outside either set"},
    "concepts":{"P":"X belongs to the intersection Red and Large","D1":"X belongs only to Red","D2":"X belongs to the complement of Large"},
    "relations":{"P":"{FP} GROUNDS_INTERSECTION_MEMBERSHIP {CP}","D1":"{FD1} GROUNDS {CD1}","D2":"{FD2} GROUNDS {CD2}"},
    "goals":{"P":"represent X membership in Red intersection Large","D1":"classify Y membership"},
    "ambiguity":"NO"
  },
  {
    "family":"cardinality_limit_violation",
    "prompts":[
      "A session may hold at most three active tokens. Four distinct tokens are currently active. Represent whether the cardinality constraint is satisfied.",
      "The allowed active-token count is no more than 3, but the current session contains 4 active tokens. Ground the limit state."
    ],
    "facts":{"P":"four active tokens are present","D1":"maximum permitted active tokens is three","D2":"all four tokens are distinct"},
    "concepts":{"P":"active-token cardinality exceeds the allowed maximum","D1":"active-token cardinality satisfies the maximum","D2":"token distinctness removes the maximum"},
    "relations":{"P":"{FP} WITH_LIMIT {FD1} GROUNDS {CP}","D1":"{FP} GROUNDS {CD1}","D2":"{FD2} GROUNDS {CD2}"},
    "goals":{"P":"represent whether the active-token cardinality is valid","D1":"enumerate token identities"},
    "ambiguity":"NO"
  },
  {
    "family":"unit_conversion_equivalence",
    "prompts":[
      "The required cable length is 1.5 meters. Inventory lists a cable as 150 centimeters. Determine whether the listed length is equivalent to the requirement.",
      "A specification asks for 1.5 m and the available cable is labeled 150 cm. Ground whether those quantities represent the same length."
    ],
    "facts":{"P":"1.5 meters equals 150 centimeters","D1":"inventory cable is labeled 150 centimeters","D2":"requirement is 1.5 meters"},
    "concepts":{"P":"inventory length is equivalent to the required length","D1":"inventory cable is shorter than required","D2":"different unit labels imply different dimensions"},
    "relations":{"P":"{FP} ESTABLISHES_UNIT_EQUIVALENCE {CP}","D1":"{FD1} GROUNDS {CD1}","D2":"{FD2} GROUNDS {CD2}"},
    "goals":{"P":"represent whether the cable length satisfies the quantity requirement","D1":"preserve the original unit labels only"},
    "ambiguity":"NO"
  },
  {
    "family":"parity_constraint_check",
    "prompts":[
      "A code word must contain an even number of set bits. The observed word contains five set bits. Determine whether the parity constraint is satisfied.",
      "Even parity is required, while the received code has 5 one-bits. Ground the parity-validity state."
    ],
    "facts":{"P":"observed code contains five set bits","D1":"required parity is even","D2":"five is an odd count"},
    "concepts":{"P":"the observed code violates the even-parity constraint","D1":"the observed code satisfies even parity","D2":"parity is unrelated to set-bit count"},
    "relations":{"P":"{FP} WITH {FD1} AND {FD2} GROUNDS {CP}","D1":"{FP} GROUNDS {CD1}","D2":"{FD2} GROUNDS {CD2}"},
    "goals":{"P":"represent whether the code satisfies the parity rule","D1":"count total code positions"},
    "ambiguity":"NO"
  },
  {
    "family":"weighted_capacity_sum",
    "prompts":[
      "A container has capacity 10 units. Two selected loads weigh 4 and 5 units. Determine whether their combined load stays within capacity.",
      "The capacity ceiling is 10. Current selected loads contribute 4 units and 5 units. Ground the combined-capacity state."
    ],
    "facts":{"P":"selected loads total nine units","D1":"container capacity is ten units","D2":"one load weighs five units"},
    "concepts":{"P":"combined selected load remains within capacity","D1":"combined load exceeds capacity","D2":"single largest load alone determines capacity use"},
    "relations":{"P":"{FP} COMPARED_WITH {FD1} GROUNDS {CP}","D1":"{FP} GROUNDS {CD1}","D2":"{FD2} GROUNDS {CD2}"},
    "goals":{"P":"represent whether the selected loads fit within capacity","D1":"identify the largest individual load"},
    "ambiguity":"NO"
  },
  {
    "family":"uniqueness_constraint_collision",
    "prompts":[
      "Seat 12A may be assigned to at most one ticket. Two different active tickets both claim seat 12A. Determine the uniqueness state for that seat.",
      "The allocation rule permits one active ticket per seat, but seat 12A appears on two distinct active tickets. Ground the uniqueness constraint result."
    ],
    "facts":{"P":"two distinct active tickets claim seat 12A","D1":"seat assignment permits at most one active ticket","D2":"both tickets are active"},
    "concepts":{"P":"seat 12A has a uniqueness collision","D1":"seat 12A satisfies unique allocation","D2":"multiple active tickets are allowed for one seat"},
    "relations":{"P":"{FP} UNDER_RULE {FD1} GROUNDS {CP}","D1":"{FP} GROUNDS {CD1}","D2":"{FD2} GROUNDS {CD2}"},
    "goals":{"P":"represent whether seat 12A allocation is unique","D1":"count all active tickets"},
    "ambiguity":"NO"
  },
  {
    "family":"equality_substitution_chain",
    "prompts":[
      "Variable x is defined equal to y, and y is fixed at value 7. Determine the value implied for x by equality substitution.",
      "The constraints state x=y and y=7. Ground the value of x implied by the equality chain."
    ],
    "facts":{"P":"x equals y and y equals seven","D1":"x has no separate assigned value","D2":"another variable z equals eight"},
    "concepts":{"P":"x is constrained to equal seven","D1":"x remains unconstrained","D2":"x equals eight"},
    "relations":{"P":"{FP} ESTABLISHES_EQUALITY_SUBSTITUTION {CP}","D1":"{FD1} GROUNDS {CD1}","D2":"{FD2} GROUNDS {CD2}"},
    "goals":{"P":"represent the value implied for x","D1":"report the value of z"},
    "ambiguity":"NO"
  }
]


def seed_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16)


def shuffled_ids(rng: random.Random, prefix: str, count: int) -> list[str]:
    ids = [f"c_x{i}" for i in range(1, count + 1)] if prefix == "c" else [f"{prefix}{i}" for i in range(1, count + 1)]
    rng.shuffle(ids)
    return ids


def make_fixture(rng: random.Random, case: dict, variant: int, seq: int) -> dict:
    fk = list(case["facts"]); ck = list(case["concepts"]); rk = list(case["relations"]); gk = list(case["goals"])
    fm = dict(zip(fk, shuffled_ids(rng, "f", len(fk))))
    cm = dict(zip(ck, shuffled_ids(rng, "c", len(ck))))
    rm = dict(zip(rk, shuffled_ids(rng, "r", len(rk))))
    gm = dict(zip(gk, shuffled_ids(rng, "g", len(gk))))
    fmt = {"FP":fm["P"],"FD1":fm["D1"],"FD2":fm["D2"],"CP":cm["P"],"CD1":cm["D1"],"CD2":cm["D2"]}
    return {
      "id": f"K{seq:03d}",
      "family": case["family"],
      "visible": {
        "prompt": case["prompts"][variant],
        "facts": {fm[k]:v for k,v in case["facts"].items()},
        "concepts": {cm[k]:v for k,v in case["concepts"].items()},
        "relations": {rm[k]:v.format(**fmt) for k,v in case["relations"].items()},
        "goals": {gm[k]:v for k,v in case["goals"].items()}
      },
      "oracle": {
        "primary_fact_id": fm["P"],
        "semantic_concept_id": cm["P"],
        "key_relation_id": rm["P"],
        "ambiguity": case["ambiguity"],
        "goal_id": gm["P"]
      }
    }


def generate(seed: str) -> list[dict]:
    rng = random.Random(seed_int(seed))
    order = list(range(len(CASES))); rng.shuffle(order)
    fixtures = []; seq = 1
    for ci in order:
        variants = [0, 1]; rng.shuffle(variants)
        for variant in variants:
            fixtures.append(make_fixture(rng, CASES[ci], variant, seq)); seq += 1
    return fixtures


def digest(fixtures: list[dict]) -> str:
    return hashlib.sha256(json.dumps(fixtures, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True)
    ap.add_argument("--generator-freeze-commit", required=True)
    ap.add_argument("--route-freeze-commit", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.route_freeze_commit != ROUTE_FREEZE_COMMIT:
        raise SystemExit("route freeze mismatch")
    if args.seed != args.generator_freeze_commit:
        raise SystemExit("seed must equal generator freeze commit")
    fixtures = generate(args.seed)
    out = {
      "protocol": PROTOCOL,
      "route_freeze_commit": ROUTE_FREEZE_COMMIT,
      "generator_freeze_commit": args.generator_freeze_commit,
      "seed_source": "generator freeze commit SHA",
      "seed": args.seed,
      "fixture_count": len(fixtures),
      "holdout_digest": digest(fixtures),
      "families": [c["family"] for c in CASES],
      "fixtures": fixtures
    }
    args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("protocol","route_freeze_commit","generator_freeze_commit","fixture_count","holdout_digest","families")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
