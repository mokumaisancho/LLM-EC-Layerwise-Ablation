from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_issue1_root_ac_w4_tcc_v7 import (
    ROOT,CFG,CFG_BLOB,EC_COMMIT,PROTOCOL,git_blob,
    qualification_plan,run,spec
)
from tools.run_issue1_root_ac_orchestrator_v6 import run as run_v6
from tools.run_issue1_ec_native_layerwise_source_probe_v1 import run as native_probe

TCC=Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC44=Path("/private/tmp/llmec-ecv44-source-20261010")
NATIVE=Path("/private/tmp/issue1-ec-native-layerwise-20261010")

@unittest.skipUnless(TCC.is_dir() and EC44.is_dir() and NATIVE.is_dir(),
                     "Pinned original TCC and new EC source checkouts absent")
class Issue1W4ActualNativeSourceTCCv7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v6=run_v6(TCC,EC44)
        cls.native=native_probe(NATIVE)
        cls.config=json.loads(CFG.read_text())

    def test_01_explicit_frozen_v7_AC_contract_hash(self):
        self.assertEqual(git_blob(CFG.read_bytes()),CFG_BLOB)
        self.assertEqual(self.config["original_required_ac_unchanged"],18)
        self.assertEqual(self.config["native_new_source_commit"],EC_COMMIT)
        self.assertEqual(self.v6["MVP_18_required_AC_status"]["required_pass_count"],2)

    def test_02_native_new_EC_source_integrated_is_actual(self):
        self.assertEqual(self.native["native_negative_tests_passed"],14)
        self.assertEqual(self.native["four_author_exposed_fixtures"],4)
        self.assertEqual(self.native["casewise_S3_development_matches"],4)
        self.assertEqual(self.native["casewise_S4_development_matches"],4)
        self.assertFalse(self.native["external_semantic_adjudicator_certified"])
        self.assertFalse(self.native["original_four_layer_AE_completed"])

    def test_03_W4_dependency_matrix_has_no_skipped_edges(self):
        x=qualification_plan(self.v6,self.native,self.config)
        jobs=x["work_dependencies"]
        self.assertEqual(jobs["W4A_NATIVE_CANDIDATE_SET_AND_CLOSURE_ENGINE"]["status"],
                         "IMPLEMENTED_EXPERIMENTAL_VERIFIED")
        self.assertEqual(jobs["W5_ORIGINAL_S1_S4_A_B_C_D_E"]["depends_on"],
            ["W4B_INDEPENDENT_SEMANTIC_ADJUDICATOR",
             "W4C_COMPLETE_S4_OBLIGATION_PROOF"])
        self.assertEqual(jobs["W6_ROOT_18AC_MVP_AND_CAUSAL_LOCALIZATION"]["depends_on"],
                         ["W5_ORIGINAL_S1_S4_A_B_C_D_E"])
        self.assertFalse(x["original_issue_mvp_complete"])

    def test_04_missing_semantic_truth_and_obligations_not_reported_PASS(self):
        x=qualification_plan(self.v6,self.native,self.config)
        self.assertFalse(x["independent_semantic_adjudicator_qualified"])
        self.assertFalse(x["complete_S4_obligation_inventory_independently_qualified"])
        self.assertEqual(x["MVP_scientifically_passed"],2)

    def test_05_one_root_success_only_never_scoped_success(self):
        graph=spec()
        self.assertEqual(len(graph["nodes"]),8)
        self.assertEqual([n["id"] for n in graph["nodes"] if n["kind"]=="terminal"
           and n["terminal_status"]=="SUCCESS"],["root_science_verified"])
        self.assertEqual(graph["entry_nodes"],["execute_root_original_v6"])

    def test_06_true_complete_pretence_in_native_source_fails_closed(self):
        wrong=copy.deepcopy(self.native)
        wrong["external_semantic_adjudicator_certified"]=True
        with self.assertRaisesRegex(ValueError,"UNVERIFIED_SEMANTIC_TRUTH"):
            qualification_plan(self.v6,wrong,self.config)

    def test_07_forged_original_root_AC18_fails_closed(self):
        wrong=copy.deepcopy(self.v6)
        wrong["MVP_18_required_AC_status"]["required_pass_count"]=18
        with self.assertRaisesRegex(ValueError,"ROOT_AC_MATRIX_NOT_REPRODUCED"):
            qualification_plan(wrong,self.native,self.config)

    def test_08_forged_native_14_test_success_must_fail(self):
        wrong=copy.deepcopy(self.native);wrong["native_negative_tests_passed"]=13
        with self.assertRaisesRegex(ValueError,"W4_NATIVE_ENGINE_SOURCE_NOT_ACTUALLY_VERIFIED"):
            qualification_plan(self.v6,wrong,self.config)

    def test_09_caller_does_not_need_repeated_user_prompts(self):
        o=run(TCC,EC44,NATIVE)
        self.assertEqual(o["TCC_terminal"],"blocked_W4_semantic_authority")
        self.assertEqual(o["terminal"],
                         "W4_NATIVE_EXECUTED_INDEPENDENT_SEMANTIC_AUTHORITY_REQUIRED")
        self.assertEqual(o["TCC_nodes"],8)
        self.assertEqual(o["TCC_edges"],9)
        self.assertFalse(o["original_scientifically_complete"])
        self.assertFalse(o["scheduled_tasks_created"])
        self.assertEqual(o["evidence_integrity_failures"],[])
        self.assertTrue(o["raw_evidence_pre_post_same"])
        self.assertTrue(o["source_code_pre_post_same"])

    def test_10_tampered_native_result_fails_entire_TCC_not_science(self):
        fake=copy.deepcopy(self.native);fake["original_four_layer_AE_completed"]=True
        with patch("tools.run_issue1_root_ac_w4_tcc_v7.run_native_probe",return_value=fake):
            out=run(TCC,EC44,NATIVE)
        self.assertEqual(out["TCC_terminal"],"blocked_integrity")
        self.assertFalse(out["original_scientifically_complete"])
        self.assertTrue(out["evidence_integrity_failures"])

    def test_11_tampered_predeclared_config_invalidated_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"contract.json";p.write_text(json.dumps({"schema":"fake"}))
            with patch("tools.run_issue1_root_ac_w4_tcc_v7.CFG",p):
                with self.assertRaisesRegex(ValueError,"VERSIONED_W4_DEPENDENCY_CONTRACT_CHANGED"):
                    run(TCC,EC44,NATIVE)

    def test_12_native_engine_changed_between_input_and_output_fails_closed(self):
        # The engine module is pinned before and after the nested science;
        # this mocked second pin represents a mid-run source mutation.
        with patch("tools.run_issue1_root_ac_w4_tcc_v7.pin_native_source",
                   side_effect=[None,ValueError("SIMULATED_NATIVE_MUTATION")]):
            out=run(TCC,EC44,NATIVE)
        self.assertEqual(out["TCC_terminal"],"blocked_integrity")
        self.assertFalse(out["original_scientifically_complete"])
        self.assertTrue(out["evidence_integrity_failures"])

    def test_13_no_schedules_ui_automations_or_false_root_claim(self):
        src=(ROOT/"tools/run_issue1_root_ac_w4_tcc_v7.py").read_text()
        for bad in ("automations.create(","chatgpt.com/","crontab","launchctl"):
            self.assertNotIn(bad,src)
        self.assertEqual(self.config["branch"]["new_source_missing"],"BLOCK_INTEGRITY")

if __name__=="__main__":unittest.main()
