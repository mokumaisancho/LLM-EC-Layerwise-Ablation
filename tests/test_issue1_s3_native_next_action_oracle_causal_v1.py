from __future__ import annotations
import copy
import json
import unittest

from tools.run_issue1_s3_native_next_action_oracle_causal_v1 import (
    CONTRACT, ROOT, FIXTURE, EC_REPORT, LLM_REPORT, POLICY,
    blob,sha,assert_pins,visible_upstream,downstream,outcome_matches,
    evaluate,PROTOCOL
)


class NativeS3OracleCausalInterventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures=json.loads(FIXTURE.read_text())["fixtures"]
        cls.results=evaluate()

    def test_01_preregistered_contract_and_exact_historical_blobs(self):
        c=json.loads(CONTRACT.read_text())
        self.assertEqual(c["protocol"],PROTOCOL)
        self.assertEqual(c["status"],"FROZEN_BEFORE_EVALUATION")
        assert_pins(c)
        self.assertEqual(blob(FIXTURE),c["frozen_sources"]["fixture_git_blob"])

    def test_02_author_visible_only_no_oracle(self):
        for fx in self.fixtures:
            up=visible_upstream(fx)
            self.assertEqual(set(up),set(fx).intersection({
                "plan","completed_work_ids","blocked_work","dynamic_spec"}))
            self.assertNotIn("oracle",up)
            self.assertNotIn("category",up)
            self.assertNotIn("id",up)

    def test_03_model_oracle_same_upstream_hash_each_case(self):
        for fx,row in zip(self.fixtures,self.results["cases"]):
            self.assertEqual(row["upstream_sha256"],sha(visible_upstream(fx)))
            self.assertTrue(row["same_upstream_across_arms"])

    def test_04_pure_downstream_does_not_modify_upstream(self):
        upstream=visible_upstream(self.fixtures[0])
        before=copy.deepcopy(upstream)
        decision={"status":"REFRAME","work_id":"NONE","reason_code":"NONE"}
        result=downstream(upstream,decision)
        self.assertEqual(upstream,before)
        self.assertEqual(result["event"],"REFRAME")
        self.assertEqual(result["next_completed_work_ids"],sorted(before.get("completed_work_ids") or []))

    def test_05_valid_known_work_applies_exactly_one(self):
        fx=self.fixtures[0]
        up=visible_upstream(fx)
        oracle=fx["oracle"]
        outcome=downstream(up,oracle)
        self.assertEqual(outcome["event"],"ACTION_APPLIED")
        self.assertEqual(len(outcome["next_completed_work_ids"]),len(up["completed_work_ids"])+1)
        self.assertEqual(outcome["work_id"],oracle["work_id"])

    def test_06_injected_unknown_work_fails_closed(self):
        up=visible_upstream(self.fixtures[0])
        v=downstream(up,{"status":"EXECUTE","work_id":"work:SECRET:repair","reason_code":"NONE"})
        self.assertEqual(v["event"],"REJECTED_UNKNOWN_WORK_ID")
        self.assertEqual(v["next_completed_work_ids"],[])

    def test_07_injected_oracle_into_downstream_upstream_rejected(self):
        up=visible_upstream(self.fixtures[0]);up["oracle"]={"status":"EXECUTE"}
        with self.assertRaisesRegex(ValueError,"NON_PUBLIC_UPSTREAM_FIELD"):
            downstream(up,{"status":"REFRAME","work_id":"NONE","reason_code":"NONE"})

    def test_08_duplicated_completed_state_rejected(self):
        up=visible_upstream(self.fixtures[0]);valid=self.fixtures[0]["oracle"]["work_id"]
        up["completed_work_ids"]=[valid,valid]
        with self.assertRaisesRegex(ValueError,"DUPLICATE_COMPLETION_STATE"):
            downstream(up,{"status":"REFRAME","work_id":"NONE","reason_code":"NONE"})

    def test_09_precommitted_placeholder_and_actual_execution(self):
        self.assertEqual(self.results["case_count"],17)
        self.assertEqual(self.results["llm_downstream_success"],1)
        self.assertEqual(self.results["ec_downstream_success"],17)
        self.assertEqual(self.results["oracle_S3_only_downstream_success"],17)
        self.assertAlmostEqual(self.results["causal_gain_oracle_S3_minus_llm_S3"],16/17)
        self.assertEqual(self.results["placebo_effect"],0.0)

    def test_10_no_original_five_arm_or_independent_holdout_false_claim(self):
        v=self.results
        for key in ("independent_gold","original_generic_s3_multiselection_tested",
                    "original_s1_s4_A_to_E_completed","original_issue_closure_authorized"):
            self.assertFalse(v[key])

    def test_11_casewise_strict_oracle_gain_replayed(self):
        wrong=[r["case_id"] for r in self.results["cases"]
               if not r["llm_downstream_success"]]
        self.assertEqual(len(wrong),16)
        self.assertEqual(set(wrong),set(r["case_id"] for r in self.results["cases"])-
                         {"N217"})
        for row in self.results["cases"]:
            self.assertEqual(row["downstream_llm_A"],row["downstream_placebo"])
            self.assertTrue(row["oracle_visible_only_in_evaluation_and_E"])

    def test_12_fake_case_policies_do_not_escape_frozen_pins(self):
        c=copy.deepcopy(json.loads(CONTRACT.read_text()))
        c["frozen_sources"]["fixture_git_blob"]="0"*40
        with self.assertRaisesRegex(ValueError,"FROZEN_SOURCE_BLOB_CHANGED"):
            assert_pins(c)


if __name__=="__main__":
    unittest.main()
