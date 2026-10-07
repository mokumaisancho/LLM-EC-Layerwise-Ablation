from __future__ import annotations
import copy
import unittest
from semantic_runtime import RuntimeContractError, discover_and_ground
from semantic_runtime.execution_v2 import execute_validated_ir
from tests.test_semantic_runtime_product import make_task, make_solver


class TrustBoundaryV2(unittest.TestCase):
    def setUp(self):
        self.task=make_task()
        self.ir=discover_and_ground(self.task)
        self.contract=make_solver()

    def execute(self, ir=None, task=None, solver=None):
        return execute_validated_ir(self.ir if ir is None else ir,
                                    self.task if task is None else task,
                                    self.contract if solver is None else solver)

    def rejects(self, label, target, mutator):
        x=copy.deepcopy(target)
        mutator(x)
        with self.assertRaises(RuntimeContractError, msg=label):
            if label.startswith("IR_"):self.execute(ir=x)
            elif label.startswith("TASK_"):self.execute(task=x)
            else:self.execute(solver=x)

    def test_01_positive(self):
        out=self.execute()
        self.assertTrue(out["result"]["applicable"])
        self.assertEqual(out["protocol"],"SEMANTIC_RUNTIME_EXECUTION_V2")

    def test_02_forged_slot(self):
        self.rejects("IR_SLOT",self.ir,lambda x:x["heldout_assignments"][0].__setitem__("slot_id",x["heldout_assignments"][1]["slot_id"]))

    def test_03_forged_argument(self):
        self.rejects("IR_ARG",self.ir,lambda x:x["heldout_assignments"][0].__setitem__("arguments",["INJECTED"]))

    def test_04_forged_eval(self):
        def mutate(x):
            p=x["discovered_slots"][0]["evaluation_probe_predictions"][0]
            p["predicted_after"][0]=1-p["predicted_after"][0]
        self.rejects("IR_EVAL",self.ir,mutate)

    def test_05_forged_modality(self):
        self.rejects("IR_MODALITY",self.ir,lambda x:x["heldout_assignments"][0].__setitem__("modality","POSSIBLE"))

    def test_06_forged_valid_protocol(self):
        self.rejects("IR_MEMBERSHIP",self.ir,lambda x:x["discovered_slots"][1].__setitem__("training_members",x["discovered_slots"][0]["training_members"]))

    def test_07_changed_visible(self):
        self.rejects("TASK_CHANGED",self.task,lambda x:x["visible"]["training_examples"][0].__setitem__("raw_text","Different completely unrelated text"))

    def test_08_unknown_solver_field(self):
        self.rejects("SOLVER_EXTRA",self.contract,lambda x:x.__setitem__("oracle","fake"))

    def test_09_unbound_variable(self):
        self.rejects("SOLVER_UNBOUND",self.contract,lambda x:x["operator_schema"]["preconditions"][0]["args"].__setitem__(0,"$UNBOUND"))

    def test_10_binding_collision(self):
        self.rejects("SOLVER_COLLISION",self.contract,lambda x:x["static_binding"].__setitem__("$X","WRONG"))

    def test_11_binding_index(self):
        self.rejects("SOLVER_INDEX",self.contract,lambda x:x["parameter_from_arguments"].__setitem__("$X",10))

    def test_12_ambiguous(self):
        self.rejects("SOLVER_ABSTAIN",self.contract,lambda x:x.__setitem__("assignment_example_id","H03"))

    def test_13_determinism(self):
        self.assertEqual(self.execute(),self.execute())

    def test_14_state_shape(self):
        self.rejects("SOLVER_STATE",self.contract,lambda x:x["before"].append({"pred":"UNEXPECTED"}))


if __name__=="__main__":
    unittest.main()
