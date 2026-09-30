#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

GENERATION = "phase1_v2"
PROTOCOL = "PHASE1_ARTIFACT_CONTRACT_V1"

# `category` is hidden evaluation metadata and MUST NOT be copied into task input.
SPECS = [
    {
        "id": "M001", "category": "direct-semantic",
        "prompt": "A claim has verified coverage and the required incident evidence. A marketing note mentions a premium discount. Determine the next semantic state relevant to claim handling.",
        "facts": ["coverage=verified", "incident_evidence=present", "marketing_note=premium_discount"],
        "rules": ["Claim progression depends on coverage and incident evidence.", "Marketing information is not claim-handling evidence."],
        "good": "PROGRESS_CLAIM", "bad": "USE_MARKETING_NOTE", "reframe": False, "closure": "CLOSE", "valid": 1,
    },
    {
        "id": "M002", "category": "near-miss-concept",
        "prompt": "A reserve estimate exists, but no payment authorization has been issued. Determine whether the claim may move to payment.",
        "facts": ["reserve_estimate=present", "payment_authorization=absent"],
        "rules": ["A reserve estimate is not payment authorization.", "Payment requires authorization."],
        "good": "DO_NOT_PAY", "bad": "TREAT_RESERVE_AS_AUTHORIZATION", "reframe": False, "closure": "CLOSE", "valid": 1,
    },
    {
        "id": "M003", "category": "multi-candidate",
        "prompt": "Two investigation routes are both evidence-compatible and preserve policy constraints; a third would bypass a mandatory control. Preserve admissible alternatives until the selection stage.",
        "facts": ["route_A=evidence_supported", "route_B=evidence_supported", "route_C=bypasses_control"],
        "rules": ["Evidence-supported routes that preserve mandatory controls remain admissible.", "A route that bypasses a mandatory control is inadmissible."],
        "good": "KEEP_ADMISSIBLE_ROUTE", "bad": "BYPASS_CONTROL", "reframe": False, "closure": "CONTINUE", "valid": 2,
    },
    {
        "id": "M004", "category": "superficial-winner",
        "prompt": "A concise explanation points to cause X, but the available evidence supports cause Y. Select the semantically supported branch.",
        "facts": ["cause_X=fluent_but_unsupported", "cause_Y=evidence_supported"],
        "rules": ["Evidence outranks linguistic fluency when selecting a causal branch."],
        "good": "SELECT_CAUSE_Y", "bad": "SELECT_CAUSE_X", "reframe": False, "closure": "CLOSE", "valid": 1,
    },
    {
        "id": "M005", "category": "reframe-required",
        "prompt": "The current analysis groups all payment failures under user error, but logs show a system-side authorization rejection that the current variables cannot represent. Preserve the original investigation goal and revise the problem model enough to represent the observed failure.",
        "facts": ["current_frame=user_error_only", "log=authorization_rejection"],
        "rules": ["Observed evidence that cannot be represented by the current frame creates a residual.", "The investigation goal must remain unchanged during reframing."],
        "good": "ADD_SYSTEM_AUTHORIZATION_VARIABLE", "bad": "KEEP_USER_ERROR_ONLY", "reframe": True, "closure": "CLOSE", "valid": 1,
    },
    {
        "id": "M006", "category": "reframe-not-required",
        "prompt": "The current variables already represent the observed failure, all evidence is explained, and the proposed additional variable has no evidence or dependency. Determine whether reframing is required.",
        "facts": ["current_frame=complete", "all_evidence=explained", "new_variable=unsupported"],
        "rules": ["Unsupported isolated variables do not justify reframing.", "Do not revise a sufficient frame without a residual."],
        "good": "PRESERVE_CURRENT_FRAME", "bad": "ADD_UNSUPPORTED_VARIABLE", "reframe": False, "closure": "CLOSE", "valid": 1,
    },
    {
        "id": "M007", "category": "false-closure-trap",
        "prompt": "The proposed answer is internally coherent, but one required evidence-backed condition remains unresolved. Determine whether the task may close.",
        "facts": ["answer=coherent", "required_condition=unresolved"],
        "rules": ["Closure requires every required condition to be resolved or explicitly authority-accepted."],
        "good": "KEEP_OPEN", "bad": "CLOSE_NOW", "reframe": False, "closure": "CONTINUE", "valid": 1,
    },
    {
        "id": "M008", "category": "valid-closure",
        "prompt": "All required constraints are satisfied, all evidence has been accounted for, and no residual remains. Determine the closure state.",
        "facts": ["constraints=satisfied", "evidence=accounted", "residuals=none"],
        "rules": ["Close when required conditions are satisfied and no unresolved residual remains."],
        "good": "CLOSE_TASK", "bad": "KEEP_SEARCHING", "reframe": False, "closure": "CLOSE", "valid": 1,
    },
    {
        "id": "M009", "category": "multiple-valid-outputs",
        "prompt": "Two different actions have equivalent semantic effects, both satisfy the constraints, and neither violates protected intent. Preserve semantic equivalence rather than requiring identical wording.",
        "facts": ["action_A=valid", "action_B=valid", "semantic_effect_A=semantic_effect_B"],
        "rules": ["Semantically equivalent valid actions are both acceptable even when surface forms differ."],
        "good": "SELECT_EQUIVALENT_VALID", "bad": "REJECT_EQUIVALENT_FOR_WORDING", "reframe": False, "closure": "CLOSE", "valid": 2,
    },
    {
        "id": "M010", "category": "domain-language-ambiguity",
        "prompt": "In this workflow, 'exposure' denotes a claim-level unit of potential liability rather than ordinary physical exposure. Determine which meaning should populate the semantic state.",
        "facts": ["workflow=claims", "term=exposure"],
        "rules": ["Within the stated claims workflow, use the domain-specific meaning of defined operational terms."],
        "good": "USE_CLAIM_EXPOSURE", "bad": "USE_GENERAL_PHYSICAL_EXPOSURE", "reframe": False, "closure": "CLOSE", "valid": 1,
    },
]


def canonical_hash(obj):
    value = dict(obj)
    value.pop("content_hash", None)
    blob = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(spec):
    fid = spec["id"]
    task = {
        "schema_version": "TASK_INPUT_V1",
        "fixture_id": fid,
        "fixture_generation": GENERATION,
        "domain": "controlled-domain-reasoning",
        "prompt": spec["prompt"],
        "context": {"facts": spec["facts"], "domain_rules": spec["rules"]},
        "source_refs": ["measurement-author-defined"],
        "protected_intent": {"goal": "Choose the semantically valid next state under the stated domain rules and evidence."},
    }

    s1 = {
        "schema_version": "S1_DOMAIN_SEMANTIC_IR_V1", "fixture_id": fid, "fixture_generation": GENERATION,
        "layer_id": "S1", "artifact_id": fid + "-S1-ORACLE", "content_hash": "", "source_refs": ["input/task.json"],
        "domain": "controlled-domain-reasoning",
        "entities": [{"id": "goal", "type": "GOAL"}] + [{"id": f"fact-{i+1}", "type": "FACT", "value": x} for i, x in enumerate(spec["facts"])],
        "relations": [{"type": "CONSTRAINS", "source": f"rule-{i+1}", "target": "goal"} for i in range(len(spec["rules"]))],
        "constraints": [{"id": f"rule-{i+1}", "type": "DOMAIN_RULE", "value": x} for i, x in enumerate(spec["rules"])],
        "goals": [{"id": "goal", "description": "Choose the semantically valid next state."}],
        "assumptions": [], "ambiguities": [],
        "oracle_constraints": {"required_elements": ["goal"] + [f"rule-{i+1}" for i in range(len(spec["rules"]))], "allowed_elements": [], "forbidden_elements": [], "equivalence_constraints": []},
    }
    s1["content_hash"] = canonical_hash(s1)

    candidates = []
    for i in range(spec["valid"]):
        cid = "v" + str(i+1)
        candidates.append({"candidate_id": cid, "semantic_transition": {"operation": spec["good"], "variant": i+1}, "claims": [{"id": cid + "-claim", "statement": "Domain-rule-compatible transition."}], "dependencies": ["goal"], "evidence_refs": ["input/task.json"]})
    candidates.append({"candidate_id": "x1", "semantic_transition": {"operation": spec["bad"]}, "claims": [{"id": "x1-claim", "statement": "Plausible but rule-incompatible transition."}], "dependencies": [], "evidence_refs": []})
    acceptable = [x["candidate_id"] for x in candidates if x["candidate_id"].startswith("v")]
    s2 = {
        "schema_version": "S2_CANDIDATE_SET_V1", "fixture_id": fid, "fixture_generation": GENERATION,
        "layer_id": "S2", "artifact_id": fid + "-S2-ORACLE", "content_hash": "", "source_refs": ["oracle/s1_domain_semantic_ir.json"],
        "semantic_ir_hash": s1["content_hash"], "candidates": candidates,
        "oracle_constraints": {"required_candidate_semantics": [spec["good"], spec["bad"]], "acceptable_candidate_ids": acceptable, "forbidden_candidate_semantics": []},
    }
    s2["content_hash"] = canonical_hash(s2)

    s3 = {
        "schema_version": "S3_SELECTED_REFRAMED_STATE_V1", "fixture_id": fid, "fixture_generation": GENERATION,
        "layer_id": "S3", "artifact_id": fid + "-S3-ORACLE", "content_hash": "", "source_refs": ["oracle/s2_candidate_set.json"],
        "candidate_set_hash": s2["content_hash"],
        "selection": {"selected_candidate_ids": acceptable, "rejected_candidate_ids": ["x1"], "decision_reasons": ["domain rules and evidence"], "ranking": acceptable + ["x1"]},
        "framing": {"reframe_required": spec["reframe"], "trigger_residuals": [{"type": "MODEL_CANNOT_REPRESENT_OBSERVATION"}] if spec["reframe"] else [], "state": {"selected_operation": spec["good"]}, "revision_operations": [{"operation": "ADD"}] if spec["reframe"] else [], "protected_intent": task["protected_intent"]},
        "oracle_constraints": {"acceptable_selected_candidate_ids": acceptable, "reframe_required": spec["reframe"], "required_residuals": ["MODEL_CANNOT_REPRESENT_OBSERVATION"] if spec["reframe"] else [], "forbidden_selections": ["x1"], "goal_fidelity_constraints": ["protected intent preserved"]},
    }
    s3["content_hash"] = canonical_hash(s3)

    residuals = [{"type": "REQUIRED_CONDITION_UNRESOLVED", "required": True}] if spec["closure"] == "CONTINUE" else []
    s4 = {
        "schema_version": "S4_CLOSURE_EXECUTION_RESULT_V1", "fixture_id": fid, "fixture_generation": GENERATION,
        "layer_id": "S4", "artifact_id": fid + "-S4-ORACLE", "content_hash": "", "source_refs": ["oracle/s3_selected_reframed_state.json"],
        "selected_state_hash": s3["content_hash"],
        "execution": {"actions": [{"type": spec["good"], "target": "goal"}], "evidence_refs": ["input/task.json"], "result_state": {"selected_valid": True}},
        "closure": {"class": spec["closure"], "residuals": residuals, "decision_reasons": ["required conditions evaluated"], "evidence_sufficient": spec["closure"] == "CLOSE"},
        "oracle_constraints": {"acceptable_closure_classes": [spec["closure"]], "required_residuals": [r["type"] for r in residuals], "forbidden_closure_classes": ["CLOSE"] if spec["closure"] == "CONTINUE" else [], "required_execution_effects": ["selected_valid"]},
    }
    s4["content_hash"] = canonical_hash(s4)

    hidden = {
        "fixture_id": fid, "fixture_generation": GENERATION, "category": spec["category"],
        "acceptable_candidate_ids": acceptable, "reframe_required": spec["reframe"], "closure_class": spec["closure"],
    }
    manifest = {
        "protocol_version": PROTOCOL, "fixture_id": fid, "fixture_generation": GENERATION, "status": "REVIEWED",
        "domain": "controlled-domain-reasoning", "tags": ["measurement"],
        "artifact_refs": {"task": "input/task.json", "s1_oracle": "oracle/s1_domain_semantic_ir.json", "s2_oracle": "oracle/s2_candidate_set.json", "s3_oracle": "oracle/s3_selected_reframed_state.json", "s4_oracle": "oracle/s4_closure_execution_result.json"},
        "oracle_independence": {"method": "Hidden spec authored before tested implementation output.", "reviewed_against_test_implementations": False, "review_notes": []},
        "hashes": {"task": canonical_hash(task), "s1_oracle": s1["content_hash"], "s2_oracle": s2["content_hash"], "s3_oracle": s3["content_hash"], "s4_oracle": s4["content_hash"]},
        "freeze": None,
    }
    return task, s1, s2, s3, s4, hidden, manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="fixtures/phase1_v2/generated")
    args = ap.parse_args()
    root = Path(args.out)
    rows = []
    for spec in SPECS:
        task, s1, s2, s3, s4, hidden, manifest = build(spec)
        d = root / spec["id"]
        for rel, obj in [
            ("input/task.json", task),
            ("oracle/s1_domain_semantic_ir.json", s1),
            ("oracle/s2_candidate_set.json", s2),
            ("oracle/s3_selected_reframed_state.json", s3),
            ("oracle/s4_closure_execution_result.json", s4),
            ("hidden/evaluation.json", hidden),
            ("fixture_manifest.json", manifest),
        ]:
            write_json(d / rel, obj)
        rows.append({"fixture_id": spec["id"], "category": spec["category"]})
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(json.dumps({"fixture_generation": GENERATION, "fixture_count": len(rows), "spec_digest": digest}, indent=2))


if __name__ == "__main__":
    main()
