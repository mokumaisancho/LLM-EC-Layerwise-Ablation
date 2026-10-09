from __future__ import annotations

import copy
import os
import unittest
from pathlib import Path

from tools import run_issue1_autonomous_tcc_workflow as ctl

DEFAULT_TCC=Path("/private/tmp/llmec-tcc-generator-reference-20261009")
TCC_ROOT=Path(os.environ.get("ISSUE1_READONLY_TCC_ROOT",str(DEFAULT_TCC)))


class Issue1AutonomousBranchContractTests(unittest.TestCase):
    def test_01_machine_workflow_declares_one_scoped_success_not_global(self):
        spec=ctl.spec()
        self.assertEqual(spec["schema"],"tcc.spec.v3")
        self.assertEqual(sum(n["kind"]=="terminal" and n["terminal_status"]=="SUCCESS" for n in spec["nodes"]),1)
        self.assertEqual(next(n["id"] for n in spec["nodes"] if n["kind"]=="terminal" and n["terminal_status"]=="SUCCESS"),"scoped_verified_external_review")
        self.assertNotIn("ORIGINAL_COMPLETE",str(spec))
        self.assertEqual(spec["entry_nodes"],["verify_frozen_origin"])

    def test_02_explicit_fail_closed_transitions(self):
        nodes={n["id"]:n for n in ctl.spec()["nodes"]}
        self.assertEqual(nodes["route_original_scope"]["branches"]["frozen_incompatible"],"verify_scoped_successor")
        self.assertEqual(nodes["route_original_scope"]["branches"]["unanticipated_change"],"blocked_integrity")
        self.assertEqual(nodes["route_external_evidence"]["branches"]["missing"],"scoped_verified_external_missing")
        self.assertEqual(nodes["route_external_evidence"]["branches"]["requires_review"],"scoped_verified_external_review")

    def test_03_no_scheduling_or_chat_recursion_in_machine_runner(self):
        s=(ctl.ROOT/"tools/run_issue1_autonomous_tcc_workflow.py").read_text()
        for forbidden in ("automations.create(", "launchctl submit", "crontab -", "chatgpt.com/conversation"):
            self.assertNotIn(forbidden,s)

    def test_04_expected_source_pin_mismatch_fails_closed_before_tcc(self):
        with self.assertRaisesRegex(ValueError,"RESEARCH_HEAD_DRIFT"):
            ctl.execute(TCC_ROOT,expected_source="0"*40)

    @unittest.skipUnless(TCC_ROOT.exists(),"pinned TCC generator not installed on this host")
    def test_05_real_generated_tcc_graph_executes_until_scoped_external_block(self):
        x=ctl.execute(TCC_ROOT)
        self.assertTrue(x["machine_steps_without_intermediate_user_prompts"])
        self.assertFalse(x["creates_automations"])
        self.assertFalse(x["starts_background_process"])
        self.assertFalse(x["original_five_arm_complete"])
        self.assertFalse(x["scientific_preservation_certified"])
        self.assertFalse(x["ecv4_closure_authorized"])
        self.assertEqual(x["stop_state"],"SCOPED_SUCCESSOR_AUDITED_ORIGINAL_REQUIRES_NEW_VALID_STUDY")
        self.assertEqual(x["tcc_terminal_id"],"scoped_verified_external_missing")
        self.assertEqual(x["actual_frozen_tcc_replay"]["terminal"],"EC_NATIVE_SCOPE_INCOMPATIBLE")
        self.assertEqual(x["scoped_successor"]["status"],"COMPLETE_FOR_CURRENT_MVP_BOUNDARY")

    @unittest.skipUnless(TCC_ROOT.exists(),"pinned TCC generator not installed on this host")
    def test_06_fake_original_success_is_rejected(self):
        from tools.audit_issue1_original_exit_and_scoped_successor import verify
        def tamper(root,*,actual_replay):
            result=verify(root,actual_replay=actual_replay)
            result["original_exit_pass"]=True
            return result
        x=ctl.execute(TCC_ROOT,verifier=tamper)
        self.assertEqual(x["tcc_terminal_id"],"blocked_integrity")
        self.assertIn("ORIGINAL_AC_FALSELY_SATISFIED",x["reason"])
        self.assertFalse(x["ecv4_closure_authorized"])

    @unittest.skipUnless(TCC_ROOT.exists(),"pinned TCC generator not installed on this host")
    def test_07_fake_independence_attestation_is_rejected(self):
        def bad_inspector(_):
            return {"external_gold_independence_verified":True,
                    "provenance_custody_verified":False,
                    "genuine_inference_verified":False}
        x=ctl.execute(TCC_ROOT,study_inspector=bad_inspector)
        self.assertEqual(x["tcc_terminal_id"],"blocked_integrity")
        self.assertIn("INDEPENDENCE_NOT_MACHINE_CERTIFIABLE",x["reason"])

    @unittest.skipUnless(TCC_ROOT.exists(),"pinned TCC generator not installed on this host")
    def test_08_machine_structural_ready_routes_to_review_only_not_science(self):
        def structurally_ready(_):
            return {"external_gold_independence_verified":False,
                    "provenance_custody_verified":False,
                    "genuine_inference_verified":False,
                    "machine_structural_complete":True}
        x=ctl.execute(TCC_ROOT,study_inspector=structurally_ready)
        self.assertEqual(x["tcc_terminal_id"],"scoped_verified_external_review")
        self.assertEqual(x["tcc_status"],"SUCCESS")
        self.assertFalse(x["original_five_arm_complete"])
        self.assertFalse(x["scientific_preservation_certified"])
        self.assertFalse(x["ecv4_closure_authorized"])
        self.assertEqual(x["stop_state"],"SCOPED_SUCCESSOR_AUDITED_ORIGINAL_REQUIRES_NEW_VALID_STUDY")

    @unittest.skipUnless(TCC_ROOT.exists(),"pinned TCC generator not installed on this host")
    def test_09_scope_incompatibility_can_not_be_silently_redefined(self):
        from tools.audit_issue1_original_exit_and_scoped_successor import verify
        def forged_native_scope(root,*,actual_replay):
            r=verify(root,actual_replay=actual_replay)
            r["frozen_tcc_replay"]["terminal"]="MVP_COARSE_LOCALIZED:S3"
            return r
        x=ctl.execute(TCC_ROOT,verifier=forged_native_scope)
        self.assertEqual(x["tcc_terminal_id"],"blocked_integrity")
        self.assertIn("UNEXPECTED_FROZEN_ORIGINAL_TERMINAL",x["reason"])

    @unittest.skipUnless(TCC_ROOT.exists(),"pinned TCC generator not installed on this host")
    def test_10_source_and_tcc_provenance_are_pinned(self):
        x=ctl.execute(TCC_ROOT)
        self.assertEqual(x["tcc_compiler_pin"],ctl.TCC_SOURCE)
        self.assertEqual(x["source_commit"],ctl.source_sha())
        self.assertEqual(x["ecv4_handoff"]["schema"],"tcc.ecv4-evidence.v0")
        self.assertEqual(x["ecv4_handoff"]["terminal_id"],x["tcc_terminal_id"])
        self.assertEqual(x["ecv4_handoff"]["terminal_status"],"BLOCKED")
        self.assertTrue(any(e["event"]=="GATE_SELECTED" for e in x["ecv4_handoff"]["evidence"]))


if __name__=="__main__":
    unittest.main()
