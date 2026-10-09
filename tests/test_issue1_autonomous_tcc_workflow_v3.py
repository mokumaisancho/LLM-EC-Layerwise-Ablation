from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_issue1_autonomous_tcc_workflow_v3 import (
    REPORT,ROOT,S4_CONTRACT,PROTOCOL,audit_report,run,spec,TCC_SOURCE
)

TCC_ROOT=Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC_ROOT=Path("/private/tmp/llmec-ecv44-source-20261010")


class Issue1Stage3MachineSelfDirectedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real=json.loads(REPORT.read_text())
        cls.available=TCC_ROOT.is_dir() and EC_ROOT.is_dir()

    def test_01_preregistered_real_inference_scores_recomputed(self):
        v=audit_report(self.real)
        self.assertEqual(v["cases"],10)
        self.assertEqual(v["calls"],20)
        self.assertEqual(v["structural_correct"],7)
        self.assertEqual(v["enriched_correct"],7)
        self.assertEqual(v["typed_public_correct"],10)
        self.assertEqual(v["paired_enriched_minus_structural"],0.0)
        self.assertEqual(v["branch"],"no_material_effect")
        self.assertEqual(v["actual_qwen_changed_decisions"],[])

    def test_02_one_and_only_one_scoped_TCC_success_terminal(self):
        graph=spec()
        self.assertEqual(len([n for n in graph["nodes"]
          if n["kind"]=="terminal" and n["terminal_status"]=="SUCCESS"]),1)
        self.assertEqual(graph["entry_nodes"],["verify_origin_and_s2"])
        self.assertTrue(any(n["id"]=="branch_on_real_information_effect" for n in graph["nodes"]))

    def test_03_changed_upstream_case_reference_fails(self):
        fake=copy.deepcopy(self.real)
        fake["result"]["case_results"][0]["full_public_features_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"PUBLIC_CASE_HASH_DRIFT"):
            audit_report(fake)

    def test_04_changed_specific_arm_input_hash_fails(self):
        fake=copy.deepcopy(self.real)
        fake["result"]["case_results"][0]["enriched"]["input_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"ACTUAL_MODEL_INPUT_NOT_FIXED_TO_ARM"):
            audit_report(fake)

    def test_05_counterfeit_source_contract_fails(self):
        fake=copy.deepcopy(self.real)
        fake["pre_registered_contract_blob_sha1"]="0"*40
        with self.assertRaisesRegex(ValueError,"PREREGISTRATION_SOURCE_BLOB_DRIFT"):
            audit_report(fake)

    def test_06_forged_raw_or_aggregate_scoring_fails(self):
        fake=copy.deepcopy(self.real)
        fake["result"]["case_results"][0]["structure_correct"]=False
        with self.assertRaisesRegex(ValueError,"REPORTED_SCORE_NOT_RAW_RECOMPUTATION"):
            audit_report(fake)
        fake=copy.deepcopy(self.real)
        fake["result"]["structural_correct"]=10
        with self.assertRaisesRegex(ValueError,"AGGREGATE_RESULTS_NOT_RECOMPUTED"):
            audit_report(fake)

    def test_07_false_independent_oracle_completed_claim_fails(self):
        fake=copy.deepcopy(self.real)
        fake["result"]["independent_holdout"]=True
        with self.assertRaisesRegex(ValueError,"SCOPED_RESEARCH_FALSE_ORIGINAL_COMPLETION"):
            audit_report(fake)

    def test_08_wrong_model_prediction_parser_fails(self):
        fake=copy.deepcopy(self.real)
        fake["result"]["case_results"][0]["structure"]["parsed_prediction"]="CONTINUE"
        with self.assertRaisesRegex(ValueError,"RAW_PARSE_OR_PREDICTION_TAMPERED"):
            audit_report(fake)

    @unittest.skipUnless(TCC_ROOT.is_dir() and EC_ROOT.is_dir(),"pinned read-only assets not installed")
    def test_09_real_generated_TCC_all_available_no_manual_prompts(self):
        out=run(TCC_ROOT,EC_ROOT)
        self.assertEqual(out["tcc_terminal_id"],"accept_scoped_machine_terminal")
        self.assertEqual(out["new_actual_llm_info_intervention"]["branch"],"no_material_effect")
        self.assertFalse(out["full_original_s1_s4_A_E_completed"])
        self.assertFalse(out["scientific_capability_preservation_certified"])
        self.assertFalse(out["ecv4_original_issue_closure_authorized"])
        self.assertFalse(out["new_scheduled_tasks"])
        self.assertEqual(out["ecv4_evidence"]["schema"],"tcc.ecv4-evidence.v0")
        self.assertEqual(out["terminal"],"ALL_AVAILABLE_SCOPED_EXPERIMENTS_AUDITED_ORIGINAL_FULL_STUDY_STILL_OPEN")

    @unittest.skipUnless(TCC_ROOT.is_dir() and EC_ROOT.is_dir(),"pinned read-only assets not installed")
    def test_10_forged_actual_file_fails_closed_not_science(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"forged.json"
            fake=copy.deepcopy(self.real)
            fake["result"]["case_results"][2]["enriched"]["raw_response"]="CONTINUE"
            p.write_text(json.dumps(fake))
            out=run(TCC_ROOT,EC_ROOT,report=p)
            self.assertEqual(out["tcc_terminal_id"],"blocked_integrity")
            self.assertFalse(out["ecv4_original_issue_closure_authorized"])
            self.assertIn("RAW_PARSE_OR_PREDICTION_TAMPERED",out["failure"])

    @unittest.skipUnless(TCC_ROOT.is_dir() and EC_ROOT.is_dir(),"pinned read-only assets not installed")
    def test_11_missing_real_report_causes_automatic_inference_then_atomic_seal(self):
        # Mock is an already SEALED REAL output. Tests branching/atomic persistence
        # only, not model competence. True 20-call model inference is separately
        # recorded in results/issue1_s4_qwen20_paired_info_ablation_actual_2026-10-10.json.
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/"new-report.json"
            with patch("tools.run_issue1_s4_public_info_paired_llm_v1.run",
                       return_value=copy.deepcopy(self.real["result"])) as model_runner:
                x=run(TCC_ROOT,EC_ROOT,report=target,
                      model=Path("/verified-model"),llama=Path("/verified-llama"),seconds=65)
            model_runner.assert_called_once()
            self.assertEqual(x["tcc_terminal_id"],"accept_scoped_machine_terminal")
            sealed=json.loads(target.read_text())
            self.assertEqual(sealed["result"]["actual_inferences"],20)
            self.assertEqual(sealed["source_verification"]["model_actual_calls"],20)
            self.assertFalse(sealed["source_verification"]["original_A_E_completed"])
            # Subsequent invocation must use only immutable cached output,
            # not call inference again.
            with patch("tools.run_issue1_s4_public_info_paired_llm_v1.run",
                       side_effect=AssertionError("unexpected repeated inference")):
                resumed=run(TCC_ROOT,EC_ROOT,report=target)
            self.assertEqual(resumed["tcc_terminal_id"],"accept_scoped_machine_terminal")

    @unittest.skipUnless(TCC_ROOT.is_dir() and EC_ROOT.is_dir(),"pinned read-only assets not installed")
    def test_12_missing_real_report_without_model_is_blocked_not_false_complete(self):
        with tempfile.TemporaryDirectory() as td:
            missing=Path(td)/"absent.json"
            out=run(TCC_ROOT,EC_ROOT,report=missing)
            self.assertEqual(out["tcc_terminal_id"],"blocked_integrity")
            self.assertIn("REAL_20_MODEL_RAW_REPORT_MISSING",out["failure"])
            self.assertFalse(out["ecv4_original_issue_closure_authorized"])

if __name__=="__main__":
    unittest.main()
