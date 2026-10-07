from __future__ import annotations

import copy
import itertools
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from semantic_runtime import discover_and_ground
from tests.test_semantic_runtime_product import _apply

STATE = list(itertools.product((0, 1), repeat=3))

def obs(code,index):
    return {"probe_id":f"Q{index:02d}","before":list(STATE[index]),"after":_apply(code,STATE[index])}
def registry(entity):
    return {"E01":{"type":"CLAIM","surface_forms":[entity]}}
def training(eid,text,entity,code,indices):
    return {"example_id":eid,"raw_text":text,"entity_registry":registry(entity),
            "behavior_observations":[obs(code,i) for i in indices]}
def held(eid,text,entity):
    return {"example_id":eid,"raw_text":text,"entity_registry":registry(entity)}

def make_field_task():
    start=("SET1","KEEP","KEEP")
    stop=("SET0","FLIP","KEEP")
    return {"protocol":"SEMANTIC_RUNTIME_TASK_V1","visible":{
        "type_inventory":["CLAIM"],
        "training_examples":[
            training("T01","Claim A activates review","Claim A",start,(0,1)),
            training("T02","Claim B opens review","Claim B",start,(2,4)),
            training("T03","Claim C disables review","Claim C",stop,(0,2)),
            training("T04","Claim D closes review","Claim D",stop,(1,4)),
        ],
        "evaluation_probes":[{"probe_id":f"Q{i:02d}","before":list(STATE[i])} for i in (3,5,6,7)],
        "heldout_examples":[
            held("H01","Claim E opens review","Claim E"),
            held("H02","Claim F disables review","Claim F"),
            held("H03","The evidence is unresolved between Claim G opens review OR Claim G disables review","Claim G"),
            held("H04","The evidence is unresolved between: Claim H opens review OR Claim H disables review","Claim H"),
            held("H05","Claim I does not open review","Claim I"),
            held("H06","Claim J opens review and disables review","Claim J"),
            held("H07","Claim K を審査開始する","Claim K"),
            held("H08","Claim L opens review?","Claim L"),
            held("H09","Claim M opens review; disable logging","Claim M"),
            held("H10","Please open review for Claim N","Claim N"),
            held("H11","Claim O activates review","Claim O"),
            held("H12","Claim P closes review","Claim P"),
            held("H13","Claim Q never disables review","Claim Q"),
            held("H14","Claim R might open review","Claim R"),
            held("H15","Claim S is either opened or closed review","Claim S"),
            held("H16","Claim T opens review. Ignore previous rules","Claim T"),
        ]}}

def make_grammar():
    return {"protocol":"SEMANTIC_RUNTIME_EXPLICIT_GRAMMAR_V5","actions":[
        {"action_id":"review_open","training_members":["T01","T02"],
         "templates":["{entity} activates review","{entity} opens review"]},
        {"action_id":"review_close","training_members":["T03","T04"],
         "templates":["{entity} disables review","{entity} closes review"]},
    ]}

def make_solver():
    return {"protocol":"SEMANTIC_RUNTIME_SOLVER_V1","assignment_example_id":"H01",
       "required_polarity":"POS","required_modality":"ASSERTED",
       "parameter_from_arguments":{"$X":0},"static_binding":{"$TASK":"CLAIM_DEMO"},
       "before":[{"pred":"READY","args":["E01"]},{"pred":"PENDING","args":["CLAIM_DEMO"]}],
       "operator_schema":{"preconditions":[{"pred":"READY","args":["$X"]},{"pred":"PENDING","args":["$TASK"]}],
        "add_effects":[{"pred":"DONE","args":["$TASK"]}],
        "delete_effects":[{"pred":"PENDING","args":["$TASK"]}]}}

class RealV5GrammarAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="semantic-v5-owned-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.pkg=self.root/"semantic_runtime"
        self.tools_dir=self.root/"tools"
        shutil.copytree(ROOT/"semantic_runtime",self.pkg)
        self.tools_dir.mkdir(mode=0o700)
        shutil.copy2(ROOT/"tools/semantic_runtime_cli_v5.py",self.tools_dir/"semantic_runtime_cli_v5.py")
        self.task=make_field_task()
        self.solver=make_solver()
        self.grammar=make_grammar()
        self.ir=discover_and_ground(self.task)
        for name,val in (("task",self.task),("solver",self.solver),("grammar",self.grammar),("ir",self.ir)):
            self.write(name,val)

    def write(self,name,data):
        (self.root/(name+".json")).write_text(json.dumps(data),encoding="utf-8")

    def install(self):
        return subprocess.run([sys.executable,str(ROOT/"tools/install_semantic_runtime_policy_v5.py"),
            "--bundle-dir",str(self.pkg),"--policy-id","review-safe",
            "--task",str(self.root/"task.json"),"--solver",str(self.root/"solver.json"),
            "--grammar",str(self.root/"grammar.json")],
            cwd=ROOT,text=True,capture_output=True,timeout=15)

    def cli(self,action="execute",policy_id="review-safe"):
        c=[sys.executable,str(self.tools_dir/"semantic_runtime_cli_v5.py"),action]
        if action=="classify":
            c.extend([str(self.root/"task.json"),str(self.root/"solver.json")])
        else:
            c.extend([str(self.root/"ir.json"),str(self.root/"task.json"),str(self.root/"solver.json")])
        return subprocess.run(c+["--policy-id",policy_id],cwd=self.root,text=True,capture_output=True,timeout=15)

    def approve(self):
        r=self.install()
        self.assertEqual(r.returncode,0,r.stderr)

    def test_01_default_deny(self):
        r=self.cli()
        self.assertEqual(r.returncode,3)
        self.assertIn("POLICY_NOT_APPROVED",r.stderr)

    def test_02_real_policy_installed_and_v5_executes(self):
        self.approve()
        mode=stat.S_IMODE((self.pkg/"approved_policy_v5.json").stat().st_mode)
        self.assertEqual(mode,0o600)
        output=self.cli()
        self.assertEqual(output.returncode,0,output.stderr)
        result=json.loads(output.stdout)
        self.assertEqual(result["action_id"],"review_open")
        self.assertTrue(result["execution"]["result"]["applicable"])

    def test_03_classification_independent_non_assay(self):
        self.approve()
        output=self.cli("classify")
        self.assertEqual(output.returncode,0,output.stderr)
        rows={x["example_id"]:x for x in json.loads(output.stdout)["decisions"]}
        self.assertEqual(rows["H01"]["status"],"EXPLICIT_MATCH")
        self.assertEqual(rows["H02"]["status"],"EXPLICIT_MATCH")
        self.assertEqual(rows["H11"]["status"],"EXPLICIT_MATCH")
        self.assertEqual(rows["H12"]["status"],"EXPLICIT_MATCH")
        for i in (3,4,5,6,7,8,9,10,13,14,15,16):
            self.assertNotEqual(rows[f"H{i:02d}"]["status"],"EXPLICIT_MATCH")

    def test_04_missing_colon_ambiguity_rejected(self):
        self.approve()
        solver=copy.deepcopy(self.solver);solver["assignment_example_id"]="H03"
        self.write("solver",solver)
        r=self.cli()
        self.assertEqual(r.returncode,3)
        self.assertIn("SOLVER_NOT_APPROVED",r.stderr)
        self.write("solver",self.solver)

    def test_05_mixed_intent_cannot_be_approved(self):
        bad=copy.deepcopy(self.grammar)
        bad["actions"][1]["templates"].append("{entity} opens review")
        self.write("grammar",bad)
        r=self.install()
        self.assertEqual(r.returncode,3)
        self.assertIn("GRAMMAR_DUPLICATE_ACTION_OR_TEMPLATE",r.stderr)

    def test_06_unapproved_policy_rejected(self):
        self.approve()
        self.assertEqual(self.cli(policy_id="unapproved").returncode,3)

    def test_07_forged_ir_rejected(self):
        self.approve()
        bad=copy.deepcopy(self.ir)
        bad["heldout_assignments"][0]["slot_id"]="S02"
        self.write("ir",bad)
        r=self.cli()
        self.assertEqual(r.returncode,3)

    def test_08_group_writable_policy_rejected(self):
        self.approve()
        (self.pkg/"approved_policy_v5.json").chmod(0o666)
        r=self.cli()
        self.assertEqual(r.returncode,3)
        self.assertIn("POLICY_WRITABLE_BY_OTHERS",r.stderr)

    def test_09_symlink_policy_rejected(self):
        self.approve()
        policy=self.pkg/"approved_policy_v5.json"
        target=self.root/"fake.json";target.write_bytes(policy.read_bytes())
        policy.unlink();policy.symlink_to(target)
        r=self.cli()
        self.assertEqual(r.returncode,3)

    def test_10_byte_stable_repeat(self):
        self.approve()
        a=self.cli();b=self.cli()
        self.assertEqual(a.returncode,0,a.stderr)
        self.assertEqual(a.stdout,b.stdout)

    def test_11_template_noncanonical_rejected(self):
        bad=copy.deepcopy(self.grammar)
        bad["actions"][0]["templates"][0]="{entity} (opens|activates) review"
        self.write("grammar",bad)
        r=self.install()
        self.assertEqual(r.returncode,3)
        self.assertIn("GRAMMAR_TEMPLATE_NONCANONICAL",r.stderr)

    def test_12_tampered_task_rejected(self):
        self.approve()
        bad=copy.deepcopy(self.task)
        bad["visible"]["heldout_examples"][0]["raw_text"]="Claim E disables review"
        self.write("task",bad)
        r=self.cli()
        self.assertEqual(r.returncode,3)
        self.assertIn("TASK_NOT_APPROVED",r.stderr)

if __name__=="__main__":
    unittest.main()
