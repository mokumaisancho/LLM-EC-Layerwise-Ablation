from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.issue1_ac_dependency_planner_v9 import (
    ROOT, REQUIRED, ALL, WORK, check_normative, inspect_ac_proof, schedule, work_order
)
from tools.run_issue1_root_ac_continuation_tcc_v9 import (
    PROTOCOL, DATA_COUNT, manifest, tracked_code_seal,
    frozen_input_seal, verify_dynamic_typed, execute,
)

NORM=json.loads((ROOT/"docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json").read_text())
V8=json.loads((ROOT/"results/issue1_root_ac_tcc_v8_actual_2026-10-10.json").read_text())["actual"]
TCC=Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC=Path("/private/tmp/llmec-ecv44-source-20261010")
OLD=Path("/private/tmp/issue1-ec-w4a-frozen-20261010")
NATIVE=Path("/private/tmp/issue1-ec-native-layerwise-20261010")

class OriginalACPlannerV9(unittest.TestCase):
    def test_original_membership_and_threshold(self):
        v=check_normative(NORM)
        self.assertEqual(len(REQUIRED),18)
        self.assertEqual(len(ALL),20)
        self.assertEqual(set(v["ac20_order"]),ALL)
        self.assertEqual(NORM["frozen_thresholds"]["oracle_substitution_gain_material_abs"],.2)

    def test_work_DAG_topological(self):
        o=work_order()
        self.assertEqual(len(o),len(WORK))
        for k in o:
            self.assertTrue(set(WORK[k]["deps"]).issubset(set(o[:o.index(k)])))

    def test_unknown_AC_and_cycle_fail_closed(self):
        bad=copy.deepcopy(NORM)
        bad["ac_dependencies"]["AC-19"]=["AC-09"]
        with self.assertRaisesRegex(ValueError,"G1_AC_CYCLE"):
            check_normative(bad)
        bad=copy.deepcopy(NORM)
        bad["ac_dependencies"]["AC-03"]=["AC-99"]
        with self.assertRaisesRegex(ValueError,"G1_UNKNOWN_AC_DEPENDENCY"):
            check_normative(bad)

    def test_scoped_success_never_promotes_root_18(self):
        result=inspect_ac_proof(V8,NORM)
        self.assertEqual(result["original_mvp_pass_count"],2)
        self.assertEqual(len(result["original_mvp_unmet"]),16)
        self.assertFalse(result["original_mvp_complete"])

    def test_forged_success_or_dirty_source_denied(self):
        fake=copy.deepcopy(V8)
        fake["original_AC_MVP18_pass_count"]=18
        with self.assertRaisesRegex(ValueError,"G11_FALSE_SCIENTIFIC_AC_PASS"):
            inspect_ac_proof(fake,NORM)
        fake=copy.deepcopy(V8)
        fake["research_code_pre_post_equal"]=False
        with self.assertRaisesRegex(ValueError,"G0_SOURCE_SEAL_FAILED"):
            inspect_ac_proof(fake,NORM)

    def test_external_gold_custody_cannot_be_self_asserted(self):
        fake={"external_gold_independence_verified":True,
              "provenance_custody_verified":False,
              "genuine_inference_verified":False}
        with self.assertRaisesRegex(ValueError,"G6_EXTERNAL_REVIEW_SELF_ASSERTED"):
            schedule(V8,NORM,fake)

    def test_unmet_work_dependencies_and_next_critical_path(self):
        x=schedule(V8,NORM)
        self.assertEqual(x["first_unmet_independence"],
            ["W4B_INDEPENDENT_SEMANTICS","W4C_INDEPENDENT_COMPLETENESS"])
        self.assertEqual(x["W0_W7_dependency_state"]["W5_ORIGINAL_A_TO_E"]["state"],
                         "BLOCKED_DEPENDENCY")
        self.assertFalse(x["root_ac_complete"])

    def test_true_exit_terminal_single(self):
        nodes=manifest()["nodes"]
        self.assertEqual([x["id"] for x in nodes if x["kind"]=="terminal"
             and x["terminal_status"]=="SUCCESS"],["root_science_verified"])
        self.assertIn("verify_bounded_native_S4_formal_properties",[x["id"] for x in nodes])

@unittest.skipUnless(all(p.is_dir() for p in (TCC,EC,OLD,NATIVE)),
                     "Pinned TCC/native EC source checkouts absent")
class OriginalACRealTCCv9(unittest.TestCase):
    def test_bounded_additional_48_without_test_gold(self):
        x=verify_dynamic_typed(NATIVE)
        self.assertEqual(x["case_count"],DATA_COUNT)
        self.assertEqual(x["all_formal_typed_cases_passed"],48)
        self.assertEqual(x["S4_false_closure_prevented"],48)
        self.assertTrue(x["tampered_document_rejected"])
        self.assertTrue(x["unknown_fact_abstention_verified"])
        self.assertTrue(x["independent_natural_language_science_not_established"])

    def test_code_and_frozen_normative_preflight(self):
        self.assertGreaterEqual(len(tracked_code_seal()),5)
        self.assertEqual(len(frozen_input_seal()),2)

    def test_full_one_invocation_AC_and_bounded_C03(self):
        v=execute(TCC,EC,OLD,NATIVE)
        self.assertEqual(v["protocol"],PROTOCOL)
        self.assertEqual(v["TCC_terminal_id"],"blocked_external_science")
        self.assertEqual(v["original_required_AC"],18)
        self.assertEqual(v["original_AC_pass_count"],2)
        self.assertFalse(v["original_issue_completed"])
        self.assertTrue(v["all_seals_same"])
        self.assertEqual(v["errors"],[])
        formal=v["C03_bounded_native_S4_formal_proof"]
        self.assertEqual(formal["bounded_state_space"]["states_checked"],936)
        self.assertEqual(formal["MC_DC_BOUNDED"]["pair_count"],5)
        self.assertEqual(formal["actual_native_source_mutation"]["killed"],5)
        self.assertFalse(formal["original_AC_C03_qualified"])

    def test_corrupted_local_bounded_formal_result_blocks_root(self):
        forged={"original_AC_C03_qualified":True,
                "bounded_state_space":{"states_checked":936,
                                       "reference_decision_exact_matches":936,
                                       "unattested_states_refused":468,
                                       "unsafe_close_within_typed_bounded_reference":0},
                "MC_DC_BOUNDED":{"pair_count":5},
                "actual_native_source_mutation":{"killed":5,"total":5},
                "independent_obligation_inventory_certified":False}
        with patch("tools.run_issue1_root_ac_continuation_tcc_v9.verify_bounded_s4",
                   return_value=forged):
            v=execute(TCC,EC,OLD,NATIVE)
        self.assertEqual(v["TCC_terminal_id"],"blocked_integrity")
        self.assertFalse(v["original_issue_completed"])

if __name__=="__main__":
    unittest.main()
