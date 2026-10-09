from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_issue1_native_grammar_ablation as ablation
from tools import run_issue1_pinned_smollm_probe as probe


class NativeGrammarSingleFactorTests(unittest.TestCase):
    def test_existing_real_baseline_has_stable_16_case_attestation(self):
        baseline = json.loads(ablation.BASELINE.read_text())
        result = ablation.load_baseline(ablation.BASELINE,
                                        model_sha=probe.EXPECTED_MODEL_SHA256,
                                        cli_sha=baseline["runtime"]["llama_cpp_binary_sha256"])
        self.assertEqual(16, len(result["per_case"]))
        self.assertEqual(16, result["observations"]["repeat_raw_response_equal_count"])
        self.assertTrue(result["limits"]["dev_fixture_seen"])
        self.assertFalse(result["limits"]["genuine_v4_authorized_run"])

    def test_llm_artifact_mismatch_blocks_scoring(self):
        baseline = json.loads(ablation.BASELINE.read_text())
        with self.assertRaisesRegex(ValueError, "BASELINE_MODEL_SHA_MISMATCH"):
            ablation.load_baseline(ablation.BASELINE,
                                   model_sha="0" * 64,
                                   cli_sha=baseline["runtime"]["llama_cpp_binary_sha256"])

    def test_prompt_drift_blocks_scoring(self):
        baseline = json.loads(ablation.BASELINE.read_text())
        baseline["prompt_sha256"] = "e" * 64
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "baseline.json"
            path.write_text(json.dumps(baseline))
            with self.assertRaisesRegex(ValueError, "BASELINE_PROMPT_DRIFT"):
                ablation.load_baseline(path,
                                       model_sha=probe.EXPECTED_MODEL_SHA256,
                                       cli_sha=baseline["runtime"]["llama_cpp_binary_sha256"])

    def test_unrepeated_baseline_rejected(self):
        baseline = json.loads(ablation.BASELINE.read_text())
        baseline["observations"]["repeat_raw_response_equal_count"] = 15
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "baseline.json"
            path.write_text(json.dumps(baseline))
            with self.assertRaisesRegex(ValueError, "BASELINE_REPEAT_NOT_VERIFIED"):
                ablation.load_baseline(path,
                                       model_sha=probe.EXPECTED_MODEL_SHA256,
                                       cli_sha=baseline["runtime"]["llama_cpp_binary_sha256"])

    def test_native_grammar_is_only_added_cli_flag(self):
        prompt = "fixed input"
        stdout = "\n\n> fixed input\n\nOPEN\n\n[ Prompt: 1.0 t/s | Generation: 2.0 t/s ]\n\nExiting...\n"
        with patch.object(probe.subprocess, "run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = stdout
            mock_run.return_value.stderr = ""
            regular = probe.run_one(Path("/bin/echo"), Path("/dev/null"), prompt, seconds=5)
            original_command = list(mock_run.call_args.args[0])
            grammar = probe.run_one(Path("/bin/echo"), Path("/dev/null"), prompt,
                                    seconds=5, grammar=ablation.GRAMMAR)
            grammar_command = list(mock_run.call_args.args[0])
        self.assertEqual(original_command + ["--grammar", ablation.GRAMMAR], grammar_command)
        self.assertEqual("OPEN", regular["raw_response"])
        self.assertEqual("OPEN", grammar["raw_response"])


if __name__ == "__main__":
    unittest.main()
