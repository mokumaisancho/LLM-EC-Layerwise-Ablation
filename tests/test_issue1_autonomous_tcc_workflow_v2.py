from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.run_issue1_autonomous_tcc_workflow_v2 import (
    DEFAULT_MODEL_EVIDENCE, ROOT, checked_model_report, run, spec, TCC_SOURCE,
)

TCC_ROOT=Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC_ROOT=Path("/private/tmp/llmec-ecv44-source-20261010")


class Issue1AutonomousV2ContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads(DEFAULT_MODEL_EVIDENCE.read_text())
        cls.assets_available=TCC_ROOT.exists() and EC_ROOT.exists()

    def test_01_true_generated_graph_has_one_scoped_success_terminal(self):
        c=spec()
        nodes=c["nodes"]
        ok=[n for n in nodes if n["kind"]=="terminal" and n["terminal_status"]=="SUCCESS"]
        self.assertEqual([n["id"] for n in ok],["scoped_machine_evidence_qualified"])
        self.assertEqual(c["entry_nodes"],["frozen_origin"])
        self.assertEqual(len(nodes),8)

    def test_02_fail_closed_gate_and_order(self):
        nodes={x["id"]:x for x in spec()["nodes"]}
        self.assertEqual(nodes["s4_public_info"]["depends_on"],["frozen_origin"])
        self.assertEqual(nodes["ec_native17"]["depends_on"],["s4_public_info"])
        self.assertEqual(nodes["llm_pinned17"]["depends_on"],["ec_native17"])
        self.assertEqual(nodes["assess_machine_scope"]["branches"]["additional_input_missing"],"blocked_external_science")
        for name in ("s4_public_info","ec_native17","llm_pinned17"):
            self.assertEqual(nodes[name]["failure_target"],"blocked_integrity")

    def test_03_real_pinned_Qwen_report_valid(self):
        q=checked_model_report(self.report)
        self.assertEqual(q["llm_actual_inference_count"],17)
        self.assertEqual(q["llm"]["decision_correct"],1)
        self.assertEqual(len(q["raw_inference"]),17)
        self.assertEqual(len(set(x["prompt_sha256"] for x in q["raw_inference"])),17)

    def test_04_forged_original_scientific_completion_rejected(self):
        q=copy.deepcopy(self.report)
        q["run"]["scientific_phase1_a_e_completed"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_CLAIM_OF_SCIENTIFIC_COMPLETION"):
            checked_model_report(q)

    def test_05_forged_model_identity_rejected(self):
        q=copy.deepcopy(self.report)
        q["run"]["qwen_model_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"LOCAL_QWEN_MODEL_PIN_MISMATCH"):
            checked_model_report(q)

    def test_06_missing_raw_rows_rejected(self):
        q=copy.deepcopy(self.report)
        q["run"]["raw_inference"].pop()
        with self.assertRaisesRegex(ValueError,"LOCAL_QWEN_REAL_INFERENCE_COVERAGE_INVALID"):
            checked_model_report(q)

    @unittest.skipUnless(TCC_ROOT.exists() and EC_ROOT.exists(),"Native source and TCC tool unavailable")
    def test_07_autonomous_second_stage_actual_branch_success_limited(self):
        v=run(TCC_ROOT,ec_root=EC_ROOT)
        self.assertTrue(v["subworkflow_machine_qualified"])
        self.assertEqual(v["native_ec_17"]["cases"],17)
        self.assertEqual(v["real_qwen_17"]["correct"],1)
        self.assertFalse(v["original_issue_1_five_arm_complete"])
        self.assertFalse(v["external_independent_gold_qualified"])
        self.assertFalse(v["ecv4_issue_closure_authorized"])
        self.assertEqual(v["ecv4_handoff"]["schema"],"tcc.ecv4-evidence.v0")

    @unittest.skipUnless(TCC_ROOT.exists(),"TCC tool unavailable")
    def test_08_missing_ec_source_does_not_skip_independent_s4_work(self):
        v=run(TCC_ROOT)
        self.assertFalse(v["subworkflow_machine_qualified"])
        self.assertEqual(v["native_ec_17"]["status"],"EC_PINNED_CHECKOUT_NOT_SUPPLIED")
        self.assertEqual(v["s4_public_information"]["retrospective_count"],10)
        self.assertEqual(v["stop_state"],"EXTERNAL_INPUT_REQUIRED")

    @unittest.skipUnless(TCC_ROOT.exists() and EC_ROOT.exists(),"Native source and TCC tool unavailable")
    def test_09_corrupt_legacy_report_blocks_integrity_not_fake_science(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"bad.json"
            v=copy.deepcopy(self.report)
            v["run"]["llm_actual_inference_count"]=1
            path.write_text(json.dumps(v))
            x=run(TCC_ROOT,ec_root=EC_ROOT,report_file=path)
            self.assertEqual(x["stop_state"],"FAIL_CLOSED_INTEGRITY")
            self.assertEqual(x["ecv4_handoff"]["terminal_id"],"blocked_integrity")
            self.assertFalse(x["ecv4_issue_closure_authorized"])

    def test_10_no_background_scheduler_or_ui_or_gold_file_read(self):
        source=(ROOT/"tools/run_issue1_autonomous_tcc_workflow_v2.py").read_text()
        for disallowed in ("automations.create(","launchctl","crontab","chatgpt.com/","gold.json"):
            self.assertNotIn(disallowed,source)


if __name__=="__main__":
    unittest.main()
