"""Original Issue #1 W4B/W4C formal-source TCC v12 regression."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_issue1_original_phase1_tcc_v12 import (
    NATIVE_COMMIT, NATIVE_PIN, manifest, run, source_pins,
)

TCC = Path("/private/tmp/llmec-tcc-generator-reference-20261009")
NATIVE_V11 = Path("/private/tmp/issue1-ec-native-layerwise-20261010")
POLICY_V2 = Path("/private/tmp/issue59-60-policy-v2")


class OriginalSourcePolicyTCCV12(unittest.TestCase):
    def test_graph_preserves_original_narrow_source_and_failure_exit(self):
        manifest_ = manifest()
        self.assertEqual(manifest_["entry_nodes"], ["freeze_new_tcc_v12"])
        self.assertEqual(len(manifest_["nodes"]), 10)
        self.assertEqual(
            [n["id"] for n in manifest_["nodes"]
             if n["kind"] == "terminal"
             and n["terminal_status"] == "SUCCESS"],
            ["root_science_verified"])

    @unittest.skipUnless(TCC.is_dir() and NATIVE_V11.is_dir()
                         and POLICY_V2.is_dir(), "Pinned checkouts absent")
    def test_real_v12_policy_source_test_and_original_root_blocker(self):
        x = run(TCC, NATIVE_V11, POLICY_V2)
        self.assertEqual(x["TCC_terminal"], "blocked_external_semantics")
        self.assertEqual(x["original_root_pass"], 2)
        self.assertEqual(x["original_root_required"], 18)
        self.assertEqual(x["new_native_policy_tests"], 46)
        self.assertEqual(x["new_formal_disjoint_cases"], 24)
        self.assertEqual(x["prior_original_v11"]["replay_adversarial_tests"], 17)
        self.assertTrue(x["source_seals_stable"])
        self.assertEqual(x["errors"], [])
        self.assertFalse(x["independent_natural_semantics_proven"])
        self.assertFalse(x["independently_complete_real_world_obligations"])
        self.assertFalse(x["real_matched_AE_validated"])
        self.assertFalse(x["original_science_complete"])

    @unittest.skipUnless(POLICY_V2.is_dir(), "Pinned policy source absent")
    def test_wrong_native_commit_rejected(self):
        with self.assertRaisesRegex(ValueError, "G0_SOURCE_COMMIT_MISMATCH"):
            source_pins(POLICY_V2, NATIVE_PIN, "0" * 40)

    @unittest.skipUnless(POLICY_V2.is_dir(), "Pinned policy source absent")
    def test_false_source_blob_rejected(self):
        with self.assertRaisesRegex(ValueError, "G0_SOURCE_BLOB_MISMATCH"):
            source_pins(POLICY_V2, {next(iter(NATIVE_PIN)): "0" * 40},
                        NATIVE_COMMIT)

    @unittest.skipUnless(POLICY_V2.is_dir(), "Pinned policy source absent")
    def test_untracked_or_substituted_source_rejected(self):
        with patch("tools.run_issue1_original_phase1_tcc_v12.git_blob",
                   return_value="0" * 40):
            with self.assertRaisesRegex(ValueError, "G0_SOURCE_BLOB_MISMATCH"):
                source_pins(POLICY_V2, NATIVE_PIN, NATIVE_COMMIT)


if __name__ == "__main__":
    unittest.main()
