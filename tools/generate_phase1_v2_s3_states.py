#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

GENERATION = "phase1_v2"

# This artifact is an ORACLE-SUBSTITUTED UPSTREAM STATE used only when S3 is the target layer.
# It is not exposed to S1/S2 implementations.
STATES = {
    "M001": {"variables": {"coverage": {"semantic_key": "coverage_verified", "evidence_refs": ["task:coverage"], "actionable": True}, "incident": {"semantic_key": "incident_evidence", "evidence_refs": ["task:incident"], "actionable": True}}, "observations": []},
    "M002": {"variables": {"reserve": {"semantic_key": "reserve_estimate", "evidence_refs": ["task:reserve"], "actionable": False}, "authorization": {"semantic_key": "payment_authorization_absent", "evidence_refs": ["task:authorization"], "actionable": True}}, "observations": []},
    "M003": {"variables": {"route_a": {"semantic_key": "route_a", "evidence_refs": ["task:route_a"], "actionable": True}, "route_b": {"semantic_key": "route_b", "evidence_refs": ["task:route_b"], "actionable": True}, "control": {"semantic_key": "mandatory_control", "evidence_refs": ["task:control"], "actionable": True}}, "observations": []},
    "M004": {"variables": {"cause_x": {"semantic_key": "unsupported_cause_x", "evidence_refs": [], "actionable": False}, "cause_y": {"semantic_key": "supported_cause_y", "evidence_refs": ["task:cause_y"], "actionable": True}}, "observations": []},
    "M005": {"variables": {"user_error": {"semantic_key": "user_error", "evidence_refs": ["task:current_frame"], "actionable": True}}, "observations": [{"observation_id": "obs-auth-reject", "semantic_key": "authorization_rejection", "evidence_ref": "task:log"}]},
    "M006": {"variables": {"known_failure": {"semantic_key": "known_failure", "evidence_refs": ["task:failure"], "explains": ["obs-known"], "actionable": True}}, "observations": [{"observation_id": "obs-known", "semantic_key": "known_failure", "evidence_ref": "task:failure"}]},
    "M007": {"variables": {"answer": {"semantic_key": "coherent_answer", "evidence_refs": ["task:answer"], "actionable": True}, "required_condition": {"semantic_key": "required_condition_unresolved", "evidence_refs": ["task:required_condition"], "actionable": False}}, "observations": []},
    "M008": {"variables": {"constraints": {"semantic_key": "constraints_satisfied", "evidence_refs": ["task:constraints"], "actionable": True}, "evidence": {"semantic_key": "evidence_accounted", "evidence_refs": ["task:evidence"], "actionable": True}}, "observations": []},
    "M009": {"variables": {"action_a": {"semantic_key": "equivalent_valid_action", "evidence_refs": ["task:action_a"], "actionable": True}, "action_b": {"semantic_key": "equivalent_valid_action", "evidence_refs": ["task:action_b"], "actionable": True}}, "observations": []},
    "M010": {"variables": {"exposure": {"semantic_key": "claim_exposure", "evidence_refs": ["task:workflow"], "actionable": True}}, "observations": []}
}


def canonical_hash(obj):
    value = dict(obj)
    value.pop("content_hash", None)
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="fixtures/phase1_v2/generated")
    args = ap.parse_args()
    root = Path(args.root)
    success = "choose_semantically_valid_next_state"
    for fid, spec in sorted(STATES.items()):
        variables = spec["variables"]
        state = {
            "schema_version": "S3_SEMANTIC_STATE_V1",
            "fixture_id": fid,
            "fixture_generation": GENERATION,
            "artifact_id": fid + "-S3-UPSTREAM-STATE",
            "content_hash": "",
            "source_refs": ["input/task.json"],
            "intent": {
                "original_intent": "Choose the semantically valid next state under the stated domain rules and evidence.",
                "success_conditions": [success],
                "protected_invariants": ["preserve stated domain rules", "preserve protected intent"],
                "prohibited_substitutions": ["replace evidence with linguistic plausibility"]
            },
            "framing": {
                "framing_revision_id": 0,
                "variables": variables,
                "edges": [],
                "goal_coverage": {success: sorted(variables)},
                "violated_invariants": [],
                "substitutions": []
            },
            "observations": spec["observations"]
        }
        state["content_hash"] = canonical_hash(state)
        out = root / fid / "upstream" / "s3_semantic_state.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fixture_generation": GENERATION, "state_count": len(STATES), "status": "GENERATED"}, indent=2))


if __name__ == "__main__":
    main()
