from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path

from tests.test_quality_blind_v2 import fixture
from tools.preflight_issue57_study_assets import inspect_study, inspect_ollama_model
from evaluation.quality_blind_v2 import sha


class ExternalStudyReadinessTests(unittest.TestCase):
    def prepare(self, directory: Path, *, placeholders: bool = False):
        public, gold, arms, seal = fixture()
        for name, envelope in arms.items():
            if not placeholders:
                envelope["model_or_runtime_ref"] = "UNVERIFIED_SOURCE_" + name
        seal["arm_raw_commitments"] = {name: sha(envelope) for name, envelope in arms.items()}
        values = {"public.json": public, "gold_precommit.json": {
            "protocol": "CAPABILITY_GOLD_PRECOMMIT_V2",
            "study_id": public["study_id"],
            "public_sha256": seal["public_sha256"],
            "gold_commitment": seal["gold_commitment"],
        }, "seal.json": seal}
        values.update({name + ".json": envelope for name, envelope in arms.items()})
        for filename, value in values.items():
            (directory / filename).write_text(json.dumps(value, ensure_ascii=False))

    def test_01_missing_study_denied(self):
        result = inspect_study(None)
        self.assertEqual(result["blockers"], ["EXTERNAL_STUDY_DIR_MISSING"])
        self.assertFalse(result["quality_preservation_certified"])

    def test_02_matching_hashes_never_certify_external_source(self):
        with tempfile.TemporaryDirectory() as folder:
            self.prepare(Path(folder))
            result = inspect_study(Path(folder))
            self.assertTrue(result["machine_structural_complete"])
            self.assertEqual(result["stage"], "INDEPENDENT_PROVENANCE_REVIEW")
            self.assertFalse(result["external_gold_independence_verified"])
            self.assertFalse(result["genuine_inference_verified"])
            self.assertFalse(result["quality_preservation_certified"])
            self.assertIn("EXTERNAL_REVIEW_REQUIRED_UNSEEN_AND_REAL_INFERENCE_UNPROVEN", result["blockers"])

    def test_03_synthetic_arm_ref_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            self.prepare(Path(folder), placeholders=True)
            result = inspect_study(Path(folder))
            self.assertFalse(result["machine_structural_complete"])
            self.assertTrue(any("SYNTHETIC_ARM_PLACEHOLDER" in e for e in result["blockers"]))

    def test_04_seal_tamper_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            self.prepare(Path(folder))
            seal = Path(folder) / "seal.json"
            value = json.loads(seal.read_text())
            value["arm_raw_commitments"]["LLM0"] = "1"*64
            seal.write_text(json.dumps(value))
            result = inspect_study(Path(folder))
            self.assertIn("SEAL_INVALID:SEAL_RAW_ARM_DRIFT", result["blockers"])

    def test_05_ambiguous_duplicate_public_json_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            self.prepare(Path(folder))
            public = Path(folder) / "public.json"
            public.write_text(public.read_text().replace(
                '"protocol": "CAPABILITY_BLIND_PUBLIC_V2"',
                '"protocol": "SPOOFED", "protocol": "CAPABILITY_BLIND_PUBLIC_V2"',
                1))
            result = inspect_study(Path(folder))
            self.assertIn("PUBLIC_INVALID:DUPLICATE_JSON_KEY", result["blockers"])

    def test_06_ollama_stale_manifest_not_a_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "manifests/registry.ollama.ai/library/qwen2.5/1.5b"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"layers": [{
                "mediaType": "application/vnd.ollama.image.model",
                "digest": "sha256:" + "a"*64, "size": 100
            }]}))
            result = inspect_ollama_model(root, "qwen2.5/1.5b")
            self.assertTrue(result["manifest_present"])
            self.assertFalse(result["model_bytes_present"])
            self.assertFalse(result["sha256_of_bytes_verified"])
            self.assertFalse(result["selected_as_llm0"])
            self.assertEqual(result["readiness"], "STORAGE_BLOB_MISSING_OR_WRONG_SIZE")

    def test_07_even_present_model_bytes_are_not_hash_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            path = root / "manifests/registry.ollama.ai/library/qwen2.5/1.5b"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"layers":[{
                "mediaType":"application/vnd.ollama.image.model",
                "digest":"sha256:"+"a"*64,"size":3}]}))
            b=root/"blobs"/("sha256-"+"a"*64)
            b.parent.mkdir()
            b.write_bytes(b"bad")
            result=inspect_ollama_model(root,"qwen2.5/1.5b")
            self.assertTrue(result["model_bytes_present"])
            self.assertFalse(result["sha256_of_bytes_verified"])
            self.assertFalse(result["selected_as_llm0"])

    def test_08_no_read_of_private_gold(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            self.prepare(path)
            (path / "gold.json").write_text("{THIS IS NOT JSON AND MUST NOT BE READ")
            result=inspect_study(path)
            self.assertTrue(result["machine_structural_complete"])
            self.assertFalse(result["quality_preservation_certified"])


if __name__ == "__main__":
    unittest.main()
