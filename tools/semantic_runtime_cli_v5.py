#!/usr/bin/env python3
"""Authorized V4 CLI: all executions require an installed owner-controlled policy.

Legacy V1/V2 CLI are not authorized execution entrypoints.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from semantic_runtime import RuntimeContractError,canonical_json,discover_and_ground
from semantic_runtime.constrained_v5 import execute_authorized_ir, classify_authorized


def read(path: str):
    return json.load(sys.stdin) if path=="-" else json.loads(Path(path).read_text(encoding="utf-8"))


def main()->int:
    parser=argparse.ArgumentParser(description="Semantic Runtime V5 strict grammar authorized CLI")
    cmd=parser.add_subparsers(dest="action",required=True)
    d=cmd.add_parser("discover-ground");d.add_argument("task")
    preview=cmd.add_parser("classify")
    preview.add_argument("task");preview.add_argument("solver");preview.add_argument("--policy-id",required=True)
    e=cmd.add_parser("execute")
    e.add_argument("ir");e.add_argument("task");e.add_argument("solver")
    e.add_argument("--policy-id",required=True)
    args=parser.parse_args()
    try:
        if args.action=="discover-ground":
            out=discover_and_ground(read(args.task))
        elif args.action=="classify":
            out=classify_authorized(read(args.task),read(args.solver),args.policy_id)
        else:
            out=execute_authorized_ir(read(args.ir),read(args.task),read(args.solver),args.policy_id)
    except (RuntimeContractError,OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
        print(canonical_json({"terminal":"FAIL_CLOSED","reason":str(exc)}),file=sys.stderr)
        return 3
    print(canonical_json(out))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
