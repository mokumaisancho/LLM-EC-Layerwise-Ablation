"""Issue #1 original 18-AC dependency/completion TCC v13 adversarial tests."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_issue1_original_phase1_tcc_v13 import (
    NODES, PLAN_PATH, STEPS, git_pins, load_plan, manifest,
    model_seal, run,
)
from tests.test_issue1_phase1_ae_gate_v2 import (
    make_fixture, repair_self_reported_hashes,
)

TCC = Path("/private/tmp/llmec-tcc-generator-reference-20261009")
ORIGINAL_NATIVE = Path("/private/tmp/issue1-ec-native-layerwise-20261010")
POLICY_NATIVE = Path("/private/tmp/issue59-60-policy-v2")
MODEL = Path(
    "/private/tmp/llmec-qwen-comparison-20261009/"
    "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf")
HAS_NATIVE = TCC.is_dir() and ORIGINAL_NATIVE.is_dir() and POLICY_NATIVE.is_dir()


class Phase1OneCallTCCV13Test(unittest.TestCase):
    def test_normative_AC20_MVP18_and_work_matrix_exact(self):
        p, norm = load_plan()
        self.assertEqual(len(norm["order"]), 20)
        self.assertEqual(len(p["original_mvp_required"]), 18)
        self.assertEqual(p["post_mvp"], ["AC-10", "AC-18"])
        self.assertEqual(set(p["ac_work_gates"]), set(
            f"AC-{n:02d}" for n in range(1, 21)))
        self.assertEqual(p["frozen_materiality_abs"], 0.20)
        self.assertEqual(p["frozen_tie_abs"], 0.10)
        self.assertEqual(list(p["work_gates"]), list(STEPS))
        self.assertEqual(len(STEPS), 11)

    def test_graph_has_one_success_and_explicit_blocker_terminals(self):
        m = manifest()
        self.assertEqual(m["entry_nodes"], [NODES[0]])
        self.assertEqual(len(m["nodes"]), 18)
        self.assertEqual(
            [x["id"] for x in m["nodes"]
             if x["kind"] == "terminal" and
             x["terminal_status"] == "SUCCESS"],
            ["root_science_verified"])
        self.assertTrue(all(x in m["tcc_id"] for x in ("S1-S4", "AC18")))

    def test_source_sha_cannot_be_self_forged(self):
        with patch(
            "tools.run_issue1_original_phase1_tcc_v13.git_blob",
            return_value="0" * 40
        ):
            with self.assertRaisesRegex(
                ValueError, "G0_TRUSTED_SOURCE_BLOB_DRIFT"):
                git_pins()

    def test_unqualified_model_size_rejected(self):
        _, context = load_plan()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "model.gguf"
            path.write_bytes(b"fake small file")
            with self.assertRaisesRegex(
                    ValueError, "G12_MODEL_CAPACITY_SIZE_MISMATCH"):
                model_seal(path, context["norm"])

    def test_unprovided_model_never_claims_inference(self):
        _, context = load_plan()
        info = model_seal(None, context["norm"])
        self.assertFalse(info["asset_verified"])
        self.assertFalse(info["inference_qualified"])

    @unittest.skipUnless(MODEL.is_file(), "Actual pinned local 0.5B model absent")
    def test_frozen_model_file_sha_and_size(self):
        _, context = load_plan()
        info = model_seal(MODEL, context["norm"])
        self.assertEqual(info["status"], "PINNED_0P5B_ASSET_VERIFIED")
        self.assertFalse(info["inference_qualified"])
        self.assertEqual(info["bytes"], 397808192)

    @unittest.skipUnless(HAS_NATIVE, "Pinned TCC/native checkout absent")
    def test_actual_compiled_onecall_stops_truthfully_with_model(self):
        result = run(TCC, ORIGINAL_NATIVE, POLICY_NATIVE,
                     MODEL if MODEL.is_file() else None)
        self.assertEqual(result["TCC_terminal"], "blocked_semantics")
        self.assertEqual(result["original_mvp"]["required"], 18)
        self.assertEqual(result["original_mvp"]["pass"], 2)
        self.assertEqual(result["original_mvp"]["unproven"], 16)
        self.assertEqual(len(result["AC20_dependency_ledger"]), 20)
        self.assertEqual(len(result["AC20_topological_order"]), 20)
        self.assertEqual(len(result["work_state_by_dependency"]), 11)
        self.assertEqual(result["work_state_by_dependency"][STEPS[1]],
                         "PASS_MACHINE_FEASIBLE_V12_ONLY")
        self.assertEqual(
            result["work_state_by_dependency"][STEPS[4]],
            "BLOCKED_INDEPENDENT_NATURAL_LANGUAGE_S3")
        self.assertFalse(result["scientific_phase1_complete"])
        self.assertTrue(result["source_and_user_data_seals_stable"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(set(
            a for a, item in result["AC20_dependency_ledger"].items()
            if item["state"] == "PASS"), {"AC-19", "AC-20"})

    @unittest.skipUnless(HAS_NATIVE, "Pinned TCC/native checkout absent")
    def test_missing_model_runs_machine_gates_but_no_false_science(self):
        result = run(TCC, ORIGINAL_NATIVE, POLICY_NATIVE)
        self.assertEqual(result["TCC_terminal"], "blocked_semantics")
        self.assertFalse(result["qualified_model_asset"]["asset_verified"])
        self.assertEqual(len(result["work_state_by_dependency"]), 11)
        self.assertEqual(result["original_mvp"]["pass"], 2)

    @unittest.skipUnless(HAS_NATIVE, "Pinned TCC/native checkout absent")
    def test_incomplete_real_AE_input_rejected_upfront(self):
        raw, _, _, _ = make_fixture()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "only_raw.json"
            p.write_text(json.dumps(raw))
            with self.assertRaisesRegex(
                ValueError, "G6_INCOMPLETE_RAW_GOLD_PUBLIC_TRIPLET"):
                run(TCC, ORIGINAL_NATIVE, POLICY_NATIVE, arms=p)

    @unittest.skipUnless(HAS_NATIVE, "Pinned TCC/native checkout absent")
    def test_author_created_raw_replay_without_trusted_runner_not_science(self):
        raw, hidden, public, _ = make_fixture()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            a, g, p = td / "arms.json", td / "gold.json", td / "public.json"
            a.write_text(json.dumps(raw))
            g.write_text(json.dumps(hidden))
            p.write_text(json.dumps(public))
            result = run(TCC, ORIGINAL_NATIVE, POLICY_NATIVE,
                         arms=a, gold=g, public=p)
        self.assertEqual(
            result["work_state_by_dependency"][STEPS[6]],
            "BLOCKED_UNTRUSTED_RAW_RECEIPTS_NO_REPLAY_AUTHORITY")
        self.assertEqual(result["original_mvp"]["pass"], 2)
        self.assertIsNone(result["optional_structural_replay"])
        self.assertEqual(result["TCC_terminal"], "blocked_semantics")
        self.assertTrue(result["source_and_user_data_seals_stable"])

    @unittest.skipUnless(HAS_NATIVE, "Pinned TCC/native checkout absent")
    def test_toy_replay_passes_structure_without_original_AC_promotion(self):
        raw, hidden, public, trusted = make_fixture()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            a, g, p = td / "arms.json", td / "gold.json", td / "public.json"
            a.write_text(json.dumps(raw))
            g.write_text(json.dumps(hidden))
            p.write_text(json.dumps(public))
            result = run(TCC, ORIGINAL_NATIVE, POLICY_NATIVE,
                         arms=a, gold=g, public=p, trusted_replay=trusted)
        self.assertEqual(result["TCC_terminal"], "blocked_semantics")
        self.assertEqual(result["optional_structural_replay"]["stages"], 32)
        self.assertFalse(result["optional_structural_replay"][
            "independent_oracle_custody_verified"])
        self.assertEqual(result["original_mvp"]["pass"], 2)

    @unittest.skipUnless(HAS_NATIVE, "Pinned TCC/native checkout absent")
    def test_original_AC_child_never_passes_unmet_parent(self):
        result = run(TCC, ORIGINAL_NATIVE, POLICY_NATIVE)
        ledger = result["AC20_dependency_ledger"]
        self.assertIn("AC-02", ledger["AC-01"]["unmet_AC_parents"])
        self.assertIn("AC-05", ledger["AC-08"]["unmet_AC_parents"])
        self.assertIn("W04_CHECK_S3_SEMANTICS",
                      ledger["AC-11"]["unqualified_work"])
        self.assertIn("W05_CHECK_S4_COMPLETENESS",
                      ledger["AC-11"]["unqualified_work"])
        self.assertEqual(ledger["AC-19"]["state"], "PASS")
        self.assertEqual(ledger["AC-20"]["state"], "PASS")
        self.assertEqual(ledger["AC-09"]["state"], "NOT_PROVEN")
        self.assertIn("W03_CHECK_LLM_CAPACITY",
                      ledger["AC-13"]["unqualified_work"])
        self.assertIn("W03_CHECK_LLM_CAPACITY",
                      ledger["AC-14"]["unqualified_work"])
        self.assertIn("W03_CHECK_LLM_CAPACITY",
                      ledger["AC-15"]["unqualified_work"])

    @unittest.skipUnless(HAS_NATIVE, "Pinned TCC/native checkout absent")
    def test_result_overturning_gold_mutation_after_replay_fails_closed(self):
        raw, hidden, public, trusted = make_fixture()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            a, g, p = td / "arms.json", td / "gold.json", td / "public.json"
            a.write_text(json.dumps(raw))
            g.write_text(json.dumps(hidden))
            p.write_text(json.dumps(public))
            from tools.issue1_phase1_ae_gate_v2 import verify as real_replay
            def valid_then_corrupt(*args):
                response = real_replay(*args)
                g.write_text(g.read_text() + " ")
                return response
            with patch(
                    "tools.run_issue1_original_phase1_tcc_v13.replay_v2",
                    side_effect=valid_then_corrupt):
                result = run(TCC, ORIGINAL_NATIVE, POLICY_NATIVE,
                             arms=a, gold=g, public=p, trusted_replay=trusted)
        self.assertEqual(result["TCC_terminal"], "blocked_integrity")
        self.assertTrue(any("G7_RAW_GOLD_PUBLIC_CHANGED_DURING_TRIAL" in x
                            for x in result["errors"]))
        self.assertFalse(result["scientific_phase1_complete"])

    @unittest.skipUnless(HAS_NATIVE, "Pinned TCC/native checkout absent")
    def test_extra_E_layer_oracle_fails_the_entire_tcc(self):
        raw, hidden, public, trusted = make_fixture()
        row = raw["cases"][0]
        arm = row["arms"][4]  # E_S1 with illicit S2
        arm["layers"]["S2"] = {"additional_oracle_override": True}
        repair_self_reported_hashes(row, arm)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            a, g, p = td / "arms.json", td / "gold.json", td / "public.json"
            a.write_text(json.dumps(raw))
            g.write_text(json.dumps(hidden))
            p.write_text(json.dumps(public))
            result = run(TCC, ORIGINAL_NATIVE, POLICY_NATIVE,
                         arms=a, gold=g, public=p, trusted_replay=trusted)
        self.assertEqual(result["TCC_terminal"], "blocked_integrity")
        self.assertTrue(any("G8_STAGE_OUTPUT_REPLAY_MISMATCH" in e
                            for e in result["errors"]))
        self.assertFalse(result["scientific_phase1_complete"])
        self.assertEqual(result["original_mvp"]["pass"], 2)


if __name__ == "__main__":
    unittest.main()
