from __future__ import annotations
import copy
import unittest
from unittest.mock import patch
from semantic_runtime import RuntimeContractError, discover_and_ground
from semantic_runtime.execution_v3 import execute_authorized_ir, _digest
from tests.test_semantic_runtime_product import make_task, make_solver

class OperatorPolicyV3Tests(unittest.TestCase):
    def setUp(self):
        self.task=make_task()
        self.solver=make_solver()
        self.ir=discover_and_ground(self.task)
        self.allowed={"protocol":"SEMANTIC_RUNTIME_APPROVED_POLICY_V3","approvals":[
            {"policy_id":"approved_fixture","task_sha256":_digest(self.task),"solver_sha256":_digest(self.solver)}
        ]}
    def run_gate(self,task=None,solver=None,ir=None,policy_id="approved_fixture"):
        return execute_authorized_ir(self.ir if ir is None else ir,
                                    self.task if task is None else task,
                                    self.solver if solver is None else solver,policy_id)
    def test_01_default_deny(self):
        with self.assertRaisesRegex(RuntimeContractError,"POLICY_NOT_APPROVED"):
            self.run_gate()
    def test_02_approved_pair(self):
        with patch("semantic_runtime.execution_v3._trusted_policy",return_value=self.allowed):
            out=self.run_gate()
        self.assertEqual(out["protocol"],"SEMANTIC_RUNTIME_EXECUTION_V3")
        self.assertTrue(out["execution"]["result"]["applicable"])
    def test_03_unapproved_policy_id(self):
        with patch("semantic_runtime.execution_v3._trusted_policy",return_value=self.allowed):
            with self.assertRaisesRegex(RuntimeContractError,"POLICY_NOT_APPROVED"):
                self.run_gate(policy_id="other")
    def test_04_task_modified(self):
        task=copy.deepcopy(self.task);task["visible"]["heldout_examples"][0]["raw_text"]="approved? no"
        with patch("semantic_runtime.execution_v3._trusted_policy",return_value=self.allowed):
            with self.assertRaisesRegex(RuntimeContractError,"TASK_NOT_APPROVED"):
                self.run_gate(task=task)
    def test_05_solver_modified(self):
        sol=copy.deepcopy(self.solver);sol["operator_schema"]["add_effects"][0]["pred"]="DESTRUCTIVE"
        with patch("semantic_runtime.execution_v3._trusted_policy",return_value=self.allowed):
            with self.assertRaisesRegex(RuntimeContractError,"SOLVER_NOT_APPROVED"):
                self.run_gate(solver=sol)
    def test_06_forged_ir(self):
        ir=copy.deepcopy(self.ir);ir["heldout_assignments"][0]["arguments"]=["BAD"]
        with patch("semantic_runtime.execution_v3._trusted_policy",return_value=self.allowed):
            with self.assertRaises(RuntimeContractError):
                self.run_gate(ir=ir)
    def test_07_exact_repeat(self):
        with patch("semantic_runtime.execution_v3._trusted_policy",return_value=self.allowed):
            self.assertEqual(self.run_gate(),self.run_gate())

if __name__=="__main__":unittest.main()
