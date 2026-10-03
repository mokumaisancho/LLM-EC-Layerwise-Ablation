#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import generate_s1a_disjoint_holdout as s1gen
import s1a_predictor_core as s1core
import generate_s2b_metadata_blind_holdout as s2gen
import s2b_metadata_blind_core as s2core

S1_SEED = "8d8a333ebc17e73ee04a43baf3a3976c865d621f"
S1_DIGEST = "3192d093d3f2162f94e22e8a2e30ea5dbb691cfc42a7913492435d511d506b9a"
S2_SEED = "5ba03b66dd6b16a2505e40129f808e589ce28bab"
S2_DIGEST = "dca0663302e7fdb50241f08f10df14e395c401d47e6c93e8e1cbd31e57e8364d"
OLD_S1_FAMILIES = {
    "domain_homonym", "near_miss_authority", "unresolved_referent", "causal_intervention",
    "representation_gap", "source_authority", "domain_near_synonym", "mandatory_control",
    "negation_evidence", "freshness_supersession",
}
FORBIDDEN_S2_CANDIDATE_METADATA = {"action_class", "target", "constraint_preserved", "forbidden"}


class ValidationRepairRegression(unittest.TestCase):
    def test_s1_disjoint_holdout_reproducible_and_structurally_disjoint(self):
        fixtures = s1gen.generate(S1_SEED)
        self.assertEqual(16, len(fixtures))
        self.assertEqual(S1_DIGEST, s1gen.digest(fixtures))
        new_families = {f["family"] for f in fixtures}
        self.assertTrue(new_families.isdisjoint(OLD_S1_FAMILIES))

    def test_s1_predictor_does_not_require_oracle_or_family(self):
        fixture = s1gen.generate(S1_SEED)[0]
        stripped = {"visible": fixture["visible"]}
        prediction = s1core.predict(stripped)
        self.assertEqual(set(s1core.FIELDS), set(prediction) & set(s1core.FIELDS))

    def test_s2_metadata_blind_holdout_reproducible(self):
        fixtures = s2gen.generate(S2_SEED)
        self.assertEqual(8, len(fixtures))
        self.assertEqual(S2_DIGEST, s2gen.digest(fixtures))

    def test_s2_predictor_visible_candidates_are_text_only(self):
        for fixture in s2gen.generate(S2_SEED):
            self.assertTrue(all(isinstance(v, str) for v in fixture["candidates"].values()))
            self.assertTrue(FORBIDDEN_S2_CANDIDATE_METADATA.isdisjoint(fixture["relation"]))
            predicted = s2core.predict(fixture["relation"], fixture["candidates"], emit_count=2)
            self.assertEqual(2, len(predicted))
            self.assertEqual(2, len(set(predicted)))
            self.assertTrue(set(predicted) <= set(fixture["candidates"]))


if __name__ == "__main__":
    unittest.main()
