#!/usr/bin/env python3
"""Root issue #1: AC-driven, preflighted, source-pinned, one-invocation TCC v6.

No false root success from a scoped native-next-action study. Executes all
machine-feasible descendants, then generates AC-level dependency/next-work
evidence. A native API that cannot perform the frozen generic multi-selection
or identify closure is a SOURCE CAPABILITY blocker, not a prompt-loop signal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_issue57_tcc_generator_gate import TCC_SOURCE, context_for, node
from tools.audit_issue1_original_exit_and_scoped_successor import verify as verify_origin
from tools.run_issue1_autonomous_tcc_workflow_v5 import run as run_stage5

PROTOCOL = "ISSUE1_ORIGINAL_AC_DEPENDENCY_DRIVEN_TCC_V6"
CFG = ROOT / "docs/ISSUE1_ROOT_AC_MVP_DEPENDENCY_ORCHESTRATION_V6.json"
CONFIG_FROZEN_BLOB = "858c93bb2d0b7e2bed73f1bf29cb4fa55e19f605"
SCOPED_RAW = [
    "fixtures/function_boundary_next_action_v1.json",
    "docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json",
    "results/issue1_ecv44_native_next_action_v2_local_replay_2026-10-10.json",
    "results/issue1_qwen_next_action_v2_mac_actual_2026-10-10.json",
    "results/issue1_s4_qwen20_paired_info_ablation_actual_2026-10-10.json",
    "results/issue1_public_gate_gbnf_qwen17_actual_2026-10-10.json",
    "results/phase1_mvp_tcc_v2_actual_2026-10-03.json",
]


class Abort(ValueError):
    pass


def require(predicate: bool, code: str) -> None:
    if not predicate:
        raise Abort(code)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def git_head(repo: Path) -> str:
    p = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                       text=True, capture_output=True, timeout=12)
    require(p.returncode == 0 and len(p.stdout.strip()) == 40, "SOURCE_GIT_HEAD_UNAVAILABLE")
    return p.stdout.strip()


def frozen_sources(config: dict, root: Path = ROOT) -> dict:
    """G0/G7: source blobs fixed in *predeclared* v6 JSON, not self-pinned live hashes."""
    require(config.get("schema") == "issue1.ac-orchestration.v6", "ORCHESTRATION_SCHEMA_DRIFT")
    pins = config["source_git_blobs"]
    actual = {}
    for name, expected in pins.items():
        p = root / name
        require(p.is_file() and not p.is_symlink(), "FROZEN_SOURCE_MISSING:" + name)
        raw = p.read_bytes()
        require(len(raw) < 5_000_000, "SOURCE_UNEXPECTEDLY_LARGE:" + name)
        value = git_blob(raw)
        require(value == expected, "G0_FROZEN_SOURCE_BLOB_CHANGED:" + name)
        actual[name] = value
    frozen = json.loads((root / config["frozen_normative_contract"]).read_text())
    require(frozen["protocol"] == config["scientific_protocol"], "G7_ORIGINAL_PROTOCOL_CHANGED")
    require(frozen["frozen_thresholds"]["oracle_substitution_gain_material_abs"] ==
            config["frozen_materiality"] == 0.20, "G7_THRESHOLD_CHANGED")
    require(config["mvp_name"] == "ORIGINAL_ROOT_COARSE_4_LAYER_CAUSAL_LOCALIZATION",
            "ROOT_MVP_RELABELED")
    require(config["provenance_rules"]["scoped_native_success_as_root_exit"] == "FORBIDDEN",
            "SCOPED_SUCCESS_OVERRIDE")
    return actual


def ac_dag(norm: dict, *, ac_text: str) -> dict:
    """G1/G2: topological closure of exact normative 20 AC; strict issue-reference validation."""
    expected = {"AC-" + str(i).zfill(2) for i in range(1, 21)}
    keys = re.findall(r"^AC-(\d\d)\.", ac_text, re.M)
    require(len(keys) == 20 and {"AC-" + n for n in keys} == expected and len(set(keys)) == 20,
            "G1_AC_TEXT_NOT_EXACTLY_20")
    deps = norm["ac_dependencies"]
    require(set(deps) == expected, "G1_AC_DEPENDENCY_TABLE_NOT_COMPLETE")
    required = norm["mvp"]["required_ac"]
    optional = norm["mvp"]["post_mvp_ac"]
    require(len(required) == len(set(required)) == 18 and set(required) | set(optional) == expected
            and set(required).isdisjoint(optional), "G2_MVP_18_OF_18_REDEFINED")
    issues = norm["issue_dependencies"]
    ac_links = {}
    issue_links = {}
    for ac, parents in deps.items():
        direct = []
        for parent in parents:
            if parent.startswith("AC-") and parent != "AC-10_IF_NEEDED":
                require(parent in expected, "G1_UNKNOWN_AC_PARENT:" + ac + ":" + parent)
                direct.append(parent)
            elif parent == "AC-10_IF_NEEDED":
                require(ac == "AC-18" and "AC-10" in optional, "G1_INVALID_OPTIONAL_DEPENDENCY")
            elif parent.startswith("ISSUE-"):
                require(parent in issues, "G1_UNKNOWN_ISSUE_PARENT:" + parent)
            else:
                raise Abort("G1_INVALID_DEPENDENCY_REF:" + str(parent))
        ac_links[ac] = direct
        issue_links[ac] = [p for p in parents if p.startswith("ISSUE-")]
    unseen = set(expected)
    order = []
    while unseen:
        ready = sorted(k for k in unseen if set(ac_links[k]).issubset(order))
        require(bool(ready), "G1_AC_DEPENDENCY_CYCLE")
        order.extend(ready)
        unseen -= set(ready)
    jobs = norm["issue_dependencies"]
    for issue, data in jobs.items():
        for dependency in data.get("depends_on", []):
            require(dependency in jobs or dependency in norm.get("logical_dependencies", {}) or
                    (issue == "ISSUE-1" and dependency in {"ARMS_A_B_C_D_E", "SCORE_AND_GAIN"}),
                    "G1_ISSUE_DEPENDENCY_UNKNOWN:" + issue + ":" + dependency)
    return {
        "required": required, "post_mvp": optional, "topological_order": order,
        "AC_dependencies": ac_links, "issue_dependencies": issue_links,
        "root_issue_depends_on": jobs["ISSUE-1"]["depends_on"],
        "original_threshold": norm["frozen_thresholds"]["oracle_substitution_gain_material_abs"],
    }


def check_work_graph(config: dict) -> list[str]:
    jobs = config["work_items"]
    keys = [j["id"] for j in jobs]
    require(len(keys) == len(set(keys)), "G1_DUPLICATE_WORK_ID")
    seen = set()
    for job in jobs:
        require(all(parent in seen for parent in job["depends_on"]),
                "G1_WORK_NOT_TOPOLOGICALLY_ORDERED:" + job["id"])
        require(job["priority"] in ("P0", "P1"), "G1_WORK_PRIORITY_MISSING")
        seen.add(job["id"])
    require(keys == [
        "W0_SOURCE_LOCK", "W1_DEPENDENCY_GRAPH", "W2_NATIVE_CONTRACT_QUALIFICATION",
        "W3_LOCAL_ACTUAL_EXPERIMENTS", "W4_VERSIONED_NATIVE_REPAIR_PLAN",
        "W5_FOUR_LAYER_ACTUAL_AE", "W6_LOCALIZE_MVP", "W7_INDEPENDENT_REVIEW"
    ], "ROOT_CRITICAL_PATH_CHANGED")
    return keys


def scientific_source_seal(root: Path = ROOT) -> dict:
    """G0/G7: all executable scientific source must match tracked HEAD blobs,
    rejecting dirty/uncommitted code that would silently invalidate validation.
    """
    names = [
        "tools/run_issue1_root_ac_orchestrator_v6.py",
        "tools/run_issue1_autonomous_tcc_workflow_v5.py",
        "tools/run_issue1_autonomous_tcc_workflow_v4.py",
        "tools/run_issue1_autonomous_tcc_workflow_v3.py",
        "tools/run_issue1_autonomous_tcc_workflow_v2.py",
        "tools/run_issue1_autonomous_tcc_workflow.py",
        "tools/audit_issue1_original_exit_and_scoped_successor.py",
        "tools/run_issue1_ecv44_native_next_action_v2.py",
        "tools/run_issue1_llm_next_action_v2_local_mac.py",
        "tools/run_issue1_s4_public_info_paired_llm_v1.py",
        "tools/run_issue1_s3_native_next_action_oracle_causal_v1.py",
        "tools/run_issue1_public_gate_gbnf_ablation_v1.py",
        "tools/run_issue1_s3_public_dynamic_guard_v2.py",
    ]
    # Paths use tracked Git file identities; executing a dirty Python module
    # is invalid even if raw datasets are byte-exact.
    hashes = {}
    for name in names:
        p = root / name
        require(p.is_file() and not p.is_symlink(), "G0_SOURCE_CODE_MISSING:" + name)
        expected = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD:" + name],
                                  capture_output=True, text=True, timeout=12)
        require(expected.returncode == 0 and
                git_blob(p.read_bytes()) == expected.stdout.strip(),
                "G0_UNCOMMITTED_OR_TAMPERED_SCIENTIFIC_CODE:" + name)
        hashes[name] = expected.stdout.strip()
    return hashes


def immutable_evidence_seal(root: Path = ROOT) -> dict:
    """Pre- and post-run raw read seals. No single digest is itself 'independent custody'."""
    locks = {}
    for name in SCOPED_RAW:
        p = root / name
        require(p.is_file() and not p.is_symlink(), "G4_REQUIRED_RAW_EVIDENCE_MISSING:" + name)
        raw = p.read_bytes()
        require(len(raw) < 9_000_000, "G4_RAW_EVIDENCE_SIZE_ABNORMAL:" + name)
        locks[name] = hashlib.sha256(raw).hexdigest()
    return locks


def verify_casewise_evidence(root: Path = ROOT) -> dict:
    """G4/G5/G6/G10: proactively check actual real source pins, all 17 cases,
    raw-to-parsed identity and truthful label custody before running any TCC action.
    Explicit historical Oracle labels are scorer-side only; never unseen gold.
    """
    pins = json.loads((root / "docs/ISSUE1_S3_NATIVE_NEXT_ACTION_ORACLE_INTERVENTION_V1.json").read_text())["frozen_sources"]
    cases_path = root / "fixtures/function_boundary_next_action_v1.json"
    qwen_path = root / "results/issue1_qwen_next_action_v2_mac_actual_2026-10-10.json"
    ec_path = root / "results/issue1_ecv44_native_next_action_v2_local_replay_2026-10-10.json"
    for p, key in ((cases_path, "fixture_git_blob"), (qwen_path, "qwen_actual_git_blob"),
                   (ec_path, "ec_actual_git_blob")):
        require(p.is_file() and not p.is_symlink() and git_blob(p.read_bytes()) == pins[key],
                "G4_G5_HISTORICAL_SOURCE_PIN_MISMATCH:" + p.name)
    cases = json.loads(cases_path.read_text())["fixtures"]
    qwen = json.loads(qwen_path.read_text())["run"]
    ec = json.loads(ec_path.read_text())["result"]
    require(qwen.get("independent_gold") is False and
            qwen.get("original_llm0_identity_established") is False and
            qwen.get("scientific_phase1_a_e_completed") is False,
            "G6_DEVELOPMENT_FIXTURES_MISLABELED_INDEPENDENT")
    require(qwen["qwen_model_sha256"] == pins["model_sha256"] and
            ec["source_ec_commit"] == pins["ec_commit"],
            "G5_EC_LLM_MODEL_SOURCE_MISMATCH")
    require(len(cases) == len(qwen["llm"]["rows"]) == len(qwen["raw_inference"]) ==
            len(ec["rows"]) == qwen["llm_actual_inference_count"] == 17,
            "G10_WRONG_CASE_COUNT")
    seen = set()
    model_correct = native_correct = 0
    for case, qr, raw, er in zip(cases, qwen["llm"]["rows"], qwen["raw_inference"], ec["rows"]):
        name = case["id"]
        require(name not in seen and name == qr["fixture_id"] == er["case_id"],
                "G10_DUPLICATE_OR_MISALIGNED_CASE:" + name)
        seen.add(name)
        visible = {k: case[k] for k in
                   ("plan", "completed_work_ids", "blocked_work", "dynamic_spec") if k in case}
        require(not any(k in visible for k in ("oracle", "hidden", "gold", "category")),
                "G5_ORACLE_FIELD_VISIBLE_TO_PREDICTOR")
        require(er["public_input_sha256"] == sha(visible) and
                er["raw_prediction_sha256"] == sha(er["prediction"]),
                "G4_UPSTREAM_OR_EC_PREDICTION_SHA_MISMATCH:" + name)
        require(qr["raw"] == raw["raw_response"] and
                json.loads(qr["raw"]) == qr["prediction"],
                "G5_RAW_MODEL_OUTPUT_NOT_EQUAL_SCORED_PREDICTION:" + name)
        require(qr["oracle"] == case["oracle"] == er["frozen_gold"],
                "G5_FROZEN_ORACLE_CHANGED_AFTER_INFERENCE:" + name)
        for key in ("stdout_sha256", "prompt_sha256", "grammar_sha256", "stderr_sha256"):
            require(isinstance(raw.get(key), str) and len(raw[key]) == 64 and
                    set(raw[key]).issubset("0123456789abcdef"),
                    "G5_RAW_MODEL_HASH_MISSING:" + name + ":" + key)
        qok = (qr["prediction"]["status"] == case["oracle"]["status"] and
               qr["prediction"]["work_id"] == case["oracle"]["work_id"])
        eok = (er["prediction"]["status"] == case["oracle"]["status"] and
               er["prediction"]["work_id"] == case["oracle"]["work_id"])
        require(qok == qr["decision_correct"] and eok == er["decision_correct"],
                "G10_DOUBLE_OR_INCONSISTENT_SCORING:" + name)
        model_correct += int(qok)
        native_correct += int(eok)
    require(model_correct == qwen["llm"]["decision_correct"] == 1 and
            native_correct == ec["ec_decision_correct"] == 17,
            "G10_AGGREGATE_DOES_NOT_MATCH_REAL_CASE_SCORES")
    return {"actual_case_count": 17, "unique_case_ids": len(seen),
            "pinned_actual_Qwen_correct": model_correct,
            "pinned_actual_native_EC_correct": native_correct,
            "historical_development_not_unseen": True,
            "strict_casewise_upstream_same_and_scoring_verified": True}


def scope_witness(root: Path = ROOT) -> dict:
    """G3: inspect pinned *native* authority and information-theoretic collisions."""
    native = json.loads((root / "results/ec_native_adapter_qualification.json").read_text())
    s4 = json.loads((root / "results/phase1_s4_identifiability_audit_2026-10-03.json").read_text())
    require(native["protocol"] == "PHASE1_EC_NATIVE_ADAPTER_V1" and
            native["status"] == "INCOMPATIBLE" and native["oracle_blind"] is True,
            "G3_NATIVE_QUALIFICATION_CHANGED")
    authority = native["subfunction_authority"]
    require(authority["s3_selection"]["authority"] == "EC_NATIVE_NOT_APPLICABLE" and
            authority["s3_selection"]["reportable"] is False, "G3_FALSE_S3_NATIVE_COMPATIBILITY")
    require(authority["s4_closure"]["authority"] == "EC_NATIVE_NOT_APPLICABLE" and
            authority["s4_closure"]["reportable"] is False, "G3_FALSE_S4_NATIVE_COMPATIBILITY")
    cases = native["qualification_evidence"]["s3_selection"]["phase1_multi_select_fixtures"]
    require(sorted(cases) == ["M003", "M009"], "G3_S3_COUNTEREXAMPLES_CHANGED")
    collision = s4["collision_groups"]
    require(s4["fixture_count"] == 10 and
            s4["identifiability"]["best_possible_majority_correct"] == 8 and
            s4["identifiability"]["metric_type"] ==
            "INTERFACE_IDENTIFIABILITY_BOUND_NOT_EC_ACCURACY",
            "G3_S4_UNDERIDENTIFICATION_NOT_REPRODUCED")
    labelled_groups = []
    for group in collision:
        labels = group["closure_labels"]
        require(set(labels) == {"CLOSE", "CONTINUE"}, "G3_S4_NO_CROSS_LABEL_COLLISION")
        labelled_groups.append({"signature": group["signature"],
                                "close_cases": labels["CLOSE"], "continue_cases": labels["CONTINUE"]})
    return {
        "same_function_native_qualified": False,
        "S3_native_mismatch": "native single action cannot represent original all-admissible selected set",
        "S3_counterexample_cases": sorted(cases),
        "S4_native_mismatch": "S3 structural state is nonidentifying for downstream CLOSE vs CONTINUE",
        "S4_best_identifiable": "8/10", "S4_collision_proofs": labelled_groups,
        "adapter_suggested_minimum": {
            "S3": ["all admissible selected candidate IDs", "accept/reject and alternatives semantics",
                   "native EC source implementation and explicit source-code provenance"],
            "S4": ["relation of chosen candidates including COMPETING/EQUIVALENT",
                   "unresolved mandatory conditions / outstanding obligations",
                   "explicit native closure semantics and independent reason codes"],
            "control": ["versioned NEW scientific contract", "same upstream hash per arm",
                        "no wrapper-only/harness-local rule mislabeled as native EC",
                        "freeze preregistration before new model inference",
                        "single-layer Oracle interventions for each coarse layer"],
        },
        "status": "NATIVE_SOURCE_CAPABILITY_GAP",
    }


def ac_matrix(norm: dict, graph: dict, witness: dict, *, provenance_passed: bool,
              scoped_verified: bool) -> dict:
    """G2/G11: no scientific AC passes by closing issue/finishing narrower test."""
    direct = {}
    for ac in graph["topological_order"]:
        if ac == "AC-19":
            state = "PASS" if provenance_passed else "FAIL_CLOSED"
            why = "versioned frozen V1/V2 schema and sources verified"
        elif ac == "AC-20":
            state = "PASS" if provenance_passed else "FAIL_CLOSED"
            why = "no auto-enabled Actions; original preflight verifies absent workflows"
        elif ac in ("AC-03", "AC-11", "AC-12"):
            state = "BLOCKED_NATIVE_SOURCE"
            why = "EC native cannot perform original generic S3 multi-selection / generic S4"
        elif ac in ("AC-13", "AC-14", "AC-15"):
            state = "SCOPED_ONLY" if scoped_verified else "NOT_DEMONSTRATED"
            why = "pinned bounded real Qwen/EC evidence is NOT full four-layer A-E"
        elif ac in ("AC-16", "AC-17"):
            state = "SCOPED_ONLY" if scoped_verified else "NOT_DEMONSTRATED"
            why = "single selected-action S3 causal intervention; all-layer Oracle still absent"
        else:
            state = "NOT_DEMONSTRATED"
            why = "no valid original same-function A/B/C/D/E layer-wide raw measurements"
        missing = [p for p in graph["AC_dependencies"][ac]
                   if direct.get(p, {}).get("state") != "PASS"]
        if state not in ("PASS", "BLOCKED_NATIVE_SOURCE") and missing:
            state = "BLOCKED_DEPENDENCY"
        direct[ac] = {"state": state, "why": why, "unmet_AC_dependencies": missing,
                      "normative_issue_deps": graph["issue_dependencies"][ac]}
    required = graph["required"]
    passes = [a for a in required if direct[a]["state"] == "PASS"]
    failed = [a for a in required if direct[a]["state"] != "PASS"]
    return {"AC": direct, "mvp_required": required, "mvp_pass": passes,
            "mvp_unmet": failed, "required_pass_count": len(passes),
            "required_count": len(required), "root_mvp_complete": len(passes) == 18 and
            witness["same_function_native_qualified"]}


def next_work(config: dict, graph: dict, matrix: dict, witness: dict,
              scoped_verified: bool) -> dict:
    """W4 is a design output, not a substitute native EC implementation."""
    statuses = {
        "W0_SOURCE_LOCK": "DONE",
        "W1_DEPENDENCY_GRAPH": "DONE",
        "W2_NATIVE_CONTRACT_QUALIFICATION": "DONE_WITH_NEGATIVE_NATIVE_WITNESS",
        "W3_LOCAL_ACTUAL_EXPERIMENTS": "DONE_SCOPED_ONLY" if scoped_verified else "BLOCKED_RAW_ASSETS",
        "W4_VERSIONED_NATIVE_REPAIR_PLAN": "SPECIFIED_NOT_IMPLEMENTED",
        "W5_FOUR_LAYER_ACTUAL_AE": "BLOCKED_GENUINE_EC_S3_S4_SOURCE",
        "W6_LOCALIZE_MVP": "BLOCKED_W5_AND_AC",
        "W7_INDEPENDENT_REVIEW": "BLOCKED_UNSEEN_GOLD_AND_ORIGINAL_LLM0_AND_AUTHORIZED_V4",
    }
    return {
        "work_items": [{**job, "state": statuses[job["id"]],
                        "depends_on_state": {p: statuses[p] for p in job["depends_on"]}}
                       for job in config["work_items"]],
        "root_critical_path": [
            "implement and prove genuinely native equivalent S3 multi-selection and S4 closure",
            "preregister a successor contract explicitly; preserve original frozen failure",
            "run all four-layer original A/B/C/D/E with same upstream and Oracle interventions",
            "recompute candidate recall, selection, false closure, missed reframe and layer gains",
            "confirm all 18 MVP AC in dependency order and original scientific exit",
        ],
        "external_validation_path": [
            "acquire independently judged unseen precommitted corpus, independent gold custody",
            "resolve genuine original LLM0 identity + authorized V4 with same-case raw output",
            "evaluate four arms under pinned no-leak metrics without development/test crossover",
        ],
        "next_executable_source_authority": "genuine native EC source extension required; no existing oracle-blind adapter qualifies",
        "all_machine_available_scoped_work_executed": scoped_verified,
    }


def tcc_spec() -> dict:
    return {
        "schema": "tcc.spec.v3", "tcc_id": "ISSUE1-ROOT-AC-MVP-DEPENDENCY-PREFLIGHT-V6",
        "goal": "Original #1 AC-01..20 and 18-entry MVP driven, all feasible machine work, no scoped success false closure",
        "acceptance": [
            "preflight Git-blob source immutability, norm 20 AC and 18 MVP, zero issue/AC DAG cycles",
            "actual frozen original Phase1 replay proves incompatibility or source compatibility",
            "casewise pinned raw provenance and same-upstream guard before model/EC validation",
            "all applicable local experiments run from TCC source-pinned v5, classify scoped only",
            "derive true minimum native S3/S4 source repair and current AC dependencies",
            "recompute strict original MVP=18/18 PASS plus whole-layer A/B/C/D/E before any success",
            "freeze result-overturning errors: model input, gold leak, dataset reuse, duplicate scores, source drift",
            "stop only on ROOT_MVP_VERIFIED or explicit irreducible genuine native-source/external requirement",
        ],
        "state_keys": ["source", "acgraph", "origin", "raw", "scoped", "witness", "acstatus"],
        "immutable_state_keys": [],
        "entry_nodes": ["pin_source"],
        "nodes": [
            node("pin_source", "action", writes=("source",), failure="blocked_integrity"),
            node("verify_ac_dependencies", "action", depends=("pin_source",),
                 writes=("acgraph",), failure="blocked_integrity"),
            node("frozen_origin_replay", "action", depends=("verify_ac_dependencies",),
                 writes=("origin",), failure="blocked_integrity"),
            node("raw_evidence_preflight", "action", depends=("frozen_origin_replay",),
                 writes=("raw",), failure="blocked_integrity"),
            node("run_scoped_machine_experiments", "action", depends=("raw_evidence_preflight",),
                 writes=("scoped",), failure="blocked_integrity"),
            node("prove_native_interface_feasibility", "action",
                 depends=("run_scoped_machine_experiments",), writes=("witness",),
                 failure="blocked_integrity"),
            node("audit_root_ac_dependencies", "action",
                 depends=("prove_native_interface_feasibility",), writes=("acstatus",),
                 failure="blocked_integrity"),
            node("root_ac_exit_gate", "gate", depends=("audit_root_ac_dependencies",),
                 reads=("source", "acgraph", "origin", "raw", "scoped", "witness", "acstatus"),
                 branches={"original_all_AC_pass": "verified_root_mvp",
                           "native_source_gap": "blocked_native_semantics",
                           "external_study_gap": "blocked_external_evidence"}),
            node("verified_root_mvp", "terminal", terminal="SUCCESS"),
            node("blocked_native_semantics", "terminal", terminal="BLOCKED"),
            node("blocked_external_evidence", "terminal", terminal="BLOCKED"),
            node("blocked_integrity", "terminal", terminal="BLOCKED"),
        ],
    }


def run(tcc_root: Path, ec_root: Path, *, model: Path | None = None,
        llama: Path | None = None, config_path: Path = CFG,
        source_root: Path = ROOT, execute_scoped: bool = True) -> dict:
    """One bounded call, with prerequisite/integrity checks on BOTH sides of experiments."""
    require(git_head(tcc_root) == TCC_SOURCE, "G0_PINNED_TCC_GENERATOR_SOURCE_CHANGED")
    require(config_path.is_file() and not config_path.is_symlink(),
            "G0_VERSIONED_ORCHESTRATION_CONTRACT_MISSING")
    require(git_blob(config_path.read_bytes()) == CONFIG_FROZEN_BLOB,
            "G0_TCC_V6_AC_ORCHESTRATION_CONFIG_CHANGED")
    config = json.loads(config_path.read_text())
    require(config["tcc_generator_source"] == TCC_SOURCE, "G0_ORCHESTRATOR_COMPILER_PIN_DRIFT")
    if str(tcc_root) not in sys.path:
        sys.path.insert(0, str(tcc_root))
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.core_v3 import validate_spec, normalize_spec, compile_spec
    from tcc.runtime_v3 import execute_graph, to_ecv4_evidence

    head = git_head(source_root)
    contract = tcc_spec()
    ctx = context_for(contract, head)
    ctx.update(selected_issue_id="ISSUE-1", actionable_issue_ids=["ISSUE-1"],
               blocked_issue_ids=[], snapshot_id="ISSUE1-AC6:" + head[:14],
               source_fingerprint="sha256:" + sha({"head": head, "contract": contract,
                                                    "config": config}))
    gen = generate_tcc_from_context(ctx)
    require(gen.get("result") == "tcc.spec.v3" and not validate_spec(gen["spec"]) and
            gen["spec"] == normalize_spec(contract), "G1_TCC_GRAPH_SEMANTIC_COMPILE_DRIFT")
    dag = compile_spec(gen["spec"])
    observed: dict = {"errors": [], "sources": {}, "pre_seal": {}, "post_seal": {},
                      "pre_code": {}, "post_code": {}}
    norm = json.loads((source_root / config["frozen_normative_contract"]).read_text())
    work_ids = check_work_graph(config)

    def pin(_n, _s, _a):
        try:
            observed["sources"] = frozen_sources(config, source_root)
            observed["pre_code"] = scientific_source_seal(source_root)
            require(not (source_root / ".github/workflows").exists() or
                    not any((source_root / ".github/workflows").iterdir()),
                    "G0_GITHUB_ACTIONS_ENABLED")
            observed["config_sha256"] = hashlib.sha256(config_path.read_bytes()).hexdigest()
        except Exception as ex:
            observed["errors"].append("G0:" + type(ex).__name__ + ":" + str(ex)[:150])
            return {"status": "failure", "evidence": ["SOURCE_PIN_FAIL"]}
        return {"status": "success", "writes": {"source": True},
                "evidence": ["G0+G7:FROZEN_PROTOCOL_SOURCE_SHA_PASS"]}

    def dependency(_n, _s, _a):
        try:
            observed["acgraph"] = ac_dag(norm, ac_text=(source_root / "ACCEPTANCE_CRITERIA.md").read_text())
            require(len(work_ids) == 8, "G1_MISSING_ROOT_WORK_ITEMS")
        except Exception as ex:
            observed["errors"].append("G1:" + type(ex).__name__ + ":" + str(ex)[:150])
            return {"status": "failure", "evidence": ["AC_DAG_FAIL"]}
        return {"status": "success", "writes": {"acgraph": True},
                "evidence": ["G1+G2:ORIGINAL_AC20_MVP18_TOPOLOGICAL_PASS"]}

    def original(_n, _s, _a):
        try:
            v = verify_origin(source_root, actual_replay=True)
            require(not v["original_exit_pass"] and
                    v["original_phase1_exit"] == "EC_NATIVE_SCOPE_INCOMPATIBLE" and
                    v["strict_original_exit_gate"] == "BLOCKED_INTERFACE_SEMANTICS",
                    "G3_ORIGINAL_FROZEN_EXIT_CHANGED")
            observed["origin"] = {"exit": v["original_phase1_exit"],
                                  "source_pin_hashes": v["source_pins_sha256"]}
        except Exception as ex:
            observed["errors"].append("G3:" + type(ex).__name__ + ":" + str(ex)[:150])
            return {"status": "failure", "evidence": ["ORIGINAL_REPLAY_FAIL"]}
        return {"status": "success", "writes": {"origin": True},
                "evidence": ["G3:ORIGINAL_V2_P0P1_PASS_P2_NATIVE_INCOMPATIBLE"]}

    def raw(_n, _s, _a):
        try:
            observed["pre_seal"] = immutable_evidence_seal(source_root)
            observed["casewise"] = verify_casewise_evidence(source_root)
        except Exception as ex:
            observed["errors"].append("G4:" + type(ex).__name__ + ":" + str(ex)[:150])
            return {"status": "failure", "evidence": ["RAW_EVIDENCE_PRESEAL_FAIL"]}
        return {"status": "success", "writes": {"raw": True},
                "evidence": ["G4+G5+G10:REAL_SCOPED_RAW_PINNED_PRESEAL_PASS"]}

    def scoped(_n, _s, _a):
        try:
            require(execute_scoped, "SCOPED_EXECUTION_MUST_NOT_BE_SKIPPED_FOR_EXIT")
            v = run_stage5(tcc_root, ec_root, model=model, llama=llama)
            require(v["machine_scoped_studies_completed"] is True and
                    v["original_phase1_S1_to_S4_AE_completed"] is False and
                    v["source_original_issue_closure_authorized"] is False and
                    v["independent_scientific_retention_certified"] is False,
                    "G9_SCOPED_EVIDENCE_FALSE_ROOT_CLAIM")
            require(v["public_dynamic_subgate"]["EC_native_fallback_invoked"] == 15 and
                    v["public_dynamic_subgate"]["hybrid_correct"] == 17 and
                    v["public_dynamic_subgate"]["attribution"] == "EC-fallback, not model competence",
                    "G9_MODEL_EC_CREDIT_CONTAMINATION")
            observed["post_seal"] = immutable_evidence_seal(source_root)
            observed["post_code"] = scientific_source_seal(source_root)
            require(observed["post_code"] == observed["pre_code"],
                    "G0_G7_EXECUTABLE_CODE_CHANGED_DURING_RUN")
            require(observed["post_seal"] == observed["pre_seal"],
                    "G4_G5_RESULT_OVERTURNING_EVIDENCE_MUTATED_DURING_RUN")
            require(observed["config_sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest(),
                    "G7_ORCHESTRATION_CONTRACT_CHANGED_DURING_RUN")
            observed["scoped"] = {"state": v["terminal"], "actual_tcc_evidence": v["ECv4_evidence"],
                                  "native_ec_fallbacks": 15, "hybrid_correct": 17,
                                  "source_commit": v["source_commit"],
                                  "original_AC_qualified": False}
        except Exception as ex:
            observed["errors"].append("G4:G5:G8:G9:" + type(ex).__name__ + ":" + str(ex)[:150])
            return {"status": "failure", "evidence": ["SCOPED_RUN_INTEGRITY_FAIL"]}
        return {"status": "success", "writes": {"scoped": True},
                "evidence": ["G8+G9:REAL_SCOPED_EC17_QWEN17_QWEN20_S3_ORACLE_GBNF_DYNAMIC_PASS",
                            "G4+G5+G7+G10:PRE_POST_SHA_STABLE"]}

    def feasibility(_n, _s, _a):
        try:
            observed["witness"] = scope_witness(source_root)
        except Exception as ex:
            observed["errors"].append("G3_NATIVE:" + type(ex).__name__ + ":" + str(ex)[:150])
            return {"status": "failure", "evidence": ["NATIVE_CONTRACT_PROOF_FAIL"]}
        return {"status": "success", "writes": {"witness": True},
                "evidence": ["G3:GENUINE_NATIVE_S3_MULTISELECT_S4_UNIDENTIFIABLE_PROVEN"]}

    def ac_eval(_n, _s, _a):
        try:
            observed["ac_matrix"] = ac_matrix(norm, observed["acgraph"],
                                              observed["witness"],
                                              provenance_passed=True, scoped_verified=True)
            observed["next_work"] = next_work(config, observed["acgraph"],
                                              observed["ac_matrix"], observed["witness"], True)
            require(observed["ac_matrix"]["required_count"] == 18 and
                    not observed["ac_matrix"]["root_mvp_complete"],
                    "G11_SCOPED_SUCCESS_FRAUDULENTLY_CLOSED_ROOT")
            for ac, item in observed["ac_matrix"]["AC"].items():
                if item["state"] == "PASS":
                    require(all(observed["ac_matrix"]["AC"][dep]["state"] == "PASS"
                                for dep in observed["acgraph"]["AC_dependencies"][ac]),
                            "G2_PASS_WITH_UNMET_AC_DEPENDENCY:" + ac)
            require(observed["post_seal"] == immutable_evidence_seal(source_root),
                    "G4_EVIDENCE_MUTATED_AFTER_EXPERIMENT")
            require(observed["post_code"] == scientific_source_seal(source_root),
                    "G0_G7_CODE_MUTATED_AFTER_EXPERIMENT")
        except Exception as ex:
            observed["errors"].append("G2:G11:" + type(ex).__name__ + ":" + str(ex)[:150])
            return {"status": "failure", "evidence": ["ROOT_AC_ASSESSMENT_FAIL"]}
        return {"status": "success", "writes": {"acstatus": True},
                "evidence": ["G2+G11:ALL18_ROOT_MVP_NOT_FAKELY_PROMOTED",
                            "W0_TO_W7_DEPENDENCY_REMEDIATION_DERIVED"]}

    def exit_gate(_n, state, _a):
        if not all(state.get(k) is True for k in
                   ("source", "acgraph", "origin", "raw", "scoped", "witness", "acstatus")):
            return {"outcome": "external_study_gap", "evidence": ["MISSING_PREREQUISITE"]}
        if observed["ac_matrix"]["root_mvp_complete"] and observed["witness"]["same_function_native_qualified"]:
            return {"outcome": "original_all_AC_pass", "evidence": ["ORIGINAL_AC18_ALL_PASS"]}
        if not observed["witness"]["same_function_native_qualified"]:
            return {"outcome": "native_source_gap",
                    "evidence": ["NATIVE_SOURCE_GAP:S3_M003_M009:S4_COLLISION_8OF10"]}
        return {"outcome": "external_study_gap", "evidence": ["UNSATISFIED_EXPERIMENTAL_AC"]}

    actual = execute_graph(dag, {
        "pin_source": pin, "verify_ac_dependencies": dependency,
        "frozen_origin_replay": original, "raw_evidence_preflight": raw,
        "run_scoped_machine_experiments": scoped,
        "prove_native_interface_feasibility": feasibility,
        "audit_root_ac_dependencies": ac_eval, "root_ac_exit_gate": exit_gate,
    })
    require(actual.get("result") == "TERMINAL" and actual.get("terminal_id") in
            ("verified_root_mvp", "blocked_native_semantics", "blocked_external_evidence",
             "blocked_integrity"), "G11_TCC_UNEXPECTED_TERMINAL")
    terminal = {
        "verified_root_mvp": "ROOT_MVP_VERIFIED",
        "blocked_native_semantics": "NATIVE_SOURCE_CAPABILITY_GAP",
        "blocked_external_evidence": "EXTERNAL_INDEPENDENCE_MISSING",
        "blocked_integrity": "INTEGRITY_FAIL_CLOSED",
    }[actual["terminal_id"]]
    # Fail-closed cannot ever be promoted into root success from a scoped child.
    root_complete = (terminal == "ROOT_MVP_VERIFIED"
                     and observed.get("ac_matrix", {}).get("root_mvp_complete", False)
                     and observed.get("witness", {}).get("same_function_native_qualified", False))
    require(terminal != "ROOT_MVP_VERIFIED" or root_complete, "G11_FALSE_ROOT_COMPLETION")
    return {
        "protocol": PROTOCOL, "source_commit": head, "TCC_source_commit": TCC_SOURCE,
        "TCC_nodes": len(dag["nodes"]), "TCC_edges": len(dag["edges"]),
        "TCC_spec_hash": dag["spec_hash"], "TCC_terminal_id": actual["terminal_id"],
        "TCC_terminal_status": actual["terminal_status"],
        "ECv4_handoff": to_ecv4_evidence(dag, actual),
        "original_AC20_topological": observed.get("acgraph"),
        "MVP_18_required_AC_status": observed.get("ac_matrix"),
        "original_native_interface_proof": observed.get("witness"),
        "dependency_ordered_execution_plan": observed.get("next_work"),
        "scoped_actual_experiment": observed.get("scoped"),
        "source_git_blob_pins": observed.get("sources"),
        "raw_evidence_pre_seal": observed.get("pre_seal"),
        "raw_evidence_post_seal": observed.get("post_seal"),
        "original_frozen_replay": observed.get("origin"),
        "G4_G5_G6_G10_casewise_gate": observed.get("casewise"),
        "blocking_integrity_errors": observed["errors"],
        "original_issue_1_completed": bool(root_complete),
        "AC_MVP_validated": bool(root_complete),
        "independent_gold_qualified": False,
        "new_scheduled_tasks": False,
        "source_code_mutated_during_run": observed.get("pre_code") != observed.get("post_code"),
        "scientific_source_code_git_blob_pins": observed.get("post_code"),
        "terminal": terminal,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tcc-root", required=True, type=Path)
    p.add_argument("--ec-root", required=True, type=Path)
    p.add_argument("--model", type=Path)
    p.add_argument("--llama-cli", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    try:
        result = run(a.tcc_root, a.ec_root, model=a.model, llama=a.llama_cli)
        serialized = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if a.out:
            require(not a.out.is_symlink(), "EVIDENCE_OUTPUT_SYMLINK_FORBIDDEN")
            a.out.write_text(serialized, encoding="utf-8")
            print(json.dumps({"terminal": result["terminal"],
                              "required_AC_pass": (result.get("MVP_18_required_AC_status") or {}).get("required_pass_count"),
                              "required_AC_total": 18,
                              "TCC_nodes": result["TCC_nodes"], "TCC_edges": result["TCC_edges"],
                              "root_complete": result["original_issue_1_completed"],
                              "out": str(a.out)}))
        else:
            print(serialized, end="")
        return 0 if result["original_issue_1_completed"] else (3 if result["terminal"] == "INTEGRITY_FAIL_CLOSED" else 2)
    except Exception as exc:
        print(json.dumps({"protocol": PROTOCOL, "terminal": "INTEGRITY_FAIL_CLOSED",
                          "error": type(exc).__name__ + ":" + str(exc)[:300]}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
