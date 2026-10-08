from __future__ import annotations
import copy
import hashlib
import json
import unittest

from evaluation.quality_blind_v2 import (
    ARM_PROTOCOL, ARMS, GOLD_PROTOCOL, PUBLIC_PROTOCOL, SEAL_PROTOCOL,
    BlindProtocolError, make_precommit, score, sha, validate_arm,
    validate_public, validate_gold,
)
SALT="unit-test-only-synthetic-not-secret-"+("a"*48)

def fixture():
    public={
        "protocol":PUBLIC_PROTOCOL,"study_id":"unit-test-not-independent-v2",
        "ontology":{"actions":["OPEN","CLOSE","ABSTAIN"]},
        "task_context":{"training_examples":[{"instruction":"something opens a box","state_before":[0],"state_after":[1]}]},
        "public_provenance":{"source_id":"synthetic-corpus-provider",
            "independent_author":"fixture-writer",
            "training_overlap_reviewed":True,"prior_v5_fixture_excluded":True},
        "cases":[
          {"case_id":"B0001","text":"Enable review of case 921","entity_registry":{"E1":{"type":"CLAIM","surface_forms":["case 921"]}},"contrast_pair":"G1"},
          {"case_id":"B0002","text":"Disable review of case 921","entity_registry":{"E1":{"type":"CLAIM","surface_forms":["case 921"]}},"contrast_pair":"G1"},
          {"case_id":"B0003","text":"案件921の審査を始める","entity_registry":{"E1":{"type":"CLAIM","surface_forms":["案件921"]}},"contrast_pair":"G2"},
          {"case_id":"B0004","text":"案件921の審査を終える","entity_registry":{"E1":{"type":"CLAIM","surface_forms":["案件921"]}},"contrast_pair":"G2"},
          {"case_id":"B0005","text":"Unclear whether case 925 is open or closed","entity_registry":{"E1":{"type":"CLAIM","surface_forms":["case 925"]}},"contrast_pair":"G3"},
          {"case_id":"B0006","text":"Enable review of case 925","entity_registry":{"E1":{"type":"CLAIM","surface_forms":["case 925"]}},"contrast_pair":"G3"},
        ]}
    gold={"protocol":GOLD_PROTOCOL,"study_id":public["study_id"],
          "gold_provenance":{"independent_adjudicator":"fixture-adjudicator",
              "adjudication_protocol":"SYNTHETIC_UNIT_TEST_ONLY","annotation_complete_before_predictions":True},
          "labels":[
            {"case_id":f"B{i:04d}","gold_action":a,
             "capability":cap,"critical":True,"tail":i in (3,4,5)}
            for i,a,cap in [(1,"OPEN","standard"),(2,"CLOSE","standard"),
                            (3,"OPEN","japanese_counterfactual"),(4,"CLOSE","japanese_counterfactual"),
                            (5,"ABSTAIN","ambiguity"),(6,"OPEN","ambiguity")]]}
    predictions={
      "LLM0":["OPEN","CLOSE","OPEN","CLOSE","ABSTAIN","OPEN"],
      "V1":["OPEN","CLOSE","OPEN","OPEN","OPEN","OPEN"],
      "V4":["OPEN","CLOSE","OPEN","OPEN","OPEN","OPEN"],
      "V5":["OPEN","CLOSE","ABSTAIN","ABSTAIN","ABSTAIN","OPEN"]}
    arms={}
    for arm_name in ARMS:
        rows=[]
        for row,answer in zip(public["cases"],predictions[arm_name]):
            raw=json.dumps({"action":answer},sort_keys=True)
            rows.append({"case_id":row["case_id"],
                         "input_sha256":sha({"text":row["text"],"entity_registry":row["entity_registry"]}),
                         "raw_output":raw,"raw_sha256":hashlib.sha256(raw.encode()).hexdigest()})
        arms[arm_name]={
            "protocol":ARM_PROTOCOL,"study_id":public["study_id"],"arm":arm_name,
            "public_sha256":sha(public),"runtime_source_sha256":("a"*64),
            "run_spec_sha256":("b"*64),"model_or_runtime_ref":"SYNTHETIC_TEST_NOT_REAL_INFERENCE",
            "adapter_sha256":("c"*64),"raw_rows":rows,"raw_rows_sha256":sha(rows)}
    precommit=make_precommit(public,gold,salt=SALT)
    seal={"protocol":SEAL_PROTOCOL,"study_id":public["study_id"],
          "public_sha256":sha(public),"gold_commitment":precommit["gold_commitment"],
          "arm_raw_commitments":{name:sha(arms[name]) for name in ARMS},
          "gold_access_after_arms":True,
          "independent_review":{"status":"PENDING","review_ref":""}}
    return public,gold,arms,seal


class BlindQualityEvaluatorTests(unittest.TestCase):
    def run_score(self,modify=None):
        public,gold,arms,seal=fixture()
        if modify:modify(public,gold,arms,seal)
        return score(public,gold,arms,seal,salt=SALT)

    def reject(self,modify,reason):
        with self.assertRaisesRegex(BlindProtocolError,reason):
            self.run_score(modify)

    def test_01_all_four_arms_scored_but_never_certified(self):
        report=self.run_score()
        self.assertEqual(report["terminal"],"REVIEW_REQUIRED_SCORES_ARE_NOT_SCIENTIFIC_CERTIFICATION")
        self.assertFalse(report["quality_preservation_certified"])
        self.assertEqual(report["case_count"],6)
        self.assertEqual(report["arm_metrics"]["V1"]["correct"],4)
        self.assertEqual(report["arm_metrics"]["V5"]["legitimate_false_refusals"],2)
        self.assertEqual(report["contrast_pair_non_discrimination"]["V1"],["G2"])
        self.assertEqual(report["contrast_pair_non_discrimination"]["V5"],["G2"])
        self.assertEqual(report["adjacent_transitions"]["V4_TO_V5"]["correct_to_abstain"],["B0003"])
        self.assertIn("B0004",report["anchor_losses"]["V5"])

    def test_02_gold_not_in_public(self):
        def modify(p,g,a,s):p["task_context"]["gold"]={"B0001":"OPEN"}
        self.reject(modify,"PUBLIC_CONTAINS_EVALUATION_KEY")

    def test_03_prior_exposed_fixture_id_rejected(self):
        def modify(p,g,a,s):p["cases"][0]["case_id"]="H07"
        self.reject(modify,"HISTORICAL_V5_ID_FORBIDDEN")

    def test_04_missing_original_llm_rejected(self):
        def modify(p,g,a,s):a.pop("LLM0")
        self.reject(modify,"FOUR_GENUINE_ARMS_REQUIRED")

    def test_05_wrong_precommitted_gold_rejected(self):
        def modify(p,g,a,s):g["labels"][0]["gold_action"]="CLOSE"
        self.reject(modify,"GOLD_REVEAL_PRECOMMIT_MISMATCH")

    def test_06_fake_raw_hash_rejected(self):
        def modify(p,g,a,s):a["V1"]["raw_rows"][0]["raw_output"]='{"action":"CLOSE"}'
        self.reject(modify,"ARM_SEAL_DRIFT")

    def test_07_prediction_case_dropped_rejected(self):
        def modify(p,g,a,s):
            arm=a["V5"];arm["raw_rows"].pop()
            arm["raw_rows_sha256"]=sha(arm["raw_rows"])
            s["arm_raw_commitments"]["V5"]=sha(arm)
        self.reject(modify,"ARM_INCOMPLETE_COVERAGE")

    def test_08_silent_rescore_forbidden(self):
        def modify(p,g,a,s):s["gold_access_after_arms"]=False
        self.reject(modify,"GOLD_ACCESS_CHRONOLOGY_INVALID")

    def test_09_nonce_wrong_rejected(self):
        p,g,a,s=fixture()
        with self.assertRaisesRegex(BlindProtocolError,"GOLD_REVEAL_PRECOMMIT_MISMATCH"):
            score(p,g,a,s,salt="other-long-salt-"+"z"*64)

    def test_10_labelled_contrast_must_differ(self):
        def modify(p,g,a,s):g["labels"][1]["gold_action"]="OPEN"
        with self.assertRaisesRegex(BlindProtocolError,"GOLD_CONTRAST_NOT_DISCRIMINATIVE"):
            p,g,a,s=fixture()
            modify(p,g,a,s)
            validate_gold(g,p)

    def test_11_lucky_same_answer_detected(self):
        r=self.run_score()
        self.assertIn("G2",r["contrast_pair_non_discrimination"]["V1"])
        self.assertTrue(r["regression_on_supplied_labels"])

    def test_12_invalid_json_kept_in_denominator(self):
        p,g,arms,seal=fixture()
        arm=arms["LLM0"]
        row=arm["raw_rows"][0];row["raw_output"]="not json"
        row["raw_sha256"]=hashlib.sha256(b"not json").hexdigest()
        arm["raw_rows_sha256"]=sha(arm["raw_rows"])
        seal["arm_raw_commitments"]["LLM0"]=sha(arm)
        result=score(p,g,arms,seal,salt=SALT)
        self.assertEqual(result["arm_metrics"]["LLM0"]["format_failures"],1)
        self.assertEqual(result["arm_metrics"]["LLM0"]["legitimate_total"],5)

    def test_13_source_not_adjudicator(self):
        def modify(p,g,a,s):g["gold_provenance"]["independent_adjudicator"]="fixture-writer"
        self.reject(modify,"GOLD_SOURCE_NOT_SEPARATED")

    def test_14_input_hash_tamper_rejected_after_refreeze(self):
        p,g,arms,seal=fixture()
        row=arms["V5"]["raw_rows"][0]
        row["input_sha256"]="f"*64
        arms["V5"]["raw_rows_sha256"]=sha(arms["V5"]["raw_rows"])
        seal["arm_raw_commitments"]["V5"]=sha(arms["V5"])
        with self.assertRaisesRegex(BlindProtocolError,"ARM_PER_CASE_INPUT_TAMPERED"):
            score(p,g,arms,seal,salt=SALT)

    def test_15_self_attested_external_review_does_not_grant_qualification(self):
        p,g,arms,seal=fixture()
        seal["independent_review"]={"status":"EXTERNALLY_REVIEWED","review_ref":"fake-self-attested"}
        result=score(p,g,arms,seal,salt=SALT)
        self.assertFalse(result["quality_preservation_certified"])
        self.assertFalse(result["external_independence_verified_by_evaluator"])

    def test_16_gold_annotation_before_outputs_required(self):
        def modify(p,g,a,s):g["gold_provenance"]["annotation_complete_before_predictions"]=False
        self.reject(modify,"GOLD_NOT_FROZEN_BEFORE_PREDICTION")

    def test_17_prediction_gold_does_not_enter_training_context(self):
        p,g,a,s=fixture()
        self.assertNotIn("gold_action",json.dumps(p))
        self.assertNotIn("fixture-adjudicator",json.dumps(p))
        self.assertNotIn("raw_output",json.dumps(p))
        self.assertEqual(set(a),set(ARMS))

    def test_18_repeatability(self):
        self.assertEqual(sha(self.run_score()),sha(self.run_score()))


if __name__=="__main__":
    unittest.main()
