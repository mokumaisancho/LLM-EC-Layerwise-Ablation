"""Negative controls for source-isolated public S3 and finite question S4."""
import copy
import unittest
from tools.run_issue1_multirc_published_s3_s4_v17 import (
    git_blob, source_rows, literal_public_only_predict,
    s4_formal_completion, score,
)

class BoundedMultiRCS3S4Tests(unittest.TestCase):
    def setUp(self):
        self.case={
            "question_id":"0/0",
            "passage":"The apples are sweet; the pears are sweet.",
            "question":"Which fruits are sweet?",
            "options":[
                {"candidate_id":"0/0/0","text":"apples"},
                {"candidate_id":"0/0/1","text":"pears"},
                {"candidate_id":"0/0/2","text":"oranges"},
            ],
        }
        self.gold={"question_id":"0/0","labels":{
            "0/0/0":True,"0/0/1":True,"0/0/2":False}}
    def test_two_correct_candidates_source_blind(self):
        p=literal_public_only_predict(self.case)
        self.assertEqual(
            [x["candidate_id"] for x in p["decisions"] if x["select"]],
            ["0/0/0","0/0/1"])
        self.assertNotIn("isAnswer",str(self.case))
        result=score([self.case],[self.gold],[p])
        self.assertEqual(result["question_exact_selected_set_matches"],1)
        self.assertEqual(result["questions_with_multiple_correct_candidates"],1)
        self.assertEqual(result["candidate_micro_F1"],1)
    def test_formal_closure_checks_completeness_not_answer_correctness(self):
        wrong=literal_public_only_predict(self.case)
        wrong["decisions"][0]["select"]=False
        self.assertTrue(s4_formal_completion(self.case,wrong)[
            "formal_question_submission_allowed"])
        self.assertFalse(s4_formal_completion(self.case,wrong)[
            "real_world_task_closure_authorized"])
        self.assertEqual(score([self.case],[self.gold],[wrong])[
            "question_exact_selected_set_matches"],0)
    def test_s4_missing_choice_fails_closed(self):
        pred=literal_public_only_predict(self.case)
        pred["decisions"].pop()
        with self.assertRaisesRegex(ValueError,
             "D05_INCOMPLETE_DUPLICATE_OR_FORGED_DECISION"):
            s4_formal_completion(self.case,pred)
    def test_s4_duplicate_choice_fails_closed(self):
        pred=literal_public_only_predict(self.case)
        pred["decisions"][-1]=copy.deepcopy(pred["decisions"][0])
        with self.assertRaisesRegex(ValueError,
             "D05_INCOMPLETE_DUPLICATE_OR_FORGED_DECISION"):
            s4_formal_completion(self.case,pred)
    def test_s4_cross_case_replay_fails_closed(self):
        pred=literal_public_only_predict(self.case)
        pred["question_id"]="other-question"
        with self.assertRaisesRegex(ValueError,"D05_UPSTREAM_ID_DRIFT"):
            s4_formal_completion(self.case,pred)
    def test_s3_hidden_gold_field_rejected(self):
        malicious=copy.deepcopy(self.case)
        malicious["gold"]={"0/0/0":True}
        with self.assertRaisesRegex(ValueError,
             "D04_MODEL_PUBLIC_ONLY_INTERFACE"):
            literal_public_only_predict(malicious)
    def test_invalid_source_blob_fails_closed(self):
        with self.assertRaisesRegex(ValueError,
             "D04_OFFICIAL_DERIVED_COPY_BLOB_DRIFT"):
            source_rows(b'{"data":[]}')
    def test_s4_nonboolean_forged_decision_rejected(self):
        pred=literal_public_only_predict(self.case)
        pred["decisions"][0]["select"]=1
        with self.assertRaisesRegex(ValueError,
             "D05_INCOMPLETE_DUPLICATE_OR_FORGED_DECISION"):
            s4_formal_completion(self.case,pred)

if __name__=="__main__":unittest.main()
