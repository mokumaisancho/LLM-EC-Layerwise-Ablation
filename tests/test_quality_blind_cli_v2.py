from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.test_quality_blind_v2 import fixture, SALT

ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/"tools/blind_quality_protocol_v2.py"

class BlindQualityCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="blind-eval-v2-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        p,g,arms,seal=fixture()
        self.inputs=(p,g,arms,seal)
        for filename,content in (("public",p),("private_gold",g)):
            (self.root/(filename+".json")).write_text(json.dumps(content),encoding="utf-8")
        for name,obj in arms.items():
            (self.root/(name+".json")).write_text(json.dumps(obj),encoding="utf-8")

    def run_cmd(self,*args,secret=True):
        env=os.environ.copy()
        if secret:env["CAPABILITY_GOLD_SECRET_SALT"]=SALT
        else:env.pop("CAPABILITY_GOLD_SECRET_SALT",None)
        return subprocess.run([sys.executable,str(CLI),*args],cwd=ROOT,
                              env=env,text=True,capture_output=True,timeout=20)

    def arm_args(self):
        a=[]
        for name in ("LLM0","V1","V4","V5"):
            a.extend(["--"+name.lower(),str(self.root/(name+".json"))])
        return a

    def test_01_three_phase_custodian_operator_scorer(self):
        public=str(self.root/"public.json")
        private=str(self.root/"private_gold.json")
        c=self.run_cmd("prepare","--public",public,"--gold",private)
        self.assertEqual(c.returncode,0,c.stderr)
        self.assertNotIn("gold_action",c.stdout)
        precommit=self.root/"precommit.json"
        precommit.write_text(c.stdout,encoding="utf-8")
        f=self.run_cmd("freeze","--public",public,
            "--precommit",str(precommit),*self.arm_args(),secret=False)
        self.assertEqual(f.returncode,0,f.stderr)
        self.assertNotIn("private_gold",f.stdout)
        self.assertNotIn("gold_action",f.stdout)
        sealed=self.root/"sealed.json";sealed.write_text(f.stdout,encoding="utf-8")
        s=self.run_cmd("score","--public",public,"--gold",private,
            "--seal",str(sealed),*self.arm_args())
        self.assertEqual(s.returncode,0,s.stderr)
        report=json.loads(s.stdout)
        self.assertEqual(report["arm_metrics"]["V1"]["correct"],4)
        self.assertFalse(report["quality_preservation_certified"])

    def test_02_private_gold_unavailable_to_freeze_process(self):
        public=str(self.root/"public.json")
        gold=str(self.root/"private_gold.json")
        pre=self.run_cmd("prepare","--public",public,"--gold",gold)
        self.assertEqual(pre.returncode,0,pre.stderr)
        (self.root/"precommit.json").write_text(pre.stdout)
        (self.root/"private_gold.json").unlink()
        freeze=self.run_cmd("freeze","--public",public,
            "--precommit",str(self.root/"precommit.json"),*self.arm_args(),secret=False)
        self.assertEqual(freeze.returncode,0,freeze.stderr)

    def test_03_custodian_requires_secret(self):
        pre=self.run_cmd("prepare","--public",str(self.root/"public.json"),
              "--gold",str(self.root/"private_gold.json"),secret=False)
        self.assertEqual(pre.returncode,3)
        self.assertIn("HIGH_ENTROPY_SALT_REQUIRED",pre.stderr)

    def test_04_freeze_rejects_wrong_public_hash(self):
        pre=self.run_cmd("prepare","--public",str(self.root/"public.json"),
            "--gold",str(self.root/"private_gold.json"))
        a=json.loads(pre.stdout);a["public_sha256"]="0"*64
        (self.root/"precommit.json").write_text(json.dumps(a))
        freeze=self.run_cmd("freeze","--public",str(self.root/"public.json"),
            "--precommit",str(self.root/"precommit.json"),*self.arm_args(),secret=False)
        self.assertEqual(freeze.returncode,3)
        self.assertIn("PRECOMMIT_PUBLIC_IDENTITY_INVALID",freeze.stderr)


    def test_05_duplicate_object_member_rejected_before_commitment(self):
        public=self.root/"public.json"
        original=public.read_text(encoding="utf-8")
        self.assertIn('"protocol":',original)
        public.write_text(original.replace('"protocol":','"protocol":"spoofed","protocol":',1),encoding="utf-8")
        result=self.run_cmd("prepare","--public",str(public),
                            "--gold",str(self.root/"private_gold.json"))
        self.assertEqual(result.returncode,3)
        self.assertIn("DUPLICATE_JSON_KEY",result.stderr)

if __name__=="__main__":
    unittest.main()
