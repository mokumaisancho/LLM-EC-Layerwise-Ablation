#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from semantic_runtime import (
    RuntimeContractError,
    canonical_json,
    discover_and_ground,
    execute_validated_ir,
)


def _read(path: str):
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(prog="semantic-runtime")
    sub = ap.add_subparsers(dest="cmd", required=True)
    discover = sub.add_parser("discover-ground")
    discover.add_argument("task")
    execute = sub.add_parser("execute")
    execute.add_argument("ir")
    execute.add_argument("solver")
    args = ap.parse_args()
    try:
        if args.cmd == "discover-ground":
            out = discover_and_ground(_read(args.task))
        else:
            out = execute_validated_ir(_read(args.ir), _read(args.solver))
        sys.stdout.write(canonical_json(out) + "\n")
        return 0
    except (RuntimeContractError, ValueError, KeyError, TypeError) as exc:
        sys.stderr.write(canonical_json({"terminal": "FAIL_CLOSED", "error": str(exc)}) + "\n")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
