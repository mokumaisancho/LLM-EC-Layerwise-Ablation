"""Contract-only unit tests. Synthetic LLM0 rows here are NOT experimental evidence."""
from __future__ import annotations
import copy
import unittest
from tools.capability_retention_v1 import (
    PROTOCOL, EvaluationContractError, digest, evaluate,
)

def sample(origin="REUSED_HISTORICAL", include_llm=False):
    cases = [
        {"case_id":"A","input_sha256":"a"*64,"gold_action":"OPEN","capability":"ordinary","critical":True,"tail":False},
        {"case_id":"B","input_sha256":"b"*64,"gold_action":"OPEN","capability":"rare_paraphrase","critical":True,"tail":True},
        {"case_id":"C","input_sha256":"c"*64,"gold_action":"ABSTAIN","capability":"ambiguity","critical":True,"tail":True},
        {"case_id":"D","input_sha256":"d"*64,"gold_action":"ABSTAIN","capability":"negative_intent","critical":True,"tail":False},
    ]
    bench={"protocol":"LLM_EC_CAPABILITY_BENCHMARK_V1","origin":origin,"measurement_only":True,"cases":cases}
    bh=digest(bench)
    predictions={
        "LLM0":["OPEN","OPEN","ABSTAIN","ABSTAIN"],
        "V1":["OPEN","OPEN","OPEN","OPEN"],
        "V4":["OPEN","OPEN","OPEN","OPEN"],
        "V5":["OPEN","ABSTAIN","ABSTAIN","ABSTAIN"],
    }
    armset=("LLM0","V1","V4","V5") if include_llm else ("V1","V5")
    arms={}
    for name in armset:
        rows=[{"case_id":row["case_id"],"input_sha256":row["input_sha256"],
               "decision":predictions[name][i]} for i,row in enumerate(cases)]
        arms[name]={"arm":name,"source_ref":"UNIT_TEST_SYNTHETIC_NEVER_PRODUCTION",
                    "benchmark_sha256":bh,"measurement_only":True,"used_for_update":False,
                    "rows":rows,"rows_sha256":digest(rows)}
    return {"protocol":PROTOCOL,"benchmark":bench,"arms":arms,
            "evaluation_locked":True,"training_feedback_used":False}

class CapabilityRetentionContractTests(unittest.TestCase):
    def rejects(self,bundle,reason,diagnostic=True):
        with self.assertRaisesRegex(EvaluationContractError,reason):
            evaluate(bundle,diagnostic=diagnostic)

    def test_01_aggregate_gain_does_not_hide_tail_loss(self):
        report=evaluate(sample(),diagnostic=True)
        self.assertEqual(report["terminal"],"RETROSPECTIVE_DIAGNOSTIC_ONLY")
        self.assertGreater(report["arm_metrics"]["V5"]["accuracy"],report["arm_metrics"]["V1"]["accuracy"])
        self.assertEqual(report["adjacent_transitions"]["V1_TO_V5"]["correct_to_abstain"],["B"])
        self.assertEqual(report["adjacent_transitions"]["V1_TO_V5"]["critical_losses"],["B"])
        self.assertEqual(report["adjacent_transitions"]["V1_TO_V5"]["tail_losses"],["B"])
        self.assertEqual(report["arm_metrics"]["V5"]["legitimate_false_refusal"],1)
        self.assertEqual(report["arm_metrics"]["V5"]["invalid_false_action"],0)

    def test_02_missing_llm0_fails_closed(self):
        self.rejects(sample(origin="INDEPENDENT_UNSEEN"),"BLOCKED_REFERENCE_LLM0_OUTPUT_MISSING",diagnostic=False)

    def test_03_reused_historical_cannot_claim_full_quality(self):
        self.rejects(sample(include_llm=True),"FULL_COMPARISON_REQUIRES_INDEPENDENT_BENCHMARK",diagnostic=False)

    def test_04_full_independent_synthetic_regression_flag(self):
        report=evaluate(sample(origin="INDEPENDENT_UNSEEN",include_llm=True),diagnostic=False)
        self.assertEqual(report["terminal"],"CAPABILITY_RETENTION_REGRESSION")
        self.assertEqual(report["anchor_transitions"]["V5"]["correct_to_abstain"],["B"])
        self.assertFalse(report["causal_replacement_proven"])

    def test_05_missing_case_rejected(self):
        x=sample()
        rows=x["arms"]["V5"]["rows"]
        rows.pop()
        x["arms"]["V5"]["rows_sha256"]=digest(rows)
        self.rejects(x,"ARM_CASE_COVERAGE_MISMATCH")

    def test_06_output_digest_rejected(self):
        x=sample();x["arms"]["V5"]["rows"][0]["decision"]="CLOSE"
        self.rejects(x,"ARM_OUTPUT_DIGEST_INVALID")

    def test_07_case_input_mismatch_rejected(self):
        x=sample();rows=x["arms"]["V5"]["rows"]
        rows[0]["input_sha256"]="9"*64
        x["arms"]["V5"]["rows_sha256"]=digest(rows)
        self.rejects(x,"ARM_INPUT_HASH_MISMATCH")

    def test_08_duplicate_case_rejected(self):
        x=sample();x["benchmark"]["cases"][1]["case_id"]="A"
        self.rejects(x,"DUPLICATE_OR_INVALID_CASE_ID")

    def test_09_benchmark_tamper_rejected(self):
        x=sample();x["benchmark"]["cases"][0]["gold_action"]="CLOSE"
        self.rejects(x,"ARM_BENCHMARK_HASH_MISMATCH")

    def test_10_evaluation_used_as_feedback_rejected(self):
        x=sample();x["training_feedback_used"]=True
        self.rejects(x,"EVALUATION_INFORMATION_FLOW_INVALID")

    def test_11_arm_used_for_update_rejected(self):
        x=sample();x["arms"]["V1"]["used_for_update"]=True
        self.rejects(x,"ARM_INFORMATION_FLOW_INVALID")

    def test_12_extra_arm_rejected(self):
        x=sample();x["arms"]["V4"]=copy.deepcopy(x["arms"]["V1"])
        self.rejects(x,"ARM_SET_INCOMPLETE_OR_UNEXPECTED")

    def test_13_invalid_action_rejected(self):
        x=sample();rows=x["arms"]["V5"]["rows"];rows[0]["decision"]="UNSURE"
        x["arms"]["V5"]["rows_sha256"]=digest(rows)
        self.rejects(x,"ARM_DECISION_INVALID")

    def test_14_output_repeatability(self):
        one=evaluate(sample(),diagnostic=True)
        two=evaluate(sample(),diagnostic=True)
        self.assertEqual(digest(one),digest(two))

    def test_15_rare_case_preservation_only_when_no_lost_tail(self):
        x=sample()
        rows=x["arms"]["V5"]["rows"]
        rows[1]["decision"]="OPEN"
        x["arms"]["V5"]["rows_sha256"]=digest(rows)
        report=evaluate(x,diagnostic=True)
        self.assertFalse(report["any_tail_capability_regression"])
        self.assertFalse(report["any_critical_capability_regression"])

    def test_16_reference_metadata_required(self):
        x=sample();x["arms"]["V1"]["source_ref"]=""
        self.rejects(x,"ARM_IDENTITY_OR_PROVENANCE_INVALID")

if __name__=="__main__":
    unittest.main()
