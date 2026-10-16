import copy
import json
import tempfile
from pathlib import Path
import importlib.util
import unittest

MODULE=Path(__file__).resolve().parent.parent/'tools/issue1_formal_holdout48_v1.py'
spec=importlib.util.spec_from_file_location('benchmark',MODULE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
EXISTING=Path(__file__).resolve().parent.parent/'holdout48_v1'

class Holdout48Tests(unittest.TestCase):
    def test_holdout_has_exact_48_distinct_inputs(self):
        rows=m.make_all()
        self.assertEqual(len(rows),48)
        self.assertEqual(len({m.digest(x['input']) for x in rows}),48)
    def test_stratification_exactly_twelve_per_outcome(self):
        rows=m.make_all()
        counts={x:sum(r['reference']['closure']==x for r in rows) for x in ('BLOCKED','CLOSE','CONTINUE','REFRAME')}
        self.assertEqual(counts,dict.fromkeys(counts,12))
    def test_full_manifest_seal_valid(self):
        pub,private,seal=m.load(EXISTING)
        self.assertEqual(m.digest(pub),seal['public_sha256'])
        self.assertEqual(m.digest(private),seal['private_gold_sha256'])
    def test_native_replay_independent_Sympy_48(self):
        score=m.score(EXISTING)
        self.assertEqual(score['n'],48)
        self.assertEqual(score['ec_exact_pass'],48)
        self.assertEqual(score['ec_exact_fail'],0)
    def test_gold_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as p:
            t=Path(p)
            for f in ('public.json','private_gold.json','manifest.json'):
                (t/f).write_bytes((EXISTING/f).read_bytes())
            gold=json.loads((t/'private_gold.json').read_text())
            gold['labels'][0]['reference']['closure']='FORGED'
            (t/'private_gold.json').write_text(json.dumps(gold))
            with self.assertRaisesRegex(AssertionError,'GOLD_DRIFT'):m.load(t)
    def test_public_task_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as p:
            t=Path(p)
            for f in ('public.json','private_gold.json','manifest.json'):
                (t/f).write_bytes((EXISTING/f).read_bytes())
            pub=json.loads((t/'public.json').read_text())
            pub['cases'][0]['input']['task']['facts']['fraud']=not pub['cases'][0]['input']['task']['facts']['fraud']
            (t/'public.json').write_text(json.dumps(pub))
            with self.assertRaisesRegex(AssertionError,'PUBLIC_DRIFT'):m.load(t)
    def test_policy_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as p:
            t=Path(p)
            for f in ('public.json','private_gold.json','manifest.json'):
                (t/f).write_bytes((EXISTING/f).read_bytes())
            pub=json.loads((t/'public.json').read_text())
            pub['policy']['operation_rules']['PAY']=[]
            (t/'public.json').write_text(json.dumps(pub))
            with self.assertRaisesRegex(AssertionError,'PUBLIC_DRIFT'):m.load(t)
    def test_conditional_unresolved_differs_from_close(self):
        case=m.case({'authorized':True,'fraud':False,'docs':False,'risk':False,'reviewed':False},'NORMAL')
        self.assertEqual(m.independent_reference(case,m.policy())['closure'],'CONTINUE')
        case['task']['facts']['docs']=True
        self.assertEqual(m.independent_reference(case,m.policy())['closure'],'CLOSE')
    def test_competing_vs_equivalent(self):
        f={'authorized':True,'fraud':False,'docs':True,'risk':True,'reviewed':False}
        competing=m.independent_reference(m.case(f,'COMPETING'),m.policy())
        equivalent=m.independent_reference(m.case(f,'EQUIVALENT'),m.policy())
        self.assertEqual(competing['closure'],'CONTINUE')
        self.assertEqual(equivalent['closure'],'CLOSE')
    def test_no_implicit_real_world_close(self):
        actual=m.score(EXISTING)
        self.assertEqual(actual['original_AC_promoted'],0)
        self.assertEqual(actual['real_llm_calls'],0)
        self.assertFalse(actual['independent_nl_reference'])
    def test_native_exact_pinned_blob(self):
        self.assertEqual(m.gitblob(m.EC),m.EC_BLOB)
    def test_original_fixture_ids_cannot_leak(self):
        pub,_,_=m.load(EXISTING)
        self.assertTrue(all(x['id'].startswith('H') for x in pub['cases']))
        self.assertTrue(all(not x['id'].startswith('M') and not x['id'].startswith('N') for x in pub['cases']))

if __name__=='__main__':unittest.main()
