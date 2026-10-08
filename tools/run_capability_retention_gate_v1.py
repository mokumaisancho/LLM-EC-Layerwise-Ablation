#!/usr/bin/env python3
"""Strict CLI entrypoint for full matched-arm capability qualification."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.capability_retention_v1 import evaluate, EvaluationContractError


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--bundle",type=Path,required=True)
    parser.add_argument("--diagnostic",action="store_true",
      help="Retrospective V1/V5 diagnostic; never issue a preservation certificate.")
    args=parser.parse_args()
    try:
        bundle=json.loads(args.bundle.read_text(encoding="utf-8"))
        result=evaluate(bundle,diagnostic=args.diagnostic)
    except (EvaluationContractError,OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({"terminal":"CAPABILITY_RETENTION_BLOCKED","reason":str(exc)},sort_keys=True))
        return 3
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
    if result["terminal"]=="CAPABILITY_RETENTION_REGRESSION":return 3
    return 0


if __name__=="__main__":
    raise SystemExit(main())
