import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SRC = Path(__file__).parent.parent / 'tools/issue1_independent_formal_policy_equivalence.py'
spec = importlib.util.spec_from_file_location('p_eq', SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

REF = {
    'schema':'EC_PUBLIC_POLICY_V2','policy_id':'claims-auth','policy_evidence_ref':'signed-policy:schema-v1',
    'operation_rules': {
        'PAY': ['fact:authorized','not:fact:fraud_flag'],
        'REVIEW':['fact:fraud_flag']},
    'obligation_rules': {
        'AUTH_EVIDENCE':{'when':['fact:claim_exists'], 'done_when':['fact:authorized']},
        'REVIEW_COMPLETE':{'when':['fact:fraud_flag'], 'done_when':['fact:reviewed']}}
}

class PolicySATTests(unittest.TestCase):
    def setUp(self):
        self.a=copy.deepcopy(REF);self.b=copy.deepcopy(REF);self.pin=m.digest(self.a)
    def check(self):
        return m.compare(self.a,self.b,self.pin)
    def test_identity(self):
        self.assertTrue(self.check()['formal_equivalent_to_pinned_reference'])
    def test_commutative_and(self):
        self.b['operation_rules']['PAY'].reverse()
        self.assertTrue(self.check()['formal_equivalent_to_pinned_reference'])
    def test_missing_authorization_detected(self):
        self.b['operation_rules']['PAY']=['not:fact:fraud_flag']
        x=self.check();self.assertFalse(x['formal_equivalent_to_pinned_reference'])
        self.assertTrue(any(v['counterexample'] for v in x['checks']))
    def test_wrong_negation_detected(self):
        self.b['operation_rules']['PAY']=['fact:authorized','fact:fraud_flag']
        self.assertFalse(self.check()['formal_equivalent_to_pinned_reference'])
    def test_missing_required_obligation_detected(self):
        del self.b['obligation_rules']['AUTH_EVIDENCE']
        self.assertFalse(self.check()['formal_equivalent_to_pinned_reference'])
    def test_extra_operation_detected(self):
        self.b['operation_rules']['BYPASS_CONTROL']=[]
        self.assertFalse(self.check()['formal_equivalent_to_pinned_reference'])
    def test_unsatisfied_done_when_detected(self):
        self.b['obligation_rules']['REVIEW_COMPLETE']['done_when']=['fact:authorized']
        self.assertFalse(self.check()['formal_equivalent_to_pinned_reference'])
    def test_ref_digest_drift_rejected(self):
        self.a['operation_rules']['PAY']=[]
        with self.assertRaisesRegex(ValueError,'PINNED_REFERENCE_CHANGED'):
            self.check()
    def test_proposal_source_identity_mismatch(self):
        self.b['policy_evidence_ref']='signed-policy:forged'
        with self.assertRaisesRegex(ValueError,'POLICY_SOURCE_REF_MISMATCH'):
            self.check()
    def test_gold_field_rejected(self):
        self.b['oracle_constraints']={'gold':True}
        with self.assertRaisesRegex(ValueError,'PRIVATE_FIELD'):
            self.check()
    def test_arbitrary_python_rejected(self):
        self.b['operation_rules']['PAY']=['__import__("os").system("x")']
        with self.assertRaisesRegex(ValueError,'UNKNOWN_LITERAL'):
            self.check()
    def test_duplicates_rejected(self):
        self.b['operation_rules']['PAY']=['fact:authorized','fact:authorized']
        with self.assertRaisesRegex(ValueError,'INVALID_CONJUNCTION'):
            self.check()
    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.json';p.write_text('{"schema":"s","schema":"x"}')
            with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON_KEY'):
                m.decode_unique(p)
    def test_unseen_fact_not_implicitly_false(self):
        self.b['operation_rules']['PAY']=['fact:authorized','not:fact:fraud_flag','fact:unobserved']
        x=self.check();self.assertFalse(x['formal_equivalent_to_pinned_reference'])
        self.assertTrue(any(v.get('counterexample') is not None for v in x['checks']))
    def test_contradictory_formulas_logically_equal(self):
        self.a['operation_rules']['PAY']=['fact:authorized','not:fact:authorized']
        self.b['operation_rules']['PAY']=['fact:fraud_flag','not:fact:fraud_flag']
        self.pin=m.digest(self.a)
        self.assertTrue(self.check()['formal_equivalent_to_pinned_reference'])
    def test_no_NL_or_external_proof_claim(self):
        x=self.check()
        self.assertFalse(x['natural_language_meaning_preserved_proven'])
        self.assertFalse(x['safe_to_claim_original_phase1_s3_semantic_AC'])
    def test_nonexistent_obligation_input_fail_closed(self):
        self.b['obligation_rules']['AUTH_EVIDENCE']['when']='fact:claim_exists'
        with self.assertRaisesRegex(ValueError,'INVALID_CONJUNCTION'):
            self.check()

if __name__ == '__main__':
    unittest.main()
