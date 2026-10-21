import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "issue1_s3_native_formal_handoff_audit.py"
S = importlib.util.spec_from_file_location("handoff_audit", TOOL)
M = importlib.util.module_from_spec(S)
S.loader.exec_module(M)

class SourceHandoffTests(unittest.TestCase):
    def test_all_actual_real_source_inputs_abstain(self):
        d = M.audit_all(ROOT)
        self.assertEqual(d["real_source_input_cases"], 10)
        self.assertEqual(d["native_formal_handoff_qualified"], 0)
        self.assertEqual(d["cases_rejected_without_label_leakage"], 10)
        self.assertTrue(all(len(x["causes"]) == 5 for x in d["cases"]))

    def test_source_facts_structurally_normalized_25_of_25(self):
        result=M.audit_all(ROOT)
        self.assertEqual(result["source_positive_atomic_literals_structurally_normalized"],25)
        self.assertEqual(result["fact_structural_conversion_possible_cases"],10)
        self.assertEqual(result["native_formal_handoff_qualified"],0)
        self.assertTrue(all(x["EC_formal_fact_object_candidate"]["schema"]=="EC_FORMAL_FACTS_V2" for x in result["cases"]))

    def test_nonlinear_source_text_must_not_be_guessed(self):
        with self.assertRaisesRegex(ValueError,"FREE_TEXT_REQUIRES_SEMANTIC_INTERPRETATION"):
            M.normalize_observed_literal_facts(["the payment failed due to missing authorization"])

    def test_fact_conflict_must_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"CONFLICTING_OBSERVED_SOURCE_VALUES"):
            M.normalize_observed_literal_facts(["coverage=verified","coverage=invalid"])

    def test_unknown_does_not_become_false(self):
        facts=M.normalize_observed_literal_facts(["coverage=verified"])
        self.assertEqual(facts,{"coverage=verified":True})
        self.assertNotIn("coverage=invalid",facts)

    def copied_fixture(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "replay/M003").mkdir(parents=True)
        (root / "generated/M003/input").mkdir(parents=True)
        for source, destination in [
            (ROOT / "replay/M003/s3_predictor_visible_v42.json", root / "replay/M003/s3_predictor_visible_v42.json"),
            (ROOT / "generated/M003/input/task.json", root / "generated/M003/input/task.json"),
            (ROOT / "generated/M003/fixture_manifest.json", root / "generated/M003/fixture_manifest.json"),
        ]:
            destination.write_bytes(source.read_bytes())
        return td, root

    def test_semantic_operation_oracle_leak_rejected(self):
        td, root = self.copied_fixture()
        with td:
            f = root / "replay/M003/s3_predictor_visible_v42.json"
            obj = json.loads(f.read_text())
            obj["oracle_constraints"] = {"acceptable_candidate_ids": ["v1"]}
            f.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, "PRIVATE_GOLD"):
                M.audit_one(root, "M003")

    def test_candidate_id_reuse_rejected(self):
        td, root = self.copied_fixture()
        with td:
            f = root / "replay/M003/s3_predictor_visible_v42.json"
            obj = json.loads(f.read_text())
            obj["candidates"][1]["candidate_id"] = obj["candidates"][0]["candidate_id"]
            f.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, "DUPLICATE"):
                M.audit_one(root, "M003")

    def test_claimed_formal_rules_are_not_derived(self):
        td, root = self.copied_fixture()
        with td:
            f = root / "replay/M003/s3_predictor_visible_v42.json"
            obj = json.loads(f.read_text())
            obj["task"]["domain_rules"] = {"BYPASS_CONTROL": ["fact:foo"]}
            f.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, "CUSTODY"):
                M.audit_one(root, "M003")

    def test_cross_case_binding_rejected(self):
        td, root = self.copied_fixture()
        with td:
            f = root / "generated/M003/input/task.json"
            obj = json.loads(f.read_text())
            obj["fixture_id"] = "M009"
            f.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, "CROSS_FIXTURE"):
                M.audit_one(root, "M003")

    def test_corrupted_schema_rejected(self):
        td, root = self.copied_fixture()
        with td:
            f = root / "replay/M003/s3_predictor_visible_v42.json"
            obj = json.loads(f.read_text())
            obj["schema"] = "NOT_P01"
            f.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, "PREDICTOR_SCHEMA"):
                M.audit_one(root, "M003")

    def test_no_silent_fixture_dropping(self):
        td, root = self.copied_fixture()
        with td:
            with self.assertRaisesRegex(ValueError, "REJECT_FIXTURE_SET_CHANGED"):
                M.audit_all(root)

if __name__ == "__main__":
    unittest.main()
