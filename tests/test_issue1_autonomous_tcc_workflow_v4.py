from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.run_issue1_autonomous_tcc_workflow_v4 import (
    REPORT,ROOT,PROTOCOL,graph_spec,audit_grammar,run
)

TCC=Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC=Path("/private/tmp/llmec-ecv44-source-20261010")

class OriginalIssueSelfContinuingV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence=json.loads(REPORT.read_text()) if REPORT.is_file() else None

    def test_01_one_scoped_success_and_other_true_blocks(self):
        g=graph_spec()
        self.assertEqual(g["entry_nodes"],["verify_prior_science"])
        self.assertEqual(len([n for n in g["nodes"] if n["kind"]=="terminal"
              and n["terminal_status"]=="SUCCESS"]),1)
        self.assertEqual(g["nodes"][3]["id"],"run_real_public_gbnf_probe")

    def test_02_conditional_branches_exist(self):
        nodes={n["id"]:n for n in graph_spec()["nodes"]}
        self.assertEqual(nodes["oracle_gain_branch"]["branches"]["material"],"run_real_public_gbnf_probe")
        self.assertEqual(nodes["grammar_effect_branch"]["branches"]["material"],"diagnose_policy_gate_effect")
        self.assertEqual(nodes["grammar_effect_branch"]["branches"]["not_material"],"diagnose_other_selection_semantics")
        self.assertEqual(nodes["semantic_new_test_required"]["terminal_status"],"BLOCKED")

    def test_03_no_scheduled_task_and_no_reply_recursion(self):
        src=(ROOT/"tools/run_issue1_autonomous_tcc_workflow_v4.py").read_text()
        for bad in ("automations.create(","chatgpt.com/","launchctl","crontab","github.com/actions"):
            self.assertNotIn(bad,src)

    @unittest.skipUnless(REPORT.is_file(),"real 17-case gate model result not yet sealed")
    def test_04_real_17_case_source_and_score_verified(self):
        r=audit_grammar(self.evidence)
        self.assertEqual(r["real_model_calls"],17)
        self.assertEqual(r["case_count"],17)
        self.assertEqual(r["baseline_correct"],1)
        self.assertEqual(r["gate_inactive"],16)
        self.assertEqual(r["gate_active"],1)
        self.assertEqual(r["real_model_stdout_sha_count"],17)

    @unittest.skipUnless(REPORT.is_file(),"real result absent")
    def test_05_forged_prompt_sha_invalidates_gate_effect(self):
        x=copy.deepcopy(self.evidence)
        x["model_run"]["paired_cases"][0]["raw_real_inference"]["historical_prompt_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"PROMPT_OR_HISTORICAL_GRAMMAR_HASH_CHANGED"):
            audit_grammar(x)

    @unittest.skipUnless(REPORT.is_file(),"real result absent")
    def test_06_mutating_actual_model_raw_response_fails_closed(self):
        x=copy.deepcopy(self.evidence)
        x["model_run"]["paired_cases"][0]["raw_real_inference"]["raw_response"]='{"status":"EXECUTE"}'
        with self.assertRaisesRegex(ValueError,"TREATMENT_RAW_PARSE_MISMATCH"):
            audit_grammar(x)

    @unittest.skipUnless(REPORT.is_file(),"real result absent")
    def test_07_fake_100pct_score_invalidates_audit(self):
        x=copy.deepcopy(self.evidence)
        x["model_run"]["gate_treatment_decision_correct"]=17
        with self.assertRaisesRegex(ValueError,"FROZEN_GAIN_NOT_RECOMPUTED"):
            audit_grammar(x)

    @unittest.skipUnless(REPORT.is_file(),"real result absent")
    def test_08_original_A_E_replacement_claim_is_forbidden(self):
        x=copy.deepcopy(self.evidence)
        x["model_run"]["original_S1_S4_five_arm_complete"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_SCIENTIFIC_CLOSURE_CLAIM"):
            audit_grammar(x)

    @unittest.skipUnless(REPORT.is_file() and TCC.is_dir() and EC.is_dir(),"sealed evidence and pinned tools not ready")
    def test_09_actual_generated_tcc_complete_scope_but_not_original(self):
        r=run(TCC,EC)
        self.assertTrue(r["machine_scoped_complete"])
        self.assertTrue(r["S3_causal_oracle"]["causal_gain"]>.9)
        self.assertEqual(r["public_gate_real_model"]["real_model_calls"],17)
        self.assertFalse(r["original_A_E_S1_S4_completed"])
        self.assertFalse(r["original_issue_closure_authorized"])
        self.assertFalse(r["independent_gold_certified"])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"pinned tools missing")
    def test_10_missing_report_no_runtime_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            r=run(TCC,EC,report=Path(d)/"absent.json")
            self.assertEqual(r["terminal"],"blocked_integrity")
            self.assertFalse(r["machine_scoped_complete"])
            self.assertIn("PINNED_MODEL_EVIDENCE_NOT_AVAILABLE",r["failure"])

if __name__=="__main__":
    unittest.main()
