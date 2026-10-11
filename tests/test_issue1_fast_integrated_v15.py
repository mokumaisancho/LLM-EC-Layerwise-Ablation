"""Adversarial source-bound original Phase1 finite one-call v15."""
from __future__ import annotations
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_issue1_fast_integrated_v15 import (
    ROOT, BLOBS, ONEP5, EC_COMMIT, run, git_pinned_source, PATHS
)

class Issue1IntegratedV15Tests(unittest.TestCase):
    def test_real_existing_1p5b_reused(self):
        actual=run(ROOT)
        r=actual["stage_evidence"][PATHS[2]]
        self.assertEqual(r["0p5b_correct"],"1/10")
        self.assertEqual(r["1p5b_correct"],"9/10")
        self.assertEqual(r["absolute_improvement"],0.8)
        self.assertFalse(r["1p5b_capacity_collapse"])
        self.assertEqual(r["1p5b_llm_S3_reframe_accuracy_diagnostic"],0.9)
        self.assertFalse(r["run_again"])
        self.assertTrue(r["not_full_S3_selection_or_S4_causal_study"])

    def test_original_frozen_scope_infeasible_no_false_closure(self):
        actual=run(ROOT)
        self.assertEqual(actual["original_ac_pass"],2)
        self.assertEqual(actual["original_mvp_AC"],18)
        self.assertEqual(actual["original_protocol_terminal"],
                         "ROOT_FROZEN_PROTOCOL_INFEASIBLE")
        self.assertEqual(actual["separate_versioned_successor_terminal"],
                         "SUCCESSOR_EXTERNAL_AUTHORITY_NOT_EVALUABLE")
        self.assertFalse(actual["original_science_complete"])
        self.assertEqual(len(actual["onecall_stages"]),5)
        self.assertTrue(actual["all_source_hashes_preserved"])
        self.assertEqual(actual["errors"],[])

    def test_source_pin_no_local_tamper(self):
        with patch("tools.run_issue1_fast_integrated_v15.blob",
                   return_value="0"*40):
            with self.assertRaisesRegex(ValueError,
                "G0_VERSIONED_SOURCE_UNTRACKED_OR_EDITED"):
                git_pinned_source(ROOT,"tools/run_issue1_fast_integrated_v15.py")

    def test_prior_1p5b_result_modified_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in [*BLOBS,ONEP5]:
                p=root/name
                p.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/name,p)
            target=root/ONEP5
            d=json.loads(target.read_text())
            d["result"]["correct"]=10
            target.write_text(json.dumps(d))
            from tools.run_issue1_fast_integrated_v15 import load_1p5
            with self.assertRaisesRegex(ValueError,
                "G0_HISTORICAL_1P5B_SOURCE_CHANGED"):
                load_1p5(root)

    def test_untrusted_document_never_self_certifies_gold(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"self_attested.json"
            p.write_text('{"independent_source_custody":true}')
            result=run(ROOT,independent_provenance=p)
            authority=result["stage_evidence"][PATHS[1]]
            self.assertEqual(authority["status"],
                             "UNVERIFIED_DOCUMENT_PRESENT_EXTERNAL_CUSTODY_REQUIRED")
            self.assertFalse(authority["S3_independent_source_custody"])
            self.assertFalse(authority["model_gold_separation_authenticated"])
            self.assertFalse(result["original_science_complete"])

    def test_incorrect_native_source_commit_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc=__import__("subprocess").run(
                ["git","init","-q",tmp],capture_output=True,text=True,check=True)
            with self.assertRaisesRegex(
                    ValueError, "G0_SUCCESSOR_NATIVE_SOURCE_COMMIT_MISMATCH"):
                run(ROOT,ec_root=Path(tmp))

    def test_existing_model_asset_cannot_be_unreported_capacity_failure(self):
        result=run(ROOT)
        cap=result["stage_evidence"][PATHS[2]]
        self.assertEqual(cap["1p5b_correct"],"9/10")
        self.assertFalse(cap["further_4b_escalation"])
        self.assertEqual(result["stage_evidence"][PATHS[3]]["status"],
                         "NOT_EXECUTED_UNQUALIFIED_INPUTS")
        self.assertIsNone(result["stage_evidence"][PATHS[4]]["dominant_layer"])


if __name__=="__main__":unittest.main()
