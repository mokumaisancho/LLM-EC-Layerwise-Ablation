#!/usr/bin/env python3
"""V2 CLI: execution always requires the source task for IR re-derivation."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from semantic_runtime import RuntimeContractError, canonical_json, discover_and_ground
from semantic_runtime.execution_v2 import execute_validated_ir

def read(path):
    if path=="-":return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    p=argparse.ArgumentParser(prog="semantic-runtime-v2")
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("discover-ground");a.add_argument("task")
    b=sub.add_parser("execute");b.add_argument("ir");b.add_argument("task");b.add_argument("solver")
    args=p.parse_args()
    try:
        out=discover_and_ground(read(args.task)) if args.command=="discover-ground" else execute_validated_ir(read(args.ir),read(args.task),read(args.solver))
        print(canonical_json(out))
        return 0
    except (RuntimeContractError,ValueError,TypeError,KeyError,json.JSONDecodeError) as e:
        print(canonical_json({"terminal":"FAIL_CLOSED","reason":str(e)}),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
