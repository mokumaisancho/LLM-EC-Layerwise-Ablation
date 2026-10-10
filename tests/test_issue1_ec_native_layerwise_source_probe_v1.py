from __future__ import annotations
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_issue1_ec_native_layerwise_source_probe_v1 import (
    ROOT, PROTOCOL, EC_COMMIT, EC_MODULE_BLOB, MODULE, CASES,
    pin,load,prepare,predict_only,run,
)
NATIVE=Path("/private/tmp/issue1-ec-w4a-frozen-20261010")

@unittest.skipUnless(NATIVE.is_dir(),"Pinned new EC-native source checkout unavailable")
class OriginalIssueW4NativeExperimentalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0,str(ROOT/"tools"))
        from generate_phase1_measurement_v2_canonical import SPECS,rebuild
        cls.frozen={s["id"]:rebuild(s) for s in SPECS if s["id"] in CASES}
        cls.engine=load(NATIVE)

    def test_01_pin_actual_upstream_ec_source_and_tests(self):
        pin(NATIVE)
        self.assertEqual(EC_COMMIT,"24fe3a665b21ad90a79095eb8d5818dda5447d62")
        self.assertEqual(len(EC_MODULE_BLOB),40)

    def test_02_public_payload_has_no_oracle_labels_or_fixture_id(self):
        for key,record in self.frozen.items():
            task,_s1,s2,_s3,_s4,hidden,_manifest=record
            obj=prepare(task,s2,EC_COMMIT)
            public=json.dumps(obj,ensure_ascii=False)
            for forbidden in ('"oracle_constraints"','"fixture_id"','"gold"','"acceptable_candidate_ids"'):
                self.assertNotIn(forbidden,public)
            self.assertNotIn('"hidden"',public)

    def test_03_all_admissible_are_selected_for_competing_and_equivalent(self):
        for label in ("M003","M009"):
            task,_s1,s2,*_=self.frozen[label]
            d=prepare(task,s2,EC_COMMIT)
            selected=self.engine.select_admissible_set(
                d["public_s2"],adjudications=d["adjudications"],
                semantic_authority=d["semantic_authority"])
            self.assertEqual(len(selected["selection"]["selected_candidate_ids"]),2)
            self.assertFalse(selected["semantic_truth_independently_verified"])

    def test_04_s4_public_competing_equivalent_and_pending_casewise(self):
        rows={row["case_id"]:row for row in run(NATIVE)["rows"]}
        self.assertEqual(rows["M003"]["closure_class"],"CONTINUE")
        self.assertEqual(rows["M009"]["closure_class"],"CLOSE")
        self.assertEqual(rows["M007"]["closure_class"],"CONTINUE")
        self.assertEqual(rows["M008"]["closure_class"],"CLOSE")

    def test_05_native_engine_unsupported_condition_inventory_fails_closed(self):
        task,_s1,s2,*_=self.frozen["M008"]
        d=prepare(task,s2,EC_COMMIT)
        selected=self.engine.select_admissible_set(
            d["public_s2"],adjudications=d["adjudications"],
            semantic_authority=d["semantic_authority"])
        with self.assertRaisesRegex(self.engine.ECAdmissibilityError,
                                    "S4_COMPLETE_CONDITION_INVENTORY_ATTESTATION_REQUIRED"):
            self.engine.evaluate_closure(selected,required_conditions={},
                framing=d["framing"],public_s2_sha256=selected["source_s2_sha256"])

    def test_06_forged_candidate_oracle_field_must_reject(self):
        task,_s1,s2,*_=self.frozen["M003"]
        d=prepare(task,s2,EC_COMMIT)
        d["public_s2"]["oracle_constraints"]={"acceptable_candidate_ids":["v1"]}
        with self.assertRaisesRegex(self.engine.ECAdmissibilityError,
                                    "ORACLE_OR_EVALUATION_FIELD_FORBIDDEN"):
            self.engine.select_admissible_set(d["public_s2"],
                adjudications=d["adjudications"],semantic_authority=d["semantic_authority"])

    def test_07_lost_adjudication_must_fail_not_guess(self):
        task,_s1,s2,*_=self.frozen["M003"]
        d=prepare(task,s2,EC_COMMIT)
        d["adjudications"].pop("v2")
        with self.assertRaisesRegex(self.engine.ECAdmissibilityError,
                                    "PER_CANDIDATE_ADJUDICATION_REQUIRED"):
            self.engine.select_admissible_set(d["public_s2"],
                adjudications=d["adjudications"],semantic_authority=d["semantic_authority"])

    def test_08_changed_source_blob_pin_prevents_inference(self):
        with patch("tools.run_issue1_ec_native_layerwise_source_probe_v1.git_blob",
                   return_value="0"*40):
            with self.assertRaisesRegex(ValueError,"SOURCE_EC_NATIVE_EXTENSION_BLOB_MISMATCH"):
                pin(NATIVE)

    def test_09_changed_upstream_hash_prevents_inference(self):
        task,_s1,s2,*_=self.frozen["M003"]
        d=prepare(task,s2,EC_COMMIT)
        d["semantic_authority"]["upstream_sha256"]="0"*64
        with self.assertRaisesRegex(self.engine.ECAdmissibilityError,
                                    "SEMANTIC_AUTHORITY_UPSTREAM_NOT_BOUND"):
            self.engine.select_admissible_set(d["public_s2"],
                adjudications=d["adjudications"],semantic_authority=d["semantic_authority"])

    def test_10_predictor_process_never_accepts_gold_envelope(self):
        task,_s1,s2,*_=self.frozen["M003"]
        d=prepare(task,s2,EC_COMMIT)
        d["oracle"]="CLOSE"
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bad.json";path.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,"UNEXPECTED_PRIVILEGED_PREDICTOR_ENVELOPE"):
                predict_only(NATIVE,path)

    def test_11_actual_native_process_runs_but_does_not_certify_semantics(self):
        result=run(NATIVE)
        self.assertEqual(result["four_author_exposed_fixtures"],4)
        self.assertEqual(result["native_negative_tests_passed"],14)
        self.assertEqual(result["casewise_S3_development_matches"],4)
        self.assertEqual(result["casewise_S4_development_matches"],4)
        self.assertFalse(result["external_semantic_adjudicator_certified"])
        self.assertFalse(result["external_complete_inventory_certified"])
        self.assertFalse(result["original_four_layer_AE_completed"])
        self.assertFalse(result["original_frozen_ec_v44_adapter_qualified"])
        self.assertFalse(result["independent_unseen_gold"])

    def test_12_nonexistent_frozen_source_checkout_must_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises((ValueError,FileNotFoundError)):
                pin(Path(tmp))

if __name__=="__main__":unittest.main()
