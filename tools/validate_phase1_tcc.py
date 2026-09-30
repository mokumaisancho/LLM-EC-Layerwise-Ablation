#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path
from jsonschema import Draft202012Validator

TCC_SKILL_PATH = os.environ.get("TCC_SKILL_PATH", "../Skills/skills/tcc/scripts")
sys.path.insert(0, TCC_SKILL_PATH)
from tcc import ToolScript

SCHEMA_MAP = {
    "input/task.json": "task_input.schema.json",
    "oracle/s1_domain_semantic_ir.json": "s1_domain_semantic_ir.schema.json",
    "oracle/s2_candidate_set.json": "s2_candidate_set.schema.json",
    "oracle/s3_selected_reframed_state.json": "s3_selected_reframed_state.schema.json",
    "oracle/s4_closure_execution_result.json": "s4_closure_execution_result.schema.json",
    "fixture_manifest.json": "fixture_manifest.schema.json",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="fixtures/phase1_v1/generated")
    ap.add_argument("--schemas", default="schemas")
    args = ap.parse_args()
    root = Path(args.root)
    schema_root = Path(args.schemas)
    script = ToolScript("ecv4.4-phase1-qualification")

    checks = {f"schema:{name}": f"test -f '{schema_root / name}'" for name in SCHEMA_MAP.values()}
    present = script.parallel_check(checks)
    script.set("schema_files_present", present)

    fixture_dirs = sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []
    script.set("fixture_count", len(fixture_dirs))
    schemas = {rel: json.loads((schema_root / name).read_text()) for rel, name in SCHEMA_MAP.items()}
    blocking = []
    findings = []
    validated = 0

    for d in fixture_dirs:
        fid = d.name
        docs = {}
        for rel in SCHEMA_MAP:
            p = d / rel
            if not p.exists():
                blocking.append({"fixture": fid, "type": "MISSING_ARTIFACT", "path": rel})
                continue
            try:
                docs[rel] = json.loads(p.read_text())
            except Exception as exc:
                blocking.append({"fixture": fid, "type": "INVALID_JSON", "path": rel, "detail": str(exc)})
                continue
            errors = sorted(Draft202012Validator(schemas[rel]).iter_errors(docs[rel]), key=lambda e: list(e.path))
            if errors:
                blocking.append({"fixture": fid, "type": "SCHEMA_VALIDATION", "path": rel, "detail": [e.message for e in errors[:5]]})
            else:
                validated += 1
        if len(docs) != len(SCHEMA_MAP):
            continue

        ids = {docs[x].get("fixture_id") for x in docs}
        gens = {docs[x].get("fixture_generation") for x in docs}
        if ids != {fid}:
            blocking.append({"fixture": fid, "type": "FIXTURE_ID_MISMATCH", "values": sorted(str(x) for x in ids)})
        if gens != {"phase1_v1"}:
            blocking.append({"fixture": fid, "type": "GENERATION_MISMATCH", "values": sorted(str(x) for x in gens)})

        s1 = docs["oracle/s1_domain_semantic_ir.json"]
        s2 = docs["oracle/s2_candidate_set.json"]
        s3 = docs["oracle/s3_selected_reframed_state.json"]
        s4 = docs["oracle/s4_closure_execution_result.json"]
        manifest = docs["fixture_manifest.json"]
        candidate_ids = {c["candidate_id"] for c in s2.get("candidates", [])}
        acceptable = set(s2.get("oracle_constraints", {}).get("acceptable_candidate_ids", []))
        selected = set(s3.get("selection", {}).get("selected_candidate_ids", []))
        rejected = set(s3.get("selection", {}).get("rejected_candidate_ids", []))
        if not acceptable <= candidate_ids:
            blocking.append({"fixture": fid, "type": "ACCEPTABLE_CANDIDATE_UNKNOWN"})
        if not selected <= candidate_ids:
            blocking.append({"fixture": fid, "type": "SELECTED_CANDIDATE_UNKNOWN"})
        if selected & rejected:
            blocking.append({"fixture": fid, "type": "SELECT_REJECT_OVERLAP"})
        if selected != acceptable:
            findings.append({"fixture": fid, "type": "SELECTION_ORACLE_DIFFERS_FROM_ACCEPTABLE_SET", "severity": "MEDIUM"})

        tag = (manifest.get("tags") or [""])[0]
        if tag == "multi-candidate" and len(acceptable) < 2:
            blocking.append({"fixture": fid, "type": "SCENARIO_CONTRACT_MISMATCH", "detail": "Prompt says two valid branches but oracle exposes fewer than two acceptable candidates."})
        if tag == "multiple-valid-outputs" and len(acceptable) < 2:
            blocking.append({"fixture": fid, "type": "MULTI_VALID_NOT_REPRESENTED"})
        if tag == "reframe-required" and not s3.get("framing", {}).get("reframe_required"):
            blocking.append({"fixture": fid, "type": "REQUIRED_REFRAME_MISSING"})
        if tag == "reframe-not-required" and s3.get("framing", {}).get("reframe_required"):
            blocking.append({"fixture": fid, "type": "UNNECESSARY_REFRAME"})
        if tag == "false-closure-trap" and s4.get("closure", {}).get("class") == "CLOSE":
            blocking.append({"fixture": fid, "type": "FALSE_CLOSURE"})
        if tag == "valid-closure" and s4.get("closure", {}).get("class") != "CLOSE":
            blocking.append({"fixture": fid, "type": "VALID_CLOSURE_MISSED"})
        if tag == "domain-language-ambiguity" and not s1.get("ambiguities"):
            blocking.append({"fixture": fid, "type": "DOMAIN_AMBIGUITY_NOT_MODELED"})
        if manifest.get("status") != "FROZEN":
            findings.append({"fixture": fid, "type": "NOT_FROZEN", "severity": "EXPECTED"})

    script.set("validated_artifact_count", validated)
    script.set("blocking_residuals", blocking)
    script.set("nonblocking_findings", findings)
    script.set("blocking_count", len(blocking))
    script.set("qualification_status", "PASS" if not blocking and len(fixture_dirs) == 10 and all(present.values()) else "BLOCKED")
    print(script.output())

if __name__ == "__main__":
    main()
