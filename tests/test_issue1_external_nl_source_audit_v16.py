"""Official external natural-language benchmark provenance and scoped-score tests."""
import json
import unittest
from tools.run_issue1_external_nl_source_audit_v16 import (
    SOURCES, fetch, git_blob, checked_source, public_inputs_from_gold, audit,
)

class OfficialNLSourceAuditV16(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw={name:fetch(name) for name in SOURCES}
    @classmethod
    def get_source(cls,name):
        return cls.raw[name]
    def test_real_official_source_and_scoped_metrics(self):
        result=audit(self.get_source)
        self.assertEqual(result["third_party_natural_language_question_count"],10)
        self.assertEqual(result["published_gold_decomposition_steps"],34)
        self.assertEqual(result["published_example_prediction_steps"],20)
        self.assertEqual(result["published_example_answer_correct"],8)
        self.assertEqual(result["published_example_exact_decomposition_count"],0)
        self.assertFalse(result["original_root_scientific_AC_pass_raised"])
        self.assertFalse(result["true_S3_candidatewise_natural_language_admissibility_evaluated"])
        self.assertFalse(result["true_S4_exhaustive_real_world_obligations_evaluated"])
    def test_real_source_blobs(self):
        for name,sha in SOURCES.items():
            self.assertEqual(git_blob(self.raw[name]),sha)
    def test_gold_and_decompositions_excluded_from_predictor(self):
        public=public_inputs_from_gold(checked_source("gold_small.json",self.get_source))
        self.assertEqual(len(public),10)
        for row in public:
            self.assertEqual(set(row),{"qid","question"})
    def test_mutated_gold_rejected_even_if_json_valid(self):
        def altered(name):
            if name=="gold_small.json":
                data=json.loads(self.raw[name])
                data[0]["answer"]=not data[0]["answer"]
                return json.dumps(data).encode()
            return self.raw[name]
        with self.assertRaisesRegex(ValueError,"D04_EXTERNAL_SOURCE_GIT_BLOB_DRIFT"):
            audit(altered)
    def test_mutated_published_predictions_rejected(self):
        def altered(name):
            return self.raw[name]+b" " if name=="predictions_small.json" else self.raw[name]
        with self.assertRaisesRegex(ValueError,"D04_EXTERNAL_SOURCE_GIT_BLOB_DRIFT"):
            audit(altered)
    def test_forbid_unregistered_upstream_file(self):
        with self.assertRaisesRegex(ValueError,"D04_UPSTREAM_PATH_NOT_ALLOWED"):
            checked_source("../../otherfile",self.get_source)

if __name__=="__main__":unittest.main()
