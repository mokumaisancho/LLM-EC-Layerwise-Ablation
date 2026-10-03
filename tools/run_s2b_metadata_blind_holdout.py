#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from s2b_metadata_blind_core import predict

PROTOCOL = "FUNCTION_BOUNDARY_S2B_METADATA_BLIND_HOLDOUT_V2"
CORE_FREEZE_COMMIT = "3ef026d9db6d2fef93c70d15f70fbbff4a98ac00"
FORBIDDEN_KEYS = {"action_class","target","constraint_preserved","forbidden","gold"}


def digest(fixtures: list[dict]) -> str:
    return hashlib.sha256(json.dumps(fixtures,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def assert_input_boundary(fixture: dict) -> None:
    if set(fixture) - {"id","family","relation","candidates","gold"}:
        raise SystemExit(f"unexpected fixture keys: {fixture['id']}")
    if not isinstance(fixture["candidates"], dict):
        raise SystemExit("candidates must be ID->text mapping")
    for cid,value in fixture["candidates"].items():
        if not isinstance(value,str):
            raise SystemExit(f"candidate metadata leak at {fixture['id']}:{cid}")
    leaked = FORBIDDEN_KEYS & set(fixture["relation"])
    if leaked:
        raise SystemExit(f"relation metadata leak: {sorted(leaked)}")


def score(fixtures: list[dict]) -> dict:
    tp=emitted=gold_total=exact=0
    per_family={}
    per_fixture={}
    for f in fixtures:
        assert_input_boundary(f)
        pred=set(predict(f["relation"], f["candidates"], emit_count=2))
        gold=set(f["gold"])
        hit=len(pred & gold)
        tp += hit; emitted += len(pred); gold_total += len(gold); exact += int(pred==gold)
        b=per_family.setdefault(f["family"],{"fixtures":0,"tp":0,"emitted":0,"gold":0,"exact":0})
        b["fixtures"]+=1; b["tp"]+=hit; b["emitted"]+=len(pred); b["gold"]+=len(gold); b["exact"]+=int(pred==gold)
        per_fixture[f["id"]]={"predicted":sorted(pred),"gold":sorted(gold),"tp":hit,"exact":pred==gold}
    fam={name:{**v,"recall":v["tp"]/v["gold"],"precision":v["tp"]/v["emitted"],"exact_set_rate":v["exact"]/v["fixtures"]} for name,v in per_family.items()}
    return {
      "candidate_recall":tp/gold_total,
      "candidate_precision":tp/emitted,
      "exact_set_rate":exact/len(fixtures),
      "true_positive_total":tp,
      "emitted_total":emitted,
      "gold_total":gold_total,
      "family_metrics":fam,
      "per_fixture":per_fixture,
    }


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("fixture_json",type=Path); ap.add_argument("manifest_json",type=Path); ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    data=json.loads(args.fixture_json.read_text()); manifest=json.loads(args.manifest_json.read_text())
    if data.get("protocol")!=PROTOCOL or manifest.get("protocol")!=PROTOCOL: raise SystemExit("protocol mismatch")
    if manifest.get("core_freeze_commit")!=CORE_FREEZE_COMMIT: raise SystemExit("core freeze mismatch")
    fixtures=data.get("fixtures",[])
    d=digest(fixtures)
    if d!=data.get("holdout_digest") or d!=manifest.get("holdout_digest"): raise SystemExit("digest mismatch")
    if data.get("seed")!=manifest.get("seed") or data.get("generator_freeze_commit")!=manifest.get("generator_freeze_commit"): raise SystemExit("provenance mismatch")
    metrics=score(fixtures)
    out={
      "schema_version":"FUNCTION_BOUNDARY_S2B_METADATA_BLIND_ACTUAL_V2",
      "protocol":PROTOCOL,
      "core_freeze_commit":CORE_FREEZE_COMMIT,
      "generator_freeze_commit":manifest["generator_freeze_commit"],
      "seed":manifest["seed"],
      "holdout_digest":d,
      "fixture_count":len(fixtures),
      "engine_input_boundary":"structured relation/operator + candidate natural-language text only",
      "forbidden_predictor_inputs":["gold","action_class","target","constraint_preserved","forbidden"],
      "metrics":metrics,
      "claim_limit":"Tests deterministic interpretation of candidate natural-language against already structured relation operators; does not test raw-language operator extraction or candidate invention.",
      "github_actions_used":False,
      "google_drive_used":False,
      "qwen3_4b_used":False,
    }
    args.output.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
