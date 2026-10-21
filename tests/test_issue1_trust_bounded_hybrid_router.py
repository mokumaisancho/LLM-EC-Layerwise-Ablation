import copy
import json
import sys
from pathlib import Path
import unittest

TOOL_DIR = Path(__file__).resolve().parent.parent / 'tools'
sys.path.insert(0, str(TOOL_DIR))
from issue1_trust_bounded_hybrid_router import TrustedReference, route
from issue1_independent_formal_policy_equivalence import digest

REFERENCE = {
    'schema': 'EC_PUBLIC_POLICY_V2',
    'policy_id': 'source-bound-formal-test',
    'policy_evidence_ref': 'fixture-only:no-external-authority',
    'operation_rules': {'REVIEW': ['fact:exists','not:fact:revoked']},
    'obligation_rules': {'ATTACHMENT': {'when': ['fact:exists'],
                                        'done_when': ['fact:attachment_present']}}
}
SRC = 'a' * 64

class RouteTests(unittest.TestCase):
    def setUp(self):
        self.original = {'raw': 'KEEP THIS LLM DECISION', 'selected': ['unknown']}
        self.reference = copy.deepcopy(REFERENCE)
        self.proposal = copy.deepcopy(REFERENCE)
        self.trusted = TrustedReference(digest(self.reference), SRC, 'formal_policy_s3', digest({'work_id': 'repair:1'}))
        self.calls=[]

    def ec(self, *, ec_input, policy):
        self.calls.append((ec_input, policy))
        return {'status': 'ACCEPTED_IN_FORMAL_SCOPE', 'id': ec_input['work_id']}

    def invoke(self, **overrides):
        kwargs = dict(llm_output=self.original, proposed_policy=self.proposal,
                      frozen_reference=self.reference, trusted=self.trusted,
                      observed_source_sha256=SRC, requested_target='formal_policy_s3',
                      native_ec=self.ec, ec_input={'work_id': 'repair:1'})
        kwargs.update(overrides)
        return route(**kwargs)

    def assert_fallback(self, result, expected):
        self.assertEqual(result['route'],'LLM_UNCHANGED')
        self.assertEqual(result['reason'],expected)
        self.assertIs(result['decision'], self.original)
        self.assertEqual(self.calls,[])

    def test_positive_formal_routing(self):
        r=self.invoke()
        self.assertEqual(r['route'],'EC_FORMAL_SCOPE_ONLY')
        self.assertEqual(r['decision']['id'],'repair:1')
        self.assertEqual(len(self.calls),1)
        self.assertIs(self.calls[0][1],self.reference)
        self.assertFalse(r['real_world_task_close_authorized'])
        self.assertFalse(r['semantic_generalization_non_degradation_proven'])

    def test_condition_permutation(self):
        self.proposal['operation_rules']['REVIEW'].reverse()
        self.assertEqual(self.invoke()['route'],'EC_FORMAL_SCOPE_ONLY')

    def test_empty_trust(self):
        self.assert_fallback(self.invoke(trusted=None),'NO_INDEPENDENTLY_PINNED_FORMAL_REFERENCE')

    def test_wrong_trust_source(self):
        self.assert_fallback(self.invoke(observed_source_sha256='b'*64),'SOURCE_CUSTODY_HASH_MISMATCH')

    def test_wrong_trust_target(self):
        self.assert_fallback(self.invoke(trusted=TrustedReference(self.trusted.policy_sha256, SRC, 'governed_next_action', digest({'work_id':'repair:1'}))),'TRUST_TARGET_SCOPE_MISMATCH')

    def test_out_of_scope_task_closure(self):
        self.assert_fallback(self.invoke(requested_target='real_world_task_closure'),'UNSUPPORTED_SEMANTIC_TARGET')

    def test_reference_changed_after_pin(self):
        self.reference['operation_rules']['REVIEW'].append('fact:second_approval')
        self.assert_fallback(self.invoke(),'FORMAL_REFERENCE_OR_PROPOSAL_INVALID')

    def test_missing_prerequisite_counterexample(self):
        self.proposal['operation_rules']['REVIEW']=['not:fact:revoked']
        r=self.invoke()
        self.assert_fallback(r,'FORMAL_RULE_NOT_EQUIVALENT')
        self.assertTrue(any(x['counterexample'] for x in r['counterexamples']))

    def test_inverted_negation_counterexample(self):
        self.proposal['operation_rules']['REVIEW']=['fact:exists','fact:revoked']
        self.assert_fallback(self.invoke(),'FORMAL_RULE_NOT_EQUIVALENT')

    def test_omitted_obligation(self):
        del self.proposal['obligation_rules']['ATTACHMENT']
        self.assert_fallback(self.invoke(),'FORMAL_RULE_NOT_EQUIVALENT')

    def test_hallucinated_extra_obligation(self):
        self.proposal['obligation_rules']['UNAUTH']={'when': [], 'done_when': []}
        self.assert_fallback(self.invoke(),'FORMAL_RULE_NOT_EQUIVALENT')

    def test_gold_key_rejected(self):
        self.proposal['oracle_constraints'] = {'answer':True}
        self.assert_fallback(self.invoke(),'FORMAL_REFERENCE_OR_PROPOSAL_INVALID')

    def test_missing_proposal(self):
        self.assert_fallback(self.invoke(proposed_policy=None),'NO_PROPOSED_FORMAL_POLICY')

    def test_missing_ec_engine(self):
        self.assert_fallback(self.invoke(native_ec=None),'PINNED_NATIVE_EC_NOT_AVAILABLE')

    def test_ec_exception_fail_closed(self):
        def failure(**kwargs):
            raise RuntimeError('simulated native failure')
        self.assert_fallback(self.invoke(native_ec=failure),'NATIVE_EC_RUNTIME_FAIL_CLOSED')

    def test_native_output_never_promoted_to_task_close(self):
        def formal_only(**kwargs):return {'closure_diagnostic':'CLOSE'}
        r=self.invoke(native_ec=formal_only)
        self.assertEqual(r['route'],'EC_FORMAL_SCOPE_ONLY')
        self.assertFalse(r['real_world_task_close_authorized'])

    def test_original_ten_unattested_cases_fallback(self):
        root=Path(__file__).resolve().parent.parent
        for k in range(1,11):
            p=root / 'replay' / f'M{k:03d}' / 's3_predictor_visible_v42.json'
            source=json.loads(p.read_text())
            r=self.invoke(llm_output=source, trusted=None, native_ec=self.ec)
            self.assertEqual(r['route'],'LLM_UNCHANGED')
            self.assertIs(r['decision'],source)
        self.assertEqual(self.calls,[])

    def test_wrong_policy_id(self):
        self.proposal['policy_id']='unrelated'
        self.assert_fallback(self.invoke(),'FORMAL_REFERENCE_OR_PROPOSAL_INVALID')

    def test_preserve_empty_llm_object(self):
        self.original={}
        self.assert_fallback(self.invoke(trusted=None),'NO_INDEPENDENTLY_PINNED_FORMAL_REFERENCE')

    def test_ec_return_bool_still_scoped(self):
        r=self.invoke(native_ec=lambda **kwargs: True)
        self.assertEqual(r['route'],'EC_FORMAL_SCOPE_ONLY')
        self.assertFalse(r['real_world_task_close_authorized'])

if __name__=='__main__':unittest.main()
