from __future__ import annotations
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.replay_issue1_ecv44_native_next_action_v2 import (
    ROOT, PROTOCOL, FIXTURE_SHA, CONTRACT_SHA, blob_sha, native_predict,
    public_fields, replay, verify, digest,
)

EC_PATH=Path("/private/tmp/llmec-ecv44-source-20261010")


class NativeEcHistorical17ReproductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((ROOT/"fixtures/function_boundary_next_action_v1.json").read_text())
        cls.ec_available=(EC_PATH/"01_repo/src/v4/ec_next_action_authority.py").is_file()
        if cls.ec_available:
            cls.actual=replay(EC_PATH)

    def test_01_frozen_dataset_has_authentic_blob(self):
        path=ROOT/"fixtures/function_boundary_next_action_v1.json"
        self.assertEqual(blob_sha(path.read_bytes()),FIXTURE_SHA)
        self.assertEqual(len(self.fixture["fixtures"]),17)
        self.assertEqual(len({fx["id"] for fx in self.fixture["fixtures"]}),17)

    def test_02_frozen_policy_is_byte_exact(self):
        path=ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json"
        self.assertEqual(blob_sha(path.read_bytes()),CONTRACT_SHA)
        val=json.loads(path.read_text())
        self.assertFalse(val["fixture_oracle_mutation"])
        self.assertEqual(val["status"],"FROZEN_BEFORE_MODEL_RUN")

    def test_03_predicate_only_sees_explicitly_allowed_visible_input(self):
        for fx in self.fixture["fixtures"]:
            visible=public_fields(fx)
            self.assertTrue(set(visible).issubset({"plan","completed_work_ids","blocked_work","dynamic_spec"}))
            self.assertNotIn("oracle",visible)
            self.assertNotIn("category",visible)
            self.assertNotIn("id",visible)

    def test_04_forced_gold_key_rejected(self):
        fx=copy.deepcopy(self.fixture["fixtures"][0])
        fx["plan"]["oracle"]="EXECUTE"
        with self.assertRaisesRegex(ValueError,"PRIVILEGED_PREDICTOR_INPUT"):
            public_fields(fx)

    def test_05_source_verifier_rejects_missing_pinned_checkout(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"EC_PINNED_GIT_CHECKOUT_REQUIRED"):
                verify(Path(d),ROOT/"fixtures/function_boundary_next_action_v1.json",
                       ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json")

    def test_06_fixture_corruption_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.json"
            p.write_bytes((ROOT/"fixtures/function_boundary_next_action_v1.json").read_bytes()+b"\n")
            if not self.ec_available:self.skipTest("Read-only pinned EC checkout not installed")
            with self.assertRaisesRegex(ValueError,"FROZEN_FIXTURE_BLOB_MISMATCH"):
                verify(EC_PATH,p,ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json")

    def test_07_policy_corruption_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"contract.json"
            p.write_bytes((ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json").read_bytes()+b"\n")
            if not self.ec_available:self.skipTest("Read-only pinned EC checkout not installed")
            with self.assertRaisesRegex(ValueError,"FROZEN_CONTRACT_BLOB_MISMATCH"):
                verify(EC_PATH,ROOT/"fixtures/function_boundary_next_action_v1.json",p)

    @unittest.skipUnless(EC_PATH.exists(),"Pinned EC checkout not present on test host")
    def test_08_all_17_native_cases_reproduced(self):
        x=self.actual
        self.assertEqual(x["cases_replayed"],17)
        self.assertEqual(x["ec_decision_correct"],17)
        self.assertEqual(x["ec_reason_correct"],17)
        self.assertEqual(x["terminal"],"NATIVE_EC_17_CASE_REPLAY_MATCH")
        self.assertTrue(x["historical_ec_aggregate_reproduced"])

    @unittest.skipUnless(EC_PATH.exists(),"Pinned EC checkout not present on test host")
    def test_09_two_dynamic_cases_are_not_assumed_static(self):
        x={row["case_id"]:row for row in self.actual["rows"]}
        for name in ("N215","N216"):
            self.assertIsNotNone(x[name]["native_dynamic_sha256"])
            self.assertTrue(x[name]["decision_correct"])
            self.assertTrue(x[name]["reason_correct"])

    @unittest.skipUnless(EC_PATH.exists(),"Pinned EC checkout not present on test host")
    def test_10_four_fail_closed_or_reframe_cases_reproduced(self):
        candidates=[r for r in self.actual["rows"] if r["frozen_gold"]["status"] in ("FAIL_CLOSED","REFRAME")]
        self.assertEqual(len(candidates),4)
        self.assertTrue(all(r["decision_correct"] and r["reason_correct"] for r in candidates))

    @unittest.skipUnless(EC_PATH.exists(),"Pinned EC checkout not present on test host")
    def test_11_each_model_visible_input_and_output_sealed(self):
        rows=self.actual["rows"]
        self.assertEqual(len({r["case_id"] for r in rows}),17)
        for row in rows:
            self.assertEqual(len(row["public_input_sha256"]),64)
            self.assertEqual(row["raw_prediction_sha256"],digest(row["prediction"]))

    @unittest.skipUnless(EC_PATH.exists(),"Pinned EC checkout not present on test host")
    def test_12_no_broader_original_claim(self):
        x=self.actual
        self.assertFalse(x["original_llm0_compared"])
        self.assertFalse(x["llm_reinferred"])
        self.assertFalse(x["original_phase1_five_arm_complete"])
        self.assertFalse(x["independent_holdout"])
        self.assertIn("not generic S3 multiselection",x["native_scope"])


if __name__=="__main__":
    unittest.main()
