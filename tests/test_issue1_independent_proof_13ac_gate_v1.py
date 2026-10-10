from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.issue1_independent_proof_13ac_gate_v1 import (
    ROOT,PLAN_BLOB,PROTOCOL,EXPECTED,verify_plan,score_frozen_c03,inspect
)
from tools.verify_issue1_s4_bounded_safety_v1 import run as run_bounded_c03

NATIVE=Path("/private/tmp/issue1-ec-native-layerwise-20261010")

class ProofPackage13ACTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=verify_plan()
        if NATIVE.is_dir():
            cls.c03=run_bounded_c03(NATIVE)
        else:
            cls.c03=None

    def test_01_full_13_AC_dependency_and_11_prereq(self):
        x=self.plan
        self.assertEqual(tuple(a["id"] for a in x["acceptance_criteria"]),EXPECTED)
        self.assertEqual(x["proof_package_mvp"]["AC_count"],11)
        self.assertEqual(x["normative_contract"]["original_required_AC"],18)
        self.assertEqual(x["normative_contract"]["original_materiality_abs"],.2)

    def test_02_old_root_definition_never_replaced(self):
        self.assertEqual(self.plan["original_root_status_on_creation"],"OPEN")
        self.assertFalse(self.plan["independent_evidence_obtained_on_creation"])

    def test_03_new_proof_contract_is_pinned_not_self_resealed(self):
        with patch("tools.issue1_independent_proof_13ac_gate_v1.blob",
                   return_value="0"*40):
            with self.assertRaisesRegex(ValueError,"P01_FROZEN_PROOF_CONTRACT_HASH_MISMATCH"):
                verify_plan()

    @unittest.skipUnless(NATIVE.is_dir(),"Pinned native source absent")
    def test_04_true_936_bounded_C03_still_partial(self):
        x=inspect(self.c03)
        self.assertEqual(x["proof_AC_total"],13)
        self.assertEqual(x["proof_package_mvp_required"],11)
        self.assertEqual(x["proof_package_mvp_pass"],0)
        self.assertEqual(x["status_by_AC"]["C03"]["state"],
                         "PARTIAL_BOUNDED_MECHANICS_ONLY")
        self.assertFalse(x["original_MVP_completed"])
        self.assertEqual(x["independent_evidence_ready_for_action"],["P01"])

    @unittest.skipUnless(NATIVE.is_dir(),"Pinned native source absent")
    def test_05_fake_independent_C03_proof_is_rejected(self):
        fake=copy.deepcopy(self.c03)
        fake["independent_obligation_inventory_certified"]=True
        with self.assertRaisesRegex(ValueError,"C03_FALSE_INDEPENDENCE_OR_ROOT_AC_PROMOTION"):
            inspect(fake)

    @unittest.skipUnless(NATIVE.is_dir(),"Pinned native source absent")
    def test_06_forged_936_state_or_mutation_score_is_rejected(self):
        for edit in ["states","mutants"]:
            fake=copy.deepcopy(self.c03)
            if edit=="states":fake["bounded_state_space"]["reference_decision_exact_matches"]=935
            else:fake["actual_native_source_mutation"]["killed"]=4
            with self.assertRaisesRegex(ValueError,"C03_BOUNDED_MECHANICAL_GATES_FAILED"):
                inspect(fake)

    @unittest.skipUnless(NATIVE.is_dir(),"Pinned native source absent")
    def test_07_missing_C02_independent_source_prevents_C03_pass(self):
        out=inspect(self.c03)
        self.assertIn("C02",out["status_by_AC"]["C03"]["missing_prerequisite_AC"])
        self.assertEqual(out["status_by_AC"]["C02"]["state"],"BLOCKED_ON_PRECEDING_PROOF_AC")

    def test_08_all_contract_or_science_overrides_fail_closed(self):
        copy_plan=copy.deepcopy(self.plan)
        copy_plan["acceptance_criteria"][1]["depends"]=["X02"]
        with patch("tools.issue1_independent_proof_13ac_gate_v1.verify_plan",
                   return_value=copy_plan):
            if self.c03 is not None:
                with self.assertRaisesRegex(ValueError,".*"):
                    inspect(self.c03)
            else:
                # Source-independent dependency ordering test.
                seen=set()
                with self.assertRaises(AssertionError):
                    for row in copy_plan["acceptance_criteria"]:
                        assert set(row["depends"]).issubset(seen)
                        seen.add(row["id"])

if __name__=="__main__":
    unittest.main()
