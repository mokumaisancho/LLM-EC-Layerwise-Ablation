from __future__ import annotations
import ast
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.run_issue1_s4_interface_information_diagnostic_v1 import (
    PROTOCOL, ROOT, baseline_signature, predict, public_projection, run,
)


class Issue1S4InterfaceInformationTests(unittest.TestCase):
    def sample(self, relation="COMPETING"):
        task={"schema_version":"TASK_INPUT_V1","fixture_id":"IGNORE-ME",
              "context":{"facts":["required_condition=resolved"],"domain_rules":[]}}
        s2={"schema_version":"S2_CANDIDATE_SET_V1","fixture_id":"IGNORE-ME",
            "candidates":[{"candidate_id":"a"},{"candidate_id":"b"}],
            "relation_groups":[{"relation_type":relation,"candidate_ids":["a","b"]}],
            "oracle_constraints":{"acceptable_candidate_ids":["NEVER_READ"]}}
        s3={"schema_version":"S3_SELECTED_REFRAMED_STATE_V1","fixture_id":"IGNORE-ME",
            "selection":{"selected_candidate_ids":["a","b"],"rejected_candidate_ids":[]},
            "framing":{"reframe_required":False,"trigger_residuals":[]},
            "oracle_constraints":{"acceptable_selected_candidate_ids":["NEVER_READ"]}}
        return task,s2,s3

    def test_01_no_id_or_oracle_reaches_predictor(self):
        values=public_projection(*self.sample())
        self.assertEqual(set(values),{
            "protocol","selected_count","rejected_count","reframe_required",
            "trigger_residual_types","relation_groups","required_condition_state",
        })
        rendered=json.dumps(values)
        self.assertNotIn("IGNORE-ME",rendered)
        self.assertNotIn("NEVER_READ",rendered)
        self.assertNotIn("oracle",rendered.lower())

    def test_02_public_relation_competing_continues(self):
        self.assertEqual(predict(public_projection(*self.sample()))["closure_class"],"CONTINUE")

    def test_03_public_relation_equivalent_closes(self):
        self.assertEqual(predict(public_projection(*self.sample("EQUIVALENT")))["closure_class"],"CLOSE")

    def test_04_pending_required_condition_blocks_even_equivalent(self):
        t,s2,s3=self.sample("EQUIVALENT")
        t["context"]["facts"]=["required_condition=unresolved"]
        self.assertEqual(predict(public_projection(t,s2,s3))["closure_class"],"CONTINUE")

    def test_05_missing_relation_changes_choice(self):
        x=public_projection(*self.sample())
        control=dict(x)
        control["relation_groups"]=[]
        self.assertEqual(predict(control)["closure_class"],"CLOSE")
        self.assertEqual(baseline_signature(control),baseline_signature(x))

    def test_06_unknown_relation_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"UNKNOWN_RELATION_TYPE"):
            public_projection(*self.sample("MADE_UP"))

    def test_07_unselected_candidate_relation_fails_closed(self):
        t,s2,s3=self.sample()
        s3["selection"]["selected_candidate_ids"]=["a"]
        with self.assertRaisesRegex(ValueError,"RELATION_SELECTED_SET_MISMATCH"):
            public_projection(t,s2,s3)

    def test_08_gold_injection_rejected(self):
        x=public_projection(*self.sample())
        x["gold"]="CONTINUE"
        with self.assertRaisesRegex(ValueError,"PUBLIC_ONLY_SCHEMA_REQUIRED"):
            predict(x)

    def test_09_fixture_id_does_not_drive_decision(self):
        t,s2,s3=self.sample()
        x=public_projection(t,s2,s3)
        for k in ("M003","M009","EXTERNAL-NEVER-SEEN"):
            t["fixture_id"]=k
            self.assertEqual(public_projection(t,s2,s3),x)

    def test_10_isolated_subprocess_actual_predictor(self):
        x=public_projection(*self.sample())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"only_public.json"
            path.write_text(json.dumps(x))
            p=subprocess.run([sys.executable,"-I",str(ROOT/"tools/run_issue1_s4_interface_information_diagnostic_v1.py"),
                              "--predict-public",str(path)],capture_output=True,text=True,timeout=12)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(json.loads(p.stdout),predict(x))

    def test_11_run_preserves_truth_scope_and_interventions(self):
        x=run()
        self.assertEqual(x["fixture_count"],10)
        self.assertEqual(x["original_structural_interface_majority_upper_bound"],0.8)
        self.assertEqual(x["enhanced_public_interface_known_fixture_accuracy"],1)
        self.assertFalse(x["independent_study_certified"])
        self.assertFalse(x["full_five_arm_run"])
        self.assertFalse(x["native_ec_closure_measured"])
        self.assertFalse(x["original_issue_one_qualified"])
        for case in ("M003","M007"):
            self.assertNotEqual(x["feature_ablation_controls"][case]["baseline"]["closure_class"],
                                x["feature_ablation_controls"][case]["negative_control_prediction"]["closure_class"])

    def test_12_predictor_no_oracle_gold_import(self):
        tree=ast.parse((ROOT/"tools/run_issue1_s4_interface_information_diagnostic_v1.py").read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="predict")
        self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(fn)))
        text=ast.unparse(fn).lower()
        for forbidden in ("oracle_constraints","hidden","evaluation","read_text","open("):
            self.assertNotIn(forbidden,text)

if __name__=="__main__":
    unittest.main()
