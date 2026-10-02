from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "run_ec_s3_s4.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_ec_s3_s4_tested", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("runner import failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ECBindingTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_runner()

    def make_repo(self, protocol: str):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        module = root / "01_repo" / "src" / "v4" / "ec_residual_detector.py"
        module.parent.mkdir(parents=True)
        module.write_text(
            "PROTOCOL = " + repr(protocol) + "\n"
            "def detect_residuals(intent, framing, observations=None):\n"
            "    return {'protocol': PROTOCOL, 'residuals': []}\n",
            encoding="utf-8",
        )
        return tmp, root

    def test_correct_pinned_residual_module_is_nonreportable_for_full_s3_s4(self):
        tmp, root = self.make_repo(self.mod.EC_V4_4_RESIDUAL_PROTOCOL)
        self.addCleanup(tmp.cleanup)
        original = self.mod.git_head
        self.mod.git_head = lambda _: self.mod.EC_V4_4_COMMIT
        self.addCleanup(setattr, self.mod, "git_head", original)
        ec, provenance = self.mod.load_ecv44_residual_detector(root)
        self.assertEqual(ec.PROTOCOL, self.mod.EC_V4_4_RESIDUAL_PROTOCOL)
        self.assertFalse(provenance["reportable_as_full_s3_s4"])
        self.assertEqual(provenance["authority"], "EC_NATIVE")
        self.assertEqual(len(provenance["module_sha256"]), 64)

    def test_commit_mismatch_fails_closed(self):
        tmp, root = self.make_repo(self.mod.EC_V4_4_RESIDUAL_PROTOCOL)
        self.addCleanup(tmp.cleanup)
        original = self.mod.git_head
        self.mod.git_head = lambda _: "0" * 40
        self.addCleanup(setattr, self.mod, "git_head", original)
        with self.assertRaisesRegex(RuntimeError, "EC_COMMIT_MISMATCH"):
            self.mod.load_ecv44_residual_detector(root)

    def test_protocol_mismatch_fails_closed(self):
        tmp, root = self.make_repo("WRONG_PROTOCOL")
        self.addCleanup(tmp.cleanup)
        original = self.mod.git_head
        self.mod.git_head = lambda _: self.mod.EC_V4_4_COMMIT
        self.addCleanup(setattr, self.mod, "git_head", original)
        with self.assertRaisesRegex(RuntimeError, "EC_PROTOCOL_MISMATCH"):
            self.mod.load_ecv44_residual_detector(root)

    def test_full_run_is_adapter_gated(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("EC_NATIVE_ADAPTER_REQUIRED", text)
        self.assertIn("PHASE1_EC_NATIVE_ADAPTER_V1", text)
        self.assertIn("ECV4_4_RESIDUAL_DIAGNOSTIC_NONREPORTABLE", text)
        self.assertNotIn("ECV4_4_REPORTABLE", text)
        self.assertNotIn("FALLBACK_NO_EC_PATH", text)


if __name__ == "__main__":
    unittest.main()
