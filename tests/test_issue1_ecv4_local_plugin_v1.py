"""Research-local EC plugin tests: real pinned native S3/S4, no engine fork."""
import copy
import importlib.util
import unittest
from pathlib import Path

from tools.issue1_ecv4_local_plugin_v1 import (
    COMMIT, evaluate, check_source, file_blob,
)

EC_ROOT=Path("/private/tmp/issue59-60-policy-v2")
NATIVE_FIXTURES=EC_ROOT/"01_repo/tests/test_ec_layerwise_source_policy_authority_v2.py"

def fixture(relation="COMPETING"):
    spec=importlib.util.spec_from_file_location("ec_plugin_fixture",NATIVE_FIXTURES)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj.fixtures(relation)

@unittest.skipUnless(EC_ROOT.is_dir() and NATIVE_FIXTURES.is_file(),
                     "EC repo source unavailable, no external science claim")
class ECPluginIntegrationTests(unittest.TestCase):
    def test_native_plugin_full_competing_set_and_continuation(self):
        policy,task,s2,sha=fixture()
        d=evaluate(EC_ROOT,s2,task,policy,sha,
                   {"reframe_required":False,"reframe_resolved":False})
        self.assertEqual(d["s3_selected"],["A","B"])
        self.assertEqual(d["s3_rejected"],["X"])
        self.assertEqual(d["s4_diagnostic"],"CONTINUE")
        self.assertTrue(d["finite_scope_plugin_works"])
        self.assertFalse(d["original_MVP_AC_pass_from_plugin"])

    def test_native_plugin_equivalent_set_can_formally_close(self):
        policy,task,s2,sha=fixture("EQUIVALENT")
        d=evaluate(EC_ROOT,s2,task,policy,sha,
                   {"reframe_required":False,"reframe_resolved":False})
        self.assertEqual(d["s3_selected"],["A","B"])
        self.assertEqual(d["s4_diagnostic"],"CLOSE")
        self.assertFalse(d["real_world_close_authorized"])

    def test_real_unresolved_obligation_stops_formal_closure(self):
        policy,task,s2,_=fixture("EQUIVALENT")
        task["facts"]["approval_required"]=True
        spec=importlib.util.spec_from_file_location("ec_plugin_policy",
            EC_ROOT/"01_repo/src/v4/ec_layerwise_source_policy_authority_v2.py")
        lib=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lib)
        s2["semantic_ir_hash"]=lib.digest(task)
        d=evaluate(EC_ROOT,s2,task,policy,lib.digest(policy),
                   {"reframe_required":False,"reframe_resolved":False})
        self.assertEqual(d["s4_diagnostic"],"CONTINUE")
        self.assertEqual(d["s4_unresolved"],["approval"])

    def test_policy_tamper_without_repin_rejected(self):
        policy,task,s2,sha=fixture("EQUIVALENT")
        policy["obligation_rules"].pop("approval")
        with self.assertRaisesRegex(ValueError,"PINNED_POLICY_SOURCE_MISMATCH"):
            evaluate(EC_ROOT,s2,task,policy,sha,
                     {"reframe_required":False,"reframe_resolved":False})

    def test_oracle_field_is_rejected(self):
        policy,task,s2,sha=fixture()
        task["gold"]={"selected":["A"]}
        with self.assertRaisesRegex(ValueError,"PRIVATE_OR_SCORER_FIELD"):
            evaluate(EC_ROOT,s2,task,policy,sha,
                     {"reframe_required":False,"reframe_resolved":False})

    def test_ec_version_pinned_dont_import_from_fork(self):
        self.assertEqual(COMMIT,
            "3f435ad4365d846d96264458540efb4848ce3541")
        check_source(EC_ROOT)
        self.assertEqual(file_blob(EC_ROOT/
            "01_repo/src/v4/ec_layerwise_source_policy_authority_v2.py"),
            "7da0cd8d876505cafdd5a9811132427e2f441a14")

if __name__=="__main__": unittest.main()
