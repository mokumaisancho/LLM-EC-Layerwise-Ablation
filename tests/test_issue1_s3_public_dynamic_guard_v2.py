from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

from tools.run_issue1_s3_public_dynamic_guard_v2 import (
    CONTRACT,ROOT,PROTOCOL,dynamic_public_guard,evaluate,
)
from tools.run_issue1_s3_public_guard_decomposition_v1 import public
FROZEN=ROOT/"fixtures/function_boundary_next_action_v1.json"
ACTUAL=ROOT/"results/issue1_public_gate_gbnf_qwen17_actual_2026-10-10.json"


class S3DynamicNativeBoundaryVersionedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx={f["id"]:f for f in json.loads(FROZEN.read_text())["fixtures"]}
        cls.actual={r["id"]:r for r in json.loads(ACTUAL.read_text())["model_run"]["paired_cases"]}
        cls.study=evaluate()

    def test_01_precommit_contract_and_no_original_closure(self):
        c=json.loads(CONTRACT.read_text())
        self.assertEqual(c["protocol"],PROTOCOL)
        self.assertEqual(c["status"],"VERSIONED_RETROSPECTIVE_SUCCESSOR_FROZEN_BEFORE_RUN")
        self.assertFalse(c["original_AC01_20_completed"] if "original_AC01_20_completed" in c else False)

    def test_02_public_guard_no_oracle_category_or_id(self):
        f=self.fx["N215"]
        p=public(f)
        self.assertNotIn("oracle",p)
        self.assertNotIn("category",p)
        self.assertNotIn("id",p)
        self.assertEqual(len(p),4)

    def test_03_dynamic_dependency_not_ready_detected(self):
        name="N215"
        reasons=dynamic_public_guard(public(self.fx[name]),self.actual[name]["treatment"])
        self.assertIn("DYNAMIC_DEPENDENCY_NOT_READY",reasons)

    def test_04_dynamic_urgency_dominance_detected(self):
        name="N216"
        reasons=dynamic_public_guard(public(self.fx[name]),self.actual[name]["treatment"])
        self.assertIn("DYNAMIC_URGENCY_DOMINANCE",reasons)

    def test_05_non_dynamic_cases_are_exactly_previous_invariants(self):
        from tools.run_issue1_s3_public_guard_decomposition_v1 import public_guard
        for name,f in self.fx.items():
            if f.get("dynamic_spec"):continue
            p=public(f);model=self.actual[name]["treatment"]
            self.assertEqual(dynamic_public_guard(p,model),public_guard(p,model))

    def test_06_unknown_public_dependency_rejected(self):
        p=public(copy.deepcopy(self.fx["N215"]))
        p["dynamic_spec"]["dependency_graph"]["issue:I01"]=["issue:MAGIC"]
        with self.assertRaisesRegex(ValueError,"DYNAMIC_DEPENDENCY_UNKNOWN_ISSUE"):
            dynamic_public_guard(p,self.actual["N215"]["treatment"])

    def test_07_hidden_oracle_field_rejected(self):
        p=public(self.fx["N215"]);p["oracle"]={"work_id":"SECRET"}
        with self.assertRaisesRegex(ValueError,"NONPUBLIC_INPUT_REJECTED"):
            dynamic_public_guard(p,self.actual["N215"]["treatment"])

    def test_08_negative_case_no_false_positive(self):
        for name in ("N211","N217"):
            p=public(self.fx[name])
            self.assertEqual(dynamic_public_guard(p,self.actual[name]["treatment"]),[])

    def test_09_actual_17_scoped_decomposition_measured(self):
        v=self.study
        self.assertEqual(v["cases"],17)
        self.assertEqual(v["pure_model_correct"],2)
        self.assertEqual(v["original_model_wrong"],15)
        self.assertEqual(v["fixed_public_guard_detected_wrong"],13)
        self.assertEqual(v["extended_guard_detected_wrong"],15)
        self.assertEqual(v["extended_guard_false_rejected_correct"],0)

    def test_10_native_fallback_quality_is_not_llm_quality(self):
        v=self.study
        self.assertTrue(v["improvement_attributable_to_EC_invocations_not_model"])
        self.assertEqual(v["extended_native_EC_fallback_count"],15)
        self.assertEqual(v["extended_hybrid_correct_with_native_fallback"],17)
        self.assertEqual(v["pure_native_EC_correct"],17)

    def test_11_dynamic_reason_coverage_exactly_two_remaining(self):
        self.assertEqual(self.study["new_dynamic_rule_trigger_counts"],
                         {"DYNAMIC_DEPENDENCY_NOT_READY":1,"DYNAMIC_URGENCY_DOMINANCE":1})
        self.assertEqual(self.study["remaining_uncaught_wrong_case_ids"],[])

    def test_12_no_full_AE_science_or_new_model_inference_fabricated(self):
        v=self.study
        self.assertFalse(v["independent_blind"])
        self.assertFalse(v["original_full_A_E_completed"])
        self.assertEqual(v["new_model_inferences"],0)
        self.assertTrue(v["same_public_model_upstream_pinned"])

if __name__=="__main__":
    unittest.main()
