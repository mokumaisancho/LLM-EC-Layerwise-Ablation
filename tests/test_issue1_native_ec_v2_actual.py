"""Run exact pinned native EC policy-v2 engine through formal-only hybrid router.

Source authority here is a synthetic test fixture; do NOT promote original AC.
EC_NATIVE_V2_PATH points at identical Git blob
7da0cd8d876505cafdd5a9811132427e2f441a14.
"""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'tools'))
import issue1_trust_bounded_hybrid_router as router
from issue1_independent_formal_policy_equivalence import digest

NATIVE = Path(os.environ.get('EC_NATIVE_V2_PATH', str(ROOT/'tools'/'ec_layerwise_source_policy_authority_v2.py')))
BLOB = '7da0cd8d876505cafdd5a9811132427e2f441a14'
def gitblob(path):
    raw = path.read_bytes()
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
assert gitblob(NATIVE)==BLOB, 'EC_NATIVE_BLOB_MISMATCH'
spec = importlib.util.spec_from_file_location('native_ec_v2',NATIVE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
COMMIT='3f435ad4365d846d96264458540efb4848ce3541'
POLICY={
 'schema':'EC_PUBLIC_POLICY_V2',
 'policy_id':'SYNTHETIC_AUTHORIZATION_DEMO_NOT_APPROVED',
 'policy_evidence_ref':'demo:synthetic-formal-source',
 'operation_rules':{'PAY':['fact:authorized','not:fact:fraud'],
                    'REVIEW':['fact:fraud'],
                    'ESCALATE':['fact:risk']},
 'obligation_rules':{'EVIDENCE':{'when':['fact:authorized'], 'done_when':['fact:docs']},
                     'FRAUD_REVIEW':{'when':['fact:fraud'], 'done_when':['fact:reviewed']}}
}

def inputs(*, authorized=True,fraud=False,risk=False,docs=True,reviewed=False,relation=''):
    task={'schema':'EC_FORMAL_FACTS_V2','source_ref':'demo:case-source',
          'facts':{'authorized':authorized,'fraud':fraud,'risk':risk,'docs':docs,'reviewed':reviewed}}
    candidates=[{'candidate_id':x,'semantic_transition':{'operation':op},
                 'evidence_refs':[],'dependencies':[],'claims':[]}
                for x,op in [('c_pay','PAY'),('c_review','REVIEW'),('c_escalate','ESCALATE')]]
    groups=[] if not relation else [{'group_id':'G','relation_type':relation,'candidate_ids':['c_pay','c_escalate']}]
    s2={'candidates':candidates,'relation_groups':groups,
        'semantic_ir_hash':native.digest(task),
        'source_refs':['demo:synthetic-formal-source','demo:case-source']}
    return {'task':task,'public_s2':s2,'framing':{'reframe_required':False,'reframe_resolved':False}}


def actual_native_adapter(*,ec_input,policy):
    s2=ec_input['public_s2'];task=ec_input['task']
    compiled=native.compile_source_policy(s2,task,policy,pinned_policy_sha256=native.digest(policy),source_commit=COMMIT)
    selected=[id for id,value in compiled['adjudications'].items() if value['status']=='ADMISSIBLE']
    rejected=[id for id,value in compiled['adjudications'].items() if value['status']=='REJECTED']
    selection={'source_s2_sha256':native.digest(s2),'semantic_truth_independently_verified':False,
               'selection':{'selected_candidate_ids':selected,'rejected_candidate_ids':rejected}}
    closure=native.evaluate_policy_closure(compiled,selection,s2,task,policy,pinned_policy_sha256=native.digest(policy),framing=ec_input['framing'])
    return {'native_protocol':compiled['protocol'],'selected':selected,'rejected':rejected,
            'closure':closure['closure_diagnostic'],'reason':closure['reason'],
            'unresolved':closure['unresolved_policy_obligations'],
            'real_world_close_authorized':closure['real_world_close_authorized'],
            'formal_only':closure['scope']}


class NativeECRealTests(unittest.TestCase):
 def setUp(self):
    self.policy=copy.deepcopy(POLICY);self.proposal=copy.deepcopy(POLICY)
    self.source_sha='a'*64
    self.llm={'raw':'keep existing inference','decision':'UNQUALIFIED'}
    self.input=inputs()
    self.trusted=router.TrustedReference(digest(self.policy),self.source_sha,'formal_policy_s3',digest(self.input))
 def reseal(self):
    self.trusted=router.TrustedReference(digest(self.policy),self.source_sha,'formal_policy_s3',digest(self.input))
 def run_route(self,**override):
    d={'llm_output':self.llm,'proposed_policy':self.proposal,
       'frozen_reference':self.policy,'trusted':self.trusted,
       'observed_source_sha256':self.source_sha,'requested_target':'formal_policy_s3',
       'native_ec':actual_native_adapter,'ec_input':self.input}
    d.update(override)
    return router.route(**d)
 def test_source_exact_git_blob(self): self.assertEqual(gitblob(NATIVE),BLOB)
 def test_real_ec_pay_close_formal_only(self):
    r=self.run_route();self.assertEqual(r['route'],'EC_FORMAL_SCOPE_ONLY')
    self.assertEqual(r['decision']['selected'],['c_pay'])
    self.assertEqual(r['decision']['closure'],'CLOSE')
    self.assertFalse(r['decision']['real_world_close_authorized'])
    self.assertFalse(r['real_world_task_close_authorized'])
 def test_real_ec_unresolved_obligation(self):
    self.input=inputs(docs=False);self.reseal()
    r=self.run_route();self.assertEqual(r['decision']['closure'],'CONTINUE')
    self.assertEqual(r['decision']['unresolved'],['EVIDENCE'])
 def test_real_ec_review_incomplete(self):
    self.input=inputs(authorized=False,fraud=True,docs=True);self.reseal()
    r=self.run_route();self.assertEqual(r['decision']['selected'],['c_review'])
    self.assertEqual(r['decision']['closure'],'CONTINUE')
    self.assertEqual(r['decision']['unresolved'],['FRAUD_REVIEW'])
 def test_real_ec_competing_selected(self):
    self.input=inputs(risk=True,relation='COMPETING');self.reseal()
    r=self.run_route();self.assertEqual(r['decision']['selected'],['c_pay','c_escalate'])
    self.assertEqual(r['decision']['closure'],'CONTINUE')
    self.assertEqual(r['decision']['reason'],'COMPETING_ADMISSIBLE_ALTERNATIVES')
 def test_real_ec_equivalent_no_competition(self):
    self.input=inputs(risk=True,relation='EQUIVALENT');self.reseal()
    r=self.run_route();self.assertEqual(r['decision']['closure'],'CLOSE')
 def test_real_ec_pending_reframe(self):
    self.input['framing']={'reframe_required':True,'reframe_resolved':False};self.reseal()
    r=self.run_route();self.assertEqual(r['decision']['closure'],'REFRAME')
 def test_real_ec_no_candidate(self):
    self.input=inputs(authorized=False,fraud=False,risk=False);self.reseal()
    r=self.run_route();self.assertEqual(r['decision']['selected'],[])
    self.assertEqual(r['decision']['closure'],'BLOCKED')
 def test_real_ec_unbound_fact_does_not_infer_false(self):
    del self.input['task']['facts']['fraud']
    self.input['public_s2']['semantic_ir_hash']=native.digest(self.input['task']);self.reseal()
    r=self.run_route();self.assertEqual(r['route'],'LLM_UNCHANGED')
    self.assertEqual(r['reason'],'NATIVE_EC_RUNTIME_FAIL_CLOSED');self.assertIs(r['decision'],self.llm)
 def test_sat_changed_policy_fallback(self):
    self.proposal['operation_rules']['PAY']=['not:fact:fraud']
    r=self.run_route();self.assertEqual(r['route'],'LLM_UNCHANGED')
    self.assertEqual(r['reason'],'FORMAL_RULE_NOT_EQUIVALENT');self.assertIs(r['decision'],self.llm)
 def test_wrong_source_custody_fallback(self):
    r=self.run_route(observed_source_sha256='b'*64)
    self.assertEqual(r['route'],'LLM_UNCHANGED');self.assertIs(r['decision'],self.llm)
 def test_absent_independent_reference_preserves_llm(self):
    r=self.run_route(trusted=None)
    self.assertEqual(r['route'],'LLM_UNCHANGED');self.assertIs(r['decision'],self.llm)
 def test_untrusted_ec_input_mutation_rejected_after_repair(self):
    original=self.run_route();self.assertEqual(original['decision']['selected'],['c_pay'])
    self.input['task']['facts']['authorized']=False
    self.input['public_s2']['semantic_ir_hash']=native.digest(self.input['task'])
    changed=self.run_route()
    # EC input hash is independently sealed; recomputation of S2 chain alone is insufficient.
    self.assertEqual(changed['route'],'LLM_UNCHANGED')
    self.assertEqual(changed['reason'],'EC_INPUT_NOT_SOURCE_BOUND')
    self.assertIs(changed['decision'],self.llm)

if __name__=='__main__':unittest.main()
