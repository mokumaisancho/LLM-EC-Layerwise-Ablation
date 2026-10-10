from __future__ import annotations
import copy
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"tools/audit_issue1_original_phase1_scope_v1.py"
spec=importlib.util.spec_from_file_location("original_issue1_scope",SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def canonical():
    return tuple(json.loads((ROOT/p).read_text(encoding="utf-8")) for p in (
       "docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json",
       "results/ec_native_adapter_qualification.json",
       "results/phase1_s4_identifiability_audit_2026-10-03.json",
    ))

class Issue1OriginalScopeTests(unittest.TestCase):
    def test_01_actual_source_pinned_and_recomputed(self):
        x=m.run(ROOT)
        self.assertEqual(x["original_mvp_AC_pass"],2)
        self.assertEqual(x["original_mvp_AC_total"],18)
        self.assertFalse(x["original_mvp_complete"])
        self.assertEqual(x["S4_signature_ceiling"]["correct"],8)
        self.assertEqual(x["S4_signature_ceiling"]["total"],10)
        self.assertTrue(x["S4_signature_ceiling"]["bound_only_not_EC_accuracy"])
    def test_02_extra_thirteen_ACs_and_120_docs_are_not_original_MVP(self):
        x=m.run(ROOT)
        self.assertIn("13_ADDITIONAL_PROOF_AC",x["optional_studies_not_frozen_root_gates"])
        self.assertIn("120_EXTERNALLY_SOURCED_HOLDOUT_DOCUMENTS",x["optional_studies_not_frozen_root_gates"])
    def test_03_original_threshold_cannot_change(self):
        c,e,s=map(copy.deepcopy,canonical())
        c["frozen_thresholds"]["oracle_substitution_gain_material_abs"]=0.1
        with self.assertRaisesRegex(ValueError,"ORIGINAL_MVP_OR_0P20_MATERIALITY_CHANGED"):
            m.audit(c,e,s)
    def test_04_new_ec_source_must_have_successor_protocol(self):
        c,e,s=map(copy.deepcopy,canonical())
        e["ec_source"]["commit"]="a"*40
        with self.assertRaisesRegex(ValueError,"FROZEN_NATIVE_PROVENANCE_CHANGED"):
            m.audit(c,e,s)
    def test_05_forged_native_s3_adapter_denied(self):
        c,e,s=map(copy.deepcopy,canonical())
        e["subfunction_authority"]["s3_selection"]["authority"]="EC_NATIVE"
        with self.assertRaisesRegex(ValueError,"FORGED_EC_NATIVE_SAME_FUNCTION_QUALIFICATION"):
            m.audit(c,e,s)
    def test_06_forged_ec_accuracy_claim_denied(self):
        c,e,s=map(copy.deepcopy,canonical())
        s["identifiability"]["metric_type"]="EC_ACCURACY"
        with self.assertRaisesRegex(ValueError,"INTERFACE_BOUND_LAUNDERED_AS_ACCURACY"):
            m.audit(c,e,s)
    def test_07_duplicate_s4_fixture_denied(self):
        c,e,s=map(copy.deepcopy,canonical())
        s["collision_groups"][1]["closure_labels"]["CLOSE"].append("M001")
        with self.assertRaisesRegex(ValueError,"DUPLICATE_CLOSURE_SCORING"):
            m.audit(c,e,s)
    def test_08_original_ac_dependency_cycle_denied(self):
        c,e,s=map(copy.deepcopy,canonical())
        c["ac_dependencies"]["AC-19"]=["AC-01"]
        with self.assertRaisesRegex(ValueError,"AC_DEPENDENCY_CYCLE"):
            m.audit(c,e,s)
    def test_09_extra_unknown_scientific_ac_denied(self):
        c,e,s=map(copy.deepcopy,canonical())
        c["ac_dependencies"]["AC-21"]=[]
        with self.assertRaisesRegex(ValueError,"AC20_ADDED_OR_REMOVED"):
            m.audit(c,e,s)
    def test_10_source_blob_tamper_denied(self):
        with patch.object(m,"blob",return_value="0"*40):
            with self.assertRaisesRegex(ValueError,"FROZEN_GIT_BLOB_MISMATCH"):
                m.run(ROOT)
    def test_11_no_original_phase1_completion_from_scoped_experiment(self):
        x=m.run(ROOT)
        self.assertFalse(x["genuine_A_B_C_D_E_four_layer_evidence"])
        self.assertFalse(x["original_mvp_complete"])
        self.assertEqual(x["actual_blocker"],"FROZEN_NATIVE_S3_S4_SAME_FUNCTION_INCOMPATIBLE")
    def test_12_correct_strict_required_ac_and_post_mvp(self):
        x=m.run(ROOT)
        self.assertEqual(x["post_MVP"],["AC-10","AC-18"])
        self.assertEqual({k for k,v in x["original_AC20_status"].items() if v=="PASS"},
                         {"AC-19","AC-20"})

if __name__=="__main__":
    unittest.main()
