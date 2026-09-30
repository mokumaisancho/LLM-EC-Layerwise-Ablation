#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

TCC_SKILL_PATH = os.environ.get("TCC_SKILL_PATH", "../Skills/skills/tcc/scripts")
sys.path.insert(0, TCC_SKILL_PATH)
from tcc import ToolScript

FORBIDDEN_PATTERNS = [
    r"reframe-required",
    r"reframe-not-required",
    r"false-closure",
    r"valid-closure",
    r"multiple-valid-outputs",
    r"multi-candidate",
    r"superficial-winner",
    r"near-miss-concept",
    r"domain-language-ambiguity",
    r"acceptable_candidate_ids",
    r"reframe_required",
    r"closure_class",
    r"expected[_ -]?closure",
    r"expected[_ -]?reframe",
]

VISIBLE_RELATIVE_PATHS = [
    "input/task.json",
]


def scan_text(text: str):
    hits = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, flags=re.I):
            hits.append(pattern)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="fixtures/phase1_v2/generated")
    args = ap.parse_args()
    root = Path(args.root)
    script = ToolScript("phase1-v2-leakage-gate")

    dirs = sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []
    findings = []
    for d in dirs:
        for rel in VISIBLE_RELATIVE_PATHS:
            p = d / rel
            if not p.exists():
                findings.append({"fixture": d.name, "path": rel, "type": "MISSING_VISIBLE_ARTIFACT"})
                continue
            text = p.read_text(encoding="utf-8")
            for hit in scan_text(text):
                findings.append({"fixture": d.name, "path": rel, "type": "ORACLE_LABEL_LEAK", "pattern": hit})
            try:
                doc = json.loads(text)
            except Exception as exc:
                findings.append({"fixture": d.name, "path": rel, "type": "INVALID_JSON", "detail": str(exc)})
                continue
            # Author-only notes are forbidden from measurement-visible task input.
            if doc.get("notes_for_fixture_author"):
                findings.append({"fixture": d.name, "path": rel, "type": "AUTHOR_NOTE_VISIBLE"})
            context = doc.get("context") or {}
            if isinstance(context, dict) and "scenario" in context:
                findings.append({"fixture": d.name, "path": rel, "type": "SCENARIO_FIELD_VISIBLE"})

    script.set("fixture_count", len(dirs))
    script.set("findings", findings)
    script.set("blocking_count", len(findings))
    script.set("status", "PASS" if len(dirs) == 10 and not findings else "BLOCKED")
    print(script.output())


if __name__ == "__main__":
    main()
