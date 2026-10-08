#!/usr/bin/env python3
"""Two-person blind evaluation workflow. Never run grader credentials with predictors.

prepare: independent custodian holds private gold and salt; publishes hash only.
freeze: prediction operator holds public cases, source-pinned raw arm outputs and
        precommit, but has NO gold or salt.
score: independent adjudicator opens gold only after separate output commitments.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from evaluation.quality_blind_v2 import (
    ARMS, ARM_PROTOCOL, PUBLIC_PROTOCOL, SEAL_PROTOCOL,
    BlindProtocolError, make_precommit, validate_public, validate_arm, score, sha,
)

def read(path: Path):
    if not path.is_file():
        raise BlindProtocolError("INPUT_NOT_FILE")
    if path.stat().st_size>16_000_000:
        raise BlindProtocolError("INPUT_TOO_LARGE")
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    for action in ("prepare","freeze","score"):
        s=sub.add_parser(action)
        s.add_argument("--public",type=Path,required=True)
        if action=="prepare":
            s.add_argument("--gold",type=Path,required=True)
        elif action=="freeze":
            s.add_argument("--precommit",type=Path,required=True)
            for name in ARMS:s.add_argument("--"+name.lower(),type=Path,required=True)
        else:
            s.add_argument("--gold",type=Path,required=True)
            s.add_argument("--seal",type=Path,required=True)
            for name in ARMS:s.add_argument("--"+name.lower(),type=Path,required=True)
    a=p.parse_args()
    try:
        public=read(a.public)
        validate_public(public)
        if a.command=="prepare":
            salt=os.getenv("CAPABILITY_GOLD_SECRET_SALT","")
            result=make_precommit(public,read(a.gold),salt=salt)
        else:
            arms={name:read(getattr(a,name.lower())) for name in ARMS}
            for name in ARMS:validate_arm(arms[name],public)
            if a.command=="freeze":
                commitment=read(a.precommit)
                expected={"protocol","study_id","public_sha256","gold_commitment"}
                if set(commitment)!=expected or commitment["protocol"]!="CAPABILITY_GOLD_PRECOMMIT_V2" or commitment["study_id"]!=public["study_id"] or commitment["public_sha256"]!=sha(public):
                    raise BlindProtocolError("PRECOMMIT_PUBLIC_IDENTITY_INVALID")
                if not isinstance(commitment["gold_commitment"],str) or len(commitment["gold_commitment"])!=64:
                    raise BlindProtocolError("PRECOMMIT_INVALID")
                result={"protocol":SEAL_PROTOCOL,"study_id":public["study_id"],
                    "public_sha256":sha(public),"gold_commitment":commitment["gold_commitment"],
                    "arm_raw_commitments":{name:sha(arms[name]) for name in ARMS},
                    "gold_access_after_arms":True,
                    "independent_review":{"status":"PENDING","review_ref":""}}
            else:
                salt=os.getenv("CAPABILITY_GOLD_SECRET_SALT","")
                result=score(public,read(a.gold),arms,read(a.seal),salt=salt)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except (BlindProtocolError,ValueError,KeyError,OSError,TypeError) as exc:
        # No confidential input bytes or gold text should ever be emitted.
        print(json.dumps({"terminal":"CAPABILITY_BLIND_V2_BLOCKED",
                          "reason":str(exc)[:200]},sort_keys=True),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
