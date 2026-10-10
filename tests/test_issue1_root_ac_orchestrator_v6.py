from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_issue1_root_ac_orchestrator_v6 import (
    ROOT, CFG, TCC_SOURCE, PROTOCOL, Abort, git_blob, frozen_sources,
    ac_dag, check_work_graph, immutable_evidence_seal, scope_witness,
    ac_matrix, next_work, verify_casewise_evidence, tcc_spec, run,
)
from tools.run_issue1_autonomous_tcc_workflow_v5 import run as old_stage5

TCC = Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC = Path("/private/tmp/llmec-ecv44-source-20261010")

class RootACDependencyOrchestratorV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads(CFG.read_text())
        cls.norm = json.loads((ROOT / cls.c["frozen_normative_contract"]).read_text())
        cls.graph = ac_dag(cls.norm, ac_text=(ROOT / "ACCEPTANCE_CRITERIA.md").read_text())

    def test_01_exact_original_mvp_18_and_total_20(self):
        self.assertEqual(len(self.graph["topological_order"]),20)
        self.assertEqual(len(self.graph["required"]),18)
        self.assertEqual(set(self.graph["post_mvp"]),{"AC-10","AC-18"})
        self.assertEqual(self.graph["original_threshold"],0.20)

    def test_02_source_and_config_are_explicit_external_sha_pinned(self):
        self.assertEqual(len(frozen_sources(self.c)),4)
        self.assertEqual(self.c["source_git_blobs"]["ACCEPTANCE_CRITERIA.md"],
                         "40e4d41914fb17ee5c7deb0cfd32276a41c9a1fc")
        self.assertEqual(len(git_blob(CFG.read_bytes())),40)

    def test_03_changed_original_acceptance_text_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in self.c["source_git_blobs"]:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/rel,p)
            (root/"ACCEPTANCE_CRITERIA.md").write_text("new easier ACs",encoding="utf-8")
            with self.assertRaisesRegex(Abort,"G0_FROZEN_SOURCE_BLOB_CHANGED"):
                frozen_sources(self.c,root)

    def test_04_mutated_frozen_threshold_is_not_allowed(self):
        cfg=copy.deepcopy(self.c)
        cfg["frozen_materiality"]=0.0
        with self.assertRaisesRegex(Abort,"G7_THRESHOLD_CHANGED"):
            frozen_sources(cfg)

    def test_05_cycle_in_ac_graph_must_not_topologically_resolve(self):
        norm=copy.deepcopy(self.norm)
        norm["ac_dependencies"]["AC-19"]=["AC-02"]
        with self.assertRaisesRegex(Abort,"G1_AC_DEPENDENCY_CYCLE"):
            ac_dag(norm,ac_text=(ROOT/"ACCEPTANCE_CRITERIA.md").read_text())

    def test_06_unknown_ac_or_issue_dependency_fails(self):
        for key, extra, error in [
            ("AC-04","AC-99","G1_UNKNOWN_AC_PARENT"),
            ("AC-11","ISSUE-999","G1_UNKNOWN_ISSUE_PARENT")]:
            norm=copy.deepcopy(self.norm)
            norm["ac_dependencies"][key].append(extra)
            with self.assertRaisesRegex(Abort,error):
                ac_dag(norm,ac_text=(ROOT/"ACCEPTANCE_CRITERIA.md").read_text())

    def test_07_all_task_dependencies_precede_dependents(self):
        keys=check_work_graph(self.c)
        self.assertEqual(len(keys),8)
        for job in self.c["work_items"]:
            self.assertTrue(set(job["depends_on"]).issubset(set(keys[:keys.index(job["id"])])))

    def test_08_task_graph_forward_reference_rejected(self):
        cfg=copy.deepcopy(self.c)
        cfg["work_items"][0]["depends_on"]=["W7_INDEPENDENT_REVIEW"]
        with self.assertRaisesRegex(Abort,"G1_WORK_NOT_TOPOLOGICALLY_ORDERED"):
            check_work_graph(cfg)

    def test_09_native_multi_select_and_s4_alias_proven(self):
        v=scope_witness()
        self.assertFalse(v["same_function_native_qualified"])
        self.assertEqual(v["S3_counterexample_cases"],["M003","M009"])
        self.assertEqual(v["S4_best_identifiable"],"8/10")
        self.assertTrue(v["S4_collision_proofs"])
        self.assertEqual(v["status"],"NATIVE_SOURCE_CAPABILITY_GAP")

    def test_10_scoped_test_never_promotes_all_18_ac(self):
        witness=scope_witness()
        out=ac_matrix(self.norm,self.graph,witness,provenance_passed=True,scoped_verified=True)
        self.assertEqual(set(out["mvp_pass"]),{"AC-19","AC-20"})
        self.assertEqual(len(out["mvp_unmet"]),16)
        self.assertFalse(out["root_mvp_complete"])
        for ac, info in out["AC"].items():
            if info["state"]=="PASS":
                self.assertTrue(all(out["AC"][parent]["state"]=="PASS"
                                    for parent in self.graph["AC_dependencies"][ac]))

    def test_11_original_root_critical_path_is_explicit_and_ordered(self):
        g=self.graph
        v=next_work(self.c,g,
                    ac_matrix(self.norm,g,scope_witness(),provenance_passed=True,scoped_verified=True),
                    scope_witness(),True)
        jobs={x["id"]:x for x in v["work_items"]}
        self.assertEqual(jobs["W4_VERSIONED_NATIVE_REPAIR_PLAN"]["state"],
                         "SPECIFIED_NOT_IMPLEMENTED")
        self.assertEqual(jobs["W5_FOUR_LAYER_ACTUAL_AE"]["state"],
                         "BLOCKED_GENUINE_EC_S3_S4_SOURCE")
        self.assertEqual(jobs["W7_INDEPENDENT_REVIEW"]["state"],
                         "BLOCKED_UNSEEN_GOLD_AND_ORIGINAL_LLM0_AND_AUTHORIZED_V4")

    def test_12_exact_preflight_17_real_Qwen_and_native_cases(self):
        v=verify_casewise_evidence()
        self.assertEqual(v["actual_case_count"],17)
        self.assertEqual(v["unique_case_ids"],17)
        self.assertEqual(v["pinned_actual_Qwen_correct"],1)
        self.assertEqual(v["pinned_actual_native_EC_correct"],17)
        self.assertTrue(v["historical_development_not_unseen"])

    def make_case_root(self)->Path:
        # Called only within an enclosing TemporaryDirectory.
        raise RuntimeError("Use case_fixture_copy for bounded test")

    def case_fixture_copy(self, root:Path):
        files=[
          "fixtures/function_boundary_next_action_v1.json",
          "results/issue1_qwen_next_action_v2_mac_actual_2026-10-10.json",
          "results/issue1_ecv44_native_next_action_v2_local_replay_2026-10-10.json",
          "docs/ISSUE1_S3_NATIVE_NEXT_ACTION_ORACLE_INTERVENTION_V1.json",
        ]
        for rel in files:
            dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/rel,dest)

    def test_13_duplicate_case_after_resealing_development_data_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.case_fixture_copy(root)
            cases=root/"fixtures/function_boundary_next_action_v1.json"
            data=json.loads(cases.read_text())
            data["fixtures"][1]["id"]=data["fixtures"][0]["id"]
            cases.write_text(json.dumps(data))
            prereg=root/"docs/ISSUE1_S3_NATIVE_NEXT_ACTION_ORACLE_INTERVENTION_V1.json"
            cfg=json.loads(prereg.read_text())
            cfg["frozen_sources"]["fixture_git_blob"]=git_blob(cases.read_bytes())
            prereg.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(Abort,"G10_DUPLICATE_OR_MISALIGNED_CASE"):
                verify_casewise_evidence(root)

    def test_14_forged_model_raw_when_resealed_must_not_be_used_for_scoring(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.case_fixture_copy(root)
            p=root/"results/issue1_qwen_next_action_v2_mac_actual_2026-10-10.json"
            data=json.loads(p.read_text())
            data["run"]["raw_inference"][0]["raw_response"]='{"status":"EXECUTE","work_id":"work:I20:repair","reason_code":"NONE"}'
            p.write_text(json.dumps(data))
            prereg=root/"docs/ISSUE1_S3_NATIVE_NEXT_ACTION_ORACLE_INTERVENTION_V1.json"
            cfg=json.loads(prereg.read_text())
            cfg["frozen_sources"]["qwen_actual_git_blob"]=git_blob(p.read_bytes())
            prereg.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(Abort,"G5_RAW_MODEL_OUTPUT_NOT_EQUAL_SCORED_PREDICTION"):
                verify_casewise_evidence(root)

    def test_15_source_seal_stable_and_covers_real_evidence(self):
        x=immutable_evidence_seal()
        self.assertEqual(len(x),7)
        self.assertEqual(x,immutable_evidence_seal())

    def test_16_TCC_makes_root_success_only_all_ac_pass(self):
        graph=tcc_spec()
        successes=[n["id"] for n in graph["nodes"]
                   if n["kind"]=="terminal" and n["terminal_status"]=="SUCCESS"]
        self.assertEqual(successes,["verified_root_mvp"])
        self.assertIn("blocked_native_semantics",[n["id"] for n in graph["nodes"]])
        self.assertEqual(graph["entry_nodes"],["pin_source"])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"Required pinned TCC/EC checkouts absent")
    def test_17_actual_one_run_checks_every_mvp_dependency_then_blocks_truthfully(self):
        out=run(TCC,EC)
        self.assertEqual(out["protocol"],PROTOCOL)
        self.assertEqual(out["TCC_terminal_id"],"blocked_native_semantics")
        self.assertEqual(out["terminal"],"NATIVE_SOURCE_CAPABILITY_GAP")
        self.assertEqual(out["MVP_18_required_AC_status"]["required_pass_count"],2)
        self.assertFalse(out["original_issue_1_completed"])
        self.assertFalse(out["AC_MVP_validated"])
        self.assertEqual(out["raw_evidence_pre_seal"],out["raw_evidence_post_seal"])
        self.assertEqual(out["blocking_integrity_errors"],[])
        self.assertTrue(out["G4_G5_G6_G10_casewise_gate"]["strict_casewise_upstream_same_and_scoring_verified"])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"Required pinned TCC/EC checkouts absent")
    def test_18_false_root_science_inside_scoped_stage5_fails_closed(self):
        native=old_stage5(TCC,EC)
        forged=copy.deepcopy(native)
        forged["original_phase1_S1_to_S4_AE_completed"]=True
        with patch("tools.run_issue1_root_ac_orchestrator_v6.run_stage5",return_value=forged):
            out=run(TCC,EC)
        self.assertEqual(out["terminal"],"INTEGRITY_FAIL_CLOSED")
        self.assertFalse(out["original_issue_1_completed"])
        self.assertIn("G9_SCOPED_EVIDENCE_FALSE_ROOT_CLAIM",out["blocking_integrity_errors"][0])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"Required pinned TCC/EC checkouts absent")
    def test_19_result_overturning_mutation_mid_run_fails_closed(self):
        real=immutable_evidence_seal()
        corrupted=dict(real);corrupted[next(iter(corrupted))]="0"*64
        with patch("tools.run_issue1_root_ac_orchestrator_v6.immutable_evidence_seal",
                   side_effect=[real,corrupted]):
            out=run(TCC,EC)
        self.assertEqual(out["TCC_terminal_id"],"blocked_integrity")
        self.assertFalse(out["original_issue_1_completed"])
        self.assertIn("G4_G5_RESULT_OVERTURNING_EVIDENCE_MUTATED",out["blocking_integrity_errors"][0])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"Required pinned TCC/EC checkouts absent")
    def test_20_bad_tcc_compiler_source_pin_blocks_before_execution(self):
        with self.assertRaisesRegex(Abort,"G0_PINNED_TCC_GENERATOR_SOURCE_CHANGED"):
            run(EC,TCC)

    def test_21_no_scheduled_tasks_no_ui_and_no_forged_science(self):
        runner=(ROOT/"tools/run_issue1_root_ac_orchestrator_v6.py").read_text()
        for disallowed in ("automations.create(","crontab","launchctl","chatgpt.com/","openai.com/v1/responses"):
            self.assertNotIn(disallowed,runner)
        self.assertEqual(self.c["provenance_rules"]["scoped_native_success_as_root_exit"],"FORBIDDEN")

if __name__ == "__main__":
    unittest.main()
