#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "S2B2_MVP_AC_DEPENDENCY_TCC_2026-10-04_V2.json"
V1 = ROOT / "docs" / "S2B2_MVP_AC_DEPENDENCY_TCC_2026-10-04.json"
A_AUDIT = ROOT / "tools" / "audit_s2b2a_existing_result.py"
EXPECTED_PROTOCOL = "S2B2_MVP_TCC_V2"


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"INVALID_TEST_CONTRACT: {path}: {exc}")


def precheck() -> dict:
    c = load(CONTRACT)
    if c.get("protocol") != EXPECTED_PROTOCOL:
        raise SystemExit("INVALID_TEST_CONTRACT: wrong V2 protocol")
    if c.get("owner_issue") != 43:
        raise SystemExit("INVALID_TEST_CONTRACT: wrong owner issue")
    if float(c.get("materiality_abs", -1)) != 0.20:
        raise SystemExit("INVALID_TEST_CONTRACT: materiality drift")
    v1 = load(V1)
    if v1.get("status") != "SUPERSEDED_DO_NOT_EXECUTE":
        raise SystemExit("SUPERSEDED_CONTRACT_IN_USE: V1 not disabled")
    inv = set(c.get("invariants", []))
    required = {
        "NO_GITHUB_ACTIONS",
        "NO_GOOGLE_DRIVE_MODEL_RELAY",
        "NO_QWEN3_4B_AUTO_BRANCH",
        "NO_PREDICTOR_AUTHORED_ORACLE",
        "NO_AGGREGATE_ONLY_QWEN_EVIDENCE",
        "NO_ASYMMETRIC_GENERATION_AUTHORITY",
        "NO_B2_NONUNIQUE_ORACLE",
        "NEW_BLOCKER_REQUIRES_REGISTRY_AND_VERSIONED_SUCCESSOR",
    }
    if required - inv:
        raise SystemExit(f"INVALID_TEST_CONTRACT: missing invariants {sorted(required-inv)}")
    return {"terminal":"V2_PRECHECK_PASS","protocol":EXPECTED_PROTOCOL}


def audit_a(output: Path | None) -> dict:
    cmd=[sys.executable,str(A_AUDIT)]
    if output:
        cmd += ["--output",str(output)]
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    if p.returncode:
        raise SystemExit(p.stderr.strip() or p.stdout.strip() or "STAGE_A_AUDIT_FAIL")
    return json.loads(p.stdout)


def main() -> int:
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="mode",required=True)
    sub.add_parser("precheck")
    a=sub.add_parser("audit-a")
    a.add_argument("--output",type=Path)
    args=ap.parse_args()
    out=precheck()
    if args.mode=="audit-a":
        out=audit_a(args.output)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
