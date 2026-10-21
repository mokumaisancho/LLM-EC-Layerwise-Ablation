"""Repeatable independent audit on GitHub-only input rehydration (no raw data required).

PASS means the audit detects known invalidating facts, not scientific AC PASS.
The formal predictive baseline is intentionally independent of SymPy and EC.
"""
from __future__ import annotations
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GENERATOR = ROOT / 'tools' / 'issue1_formal_holdout48_v1.py'
MANIFEST = ROOT / 'fixtures' / 'issue1_formal_holdout48_v1' / 'manifest.json'
REHYDRATE = ROOT / 'tools' / 'issue1_rehydrate_audit_v2.py'
sys.path.insert(0,str(REHYDRATE.parent))
import issue1_rehydrate_audit_v2 as audit


def public_only_baseline(public):
    """Uses no private gold, no original generator, no SymPy, no native EC."""
    policy=public['policy']
    def predicate(tokens,facts):
        for token in tokens:
            neg=token.startswith('not:fact:')
            key=token[9:] if neg else token[5:]
            if key not in facts or type(facts[key]) is not bool:
                raise ValueError('UNBOUND_PUBLIC_FACT:'+key)
            if facts[key] is neg:
                return False
        return True
    derived=[]
    for item in public['cases']:
        d=item['input'];facts=d['task']['facts'];s2=d['public_s2']
        selected=[c['candidate_id'] for c in s2['candidates'] if predicate(
            policy['operation_rules'][c['semantic_transition']['operation']],facts)]
        obligations=[k for k,v in policy['obligation_rules'].items()
                     if predicate(v['when'],facts) and not predicate(v['done_when'],facts)]
        competing=[g['group_id'] for g in s2['relation_groups'] if g['relation_type']=='COMPETING'
                   and len(set(g['candidate_ids'])&set(selected))>1]
        frame=d['framing']
        if frame['reframe_required'] and not frame['reframe_resolved']:
            status='REFRAME'
        elif obligations or competing:
            status='CONTINUE'
        elif not selected:
            status='BLOCKED'
        else:
            status='CLOSE'
        derived.append({'id':item['id'],'reference':{'selected':selected,'closure':status,
                                                      'unresolved':sorted(obligations),'conflicts':competing}})
    return {'schema':'ISSUE1_HOLDOUT48_PRIVATE_V1','labels':derived}


class FalsificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public,cls.gold,cls.manifest=audit.rehydrate(GENERATOR,MANIFEST)

    def test_rehydration_source_is_fixed(self):
        self.assertEqual(audit.sha(self.public),audit.PUBLIC_DIGEST)
        self.assertEqual(audit.sha(self.gold),audit.GOLD_DIGEST)

    def test_public_only_baseline_reconstructs_all_gold(self):
        alternate=public_only_baseline(self.public)
        self.assertEqual(audit.sha(alternate),audit.GOLD_DIGEST)
        self.assertEqual(sum(x==y for x,y in zip(alternate['labels'],self.gold['labels'])),48)

    def test_no_explicit_gold_keys_in_genuine_public(self):
        audit.public_free(self.public)
        self.assertNotIn('formal_reference',json.dumps(self.public))

    def test_value_smuggling_would_pass_key_only_scanner(self):
        examples=[('source_ref','answer=CLOSE'),('candidate_id','CORRECT_CLOSE'),('policy_id','truth:REFRAME')]
        for where,smuggled in examples:
            x=copy.deepcopy(self.public)
            if where=='source_ref': x['cases'][0]['input']['task']['source_ref']=smuggled
            elif where=='candidate_id': x['cases'][0]['input']['public_s2']['candidates'][0]['candidate_id']=smuggled
            else: x['policy']['policy_id']=smuggled
            # Characterizes the vulnerability; this scanner's PASS does NOT imply no leakage.
            audit.public_free(x)
            self.assertIn(smuggled,json.dumps(x))

    def test_tampered_public_cannot_pass_frozen_manifest_validation(self):
        x=copy.deepcopy(self.public)
        x['cases'][0]['input']['task']['source_ref']='answer=CLOSE'
        self.assertNotEqual(audit.sha(x),audit.PUBLIC_DIGEST)

    def test_label_derived_class_balance_not_unseen_sampling(self):
        s=GENERATOR.read_text()
        self.assertIn("r['reference']['closure']==label",s)
        classes=[r['reference']['closure'] for r in self.gold['labels']]
        self.assertEqual({x:classes.count(x) for x in sorted(set(classes))},
                         {'BLOCKED':12,'CLOSE':12,'CONTINUE':12,'REFRAME':12})

    def test_generator_contains_answer_computation(self):
        s=GENERATOR.read_text()
        self.assertIn('def independent_reference(',s)
        self.assertIn("'reference':output",s)

    def test_public_only_evaluator_is_not_a_language_model(self):
        self.assertEqual(audit.run(GENERATOR,MANIFEST)['new_real_llm_inference'],0)
        self.assertFalse(audit.run(GENERATOR,MANIFEST)['semantic_gold_independent'])

    def test_optimized_unmodified_rehydration_succeeds(self):
        p=subprocess.run([sys.executable,'-O',str(REHYDRATE),'--generator',str(GENERATOR),
                          '--manifest',str(MANIFEST)],text=True,capture_output=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['public_sha256'],audit.PUBLIC_DIGEST)

    def test_optimized_tampered_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            temp=pathlib.Path(d)
            gen=temp/'generator.py';man=temp/'manifest.json'
            gen.write_bytes(GENERATOR.read_bytes());man.write_bytes(MANIFEST.read_bytes())
            wrong=json.loads(man.read_text());wrong['public_sha256']='0'*64
            man.write_text(json.dumps(wrong))
            p=subprocess.run([sys.executable,'-O',str(REHYDRATE),'--generator',str(gen),
                              '--manifest',str(man)],text=True,capture_output=True,timeout=20)
            self.assertEqual(p.returncode,3)
            self.assertIn('MANIFEST_GIT_BLOB_MISMATCH',p.stderr)

    def test_optimized_tampered_generator_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            temp=pathlib.Path(d)
            gen=temp/'generator.py';man=temp/'manifest.json'
            gen.write_bytes(GENERATOR.read_bytes());man.write_bytes(MANIFEST.read_bytes())
            gen.write_text(gen.read_text()+'\n# changed\n')
            p=subprocess.run([sys.executable,'-O',str(REHYDRATE),'--generator',str(gen),
                              '--manifest',str(man)],text=True,capture_output=True,timeout=20)
            self.assertEqual(p.returncode,3)
            self.assertIn('GENERATOR_GIT_BLOB_MISMATCH',p.stderr)

    def test_score_file_is_not_a_public_predictor_input(self):
        local=ROOT/'holdout48_v1'/'native_score.json'
        if not local.exists():self.skipTest('Raw saved score intentionally not in GitHub')
        original=json.loads(local.read_text())
        self.assertEqual(len(original['cases']),48)
        self.assertTrue(all('formal_reference' in x for x in original['cases']))
        with self.assertRaises(audit.VerificationError):audit.public_free(original)

    def test_saved_score_reconciles_but_not_independence(self):
        local=ROOT/'holdout48_v1'/'native_score.json'
        if not local.exists():self.skipTest('Raw saved score intentionally not in GitHub')
        stats=audit.check_saved_score(local,self.public,self.gold,self.manifest)
        self.assertEqual(stats['recorded_native_count'],48)
        self.assertFalse(audit.run(GENERATOR,MANIFEST)['full_s1_s4_non_degradation_demonstrated'])

    def test_no_raw_data_needed_to_reconstruct(self):
        with tempfile.TemporaryDirectory() as d:
            temp=pathlib.Path(d)
            gen=temp/'generator.py';man=temp/'manifest.json'
            gen.write_bytes(GENERATOR.read_bytes());man.write_bytes(MANIFEST.read_bytes())
            got=audit.run(gen,man)
            self.assertEqual(got['public_cases'],48)
            self.assertFalse(got['semantic_gold_independent'])

if __name__=='__main__':unittest.main()
