from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_issue1_qwen25_capacity_format_sweep as sweep
from tools import run_issue1_qwen_tcc_generator_lane as tcc_lane


class Issue1QwenSweepAndTCCTests(unittest.TestCase):
    def test_01_model_pins_are_source_frozen(self):
        self.assertEqual(
            "6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653",
            sweep.MODELS["qwen25_0p5b"]["sha256"])
        self.assertEqual(
            "1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370",
            sweep.MODELS["qwen25_1p5b"]["sha256"])
        self.assertEqual(len(sweep.TREATMENTS), 2)

    def test_02_mismatched_model_file_size_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"
            path.write_bytes(b"fake_model")
            with self.assertRaisesRegex(ValueError, "MODEL_MISSING_OR_WRONG_BYTES"):
                sweep.verify(path,sweep.MODELS["qwen25_0p5b"])

    def test_03_64_calls_and_identical_prompt_per_model_per_case(self):
        with tempfile.TemporaryDirectory() as temporary:
            tmp=Path(temporary)
            for spec in sweep.MODELS.values():
                (tmp/spec["filename"]).write_bytes(b"placeholder")
            cli=tmp/"llama-cli"
            cli.write_bytes(b"some_binary")
            invoked=[]
            def fake_run_one(llama, model, prompt, *, seconds, grammar=None):
                invoked.append((model.name, prompt, grammar))
                raw = "CLOSE" if grammar is not None else "CLOSE -> OPEN"
                return {"raw_response":raw, "parsed_action": "CLOSE" if grammar is not None else "FORMAT_ERROR",
                        "full_cli_stdout_sha256":"d"*64,"raw_stderr_sha256":"e"*64}
            with patch.object(sweep,"verify",return_value=None), patch.object(sweep,"run_one",side_effect=fake_run_one):
                actual=sweep.run(tmp,cli,15,head="test:source")
            self.assertEqual(len(invoked),64)
            self.assertEqual(actual["runtime"]["expected_total_model_invocations"],64)
            self.assertEqual(len(actual["paired_cases"]),16)
            self.assertEqual(actual["observations"]["qwen25_0p5b"]["native_gbnf"]["label_format_compliant"],16)
            self.assertEqual(actual["observations"]["qwen25_1p5b"]["unconstrained"]["format_error"],16)
            for idx in range(0,64,4):
                a=invoked[idx:idx+4]
                self.assertEqual({v[1] for v in a},{a[0][1]})
                self.assertEqual([v[2] for v in a],[None,sweep.GRAMMAR,None,sweep.GRAMMAR])
            self.assertFalse(actual["independent_corpus"])
            self.assertFalse(actual["genuine_v4_authorized"])
            self.assertEqual(actual["scientific_four_arm_study"],"NOT_RUN")

    def test_04_tcc_spec_declares_diagnostic_not_scientific_certification(self):
        spec=tcc_lane.spec()
        self.assertEqual(spec["schema"],"tcc.spec.v3")
        self.assertEqual(spec["entry_nodes"],["verify_pin"])
        self.assertEqual(len(spec["nodes"]),5)
        self.assertEqual({n["id"] for n in spec["nodes"]},
                         {"verify_pin","run_actual_paired_sweep","diagnostic_only_complete","blocked_pin","blocked_sweep"})
        self.assertEqual(spec["immutable_state_keys"],[])
        self.assertIn("cannot close issue #1", " ".join(spec["acceptance"]))

    def test_05_tcc_pin_is_exact(self):
        self.assertEqual(
            "786d52c1efbc9271096f9311d768ef49bcd116e2",
            tcc_lane.TCC_SOURCE)

    def test_06_sweep_does_not_read_any_gold(self):
        self.assertFalse(sweep.CONTRACT["scientific_performance_certification"])
        self.assertTrue(sweep.CONTRACT["non_independent_external_gold"])
        self.assertEqual(sweep.CONTRACT["benchmark"],"EXPOSED_H01_H16_ONLY")


if __name__=="__main__":
    unittest.main()
