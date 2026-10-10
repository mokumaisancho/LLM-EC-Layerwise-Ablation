from __future__ import annotations
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools.run_issue1_root_ac_w4b_tcc_v8 import (
  PROTOCOL,ROOT,SOURCE_COMMIT,MODULE_BLOB,CONTRACT,
  public_case,sources_pin,researcher_source_seal,child_predict,measure,tcc_spec,run,digest
)
TCC=Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC=Path("/private/tmp/llmec-ecv44-source-20261010")
OLD=Path("/private/tmp/issue1-ec-w4a-frozen-20261010")
NEW=Path("/private/tmp/issue1-ec-native-layerwise-20261010")
READY=all(p.is_dir() for p in (TCC,EC,OLD,NEW))

@unittest.skipUnless(READY,"Pinned source checkouts missing")
class ACDrivenW4BWTCCv8(unittest.TestCase):
    def test_01_real_new_source_pinned(self):
        pins=sources_pin(NEW)
        self.assertEqual(pins["01_repo/src/v4/ec_layerwise_typed_evidence_authority_v1.py"],
                         MODULE_BLOB)
        self.assertEqual(SOURCE_COMMIT,"ae4b02bca34147d549abda85fad9cdc793ca054f")
    def test_02_research_execution_sources_exact_head(self):
        self.assertEqual(len(researcher_source_seal()),3)
    def test_03_no_hidden_scoring_in_typed_cases(self):
        for i in range(1,13):
            packet=public_case(i)
            text=json.dumps(packet)
            self.assertNotIn('"oracle"',text)
            self.assertNotIn('"gold"',text)
            self.assertNotIn('"fixture_id"',text)
            self.assertNotIn('"category"',text)
            self.assertEqual(packet["typed_document"]["source_sha256"],
                digest({k:v for k,v in packet["typed_document"].items() if k!="source_sha256"}))
    def test_04_native_negative_and_all_casewise_results(self):
        result=measure(NEW)
        self.assertEqual(result["native_source_tests_passed"],24)
        self.assertEqual(result["public_new_typed_cases"],12)
        self.assertEqual(result["formal_invariant_cases_passed"],12)
        self.assertEqual(result["S4_false_closure_preventions"],12)
        self.assertFalse(result["true_natural_language_semantic_adjudication"])
        self.assertFalse(result["independently_verified_complete_obligation_inventory"])
    def test_05_unknown_case_fact_must_abstain(self):
        packet=public_case(91)
        first=packet["public_s2"]["candidates"][0]["candidate_id"]
        packet["typed_document"]["candidate_requirements"][first]=["fact:absent_random"]
        base={k:v for k,v in packet["typed_document"].items() if k!="source_sha256"}
        packet["typed_document"]["source_sha256"]=digest(base)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"f.json";p.write_text(json.dumps(packet))
            with self.assertRaisesRegex(Exception,"FACT_NOT_PROVEN_ABSTAIN"):
                child_predict(NEW,p)
    def test_06_privileged_fields_child_denied(self):
        packet=public_case(3);packet["oracle"]={"expected":"CLOSE"}
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"f.json";p.write_text(json.dumps(packet))
            with self.assertRaisesRegex(Exception,"PRIVILEGED_CHILD_PACKET_FIELDS"):
                child_predict(NEW,p)
    def test_07_mismatched_model_source_raises(self):
        with patch("tools.run_issue1_root_ac_w4b_tcc_v8.git_head",return_value="0"*40):
            with self.assertRaisesRegex(ValueError,"W4B_NATIVE_GIT_COMMIT_MISMATCH"):
                sources_pin(NEW)
    def test_08_real_AC_dag_has_one_original_only_success(self):
        graph=tcc_spec()
        success=[n["id"] for n in graph["nodes"] if n["kind"]=="terminal" and
                 n["terminal_status"]=="SUCCESS"]
        self.assertEqual(success,["verified_original_science"])
        self.assertEqual(graph["entry_nodes"],["execute_root_original_v7"])
    def test_09_single_invocation_end_to_end_and_true_stop(self):
        result=run(TCC,EC,OLD,NEW)
        self.assertEqual(result["protocol"],PROTOCOL)
        self.assertEqual(result["TCC_terminal_id"],"blocked_external_semantics")
        self.assertEqual(result["original_AC_MVP18_pass_count"],2)
        self.assertEqual(result["original_AC_MVP18_total"],18)
        self.assertEqual(result["errors"],[])
        self.assertFalse(result["original_root_completed"])
        self.assertTrue(result["evidence_pre_post_equal"])
        self.assertTrue(result["native_source_pre_post_equal"])
        self.assertTrue(result["research_code_pre_post_equal"])
        self.assertTrue(result["preregistered_contract_pre_post_equal"])
    def test_10_forged_root_v7_completion_blocked(self):
        false_v7={"TCC_terminal":"root_science_verified"}
        with patch("tools.run_issue1_root_ac_w4b_tcc_v8.run_v7",return_value=false_v7):
            x=run(TCC,EC,OLD,NEW)
        self.assertEqual(x["TCC_terminal_id"],"blocked_integrity")
        self.assertFalse(x["original_root_completed"])
    def test_11_forged_typed_results_blocked(self):
        wrong={"native_source_tests_passed":24,"formal_invariant_cases_passed":12,
               "S4_false_closure_preventions":0,"undeclared_requirement_abstention_verified":True}
        with patch("tools.run_issue1_root_ac_w4b_tcc_v8.measure",return_value=wrong):
            x=run(TCC,EC,OLD,NEW)
        self.assertEqual(x["TCC_terminal_id"],"blocked_integrity")
        self.assertFalse(x["original_root_completed"])
    def test_12_no_schedule_and_no_ui_reentrant_send(self):
        text=(ROOT/"tools/run_issue1_root_ac_w4b_tcc_v8.py").read_text()
        for item in ("automations.create(","launchctl","crontab","chatgpt.com/","openai.com/v1/responses"):
            self.assertNotIn(item,text)

if __name__=="__main__":unittest.main()
