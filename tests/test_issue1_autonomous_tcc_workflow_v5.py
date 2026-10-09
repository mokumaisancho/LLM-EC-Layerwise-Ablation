from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_issue1_autonomous_tcc_workflow_v5 import (
    ROOT,contract,run,PROTOCOL
)
TCC=Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC=Path("/private/tmp/llmec-ecv44-source-20261010")

class AutonomousOriginalIssueV5Tests(unittest.TestCase):
    def test_01_declared_goal_is_not_substituted_with_scoped_finish(self):
        c=contract()
        self.assertEqual(c["entry_nodes"],["verify_previous_machine_science"])
        self.assertIn("original",str(c["acceptance"]).lower())
        self.assertEqual(c["schema"],"tcc.spec.v3")

    def test_02_tcc_scoped_only_success_and_explicit_blocks(self):
        c=contract();nodes={n["id"]:n for n in c["nodes"]}
        self.assertEqual([n["id"] for n in nodes.values() if n["kind"]=="terminal" and n["terminal_status"]=="SUCCESS"],["machine_scoped_complete"])
        self.assertEqual(nodes["branch_dynamic_residual"]["branches"]["all_detected"],"audit_external_independence")
        self.assertEqual(nodes["branch_dynamic_residual"]["branches"]["unresolved"],"unresolved_semantic_assay_required")
        self.assertEqual(nodes["check_remaining_semantic_errors"]["branches"]["dynamic_residual"],"run_public_dynamic_gate")

    def test_03_source_has_no_automation_scheduling_or_background_chat_send(self):
        text=(ROOT/"tools/run_issue1_autonomous_tcc_workflow_v5.py").read_text()
        for forbidden in ("automations.create(","chatgpt.com/","launchctl","crontab","new Promise("):
            self.assertNotIn(forbidden,text)

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"pinned assets unavailable")
    def test_04_actual_recursive_TCC_reaches_all_local_scientific_gates(self):
        x=run(TCC,EC)
        self.assertEqual(x["protocol"],PROTOCOL)
        self.assertEqual(x["TCC_terminal"],"machine_scoped_complete")
        self.assertTrue(x["machine_scoped_studies_completed"])
        self.assertEqual(x["prior_actual_inferences_and_interventions"]["S3_Oracle_gain"],16/17)
        self.assertEqual(x["public_invariant_subgate"]["caught"],13)
        self.assertEqual(x["public_dynamic_subgate"]["public_extended_caught"],15)
        self.assertEqual(x["public_dynamic_subgate"]["hybrid_correct"],17)
        self.assertEqual(x["public_dynamic_subgate"]["EC_native_fallback_invoked"],15)
        self.assertFalse(x["original_phase1_S1_to_S4_AE_completed"])
        self.assertFalse(x["independent_scientific_retention_certified"])
        self.assertFalse(x["source_original_issue_closure_authorized"])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"pinned assets unavailable")
    def test_05_malicious_original_scientific_success_fails_closed(self):
        from tools.run_issue1_autonomous_tcc_workflow_v4 import run as original_run
        # Mocking affects only the old-stage proof, not real EC or model scores.
        upstream=original_run(TCC,EC)
        fake=copy.deepcopy(upstream)
        fake["original_A_E_S1_S4_completed"]=True
        with patch("tools.run_issue1_autonomous_tcc_workflow_v5.stage4",return_value=fake):
            outcome=run(TCC,EC)
        self.assertEqual(outcome["TCC_terminal"],"blocked_integrity")
        self.assertFalse(outcome["machine_scoped_studies_completed"])
        self.assertFalse(outcome["source_original_issue_closure_authorized"])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"pinned assets unavailable")
    def test_06_missing_evaluable_guard_scoped_test_fails_closed(self):
        from tools.run_issue1_s3_public_guard_decomposition_v1 import evaluate
        fake=evaluate();fake["Qwen_wrong"]=0
        with patch("tools.run_issue1_autonomous_tcc_workflow_v5.fixed_guard",return_value=fake):
            outcome=run(TCC,EC)
        self.assertEqual(outcome["TCC_terminal"],"blocked_integrity")
        self.assertFalse(outcome["machine_scoped_studies_completed"])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"pinned assets unavailable")
    def test_07_unresolved_dynamic_errors_require_new_semantic_study(self):
        from tools.run_issue1_s3_public_dynamic_guard_v2 import evaluate
        fake=evaluate();fake["remaining_uncaught_wrong_case_ids"]=["NEW_UNKNOWN"]
        with patch("tools.run_issue1_autonomous_tcc_workflow_v5.dynamic_guard",return_value=fake):
            outcome=run(TCC,EC)
        self.assertEqual(outcome["TCC_terminal"],"unresolved_semantic_assay_required")
        self.assertFalse(outcome["machine_scoped_studies_completed"])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"pinned assets unavailable")
    def test_08_independent_external_certificate_cannot_be_self_asserted(self):
        v=run(TCC,EC)
        self.assertIn("EXTERNAL_STUDY_DIR_MISSING",v["independent_gold_and_original_contract"]["blockers"])
        self.assertEqual(v["independent_gold_and_original_contract"]["unseen_precommitted_gold"],
                         "NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(v["independent_gold_and_original_contract"]["original_same_function_five_arm"],
                         "NOT_RUN")
        self.assertFalse(v["new_scheduled_tasks"])

if __name__=="__main__":
    unittest.main()
