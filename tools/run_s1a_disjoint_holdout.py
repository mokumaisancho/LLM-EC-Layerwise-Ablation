#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from s1a_predictor_core import score

PROTOCOL = "FUNCTION_BOUNDARY_S1A_DISJOINT_HOLDOUT_V2"
ALGORITHM_FREEZE_COMMIT = "84c8585e7362976069d2a385b370a20084534b79"


def fixture_digest(fixtures: list[dict]) -> str:
    canonical = json.dumps(fixtures, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture_json", type=Path)
    ap.add_argument("manifest_json", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    data = json.loads(args.fixture_json.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest_json.read_text(encoding="utf-8"))

    if data.get("protocol") != PROTOCOL or manifest.get("protocol") != PROTOCOL:
        raise SystemExit("protocol mismatch")
    if manifest.get("algorithm_freeze_commit") != ALGORITHM_FREEZE_COMMIT:
        raise SystemExit("algorithm freeze mismatch")
    if data.get("seed") != manifest.get("seed"):
        raise SystemExit("seed mismatch")
    if data.get("generator_freeze_commit") != manifest.get("generator_freeze_commit"):
        raise SystemExit("generator freeze mismatch")
    fixtures = data.get("fixtures")
    if not isinstance(fixtures, list) or len(fixtures) != manifest.get("fixture_count"):
        raise SystemExit("fixture count mismatch")
    digest = fixture_digest(fixtures)
    if digest != data.get("holdout_digest") or digest != manifest.get("holdout_digest"):
        raise SystemExit("holdout digest mismatch")

    result = score(fixtures)
    out = {
        "schema_version": "FUNCTION_BOUNDARY_S1A_DISJOINT_HOLDOUT_ACTUAL_V2",
        "protocol": PROTOCOL,
        "algorithm_freeze_commit": ALGORITHM_FREEZE_COMMIT,
        "generator_freeze_commit": manifest["generator_freeze_commit"],
        "seed": manifest["seed"],
        "holdout_digest": digest,
        "fixture_count": len(fixtures),
        "result": result,
        "claim_limits": [
            "Synthetic prospective holdout with structural families disjoint from S101-S110 and the prior surface holdout.",
            "Tests grounding against supplied semantic dictionaries, not ontology induction from unconstrained raw text.",
            "No algorithm change is permitted after this holdout is scored."
        ],
        "github_actions_used": False,
        "google_drive_used": False,
        "qwen3_4b_used": False,
    }
    args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
