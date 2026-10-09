from __future__ import annotations
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from tools.run_issue1_llm_next_action_v2_local_mac import (
    ARCHIVED, HISTORICAL_BLOB, ROOT, MODEL_BYTES, MODEL_SHA,
    git_blob, load_historical, run_one_local, verify,
)


class QwenNextActionMacCompatibilityTests(unittest.TestCase):
    def test_01_exact_historical_source_is_frozen(self):
        self.assertTrue(ARCHIVED.is_file())
        self.assertEqual(git_blob(ARCHIVED.read_bytes()),HISTORICAL_BLOB)
        source=ARCHIVED.read_text()
        self.assertIn("def grammar_for(work_ids):",source)
        self.assertIn("def run_llm(server_url,fixture,contract,ec_rows):",source)

    def test_02_archived_policies_have_no_modified_fixture_labels(self):
        contract=json.loads((ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json").read_text())
        self.assertEqual(contract["status"],"FROZEN_BEFORE_MODEL_RUN")
        self.assertFalse(contract["fixture_oracle_mutation"])

    def test_03_historical_prompt_does_not_include_oracle_or_category(self):
        original=load_historical()
        fixed=json.loads((ROOT/"fixtures/function_boundary_next_action_v1.json").read_text())
        policy=json.loads((ROOT/"docs/NEXT_ACTION_V2_CONTRACT_2026-10-03.json").read_text())
        one=fixed["fixtures"][0]
        unsafe_token="SECRET_ORACLE_LABEL_SHOULD_NOT_LEAK"
        one=dict(one)
        one["oracle"]={"status":unsafe_token,"work_id":unsafe_token,"reason_code":unsafe_token}
        requests=[]
        def stub(_url,payload,timeout=180):
            requests.append(payload)
            return {"content":"{}"}
        original.post_json=stub
        with contextlib.redirect_stdout(io.StringIO()):
            rows=original.run_llm("DISABLED_TEST_SERVER",
                                  {"fixtures":[one],"policy_contract":fixed["policy_contract"]},
                                  policy,[{"dynamic_context":None}])
        self.assertEqual(len(requests),1)
        self.assertEqual(len(rows),1)
        self.assertNotIn(unsafe_token,json.dumps(requests[0]))
        self.assertNotIn("oracle",requests[0]["prompt"].lower())
        self.assertNotIn("category",requests[0]["prompt"].lower())

    def test_04_constrained_grammar_does_not_reveal_correct_answer(self):
        original=load_historical()
        grammar=original.grammar_for(["work:I20:repair","work:I10:regression"])
        self.assertIn("EXECUTE",grammar)
        self.assertIn("REFRAME",grammar)
        self.assertIn("BLOCKED",grammar)
        self.assertIn("work:I20:repair",grammar)
        self.assertIn("work:I10:regression",grammar)
        self.assertNotIn("SECRET_ORACLE_LABEL",grammar)

    def test_05_malformed_local_binary_rejected_before_inference(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"bad.gguf";file.write_bytes(b"bad")
            with self.assertRaisesRegex(ValueError,"FROZEN_QWEN_MODEL_MISSING_OR_WRONG_SIZE"):
                verify(file,Path("/opt/homebrew/bin/llama-cli"))

    def test_06_response_parser_extracts_only_actual_generated_answer(self):
        stdout="\n\n> prompt-truncated\n\n{\"status\":\"EXECUTE\",\"work_id\":\"work:I20:repair\",\"reason_code\":\"NONE\"}\n\n[ Prompt: 12.0 t/s | Generation: 9.0 t/s ]"
        mocked=SimpleNamespace(returncode=0,stdout=stdout,stderr="")
        with patch("tools.run_issue1_llm_next_action_v2_local_mac.subprocess.run",return_value=mocked):
            v=run_one_local(Path("/fake/llama"),Path("/fake/model"),"prompt","root ::= \"x\"",5)
        self.assertIn("EXECUTE",v["raw_response"])
        self.assertEqual(len(v["stdout_sha256"]),64)

    def test_07_llm_cli_nonzero_fails_closed(self):
        mocked=SimpleNamespace(returncode=2,stdout="",stderr="GRAMMAR_INVALID")
        with patch("tools.run_issue1_llm_next_action_v2_local_mac.subprocess.run",return_value=mocked):
            with self.assertRaisesRegex(RuntimeError,"PINNED_NATIVE_INFERENCE_FAILED"):
                run_one_local(Path("/fake/llama"),Path("/fake/model"),"prompt","root ::= \"x\"",5)

    def test_08_local_wrapper_does_not_auto_download_model(self):
        src=(ROOT/"tools/run_issue1_llm_next_action_v2_local_mac.py").read_text()
        self.assertNotIn("urllib.request",src)
        self.assertNotIn("extractall(",src)
        self.assertIn("archived.post_json=local_completion",src)


if __name__=="__main__":
    unittest.main()
