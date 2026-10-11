"""TCC v11 original AC nonpromotion and Issue #61 replay fail-closed tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from tools.run_issue1_original_phase1_tcc_v11 import manifest, run
from tests.test_issue1_phase1_ae_gate_v2 import (
    make_fixture, repair_self_reported_hashes,
)

TCC = Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC = Path("/private/tmp/issue1-ec-native-layerwise-20261010")


class OriginalPhase1TCCV11Test(unittest.TestCase):
    def test_v11_tcc_adds_replay_gate_without_widening_root(self):
        s = manifest()
        self.assertEqual(s["tcc_id"],
                         "ISSUE1-ORIGINAL-S1-S4-AC18-V11-ISSUE61")
        self.assertEqual(
            [n["id"] for n in s["nodes"]
             if n["kind"] == "terminal"
             and n["terminal_status"] == "SUCCESS"],
            ["root_science_verified"])
        self.assertEqual(s["entry_nodes"], ["pin_additional_sources"])
        self.assertEqual(len(s["nodes"]), 9)

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(), "Pinned checkouts absent")
    def test_real_compiled_v11_reports_native_blocker_not_false_mvp(self):
        result = run(TCC, EC)
        self.assertEqual(result["TCC_nodes"], 9)
        self.assertEqual(result["TCC_edges"], 12)
        self.assertEqual(result["TCC_terminal"], "blocked_native")
        self.assertEqual(result["original_TCC_v10_terminal"], "blocked_native")
        self.assertEqual(result["original_root_pass"], 2)
        self.assertEqual(result["original_root_required"], 18)
        self.assertEqual(result["replay_v2_negative_test_count"], 17)
        self.assertTrue(result["source_seals_stable"])
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["original_science_complete"])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(), "Pinned checkouts absent")
    def test_incomplete_trusted_trace_fails_closed(self):
        raw, _, _, _ = make_fixture()
        with self.assertRaisesRegex(
            ValueError, "G8_INCOMPLETE_EXTERNAL_REPLAY_AUTHORITY"):
            run(TCC, EC, raw_v2=raw)

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(), "Pinned checkouts absent")
    def test_toy_trace_replayed_but_no_original_science_promotion(self):
        raw, gold, public, trusted = make_fixture()
        result = run(TCC, EC, raw, gold, public, trusted)
        self.assertEqual(result["TCC_terminal"], "blocked_native")
        self.assertEqual(result["replay_v2_stages"], 32)
        self.assertEqual(
            result["replay_v2_real_evidence"],
            "STRUCTURAL_RERUN_ONLY_NOT_INDEPENDENT_SCIENCE")
        self.assertFalse(result["original_science_complete"])
        self.assertEqual(result["original_root_pass"], 2)
        self.assertEqual(result["errors"], [])

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(), "Pinned checkouts absent")
    def test_forged_nontarget_e_intervention_is_integrity_blocker(self):
        raw, gold, public, trusted = make_fixture()
        row = raw["cases"][0]
        arm = row["arms"][4]  # E_S1
        arm["layers"]["S2"] = {"additional_oracle_override": True}
        repair_self_reported_hashes(row, arm)
        result = run(TCC, EC, raw, gold, public, trusted)
        self.assertEqual(result["TCC_terminal"], "blocked_integrity")
        self.assertEqual(result["original_root_pass"], 2)
        self.assertTrue(any(
            "G8_STAGE_OUTPUT_REPLAY_MISMATCH" in e
            for e in result["errors"]))
        self.assertFalse(result["original_science_complete"])


if __name__ == "__main__":
    unittest.main()
