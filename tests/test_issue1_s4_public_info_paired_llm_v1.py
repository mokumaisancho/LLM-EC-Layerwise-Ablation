from __future__ import annotations

import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from tools.run_issue1_s4_public_info_paired_llm_v1 import (
    CONTRACT, FIELDS, PROTOCOL, ROOT, GRAMMAR, INSTRUCTIONS, arm_projection,
    blob_sha, read_contract, strict_public, predict_only,
)
from tools.run_issue1_s4_interface_information_diagnostic_v1 import public_projection


class S4ActualPairedQwenInformationControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0,str(ROOT/"tools"))
        from tools.generate_phase1_measurement_v2_canonical import SPECS,rebuild
        cls.cases=[rebuild(x) for x in SPECS]
        cls.contract=json.loads(CONTRACT.read_text())

    def test_01_preregistered_contract_is_not_rewritten_after_outputs(self):
        self.assertEqual(self.contract["protocol"],PROTOCOL)
        self.assertEqual(self.contract["status"],"FROZEN_BEFORE_MODEL_RUN")
        self.assertEqual(len(self.contract["dataset"]["cases"]),10)
        self.assertTrue(self.contract["not_oracle_substitution"])
        self.assertTrue(self.contract["not_independent_heldout"])

    def test_02_hidden_answers_and_case_ids_never_in_predictor_payload(self):
        denied=self.contract["comparison"]["deny_gold_fields"]
        for task,_,s2,s3,_,hidden,_ in self.cases:
            public=public_projection(task,s2,s3)
            for arm in ("STRUCTURAL","ENRICHED"):
                x=arm_projection(public,arm)
                for field in denied:
                    self.assertNotIn(field,x)
                self.assertNotIn(hidden["fixture_id"],json.dumps(x))
                self.assertNotIn("oracle_constraints",json.dumps(x))

    def test_03_only_two_treatment_fields_differ(self):
        for task,_,s2,s3,_,hidden,_ in self.cases:
            public=public_projection(task,s2,s3)
            base=arm_projection(public,"STRUCTURAL")
            enriched=arm_projection(public,"ENRICHED")
            self.assertEqual(set(enriched)-set(base),
                             {"relation_groups","required_condition_state"})
            for key in base:self.assertEqual(base[key],enriched[key])

    def test_04_bad_gold_injection_rejected_in_child(self):
        task,_,s2,s3,_,_,_=self.cases[0]
        injected=arm_projection(public_projection(task,s2,s3),"ENRICHED")
        injected["reference_label"]="CLOSE"
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"in.json"
            p.write_text(json.dumps({"arm":"ENRICHED","public":injected}))
            with self.assertRaisesRegex(ValueError,"UNSAFE_OR_INCOMPLETE_PREDICTOR_INPUT"):
                predict_only(Path("/dev/null"),Path("/dev/null"),p,1)

    def test_05_structural_cannot_receive_enrichment_secretly(self):
        task,_,s2,s3,_,_,_=self.cases[0]
        public=public_projection(task,s2,s3)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"in.json"
            p.write_text(json.dumps({"arm":"STRUCTURAL","public":public}))
            with self.assertRaisesRegex(ValueError,"STRUCTURAL_ALLOWLIST_REQUIRED"):
                predict_only(Path("/dev/null"),Path("/dev/null"),p,1)

    def test_06_cli_prompt_contains_no_oracle_fields(self):
        task,_,s2,s3,_,_,_=self.cases[0]
        public=arm_projection(public_projection(task,s2,s3),"ENRICHED")
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"in.json"
            p.write_text(json.dumps({"arm":"ENRICHED","public":public}))
            fake=SimpleNamespace(returncode=0,stdout="\n\n> prompt\n\nCLOSE\n\n[ Prompt: 12 t/s | Generation: 10 t/s ]",
                                 stderr="")
            with patch("tools.run_issue1_s4_public_info_paired_llm_v1.subprocess.run",return_value=fake) as mock:
                result=predict_only(Path("/dev/null"),Path("/dev/null"),p,1)
            self.assertEqual(result["parsed_prediction"],"CLOSE")
            command=mock.call_args.args[0]
            prompt=command[command.index("-p")+1]
            self.assertNotIn("fixture_id",prompt)
            self.assertNotIn("oracle_constraints",prompt)
            self.assertNotIn("gold",prompt.lower())
            self.assertEqual(command[command.index("--grammar")+1],GRAMMAR)

    def test_07_model_error_is_not_silently_mapped_to_label(self):
        task,_,s2,s3,_,_,_=self.cases[0]
        public=arm_projection(public_projection(task,s2,s3),"STRUCTURAL")
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"in.json"
            p.write_text(json.dumps({"arm":"STRUCTURAL","public":public}))
            with patch("tools.run_issue1_s4_public_info_paired_llm_v1.subprocess.run",
                       return_value=SimpleNamespace(returncode=1,stderr="bad",stdout="")):
                with self.assertRaisesRegex(RuntimeError,"LLAMA_PROCESS_ERROR"):
                    predict_only(Path("/dev/null"),Path("/dev/null"),p,1)

    def test_08_invalid_relation_type_fails(self):
        task,_,s2,s3,_,_,_=self.cases[2]
        public=arm_projection(public_projection(task,s2,s3),"ENRICHED")
        public["relation_groups"][0]["relation_type"]="ORACLE_CORRECT"
        with self.assertRaisesRegex(ValueError,"INVALID_RELATION_TYPE"):
            strict_public(public)

    def test_09_missing_public_field_fails_closed(self):
        task,_,s2,s3,_,_,_=self.cases[0]
        public=arm_projection(public_projection(task,s2,s3),"ENRICHED")
        del public["selected_count"]
        with self.assertRaisesRegex(ValueError,"UNSAFE_OR_INCOMPLETE_PREDICTOR_INPUT"):
            strict_public(public)

    def test_10_predictor_must_not_import_hidden_gold_scoring(self):
        tree=ast.parse((ROOT/"tools/run_issue1_s4_public_info_paired_llm_v1.py").read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="predict_only")
        source=ast.unparse(fn)
        for forbidden in ("[\"oracle\"]","[\"hidden\"]","rebuild(","SPECS"):
            self.assertNotIn(forbidden,source)

    def test_11_every_structural_signature_collision_is_retained(self):
        from tools.run_issue1_s4_interface_information_diagnostic_v1 import baseline_signature
        signatures={}
        for task,_,s2,s3,_,hidden,_ in self.cases:
            signatures.setdefault(baseline_signature(public_projection(task,s2,s3)),[]).append(hidden["fixture_id"])
        self.assertIn(["M003","M009"],list(signatures.values()))
        self.assertTrue(any("M007" in group and "M001" in group for group in signatures.values()))

    def test_12_no_implicit_claim_of_ec_native_or_independent_quality(self):
        self.assertFalse(self.contract["not_original_frozen_phase1"] is False)
        self.assertFalse(self.contract["not_independent_heldout"] is False)
        self.assertFalse(self.contract["not_oracle_substitution"] is False)


if __name__=="__main__":
    unittest.main()
