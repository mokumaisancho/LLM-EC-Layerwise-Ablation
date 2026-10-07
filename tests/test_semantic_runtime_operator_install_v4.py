from __future__ import annotations

import copy
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from tests.test_semantic_runtime_product import make_task, make_solver
from semantic_runtime import discover_and_ground


class RealInstalledPolicyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="owned-policy-v4-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.bundle=self.root/"semantic_runtime"
        shutil.copytree(ROOT/"semantic_runtime",self.bundle)
        self.task=make_task()
        self.solver=make_solver()
        self.ir=discover_and_ground(self.task)
        self.write("task",self.task)
        self.write("solver",self.solver)
        self.write("ir",self.ir)

    def write(self,name,data):
        (self.root/(name+".json")).write_text(json.dumps(data),encoding="utf-8")

    def execute(self,policy_id="only_this_pair"):
        code="""
import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from semantic_runtime.execution_v4 import execute_authorized_ir
from semantic_runtime.runtime import RuntimeContractError
root=Path(sys.argv[1])
try:
    data=[json.loads((root/(name+'.json')).read_text()) for name in ('ir','task','solver')]
    x=execute_authorized_ir(*data,sys.argv[2])
    print(json.dumps(x,sort_keys=True))
except (RuntimeContractError,OSError,ValueError,KeyError,TypeError) as exc:
    print(json.dumps({'terminal':'FAIL_CLOSED','reason':str(exc)}))
    sys.exit(3)
"""
        return subprocess.run([sys.executable,"-c",code,str(self.root),policy_id],
                              cwd=self.root,capture_output=True,text=True)

    def install(self):
        cmd=[sys.executable,str(ROOT/"tools"/"install_semantic_runtime_policy_v4.py"),
             "--bundle-dir",str(self.bundle),"--policy-id","only_this_pair",
             "--task",str(self.root/"task.json"),"--solver",str(self.root/"solver.json")]
        return subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)

    def test_01_default_deny_real_installed_file(self):
        bad=self.execute()
        self.assertEqual(bad.returncode,3,bad.stdout+bad.stderr)
        self.assertIn("POLICY_NOT_APPROVED",bad.stdout)

    def test_02_real_nonmock_install_and_execute(self):
        installed=self.install()
        self.assertEqual(installed.returncode,0,installed.stdout+installed.stderr)
        policy=json.loads((self.bundle/"approved_policy_v3.json").read_text())
        self.assertEqual(len(policy["approvals"]),1)
        self.assertEqual(stat.S_IMODE((self.bundle/"approved_policy_v3.json").stat().st_mode),0o600)
        result=self.execute()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue(json.loads(result.stdout)["execution"]["result"]["applicable"])

    def test_03_task_tamper_block(self):
        self.assertEqual(self.install().returncode,0)
        t=copy.deepcopy(self.task)
        t["visible"]["heldout_examples"][0]["raw_text"]="Different action"
        self.write("task",t)
        bad=self.execute()
        self.assertEqual(bad.returncode,3)
        self.assertIn("TASK_NOT_APPROVED",bad.stdout)

    def test_04_solver_tamper_block(self):
        self.assertEqual(self.install().returncode,0)
        t=copy.deepcopy(self.solver)
        t["operator_schema"]["add_effects"][0]["pred"]="UNAPPROVED"
        self.write("solver",t)
        bad=self.execute()
        self.assertEqual(bad.returncode,3)
        self.assertIn("SOLVER_NOT_APPROVED",bad.stdout)

    def test_05_ir_tamper_block(self):
        self.assertEqual(self.install().returncode,0)
        ir=copy.deepcopy(self.ir)
        ir["heldout_assignments"][0]["slot_id"]=ir["heldout_assignments"][1]["slot_id"]
        self.write("ir",ir)
        bad=self.execute()
        self.assertEqual(bad.returncode,3)

    def test_06_unapproved_policy_id_block(self):
        self.assertEqual(self.install().returncode,0)
        bad=self.execute("any_other_id")
        self.assertEqual(bad.returncode,3)
        self.assertIn("POLICY_NOT_APPROVED",bad.stdout)

    def test_07_policy_symlink_block(self):
        self.assertEqual(self.install().returncode,0)
        manifest=self.bundle/"approved_policy_v3.json"
        copy=self.root/"target.json"
        copy.write_bytes(manifest.read_bytes())
        manifest.unlink()
        manifest.symlink_to(copy)
        bad=self.execute()
        self.assertEqual(bad.returncode,3)
        self.assertIn("TRUSTED_POLICY_OPEN_OR_PARSE_FAILED",bad.stdout)

    def test_08_policy_permissions_block(self):
        self.assertEqual(self.install().returncode,0)
        file=self.bundle/"approved_policy_v3.json"
        file.chmod(0o666)
        bad=self.execute()
        self.assertEqual(bad.returncode,3)
        self.assertIn("TRUSTED_POLICY_GROUP_OR_WORLD_WRITABLE",bad.stdout)

    def test_09_directory_permissions_block(self):
        self.assertEqual(self.install().returncode,0)
        self.bundle.chmod(0o777)
        bad=self.execute()
        self.assertEqual(bad.returncode,3)
        self.assertIn("POLICY_DIRECTORY_GROUP_OR_WORLD_WRITABLE",bad.stdout)

    def test_10_overwrite_requires_explicit_separate_release(self):
        self.assertEqual(self.install().returncode,0)
        overwrite=self.install()
        self.assertEqual(overwrite.returncode,3)
        self.assertIn("BUNDLE_MUST_BE_DEFAULT_DENY_BEFORE_INSTALL",overwrite.stderr)

    def test_11_local_cli_byte_stability(self):
        self.assertEqual(self.install().returncode,0)
        a=self.execute()
        b=self.execute()
        self.assertEqual(a.returncode,0)
        self.assertEqual(a.stdout,b.stdout)

if __name__=="__main__":
    unittest.main()
