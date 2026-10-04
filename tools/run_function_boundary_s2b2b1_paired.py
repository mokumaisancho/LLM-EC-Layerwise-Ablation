#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "ec26fee3e0a85598f1d6ad2d55d9b6f128461d33"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def fail(detail: str) -> None:
    print(json.dumps({"terminal": "B1_EXECUTION_ADAPTER_FAILED", "detail": detail}, indent=2), flush=True)
    raise SystemExit(2)


# Infrastructure-only adapter for Render service quota reuse.
# It never executes the superseded B1 implementation in this branch.
p = run("git", "fetch", "origin", "main")
if p.returncode:
    fail("git fetch origin main: " + (p.stderr or p.stdout).strip())

p = run("git", "cat-file", "-e", PIN + "^{commit}")
if p.returncode:
    fail("frozen V3 commit unavailable")

p = run("git", "checkout", "--detach", PIN)
if p.returncode:
    fail("checkout frozen V3 commit: " + (p.stderr or p.stdout).strip())

head = run("git", "rev-parse", "HEAD")
if head.returncode or head.stdout.strip() != PIN:
    fail("HEAD is not frozen V3 runner commit")

p = subprocess.run([sys.executable, "tools/preflight_s2b2_v3_static.py"], cwd=ROOT, text=True, capture_output=True)
if p.returncode:
    fail("V3 static/scientific preflight: " + (p.stderr or p.stdout).strip())
try:
    gate = json.loads(p.stdout)
except Exception as e:
    fail(f"V3 preflight JSON parse: {e}")
if gate.get("terminal") != "V3_L00_IMPLEMENTATION_STATIC_VALID":
    fail("V3 preflight terminal mismatch")

print(json.dumps({"terminal": "B1_EXECUTION_ADAPTER_PASS", "pinned_commit": PIN, "v3_gate": gate["terminal"]}, indent=2), flush=True)
os.execv(sys.executable, [sys.executable, "tools/run_s2b2b1_paired_v3.py"])
