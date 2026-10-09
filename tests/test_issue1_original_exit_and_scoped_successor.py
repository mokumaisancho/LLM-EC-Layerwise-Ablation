from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.audit_issue1_original_exit_and_scoped_successor import (
    EvidenceError, PATHS, ROOT, s4_structural_identifiability, verify,
)


class OriginIssue1ExitGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = verify(ROOT)
        cls.s4 = json.loads((ROOT / PATHS["s4_identifiability"]).read_text())

    def test_01_true_scope_disclosed_without_false_original_closure(self):
        v = self.reference
        self.assertFalse(v["original_exit_pass"])
        self.assertFalse(v["issue1_auto_closure_authorized"])
        self.assertEqual(v["original_phase1_exit"],"EC_NATIVE_SCOPE_INCOMPATIBLE")
        self.assertEqual(v["completed_scoped_successor"]["scoped_study_status"],
                         "COMPLETE_FOR_CURRENT_MVP_BOUNDARY")
        self.assertEqual(v["independent_original_LLM0_four_arm_quality"],"NOT_RUN")

    def test_02_bound_recomputed_from_raw_collision_groups(self):
        result=s4_structural_identifiability(self.s4)
        self.assertEqual(result["unique_fixture_count"],10)
        self.assertEqual(result["max_majority_correct"],8)
        self.assertAlmostEqual(result["structural_upper_bound"],0.8)
        self.assertTrue(result["not_ec_accuracy"])

    def test_03_duplicate_fixtures_detected(self):
        audit=copy.deepcopy(self.s4)
        audit["collision_groups"][1]["closure_labels"]["CLOSE"].append("M001")
        with self.assertRaisesRegex(EvidenceError,"COLLISION_FIXTURE_OVERLAP"):
            s4_structural_identifiability(audit)

    def test_04_majority_bound_tamper_rejected(self):
        audit=copy.deepcopy(self.s4)
        audit["identifiability"]["best_possible_majority_correct"]=10
        with self.assertRaisesRegex(EvidenceError,"IDENTIFIABILITY_BOUND_NOT_REPRODUCED"):
            s4_structural_identifiability(audit)

    def test_05_fake_ec_accuracy_claim_rejected(self):
        audit=copy.deepcopy(self.s4)
        audit["identifiability"]["metric_type"]="EC_NATIVE_DECISION_ACCURACY"
        with self.assertRaisesRegex(EvidenceError,"INTERFACE_METRIC_RELABELED"):
            s4_structural_identifiability(audit)

    def with_copied_evidence(self, mutate):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for path in PATHS.values():
                src=ROOT/path
                dst=root/path
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(src,dst)
            mutate(root)
            return verify(root)

    def test_06_forged_adapter_qualification_rejected(self):
        def mutation(root):
            p=root/PATHS["adapter"]
            a=json.loads(p.read_text())
            a["status"]="PASS"
            p.write_text(json.dumps(a))
        with self.assertRaisesRegex(EvidenceError,"ADAPTER_QUALIFICATION_REWRITTEN"):
            self.with_copied_evidence(mutation)

    def test_07_forged_s3_ec_native_semantics_rejected(self):
        def mutation(root):
            p=root/PATHS["adapter"]
            a=json.loads(p.read_text())
            a["subfunction_authority"]["s3_selection"]["authority"]="EC_NATIVE"
            a["subfunction_authority"]["s3_selection"]["reportable"]=True
            p.write_text(json.dumps(a))
        with self.assertRaisesRegex(EvidenceError,"FORGED_EC_NATIVE_AUTHORITY:s3_selection"):
            self.with_copied_evidence(mutation)

    def test_08_forged_successor_termination_rejected(self):
        def mutation(root):
            p=root/PATHS["successor_boundary"]
            a=json.loads(p.read_text())
            a["research_status"]="COMPLETE_FOR_UNRESTRICTED_LANGUAGE"
            p.write_text(json.dumps(a))
        with self.assertRaisesRegex(EvidenceError,"SUCCESSOR_SCOPE_UNVERIFIED"):
            self.with_copied_evidence(mutation)

    def test_09_pinned_real_model_artifact_tampering_rejected(self):
        def mutation(root):
            p=root/PATHS["s1c_actual"]
            with p.open("ab") as fh:
                fh.write(b"\n")
        with self.assertRaisesRegex(EvidenceError,"S1C_ACTUAL_OUTPUT_SHA_DRIFT"):
            self.with_copied_evidence(mutation)

    def test_10_phase1_frozen_contract_changed_rejected(self):
        def mutation(root):
            p=root/PATHS["original_contract"]
            a=json.loads(p.read_text())
            a["frozen_thresholds"]["oracle_substitution_gain_material_abs"]=0.15
            p.write_text(json.dumps(a))
        with self.assertRaisesRegex(EvidenceError,"THRESHOLD_CHANGED"):
            self.with_copied_evidence(mutation)

    def test_11_true_compatibility_must_not_be_misreported_as_frozen(self):
        def mutation(root):
            p=root/PATHS["frozen_actual"]
            a=json.loads(p.read_text())
            a["terminal_state"]="MVP_COARSE_LOCALIZED:S1"
            p.write_text(json.dumps(a))
        with self.assertRaisesRegex(EvidenceError,"FALSE_SUCCESS_ON_INCOMPATIBLE_DATA"):
            self.with_copied_evidence(mutation)

    def test_12_workflow_added_is_disallowed(self):
        def mutation(root):
            p=root/".github"/"workflows"/"automatically_fake_pass.yml"
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text("name: fake\n")
        with self.assertRaisesRegex(EvidenceError,"GITHUB_ACTIONS_NOT_ALLOWED"):
            self.with_copied_evidence(mutation)


if __name__=="__main__":
    unittest.main()
