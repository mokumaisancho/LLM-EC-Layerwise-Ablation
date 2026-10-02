from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "run_llm_s3_s4_cache.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_llm_s3_s4_cache_tested", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("runner import failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class LLMOutputContractTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_runner()
        self.ids = {"v1", "x1"}

    def valid(self):
        return {
            "selected_candidate_ids": ["v1"],
            "rejected_candidate_ids": ["x1"],
            "reframe_required": False,
            "closure_class": "CLOSE",
            "decision_reasons": ["evidence"],
        }

    def test_valid_partition_passes(self):
        ok, err = self.mod.validate_output_contract(self.valid(), self.ids)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_unknown_candidate_fails(self):
        doc = self.valid()
        doc["selected_candidate_ids"] = ["invented"]
        ok, err = self.mod.validate_output_contract(doc, self.ids)
        self.assertFalse(ok)
        self.assertEqual(err, "UNKNOWN_CANDIDATE_ID")

    def test_incomplete_partition_fails(self):
        doc = self.valid()
        doc["rejected_candidate_ids"] = []
        ok, err = self.mod.validate_output_contract(doc, self.ids)
        self.assertFalse(ok)
        self.assertEqual(err, "CANDIDATE_PARTITION_INCOMPLETE")

    def test_schema_constrained_marker_exists(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("format_contract_ok", text)
        self.assertIn("schema_constrained", text)
        self.assertIn("response_format", text)
        self.assertIn("semantic_metrics_eligible", text)


if __name__ == "__main__":
    unittest.main()
