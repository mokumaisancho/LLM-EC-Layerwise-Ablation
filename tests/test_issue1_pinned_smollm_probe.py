from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_issue1_pinned_smollm_probe as probe


class PinnedSmollmProbeTests(unittest.TestCase):
    def make_fake_llama(self, directory: Path, *, output="OPEN", truncate=False, rc=0):
        p = directory / "fake-llama"
        script = (
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "v=sys.argv\n"
            "prompt=v[v.index('-p')+1]\n"
            f"prompt=(prompt[:450]+' ... (truncated)') if {truncate!r} else prompt\n"
            f"sys.stdout.write('banner\\n\\n> '+prompt+'\\n\\n'+{output!r}+'\\n\\n[ Prompt: 40 t/s | Generation: 30 t/s ]\\n\\nExiting...\\n')\n"
            f"sys.exit({rc})\n"
        )
        p.write_text(script, encoding="utf-8")
        p.chmod(0o700)
        return p

    def test_long_display_truncation_preserves_actual_raw_model_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = self.make_fake_llama(Path(tmp), output="OPEN", truncate=True)
            prompt = "Frozen protocol " + ("a long prompt " * 70)
            out = probe.run_one(fake, Path("/dev/null"), prompt, seconds=5)
            self.assertEqual(out["raw_response"], "OPEN")
            self.assertEqual(out["parsed_action"], "OPEN")

    def test_format_deviations_are_not_silently_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = self.make_fake_llama(Path(tmp), output="OPEN -> CLOSE")
            out = probe.run_one(fake, Path("/dev/null"), "p", seconds=5)
            self.assertEqual(out["raw_response"], "OPEN -> CLOSE")
            self.assertEqual(out["parsed_action"], "FORMAT_ERROR")

    def test_nonzero_exit_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = self.make_fake_llama(Path(tmp), rc=19)
            with self.assertRaisesRegex(RuntimeError, "MODEL_INFERENCE_FAILED:19"):
                probe.run_one(fake, Path("/dev/null"), "p", seconds=5)

    def test_model_bytes_must_match_exact_pinned_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "SmolLM2-135M-Instruct-Q4_K_M.gguf"
            p.write_bytes(b"not a valid gguf")
            with self.assertRaisesRegex(ValueError, "MODEL_SIZE_MISMATCH"):
                probe.verify_model(p)

    def test_fixture_coverage_kept_at_all_16_cases_and_study_not_certified(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = self.make_fake_llama(Path(tmp))
            result = {
                "raw_response": "OPEN", "parsed_action": "OPEN",
                "full_cli_stdout_sha256": "0" * 64,
                "full_cli_stdout_bytes": 2,
                "raw_stderr_sha256": "1" * 64,
            }
            with patch.object(probe, "verify_model", return_value={"sha": "fake"}), \
                 patch.object(probe, "run_one", return_value=result) as invoked:
                got = probe.run(Path("/dev/null"), fake, 5)
            self.assertEqual(invoked.call_count, 16)
            self.assertEqual(got["case_count"], 16)
            self.assertFalse(got["independent_test_set"])
            self.assertFalse(got["true_original_llm0_verified"])
            self.assertFalse(got["genuine_authorized_v4_run"])
            self.assertIsNone(got["scientific_retention_score"])
            self.assertEqual(got["four_arm_quality_claim"], "NOT_ESTABLISHED")

    def test_missing_display_marker_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "no-marker"
            p.write_text("#!/usr/bin/env python3\nprint('no model response UI delimiter')\n")
            p.chmod(0o700)
            with self.assertRaisesRegex(RuntimeError, "MODEL_INPUT_MARKER_MISSING"):
                probe.run_one(p, Path("/dev/null"), "x", seconds=5)


if __name__ == "__main__":
    unittest.main()
