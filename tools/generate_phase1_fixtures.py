#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

GENERATION = "phase1_v1"
PROTOCOL = "PHASE1_ARTIFACT_CONTRACT_V1"

SCENARIOS = [
    ("P1-001-direct-semantic", "direct-semantic", "Extract the domain-semantic structure and ignore an irrelevant linguistic distractor.", "APPLY_EVIDENCE_SUPPORTED_RULE", "PROMOTE_DISTRACTOR", False, "CLOSE", 1),
    ("P1-002-near-miss-concept", "near-miss-concept", "A domain term has a common-language near-synonym that is invalid in the domain. Preserve the domain-specific concept and reject the near miss.", "SELECT_DOMAIN_CONCEPT", "SELECT_NEAR_MISS", False, "CLOSE", 1),
    ("P1-003-multi-candidate", "multi-candidate", "Three semantic branches are plausible. Two satisfy the domain constraints and one violates a protected invariant. Preserve both valid branches until selection.", "SELECT_VALID_BRANCH", "SELECT_INVALID_BRANCH", False, "CONTINUE", 2),
    ("P1-004-superficial-winner", "superficial-winner", "The most fluent candidate conflicts with explicit evidence while a less fluent candidate is evidence-supported. Select by evidence, not linguistic plausibility.", "SELECT_EVIDENCE_BRANCH", "SELECT_FLUENT_UNSUPPORTED", False, "CLOSE", 1),
    ("P1-005-reframe-required", "reframe-required", "The initial problem framing cannot satisfy the stated success condition. A local framing revision is required while protected intent must remain unchanged.", "REFRAME_AND_SELECT", "PRESERVE_BROKEN_FRAME", True, "CLOSE", 1),
    ("P1-006-reframe-not-required", "reframe-not-required", "The current framing already satisfies the success condition. A proposed reframe adds complexity without resolving any residual and must be rejected.", "PRESERVE_FRAME", "UNNECESSARY_REFRAME", False, "CLOSE", 1),
    ("P1-007-false-closure-trap", "false-closure-trap", "A locally coherent answer remains missing one required evidence-backed condition. Closing now would be a false closure.", "KEEP_OPEN_FOR_RESIDUAL", "CLOSE_EARLY", False, "CONTINUE", 1),
    ("P1-008-valid-closure", "valid-closure", "All required constraints, evidence, and success conditions are satisfied. Close without introducing additional revisions.", "CLOSE_VALIDLY", "KEEP_SEARCHING", False, "CLOSE", 1),
    ("P1-009-multiple-valid-outputs", "multiple-valid-outputs", "Two semantically equivalent transitions satisfy the task. Surface wording differs, but both preserve intent and satisfy all constraints.", "SELECT_EQUIVALENT_VALID", "REJECT_ALL_EQUIVALENTS", False, "CLOSE", 2),
    ("P1-010-domain-language-ambiguity", "domain-language-ambiguity", "A phrase has a general-language interpretation and a domain-specific interpretation. The domain context constrains which semantic reading is valid.", "SELECT_DOMAIN_READING", "SELECT_GENERAL_READING", False, "CLOSE", 1),
]


def canonical_hash(obj, omit_content_hash=False):
    value = dict(obj)
    if omit_content_hash:
        value.pop("content_hash", None)
    blob = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_fixture(fid, tag, prompt, good, bad, reframe, closure, valid_count):
    task = {
        "schema_version": "TASK_INPUT_V1", "fixture_id": fid, "fixture_generation": GENERATION,
        "domain": "generic-domain-reasoning", "prompt": prompt,
        "context": {"goal": "Choose the semantically valid next state under explicit domain constraints.", "domain_rules": ["Evidence and protected intent outrank surface-language plausibility."], "scenario": tag},
        "source_refs": ["fixture-author-defined"],
        "protected_intent": {"goal": "Preserve the stated task objective and domain constraints."},
        "notes_for_fixture_author": ["Oracle authored independently of tested implementations."]
    }
    s1 = {
        "schema_version": "S1_DOMAIN_SEMANTIC_IR_V1", "fixture_id": fid, "fixture_generation": GENERATION, "layer_id": "S1", "artifact_id": fid + "-S1-ORACLE", "content_hash": "",
        "source_refs": ["input/task.json"], "domain": "generic-domain-reasoning",
        "entities": [{"id": "goal", "type": "GOAL"}, {"id": "rule-1", "type": "DOMAIN_RULE"}],
        "relations": [{"type": "CONSTRAINS", "source": "rule-1", "target": "goal"}],
        "constraints": [{"id": "c1", "type": "EVIDENCE_REQUIRED"}, {"id": "c2", "type": "PROTECTED_INTENT"}],
        "goals": [{"id": "g1", "description": "Choose a semantically valid next state."}], "assumptions": [],
        "ambiguities": [{"id": "a1", "scenario": tag}] if tag in {"near-miss-concept", "domain-language-ambiguity", "multiple-valid-outputs"} else [],
        "oracle_constraints": {"required_elements": ["goal", "rule-1", "EVIDENCE_REQUIRED", "PROTECTED_INTENT"], "allowed_elements": [], "forbidden_elements": [], "equivalence_constraints": ["surface-form differences do not imply semantic inequality"] if tag == "multiple-valid-outputs" else []}
    }
    candidates = [{"candidate_id": "c-valid", "semantic_transition": {"operation": good, "target": "goal"}, "claims": [{"id": "claim-valid", "statement": "Constraint-compatible semantic transition."}], "dependencies": ["rule-1"], "evidence_refs": ["rule-1"]}]
    if valid_count == 2:
        candidates.append({"candidate_id": "c-valid-2", "semantic_transition": {"operation": good, "target": "goal", "variant": "B"}, "claims": [{"id": "claim-valid-2", "statement": "Second semantically valid transition."}], "dependencies": ["rule-1"], "evidence_refs": ["rule-1"]})
    candidates.append({"candidate_id": "c-invalid", "semantic_transition": {"operation": bad, "target": "goal"}, "claims": [{"id": "claim-invalid", "statement": "Plausible but constraint-incompatible transition."}], "dependencies": [], "evidence_refs": []})
    acceptable = [c["candidate_id"] for c in candidates if c["candidate_id"].startswith("c-valid")]
    s2 = {
        "schema_version": "S2_CANDIDATE_SET_V1", "fixture_id": fid, "fixture_generation": GENERATION, "layer_id": "S2", "artifact_id": fid + "-S2-ORACLE", "content_hash": "", "source_refs": ["oracle/s1_domain_semantic_ir.json"], "semantic_ir_hash": "",
        "candidates": candidates, "oracle_constraints": {"required_candidate_semantics": [good, bad], "acceptable_candidate_ids": acceptable, "forbidden_candidate_semantics": []}
    }
    s3 = {
        "schema_version": "S3_SELECTED_REFRAMED_STATE_V1", "fixture_id": fid, "fixture_generation": GENERATION, "layer_id": "S3", "artifact_id": fid + "-S3-ORACLE", "content_hash": "", "source_refs": ["oracle/s2_candidate_set.json"], "candidate_set_hash": "",
        "selection": {"selected_candidate_ids": acceptable, "rejected_candidate_ids": ["c-invalid"], "decision_reasons": [], "ranking": acceptable + ["c-invalid"]},
        "framing": {"reframe_required": reframe, "trigger_residuals": [{"type": "FRAMING_INADEQUATE"}] if reframe else [], "state": {"scenario": tag, "selected_operation": good}, "revision_operations": [{"operation": "REABSTRACT"}] if reframe else [], "protected_intent": {"goal": "Preserve the stated task objective and domain constraints."}},
        "oracle_constraints": {"acceptable_selected_candidate_ids": acceptable, "reframe_required": reframe, "required_residuals": ["FRAMING_INADEQUATE"] if reframe else [], "forbidden_selections": ["c-invalid"], "goal_fidelity_constraints": ["protected intent preserved"]}
    }
    residuals = [{"type": "REQUIRED_CONDITION_UNRESOLVED", "required": True}] if closure == "CONTINUE" else []
    s4 = {
        "schema_version": "S4_CLOSURE_EXECUTION_RESULT_V1", "fixture_id": fid, "fixture_generation": GENERATION, "layer_id": "S4", "artifact_id": fid + "-S4-ORACLE", "content_hash": "", "source_refs": ["oracle/s3_selected_reframed_state.json"], "selected_state_hash": "",
        "execution": {"actions": [{"type": good, "target": "goal"}], "evidence_refs": ["rule-1"], "result_state": {"scenario": tag, "selected_valid": True}},
        "closure": {"class": closure, "residuals": residuals, "decision_reasons": [], "evidence_sufficient": closure == "CLOSE"},
        "oracle_constraints": {"acceptable_closure_classes": [closure], "required_residuals": [x["type"] for x in residuals], "forbidden_closure_classes": ["CLOSE"] if closure == "CONTINUE" else [], "required_execution_effects": ["selected_valid"]}
    }
    for obj in (s1, s2, s3, s4):
        obj["content_hash"] = canonical_hash(obj, omit_content_hash=True)
    s2["semantic_ir_hash"] = s1["content_hash"]
    s3["candidate_set_hash"] = s2["content_hash"]
    s4["selected_state_hash"] = s3["content_hash"]
    manifest = {
        "protocol_version": PROTOCOL, "fixture_id": fid, "fixture_generation": GENERATION, "status": "REVIEWED", "domain": "generic-domain-reasoning", "tags": [tag],
        "artifact_refs": {"task": "input/task.json", "s1_oracle": "oracle/s1_domain_semantic_ir.json", "s2_oracle": "oracle/s2_candidate_set.json", "s3_oracle": "oracle/s3_selected_reframed_state.json", "s4_oracle": "oracle/s4_closure_execution_result.json"},
        "oracle_independence": {"method": "Authored from task/domain rules before implementation comparison.", "reviewed_against_test_implementations": False, "review_notes": []},
        "hashes": {"task": canonical_hash(task), "s1_oracle": s1["content_hash"], "s2_oracle": s2["content_hash"], "s3_oracle": s3["content_hash"], "s4_oracle": s4["content_hash"]}, "freeze": None
    }
    return task, s1, s2, s3, s4, manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="fixtures/phase1_v1/generated")
    args = ap.parse_args()
    root = Path(args.out)
    rows = []
    for scenario in SCENARIOS:
        fid = scenario[0]
        task, s1, s2, s3, s4, manifest = build_fixture(*scenario)
        d = root / fid
        for rel, obj in [("input/task.json", task), ("oracle/s1_domain_semantic_ir.json", s1), ("oracle/s2_candidate_set.json", s2), ("oracle/s3_selected_reframed_state.json", s3), ("oracle/s4_closure_execution_result.json", s4), ("fixture_manifest.json", manifest)]:
            write_json(d / rel, obj)
        h = hashlib.sha256()
        for p in sorted(d.rglob("*.json")):
            h.update(str(p.relative_to(d)).encode() + b"\0" + p.read_bytes() + b"\0")
        rows.append({"fixture_id": fid, "fixture_digest": h.hexdigest()})
    dataset_digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(json.dumps({"fixture_generation": GENERATION, "fixture_count": len(rows), "dataset_digest": dataset_digest, "fixtures": rows}, indent=2))

if __name__ == "__main__":
    main()
