from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.verify_issue1_s4_bounded_safety_v1 import (
    ROOT, PROTOCOL, EC_COMMIT, S4_BLOB, RELATIONS, FRAMES, STATUSES,
    MUTANTS, PREDICATES, all_states, case, oracle, pin, run, witnesses,
)
from tools.run_issue1_root_ac_continuation_tcc_v9 import manifest, execute

NATIVE=Path("/private/tmp/issue1-ec-native-layerwise-20261010")
TCC=Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC=Path("/private/tmp/llmec-ecv44-source-20261010")
OLD=Path("/private/tmp/issue1-ec-w4a-frozen-20261010")

class C03BoundedSafetySchemaTests(unittest.TestCase):
    def test_01_explicit_finite_state_domain_has_936_states(self):
        self.assertEqual(sum(1 for _ in all_states()),936)
        self.assertEqual(len(RELATIONS),3)
        self.assertEqual(len(FRAMES),3)
        self.assertEqual(len(STATUSES),3)

    def test_02_stable_frozen_source_git_blob_declared(self):
        self.assertEqual(EC_COMMIT,"ae4b02bca34147d549abda85fad9cdc793ca054f")
        self.assertEqual(S4_BLOB,"c12e4743c89221a9b81a2f2fa98c4df9d61d72b2")

    def test_03_independent_condition_decision_witnesses_covered(self):
        samples=witnesses()
        self.assertEqual(set(samples),set(PREDICATES))
        for name,(a,b) in samples.items():
            self.assertNotEqual(a,b,name)

    def test_04_actual_source_mutants_are_five_distinct_failures(self):
        self.assertEqual(len(MUTANTS),5)
        self.assertEqual(len(set(MUTANTS)),5)

    def test_05_simple_reference_obligation_monotonicity(self):
        self.assertEqual(oracle(("A","B"),"EQUIVALENT",(),(False,False),True),"CLOSE")
        self.assertEqual(oracle(("A","B"),"EQUIVALENT",("UNRESOLVED",),(False,False),True),"CONTINUE")
        self.assertEqual(oracle(("A","B"),"COMPETING",(),(False,False),True),"CONTINUE")
        self.assertEqual(oracle(("A",),"NONE",(),(False,False),False),"REJECT_INVENTORY")

    def test_06_tcc9_has_real_s4_formal_node_and_root_exit(self):
        x=manifest()
        self.assertIn("s4formal",x["state_keys"])
        nodes=x["nodes"]
        self.assertIn("verify_bounded_native_S4_formal_properties",[n["id"] for n in nodes])
        self.assertEqual([n["id"] for n in nodes if n["kind"]=="terminal" and n["terminal_status"]=="SUCCESS"],
                         ["root_science_verified"])

@unittest.skipUnless(all(x.is_dir() for x in (NATIVE,TCC,EC,OLD)),
                     "actual pinned EC and source checkouts unavailable")
class C03NativeActualSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=run(NATIVE)

    def test_07_native_full_bounded_state_space(self):
        x=self.report["bounded_state_space"]
        self.assertEqual(x["states_checked"],936)
        self.assertEqual(x["reference_decision_exact_matches"],936)
        self.assertEqual(x["unattested_states_refused"],468)
        self.assertEqual(x["unsafe_close_within_typed_bounded_reference"],0)

    def test_08_all_five_MC_DC_independent_condition_pairs(self):
        x=self.report["MC_DC_BOUNDED"]
        self.assertEqual(x["pair_count"],5)
        self.assertEqual(set(x["independent_pairs"]),set(PREDICATES))
        for pair in x["independent_pairs"].values():
            self.assertEqual(pair[0],"CLOSE")
            self.assertNotEqual(pair[0],pair[1])

    def test_09_all_five_actual_source_mutations_killed(self):
        x=self.report["actual_native_source_mutation"]
        self.assertEqual(x["killed"],x["total"])
        self.assertEqual(x["killed"],5)
        self.assertTrue(all(x["mutants"][m]["killed"] for m in x["mutants"]))

    def test_10_partial_c03_does_not_pass_full_requirement_AC(self):
        self.assertFalse(self.report["original_AC_C03_qualified"])
        self.assertFalse(self.report["independent_obligation_inventory_certified"])
        self.assertFalse(self.report["independent_natural_language_semantics_certified"])

    def test_11_forged_ec_git_blob_refused(self):
        with patch("tools.verify_issue1_s4_bounded_safety_v1.git_blob",return_value="0"*40):
            with self.assertRaisesRegex(ValueError,"C03_NATIVE_SOURCE_BLOB_CHANGED"):
                pin(NATIVE)

    def test_12_reference_oracle_corruption_detected_before_scientific_acceptance(self):
        with patch("tools.verify_issue1_s4_bounded_safety_v1.oracle",return_value="CLOSE"):
            with self.assertRaisesRegex(ValueError,"C03_STATE_COUNTEREXAMPLES"):
                run(NATIVE)

    def test_13_tcc_rejects_false_C03_certification(self):
        fake=dict(self.report);fake["original_AC_C03_qualified"]=True
        with patch("tools.run_issue1_root_ac_continuation_tcc_v9.verify_bounded_s4",
                   return_value=fake):
            result=execute(TCC,EC,OLD,NATIVE)
        self.assertEqual(result["TCC_terminal_id"],"blocked_integrity")
        self.assertFalse(result["original_issue_completed"])

if __name__=="__main__":
    unittest.main()
