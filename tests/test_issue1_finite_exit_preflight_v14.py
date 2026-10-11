"""Finite original Phase1 impossible-comparand preflight; no model inference."""
from __future__ import annotations
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_issue1_finite_exit_preflight_v14 import (
    BLOBS, CAPS, NO_PROGRESS, PHASES, TERMINAL_ORIGINAL, pinned, run,
)

REPO=Path(__file__).resolve().parents[1]


class FiniteExitV14Tests(unittest.TestCase):
    def test_original_frozen_protocol_feasibility_proved_once(self):
        result=run(REPO)
        self.assertEqual(result["terminal"],TERMINAL_ORIGINAL)
        self.assertFalse(result["scientific_root_AC_completed"])
        self.assertEqual(result["scientific_root_AC_pass"],2)
        self.assertEqual(result["scientific_root_AC_required"],18)
        self.assertEqual(result["S3"]["witnesses"],["M003","M009"])
        self.assertEqual(result["S4"]["identifiability_bound"],"8/10")
        self.assertTrue(result["S4"]["not_empirical_accuracy"])
        self.assertTrue(result["source_seals_stable"])

    def test_0p5b_already_real_experiment_not_asset_only(self):
        result=run(REPO)
        self.assertEqual(
            result["known_llm_evidence"]["status"],
            "ACTUAL_0P5B_MEASURED_CAPACITY_COLLAPSE")
        self.assertEqual(result["known_llm_evidence"]["accuracy"],"1/10")
        self.assertEqual(
            result["known_llm_evidence"]["per_frozen_protocol_next"],
            "EXACTLY_ONE_1P5B_ASSAY")
        self.assertEqual(
            result["analysis_loop_control"]["once_only_successor_stage_caps"][
                "model_1p5b_capacity_escalation"],1)

    def test_no_unbounded_identical_input_cycle(self):
        a=run(REPO)
        b=run(REPO)
        self.assertEqual(
            a["analysis_loop_control"]["evidence_fingerprint"],
            b["analysis_loop_control"]["evidence_fingerprint"])
        self.assertEqual(
            a["analysis_loop_control"]["same_fingerprint_rerun"],
            NO_PROGRESS)
        self.assertEqual(
            a["analysis_loop_control"]["identical_input_retries_remaining"],0)
        self.assertEqual(a["analysis_loop_control"][
            "once_only_successor_stage_caps"],CAPS)
        self.assertEqual(a["successor_not_original"]["phases"],list(PHASES))

    def test_scientific_root_success_not_fabricated(self):
        x=run(REPO)
        self.assertNotIn("VERIFIED",x["terminal"])
        self.assertTrue(x["successor_not_original"][
            "requires_explicit_versioned_protocol_change"])
        self.assertTrue(x["successor_not_original"][
            "scientific_AC_do_not_increase_on_feasibility_diagnostic"])

    def test_frozen_s4_evidence_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in BLOBS:
                target=Path(temp)/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(REPO/name,target)
            target=Path(temp)/"results/phase1_s4_identifiability_audit_2026-10-03.json"
            target.write_text(target.read_text()+" ")
            with self.assertRaisesRegex(
                ValueError,"G0_FROZEN_EVIDENCE_DRIFT"):
                run(Path(temp))

    def test_0p5b_historical_evidence_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in BLOBS:
                target=Path(temp)/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(REPO/name,target)
            target=Path(temp)/"results/phase1_qwen25_0p5b_reframe_actual_2026-10-03.json"
            packet=json.loads(target.read_text())
            packet["result"]["correct"]=9
            target.write_text(json.dumps(packet))
            with self.assertRaisesRegex(
                ValueError,"G0_FROZEN_EVIDENCE_DRIFT"):
                run(Path(temp))

    def test_plan_must_not_enable_frozen_ec_success_or_expand_mvp(self):
        actual=run(REPO)
        self.assertEqual(actual["original_frozen_native_EC_status"],
                         "INCOMPATIBLE")
        self.assertTrue(actual["successor_not_original"][
            "frozen_EC_can_not_be_renamed_as_successor_native"])
        self.assertEqual(actual["analysis_loop_control"][
            "once_only_successor_stage_caps"]["versioned_protocol_revisions"],1)


if __name__=="__main__":
    unittest.main()
