from __future__ import annotations
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools.run_issue1_original_phase1_tcc_v10 import (
    ROOT,AC18,PROTOCOL,manifest,run,code_seals
)
from tools.issue1_phase1_ae_gate_v1 import verify,h,LAYERS,ARMS
from tools.run_issue57_tcc_generator_gate import TCC_SOURCE

TCC=Path("/private/tmp/llmec-tcc-generator-reference-20261009")
EC=Path("/private/tmp/issue1-ec-native-layerwise-20261010")

def setup_ae():
    cid="dev-smoke-not-independent"
    oracle={x:{"oracle":x} for x in LAYERS}
    raw={"protocol":"ISSUE1_PHASE1_AE_RAW_V1","fixture_commit":"f"*40,
         "materiality":.2,"cases":[]}
    gold={"protocol":"ISSUE1_PHASE1_GOLD_V1","fixture_commit":"f"*40,
          "materiality":.2,"cases":[{"case_id":cid,"oracle_layers":oracle,
                                    "label":True,"family":"development-only"}]}
    baseline={x:{"value":x} for x in LAYERS}
    inp="1"*64
    arms=[]
    for key in ARMS:
        layers=copy.deepcopy(baseline)
        if key.startswith("E_"):
            layers[key[2:]]=oracle[key[2:]]
        upstream={layer:inp if i==0 else h(layers[LAYERS[i-1]])
                  for i,layer in enumerate(LAYERS)}
        arms.append({"arm":key,"layers":layers,"upstream":upstream,
                     "implementation":"ORACLE_INTERVENTION" if key.startswith("E_") else
                         "NATIVE_EC" if key in ("B","D") else "LLM",
                     "input_sha256":inp,"final_success":key=="E_S3"})
    raw["cases"]=[{"case_id":cid,"input_sha256":inp,"arms":arms}]
    return raw,gold

class TCCV10Policy(unittest.TestCase):
    def test_original_mvp_exact_18(self):
        self.assertEqual(len(AC18),18)
        self.assertNotIn("AC-10",AC18)
        self.assertNotIn("AC-18",AC18)
    def test_compiled_graph_has_only_true_science_success(self):
        x=manifest()
        self.assertEqual(x["entry_nodes"],["freeze_original_source"])
        self.assertEqual([a["id"] for a in x["nodes"] if a["kind"]=="terminal"
                          and a["terminal_status"]=="SUCCESS"],["root_science_verified"])
        self.assertFalse("13" in x["tcc_id"])
    def test_positive_structural_ae_gain_not_scientific_pass(self):
        x=verify(*setup_ae())
        self.assertEqual(x["cases"],1)
        self.assertEqual(x["oracle_gains"]["S3"],1.)
        self.assertFalse(x["original_AC18_pass_automatically"])
    def test_duplicate_arm_fails(self):
        raw,gold=setup_ae()
        raw["cases"][0]["arms"][1]["arm"]="A"
        with self.assertRaisesRegex(ValueError,"G10_DUPLICATE_OR_UNKNOWN_ARM"):
            verify(raw,gold)
    def test_wrong_ec_identity_fails(self):
        raw,gold=setup_ae()
        raw["cases"][0]["arms"][1]["implementation"]="LLM"
        with self.assertRaisesRegex(ValueError,"G9_FALSE_ENGINE_ARM"):
            verify(raw,gold)
    def test_wrong_upstream_hash_fails(self):
        raw,gold=setup_ae()
        raw["cases"][0]["arms"][1]["upstream"]["S4"]="tamper"
        with self.assertRaisesRegex(ValueError,"G4_BROKEN_LAYER_HASH_CHAIN"):
            verify(raw,gold)
    def test_E_changes_preceding_layer_fails(self):
        raw,gold=setup_ae()
        raw["cases"][0]["arms"][7]["layers"]["S3"]={"changed":True}
        with self.assertRaisesRegex(ValueError,"G4_ORACLE_CHANGED_UPSTREAM"):
            verify(raw,gold)
    def test_fake_oracle_selection_fails(self):
        raw,gold=setup_ae()
        raw["cases"][0]["arms"][6]["layers"]["S3"]={"wrong":True}
        with self.assertRaisesRegex(ValueError,"G5_INTERVENTION_ORACLE_MISMATCH"):
            verify(raw,gold)
    def test_post_scoring_gold_change_fails(self):
        raw,gold=setup_ae()
        gold["fixture_commit"]="0"*40
        with self.assertRaisesRegex(ValueError,"G4_FIXTURE_COMMIT_MISMATCH"):
            verify(raw,gold)
    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"Pinned TCC/native checkouts absent")
    def test_real_v10_TCC_executes_native_blocker(self):
        x=run(TCC,EC)
        self.assertEqual(x["protocol"],PROTOCOL)
        self.assertEqual(x["TCC_terminal"],"blocked_native")
        self.assertEqual(x["original_root_pass"],2)
        self.assertEqual(x["original_root_required"],18)
        self.assertTrue(x["source_and_input_seals_stable"])
        self.assertFalse(x["original_science_complete"])
        self.assertEqual(x["errors"],[])
        self.assertEqual(x["work_state"]["successor"],
             "EXPERIMENTAL_TYPED_SOURCE_NOT_INDEPENDENT_SEMANTICS")
    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"Pinned TCC/native checkouts absent")
    def test_tampered_tracked_source_fails_closed(self):
        with patch("tools.run_issue1_original_phase1_tcc_v10.git_blob",return_value="0"*40):
            with self.assertRaisesRegex(ValueError,"G0_UNTRACKED_OR_CHANGED_SOURCE"):
                code_seals()
    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"Pinned TCC/native checkouts absent")
    def test_missing_half_ae_denied(self):
        with self.assertRaisesRegex(ValueError,"G6_HALF_PROVIDED_AE_EVIDENCE"):
            run(TCC,EC,Path("/tmp/missing-arm"))


    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"Pinned TCC/native checkouts absent")
    def test_actual_complete_AC20_work_dependency_ledger(self):
        result=run(TCC,EC)
        self.assertEqual(len(result["original_AC20_dependency_ledger"]),20)
        self.assertEqual(len(result["original_AC20_topological_order"]),20)
        self.assertEqual([k for k,v in result["original_AC20_dependency_ledger"].items()
                          if v["state"]=="PASS"],["AC-19","AC-20"])
        self.assertEqual(result["TCC_terminal"],"blocked_native")

    @unittest.skipUnless(TCC.is_dir() and EC.is_dir(),"Pinned TCC/native checkouts absent")
    def test_optional_complete_AE_raw_structural_branch_does_not_fake_root(self):
        raw,gold=setup_ae()
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/"arms.json";b=Path(td)/"gold.json"
            a.write_text(json.dumps(raw));b.write_text(json.dumps(gold))
            result=run(TCC,EC,a,b)
        self.assertEqual(result["raw_AE_structural_replay"]["cases"],1)
        self.assertEqual(result["raw_AE_structural_replay"]["oracle_gains"]["S3"],1.)
        self.assertFalse(result["raw_AE_structural_replay"]["native_source_independently_qualified"])
        self.assertEqual(result["original_root_pass"],2)
        self.assertEqual(result["TCC_terminal"],"blocked_native")


if __name__=="__main__":
    unittest.main()
