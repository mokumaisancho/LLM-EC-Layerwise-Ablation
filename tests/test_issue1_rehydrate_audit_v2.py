"""GitHub-only regression suite: no raw public, gold or native output files required."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
TOOL=(HERE/'issue1_rehydrate_audit_v2.py' if (HERE/'issue1_rehydrate_audit_v2.py').exists()
      else ROOT/'tools/issue1_rehydrate_audit_v2.py')
# In GitHub these paths are relative to root; in sandbox keep the source
# exactly byte-identical as the repository historical V1 file.
if (ROOT/'tools/issue1_formal_holdout48_v1.py').exists():
    GENERATOR=ROOT/'tools/issue1_formal_holdout48_v1.py'
    MANIFEST=(ROOT/'fixtures/issue1_formal_holdout48_v1/manifest.json'
              if (ROOT/'fixtures/issue1_formal_holdout48_v1/manifest.json').exists()
              else ROOT/'holdout48_v1/manifest.json')
    OLD_SCORE=ROOT/'holdout48_v1/native_score.json'
else:
    PROJECT=HERE.parent.parent
    GENERATOR=PROJECT/'tools/issue1_formal_holdout48_v1.py'
    MANIFEST=PROJECT/'fixtures/issue1_formal_holdout48_v1/manifest.json'
    OLD_SCORE=PROJECT/'results/DOES_NOT_EXIST_RAW_SCORE.json'
spec=importlib.util.spec_from_file_location('replay_v2',TOOL)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class RehydrateV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public,cls.gold,cls.manifest=m.rehydrate(GENERATOR,MANIFEST)

    def copy_pins(self,temp):
        d=Path(temp)
        a=d/'generator.py'; b=d/'manifest.json'
        a.write_bytes(GENERATOR.read_bytes());b.write_bytes(MANIFEST.read_bytes())
        return a,b

    def test_regenerate_48_without_existing_raw_data(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=self.copy_pins(t)
            # Only generator.py and manifest.json available, no input/label files.
            self.assertEqual(len(list(Path(t).iterdir())),2)
            r=m.run(a,b)
            self.assertEqual(r['public_cases'],48)
            self.assertTrue(r['raw_input_files_in_git_required'] is False)
            self.assertIsNone(r['recorded_score_replay'])

    def test_original_public_content_hash_recovered(self):
        self.assertEqual(m.sha(self.public),m.PUBLIC_DIGEST)
    def test_original_private_label_digest_recovered_without_file(self):
        self.assertEqual(m.sha(self.gold),m.GOLD_DIGEST)
    def test_manifest_root_and_blob_recovered(self):
        self.assertEqual(m.sha(self.manifest),m.SOURCE_MANIFEST_DIGEST)
        self.assertEqual(m.blob(MANIFEST),m.MANIFEST_BLOB)
    def test_class_balance_and_unique_ids(self):
        ids=[x['id'] for x in self.public['cases']]
        self.assertEqual(len(ids),len(set(ids)))
        counts={k:0 for k in m.ALLOWED_CLASSES}
        for x in self.gold['labels']:counts[x['reference']['closure']]+=1
        self.assertEqual(counts,{k:12 for k in m.ALLOWED_CLASSES})
    def test_public_has_no_literal_answer_fields(self):
        m.public_free(self.public)
    def test_injected_oracle_field_is_rejected(self):
        public=copy.deepcopy(self.public)
        public['cases'][3]['input']['oracle_constraints']={'expected':'CLOSE'}
        with self.assertRaisesRegex(m.VerificationError,'PREDICTOR_GOLD_KEY'):
            m.public_free(public)
    def test_gold_is_not_claimed_independent(self):
        result=m.run(GENERATOR,MANIFEST)
        self.assertFalse(result['semantic_gold_independent'])
        self.assertFalse(result['full_s1_s4_non_degradation_demonstrated'])
        self.assertEqual(result['new_real_llm_inference'],0)
        self.assertEqual(result['original_science_ac_promoted'],0)
    def test_changed_generator_rejected_normally(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=self.copy_pins(t)
            a.write_text(a.read_text()+'\n# injected change\n')
            with self.assertRaisesRegex(m.VerificationError,'GENERATOR_GIT_BLOB_MISMATCH'):
                m.rehydrate(a,b)
    def test_changed_manifest_rejected_normally(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=self.copy_pins(t)
            manifest=json.loads(b.read_text());manifest['public_sha256']='0'*64
            b.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(m.VerificationError,'MANIFEST_GIT_BLOB_MISMATCH'):
                m.rehydrate(a,b)
    def test_coordinated_manifest_edit_rejected_normally(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=self.copy_pins(t)
            manifest=json.loads(b.read_text());manifest['public_sha256']='a'*64
            manifest['private_gold_sha256']='b'*64
            manifest['formal_source_policy_sha256']='c'*64
            b.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(m.VerificationError,'MANIFEST_GIT_BLOB_MISMATCH'):
                m.rehydrate(a,b)
    def test_optimized_python_refuses_modified_generator(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=self.copy_pins(t);a.write_text(a.read_text()+'\n# tamper\n')
            proc=subprocess.run([sys.executable,'-O',str(TOOL),'--generator',str(a),'--manifest',str(b)],capture_output=True,text=True,timeout=20)
            self.assertEqual(proc.returncode,3,proc.stdout+proc.stderr)
            self.assertIn('GENERATOR_GIT_BLOB_MISMATCH',proc.stderr)
    def test_optimized_python_refuses_modified_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=self.copy_pins(t);ob=json.loads(b.read_text());ob['n']=999;b.write_text(json.dumps(ob))
            proc=subprocess.run([sys.executable,'-O',str(TOOL),'--generator',str(a),'--manifest',str(b)],capture_output=True,text=True,timeout=20)
            self.assertEqual(proc.returncode,3,proc.stdout+proc.stderr)
            self.assertIn('MANIFEST_GIT_BLOB_MISMATCH',proc.stderr)
    def test_optimized_python_clean_recovery(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=self.copy_pins(t)
            proc=subprocess.run([sys.executable,'-O',str(TOOL),'--generator',str(a),'--manifest',str(b)],capture_output=True,text=True,timeout=20)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['public_sha256'],m.PUBLIC_DIGEST)
    def test_incorrect_native_file_refused(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'fake.py';f.write_text('raise RuntimeError("CODE_EXECUTED")\n')
            with self.assertRaisesRegex(m.VerificationError,'NATIVE_EC_SOURCE_GIT_BLOB_MISMATCH'):
                m.run(GENERATOR,MANIFEST,native_path=f)
    def test_optimized_incorrect_native_refused_before_import(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=self.copy_pins(t);fake=Path(t)/'fake.py';fake.write_text('raise RuntimeError("CODE_EXECUTED")\n')
            proc=subprocess.run([sys.executable,'-O',str(TOOL),'--generator',str(a),'--manifest',str(b),'--native-source',str(fake)],capture_output=True,text=True,timeout=20)
            self.assertEqual(proc.returncode,3,proc.stdout+proc.stderr)
            self.assertIn('NATIVE_EC_SOURCE_GIT_BLOB_MISMATCH',proc.stderr)
            self.assertNotIn('CODE_EXECUTED',proc.stderr)
    def test_saved_score_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            fake=Path(t)/'score.json'
            fake.write_text('{"cases":[],"ec_exact_pass":48}')
            with self.assertRaisesRegex(m.VerificationError,'SAVED_SCORE_SHA256_MISMATCH'):
                m.run(GENERATOR,MANIFEST,recorded_score=fake)
    def test_model_visible_export_excludes_private_labels(self):
        with tempfile.TemporaryDirectory() as t:
            dst=Path(t)/'only_public.json'
            m.run(GENERATOR,MANIFEST,public_output=dst)
            obj=json.loads(dst.read_text())
            self.assertEqual(m.sha(obj),m.PUBLIC_DIGEST)
            m.public_free(obj)
            self.assertEqual(set(Path(t).iterdir()),{dst})
    def test_export_must_not_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as t:
            dst=Path(t)/'only_public.json';dst.write_text('original')
            with self.assertRaisesRegex(m.VerificationError,'REFUSE_TO_OVERWRITE_PUBLIC'):
                m.run(GENERATOR,MANIFEST,public_output=dst)
            self.assertEqual(dst.read_text(),'original')
    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            dst=Path(t)/'bad.json';dst.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(m.VerificationError,'DUPLICATE_JSON_KEY'):
                m.parse_json(dst)
    def test_preexisting_raw_score_optional_not_required(self):
        if OLD_SCORE.exists():
            observed=m.run(GENERATOR,MANIFEST,recorded_score=OLD_SCORE)
            self.assertEqual(observed['recorded_score_replay']['recorded_native_count'],48)
        else:
            observed=m.run(GENERATOR,MANIFEST)
            self.assertIsNone(observed['recorded_score_replay'])

if __name__=='__main__':unittest.main()
