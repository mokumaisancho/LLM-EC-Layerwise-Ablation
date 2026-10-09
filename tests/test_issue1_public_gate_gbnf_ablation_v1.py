from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.run_issue1_public_gate_gbnf_ablation_v1 import (
    CONTRACT,FIXTURE,ROOT,PROTOCOL,
    ROOT_ORIGINAL,ROOT_RESTRICTED,gate_active,treatment_grammar,
    load_historical,blob
)
from tools.replay_issue1_ecv44_native_next_action_v2 import public_fields


class PublicGateGrammarSingleFactorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads(CONTRACT.read_text())
        cls.cases=json.loads(FIXTURE.read_text())["fixtures"]
        cls.archived=load_historical()

    def test_01_pre_registered_before_model_qualification(self):
        self.assertEqual(self.contract["protocol"],PROTOCOL)
        self.assertEqual(self.contract["status"],"FROZEN_BEFORE_PREDICTIONS")
        self.assertEqual(self.contract["case_count"],17)
        self.assertTrue(self.contract["frozen_analysis"]["no_independence_claim"])
        self.assertTrue(self.contract["frozen_analysis"]["no_original_A_E_claim"])

    def test_02_exact_original_fixture_and_historical_grammar_source(self):
        self.assertEqual(blob(FIXTURE),self.contract["fixture_git_blob"])
        orig=ROOT/"verification/issue1_next_action_v2/archived_original_runner_2026_10_03.py"
        self.assertEqual(blob(orig),self.contract["archived_historical_runner_git_blob"])

    def test_03_exact_16_inactive_one_active_visibility(self):
        counts=[gate_active(public_fields(row)) for row in self.cases]
        self.assertEqual(counts.count(False),16)
        self.assertEqual(counts.count(True),1)
        self.assertTrue(counts[-1])

    def test_04_single_only_root_grammar_replacement(self):
        for row in self.cases:
            visible=public_fields(row)
            work=[w if isinstance(w,str) else w["work_id"]
                  for issue in row["plan"]["issues"] for w in issue.get("work",[])]
            original=self.archived.grammar_for(work)
            modified,active=treatment_grammar(original,visible)
            self.assertEqual(modified,original if active else original.replace(
                ROOT_ORIGINAL,ROOT_RESTRICTED,1))
            self.assertEqual(modified.count("root ::= "),1)
            self.assertEqual(modified.splitlines()[1:],original.splitlines()[1:])

    def test_05_forbidden_gold_or_category_in_gate_input_rejected(self):
        state=public_fields(self.cases[0])
        for field in ("oracle","id","category","known_answer"):
            tampered=dict(state)
            tampered[field]="REFRAME"
            with self.assertRaisesRegex(ValueError,"PRIVILEGED_GATE_FIELDS_FORBIDDEN"):
                gate_active(tampered)

    def test_06_case_id_changes_do_not_change_public_gate(self):
        for row in self.cases:
            state=public_fields(row)
            self.assertEqual(gate_active(state),gate_active(copy.deepcopy(state)))

    def test_07_unknown_policy_never_adds_ref_branch(self):
        original=self.archived.grammar_for(["work:I20:repair"])
        treatment,active=treatment_grammar(original,public_fields(self.cases[0]))
        self.assertFalse(active)
        self.assertNotIn("reframe",treatment.splitlines()[0])

    def test_08_real_public_issue_contract_keeps_reframe(self):
        original=self.archived.grammar_for(["work:I20:repair"])
        treatment,active=treatment_grammar(original,public_fields(self.cases[-1]))
        self.assertTrue(active)
        self.assertEqual(treatment,original)
        self.assertIn("reframe",treatment.splitlines()[0])

    def test_09_gate_corruption_from_nonoriginal_grammar_rejected(self):
        with self.assertRaisesRegex(ValueError,"HISTORICAL_GBNF_ROOT_CHANGED"):
            treatment_grammar("root ::= xyz\n",public_fields(self.cases[0]))

    def test_10_historical_gold_label_not_read_in_public_condition(self):
        source=(ROOT/"tools/run_issue1_public_gate_gbnf_ablation_v1.py").read_text()
        start=source.index("def gate_active(")
        end=source.index("\ndef treatment_grammar",start)
        function=source[start:end]
        self.assertNotIn('["oracle"]',function)
        self.assertNotIn('["gold"]',function)
        self.assertNotIn('["reference_label"]',function)
        self.assertNotIn("category",function.lower())

    def test_11_frozen_public_status_hypothesis_is_not_retroactive(self):
        self.assertEqual(self.contract["preregistered_intervention"]["gate_inactive_root"],ROOT_RESTRICTED)
        self.assertEqual(self.contract["preregistered_intervention"]["gate_active_root"],ROOT_ORIGINAL)
        self.assertEqual(self.contract["frozen_analysis"]["materiality_threshold"],0.2)

    def test_12_no_automatic_submission_to_chat_or_tasks(self):
        source=(ROOT/"tools/run_issue1_public_gate_gbnf_ablation_v1.py").read_text()
        for forbidden in ("automations.create(","chatgpt.com/","openai.com/v1/responses","crontab","launchctl"):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
