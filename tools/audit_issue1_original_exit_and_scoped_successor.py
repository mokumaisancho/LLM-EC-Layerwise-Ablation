#!/usr/bin/env python3
"""Origin #1: honest frozen-protocol exit gate and successor-scope reconciliation.

Reads pinned, already-executed experimental artifacts and *actually* replays
the frozen Phase1 v2 TCC. It does NOT relabel incompatible EC-native semantics,
score raw data as independent, or assume ACs passed because an issue closed.

Terminal: old Phase1 frozen A/B/C/D/E specification unmeasurable under the
actual EC native interface; bounded follow-on empirical result valid in its
own narrower scope. This is an exit-decision gate, never fake completion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "original_contract": "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json",
    "successor_contract": "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_V2_2026-10-03.json",
    "frozen_actual": "results/phase1_mvp_tcc_v2_actual_2026-10-03.json",
    "adapter": "results/ec_native_adapter_qualification.json",
    "s4_identifiability": "results/phase1_s4_identifiability_audit_2026-10-03.json",
    "next_action": "results/function_boundary_next_action_v2_actual_2026-10-03.json",
    "successor_boundary": "results/s1c_semantic_space_final_boundary_2026-10-08.json",
    "s1c_terminal": "results/s1c_v32_audited_terminal_2026-10-08.json",
    "s1c_actual": "results/s1c_v32_paired_actual_2026-10-08.json",
    "issue57_method": "results/issue57_conservation_gate_verification_2026-10-09.json",
}


class EvidenceError(ValueError):
    pass


def require(test: bool, reason: str):
    if not test:
        raise EvidenceError(reason)


def fetch(directory: Path, name: str) -> tuple[dict, str]:
    path = directory / PATHS[name]
    require(path.is_file() and not path.is_symlink(), "REQUIRED_PINNED_EVIDENCE_MISSING:" + name)
    data = path.read_bytes()
    require(len(data) < 8_000_000, "EVIDENCE_TOO_LARGE:" + name)
    return json.loads(data), hashlib.sha256(data).hexdigest()


def s4_structural_identifiability(audit: dict) -> dict:
    groups = audit["collision_groups"]
    separately = audit["separately_identifiable"]
    require(len(groups) > 0, "MISSING_COLLISION_GROUPS")
    signatures: set[str] = set()
    unique_ids: set[str] = set()
    counts = Counter()
    majority_best = 0
    for group in groups:
        key = json.dumps(group["signature"], sort_keys=True, separators=(",",":"))
        require(key not in signatures, "DUPLICATE_SIGNATURE")
        signatures.add(key)
        labels = group["closure_labels"]
        require(len(labels) >= 2, "NOT_AN_AMBIGUOUS_COLLISION")
        count_by_label = []
        for label, ids in labels.items():
            require(label in ("CLOSE", "CONTINUE"), "UNKNOWN_CLOSURE_LABEL")
            require(isinstance(ids,list) and ids, "EMPTY_CLOSURE_GROUP")
            require(not unique_ids.intersection(ids), "COLLISION_FIXTURE_OVERLAP")
            unique_ids.update(ids)
            counts[label] += len(ids)
            count_by_label.append(len(ids))
        majority_best += max(count_by_label)
    for row in separately:
        fixture_id = row["fixture_id"]
        require(fixture_id not in unique_ids, "SEPARATE_FIXTURE_OVERLAP")
        require(row["closure"] in ("CLOSE", "CONTINUE"), "INVALID_SEPARATE_LABEL")
        unique_ids.add(fixture_id)
        majority_best += 1
        counts[row["closure"]] += 1
    s = audit["identifiability"]
    require(len(unique_ids)==audit["fixture_count"]==s["total"]==10, "IDENTIFIABILITY_SAMPLE_DRIFT")
    require(majority_best==s["best_possible_majority_correct"]==8, "IDENTIFIABILITY_BOUND_NOT_REPRODUCED")
    require(s["closure_is_deterministic_function_of_structural_signature"] is False, "FALSELY_IDENTIFIABLE")
    require(s["metric_type"]=="INTERFACE_IDENTIFIABILITY_BOUND_NOT_EC_ACCURACY", "INTERFACE_METRIC_RELABELED")
    return {"unique_fixture_count":len(unique_ids), "max_majority_correct":majority_best,
            "structural_upper_bound":majority_best/len(unique_ids),
            "labels":dict(counts), "not_ec_accuracy": True,
            "input_aliasing_is_real": True}


def verify(directory: Path, *, actual_replay: bool = False) -> dict:
    values, pins = {}, {}
    for name in PATHS:
        values[name], pins[name] = fetch(directory,name)
    c=values["original_contract"]
    require(c["protocol"]=="PHASE1_MVP_TCC_V1", "ORIGINAL_CONTRACT_CHANGED")
    require(c["canonical_inputs"]["phase1_v2_dataset_sha256"]=="8bfce027bdc82a34b78e9b1a87f7812d907db34c164f50a9a996bd41b3b824d6", "FROZEN_CASES_CHANGED")
    require(c["canonical_inputs"]["ec_commit"]=="d5ec423968f1c9242c590e5e77ccfd92d1f59eb2", "EC_NATIVE_PIN_CHANGED")
    require(c["frozen_thresholds"]["oracle_substitution_gain_material_abs"]==0.20, "THRESHOLD_CHANGED")
    require(c["mvp"]["required_ac"] and len(c["mvp"]["required_ac"])==18,"REQUIRED_AC_COUNT_CHANGED")
    require((directory/".github/workflows").exists() is False or not any((directory/".github/workflows").iterdir()), "GITHUB_ACTIONS_NOT_ALLOWED")

    newer=values["successor_contract"]
    require(newer["protocol"]=="PHASE1_MVP_TCC_V2", "SUCCESSOR_PROTOCOL_MISMATCH")
    prev=values["frozen_actual"]
    require(prev["terminal_state"]=="EC_NATIVE_SCOPE_INCOMPATIBLE","FALSE_SUCCESS_ON_INCOMPATIBLE_DATA")
    require(prev["foundation"]["status"]=="PASS", "FOUNDATION_FAILED")
    require(prev["foundation"]["dataset_digest"]==c["canonical_inputs"]["phase1_v2_dataset_sha256"],"FOUNDATION_DATA_DRIFT")
    require(prev["adapter_qualification"]["status"]=="INCOMPATIBLE","FROZEN_ADAPTER_STATE_CHANGED")
    require(prev["dependency_decision"]["downstream_issue22_required"] is False,"INVALID_BACKPROPAGATED_DEPENDENCY")
    require(prev["fixtures_changed"] is False and prev["thresholds_changed"] is False,"FROZEN_PROTOCOL_MUTATED")

    adapter=values["adapter"]
    require(adapter["protocol"]=="PHASE1_EC_NATIVE_ADAPTER_V1" and adapter["status"]=="INCOMPATIBLE","ADAPTER_QUALIFICATION_REWRITTEN")
    require(adapter["oracle_blind"] is True,"ADAPTER_ORACLE_LEAK")
    auth=adapter["subfunction_authority"]
    require(auth["s3_reframing"]["authority"]=="EC_NATIVE","EC_NATIVE_REFRAME_PROVENANCE_LOST")
    for name in ("s3_selection","s4_closure"):
        require(auth[name]["authority"]=="EC_NATIVE_NOT_APPLICABLE" and not auth[name]["reportable"],
                "FORGED_EC_NATIVE_AUTHORITY:"+name)
    require(adapter["ec_source"]["commit"]==c["canonical_inputs"]["ec_commit"],"EC_PROVENANCE_DRIFT")

    bound=s4_structural_identifiability(values["s4_identifiability"])
    require(abs(bound["structural_upper_bound"]-auth["s4_closure"]["structural_upper_bound"])<1e-15,"BOUND_AND_AUTH_CONFLICT")
    require(set(adapter["qualification_evidence"]["s3_selection"]["phase1_multi_select_fixtures"])=={"M003","M009"},
            "S3_MULTIPLE_SELECTION_COUNTEREXAMPLES_CHANGED")

    next_action=values["next_action"]
    require(next_action["status"]=="REPORTABLE","NATIVE_SUCCESSOR_MISSING")
    require(next_action["ec"]["decision_correct"]==next_action["fixture_count"]==17,"NATIVE_NEXT_ACTION_NOT_EXACT")
    require(next_action["ec"]["commit"]==c["canonical_inputs"]["ec_commit"], "SUCCESSOR_EC_COMMIT_DRIFT")
    require(next_action["assay_scope"]["shared_function"].startswith("structured governed"),"UNFROZEN_SHARED_FUNCTION")

    final=values["successor_boundary"]
    require(final["terminal"]=="V32_DETERMINISTIC_MATERIAL_ADVANTAGE","SUCCESSOR_TERMINAL_CHANGED")
    require(final["research_status"]=="COMPLETE_FOR_CURRENT_MVP_BOUNDARY","SUCCESSOR_SCOPE_UNVERIFIED")
    require(final["root_issue"]==48, "WRONG_SUCCESSOR_PROVENANCE")
    terminal=values["s1c_terminal"]
    require(terminal["terminal"]==final["terminal"],"S1C_TERMINAL_CONFLICT")
    require(terminal["evidence"]["paired_runtime_sha256"]==pins["s1c_actual"],"S1C_ACTUAL_OUTPUT_SHA_DRIFT")
    require(terminal["evidence"]["paired_runtime_sha256"]==final["canonical_evidence"]["paired_runtime_sha256"],"S1C_FINAL_PIN_CONFLICT")
    require(terminal["gates"]["result_overturning_gate_failures"]==0,"S1C_AUDIT_FAIL")
    require(terminal["gates"]["fixed_b2_causal_replay"]=="PASS","S1C_CAUSAL_REPLAY_FAIL")
    require(terminal["gates"]["model_reinference"] is False,"S1C_MODEL_RERUN_CONFUSION")

    current=values["s1c_actual"]
    require(current["model"]["sha256"]=="1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370",
            "ORIGINAL_QWEN_MODEL_MISMATCH")
    require(len(current["raw_qwen_rows"])==8,"RAW_EVIDENCE_COUNT_CHANGED")
    require(final["limitation"] and len(final["architectural_implication"]["not_established"])>=3,"SUCCESSOR_LIMITATIONS_DROPPED")

    independent=values["issue57_method"]
    require(independent.get("scientific_four_arm_run","NOT_RUN")!="PASS","FALSE_FULL_INDEPENDENT_COMPARISON")
    replay = {"performed":False, "terminal":None, "rc":None}
    if actual_replay:
        script=directory/"tools/run_phase1_mvp_tcc_v2.py"
        require(script.is_file() and not script.is_symlink(),"V2_RUNNER_MISSING")
        run=subprocess.run([sys.executable,str(script)], cwd=directory,
                           capture_output=True,text=True,timeout=90)
        try:
            live=json.loads(run.stdout)
        except json.JSONDecodeError as exc:
            raise EvidenceError("FROZEN_REPLAY_OUTPUT_NOT_JSON") from exc
        require(run.returncode==4 and live["terminal_state"]=="EC_NATIVE_SCOPE_INCOMPATIBLE",
                "FROZEN_TCC_REPLAY_RESULT_CHANGED")
        gates=[x["gate"] for x in live["history"]]
        require(gates==["P0_EARLY_PRECHECK","P1_FOUNDATION_GATE","P2_EC_ADAPTER_GATE"],
                "FROZEN_TCC_GATE_SEQUENCE_CHANGED")
        replay={"performed":True,"terminal":live["terminal_state"],"rc":run.returncode,
                "gates":gates,"early_precheck_status":live["history"][0]["result"]["status"]}
    return {
        "protocol":"ISSUE1_ORIGINAL_VS_SUCCESSOR_ACCEPTANCE_RECONCILIATION_V1",
        "source_pins_sha256":pins,
        "frozen_tcc_replay":replay,
        "original_issue":1,
        "original_exit_pass":False,
        "original_phase1_exit":"EC_NATIVE_SCOPE_INCOMPATIBLE",
        "original_requested_five_arm_protocol":"UNREPORTABLE_BY_NATIVE_INTERFACE_MISMATCH",
        "original_missing_condition":"A/B/C/D/E same-function comparability for native EC S3 selection and S4 closure",
        "s3": {"ec_native_selection_status":"NOT_APPLICABLE","counterexample_fixtures":["M003","M009"]},
        "s4": bound,
        "completed_scoped_successor":{
            "scope":"Finite 64-function explicit typed-space semantic partition under V3.2; not unrestricted natural-language semantic invention",
            "ec_native_next_action_accuracy_on_17_frozen_fixtures":1.0,
            "next_action_is_separate_from_generic_S3_all_admissible_selection":True,
            "s1c_terminal":final["terminal"],
            "s1c_limitations":final["architectural_implication"]["not_established"],
            "source_report":"results/s1c_semantic_space_final_boundary_2026-10-08.json",
            "scoped_study_status":"COMPLETE_FOR_CURRENT_MVP_BOUNDARY",
        },
        "independent_original_LLM0_four_arm_quality":"NOT_RUN",
        "issue57_scientific_certification":False,
        "unresolved_external_evidence":[
            "Independent previously unseen judged corpus+separate gold custody (#57)",
            "Original LLM0 model identity and authentic same-case predictions (#57)",
            "Owner-authorized matching V4 policy/execution (#57)",
        ],
        "strict_original_exit_gate":"BLOCKED_INTERFACE_SEMANTICS",
        "issue1_auto_closure_authorized":False,
        "prohibited_overclaims":[
            "Current S1C scoped success proves full original S1/S2/S3/S4 five-arm oracle study",
            "8/10 S4 interface limit is measured EC decision accuracy",
            "Closed superseded issue #20/#22/#23/#24 means original AC automatically passed",
            "H01-H16 development fixture is independent human-adjudicated gold",
        ],
        "terminal":"FROZEN_ORIGINAL_UNREPORTABLE_SCOPED_SUCCESSOR_AUDITED_COMPLETE",
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=ROOT)
    ap.add_argument("--replay",action="store_true")
    a=ap.parse_args()
    try:
        result=verify(a.root,actual_replay=a.replay)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"protocol":"ISSUE1_ORIGINAL_VS_SUCCESSOR_ACCEPTANCE_RECONCILIATION_V1",
                          "terminal":"FAIL_CLOSED","error":type(exc).__name__+":"+str(exc)[:300]}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
