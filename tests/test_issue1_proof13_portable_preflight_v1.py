import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import issue1_proof13_portable_preflight_v1 as g


def scoped_plan():
    ids = g.EXPECTED
    return {'schema': 'issue1-independent-proof.ac.v1',
        'normative_contract': {'original_required_AC':18,'original_total_AC':20,'original_materiality_abs':.20},
        'proof_package_mvp': {'AC_count':11},
        'acceptance_criteria': [dict(id=x, depends=[] if i==0 else [ids[i-1]], parent=['AC-19'],
                                      evidence=['file_sha'], **{'pass':'must have evidence'})
                                for i,x in enumerate(ids)]}


def corpus(n=120):
    return {'schema':'issue1.corpus.v1','documents':[
        {'id':f'case{i}', 'family':f'fam{i}', 'split':'holdout',
         'source_sha256':hashlib.sha256(str(i).encode()).hexdigest(),
         'source_uri':f'https://example.org/source/{i}', 'license':'review-required',
         'collected_at':'2026-10-10'} for i in range(n)]}


def trace():
    return dict(schema='issue1.s4trace.v1', requirements_baseline_sha256='1'*64,
                clauses=['r1','r2'], obligations=['o1','o2'],
                links=[{'clause_id':'r1','obligation_id':'o1'},
                       {'clause_id':'r2','obligation_id':'o2'}], empty_scope_proof=None)


class Proof13SandboxTests(unittest.TestCase):
    def test_01_frozen_plan_hash_and_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'plan.json';p.write_text(json.dumps(scoped_plan()))
            token = g.git_blob_sha1(p.read_bytes())
            self.assertEqual([x['id'] for x in g.check_plan(p,expected_blob=token)['acceptance_criteria']], list(g.EXPECTED))
            with self.assertRaisesRegex(ValueError, 'G01_FROZEN_AC13_PLAN_CHANGED'):
                g.check_plan(p)

    def test_02_plan_cycle_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'plan.json';d=scoped_plan();d['acceptance_criteria'][1]['depends']=['X02']
            p.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,'G01_PROOF13_CYCLE'):
                g.check_plan(p,expected_blob=g.git_blob_sha1(p.read_bytes()))

    def test_03_minimum_holdout_and_split(self):
        x=g.validate_corpus(corpus())
        self.assertEqual(x['counts']['holdout'],120)
        self.assertFalse(x['independent_origin_certified'])

    def test_04_too_few_independent_holdout_cases(self):
        with self.assertRaisesRegex(ValueError,'P02_HOLDOUT_TOO_SMALL'):
            g.validate_corpus(corpus(119))

    def test_05_leaked_family_dev_holdout(self):
        c=corpus();d=copy.deepcopy(c['documents'][0]);d['id']='different';d['split']='development';d['source_sha256']='a'*64
        c['documents'].append(d)
        with self.assertRaisesRegex(ValueError,'G03_CROSS_SPLIT_FAMILY_LEAK'):
            g.validate_corpus(c)

    def test_06_exact_source_split_leak(self):
        c=corpus();d=copy.deepcopy(c['documents'][0]);d['id']='different';d['family']='other';d['split']='development'
        c['documents'].append(d)
        with self.assertRaisesRegex(ValueError,'G03_CROSS_SPLIT_EXACT_DOCUMENT_LEAK'):
            g.validate_corpus(c)

    def test_07_duplicate_id_denied(self):
        c=corpus();d=copy.deepcopy(c['documents'][0]);d['family']='other';c['documents'].append(d)
        with self.assertRaisesRegex(ValueError,'G07_DUPLICATE_DOCUMENT_ID'):
            g.validate_corpus(c)

    def test_08_bidirectional_clause_trace(self):
        out=g.validate_trace(trace())
        self.assertTrue(out['structurally_complete'])
        self.assertFalse(out['independent_completeness_certified'])

    def test_09_unknown_or_unlinked_obligations_denied(self):
        x=trace();x['links'].pop()
        with self.assertRaisesRegex(ValueError,'C02_BIDIRECTIONAL_COVERAGE_MISSING'):
            g.validate_trace(x)
        x=trace();x['links'].append({'clause_id':'r1','obligation_id':'bad'})
        with self.assertRaisesRegex(ValueError,'C02_UNKNOWN_OR_UNGROUNDED_LINK'):
            g.validate_trace(x)

    def test_10_empty_inventory_needs_explicit_evidence_and_never_authenticates(self):
        x=trace();x['clauses']=[];x['obligations']=[];x['links']=[]
        with self.assertRaisesRegex(ValueError,'C02_EMPTY_INVENTORY_UNPROVEN'):
            g.validate_trace(x)
        x['empty_scope_proof']='author assertion only'
        out=g.validate_trace(x)
        self.assertFalse(out['independent_completeness_certified'])
        x['clauses']=['r1']
        with self.assertRaisesRegex(ValueError,'C02_HALF_EMPTY_INVENTORY'):
            g.validate_trace(x)

    def test_11_artifact_tamper_and_symlink_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'source.txt';p.write_text('original')
            item={'path':'source.txt','sha256':g.sha256(p)}
            self.assertEqual(g.checked_artifact(root,item)['path'],'source.txt')
            p.write_text('modified')
            with self.assertRaisesRegex(ValueError,'G06_ARTIFACT_SHA256_CHANGED'):
                g.checked_artifact(root,item)
            (root/'symlink.txt').symlink_to('source.txt')
            with self.assertRaisesRegex(ValueError,'G02_ARTIFACT_OUTSIDE_ROOT_OR_MISSING'):
                g.checked_artifact(root,{'path':'symlink.txt','sha256':g.sha256(p)})

    def test_12_submission_structure_success_is_not_scientific_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'plan.json';p.write_text(json.dumps(scoped_plan()))
            sub=root/'submission.json';sub.write_text(json.dumps({'schema':'issue1.proof13.evidence.v1',
                 'artifacts':[],'corpus':corpus(),'trace':trace()}))
            with patch.object(g,'PLAN_SHA1',g.git_blob_sha1(p.read_bytes())):
                report=g.run(p,root,sub)
            self.assertEqual(report['structural_preflight']['P02']['counts']['holdout'],120)
            self.assertEqual(report['proof13_total'],13)
            self.assertEqual(report['independent_proof_AC_pass'],0)
            self.assertFalse(report['original_root_complete'])
            self.assertEqual(report['status'],'STRUCTURE_CHECKED_INDEPENDENT_CUSTODY_NOT_AUTHENTICATED')

    def test_13_no_input_means_missing_external_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'plan.json';p.write_text(json.dumps(scoped_plan()))
            with patch.object(g,'PLAN_SHA1',g.git_blob_sha1(p.read_bytes())):
                report=g.run(p,root)
            self.assertEqual(report['missing_first_prerequisite'],['P01','P02','B01','C01'])
            self.assertEqual(report['independent_proof_AC_pass'],0)


if __name__=='__main__':
    unittest.main()
