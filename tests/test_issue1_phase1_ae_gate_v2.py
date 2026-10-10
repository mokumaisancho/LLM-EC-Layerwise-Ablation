"""Issue #61 adversarial replay tests (development-only, not scientific cases)."""
from __future__ import annotations

import copy
import hashlib
import unittest
from dataclasses import replace
from pathlib import Path

from tools.issue1_phase1_ae_gate_v1 import (
    ARMS, LAYERS, h, verify as unsafe_structural_v1,
)
from tools.issue1_phase1_ae_gate_v2 import (
    Binding, KINDS, PROTOCOL, TrustedReplay, verify,
)

# Deliberately transparent toy implementations, never considered native EC
# qualification or live model evidence. Replay authority pins this module.


def llm_s1(public, prior, seed, model_id, params):
    return {"stage": "S1", "query": public["query"], "model": model_id}


def llm_s2(public, prior, seed, model_id, params):
    return {"stage": "S2", "input": prior, "model": model_id}


def llm_s3(public, prior, seed, model_id, params):
    return {"stage": "S3", "input": prior, "model": model_id}


def llm_s4(public, prior, seed, model_id, params):
    return {"stage": "S4", "input": prior, "model": model_id}


def fixed_s1(public, prior, seed, model_id, params):
    return {"stage": "FIX1", "query": public["query"]}


def fixed_s2(public, prior, seed, model_id, params):
    return {"stage": "FIX2", "input": prior}


def ec_s3(public, prior, seed, model_id, params):
    return {"stage": "EC3", "input": prior}


def ec_s4(public, prior, seed, model_id, params):
    return {"stage": "EC4", "input": prior}


def judge(public, final_s4, gold):
    return final_s4 == gold["oracle_layers"]["S4"]


def illicit_gold_receiving_engine(public, prior, seed, model, params, gold):
    return gold["oracle_layers"]["S2"]


ENGINES = {
    "llm_s1": llm_s1, "llm_s2": llm_s2,
    "llm_s3": llm_s3, "llm_s4": llm_s4,
    "fixed_s1": fixed_s1, "fixed_s2": fixed_s2,
    "ec_s3": ec_s3, "ec_s4": ec_s4,
}


def make_fixture():
    path = Path(__file__).resolve()
    source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    bindings = {
        engine_id: Binding(engine_id, KINDS[engine_id], path, source_sha,
                           "development-toy-v1", 17, {"temperature": 0},
                           fn)
        for engine_id, fn in ENGINES.items()
    }
    judge_binding = Binding(
        "independent_judge", "JUDGE", path, source_sha,
        "development-only-judge-v1", 17, {}, judge)
    authority = TrustedReplay(bindings, judge_binding)
    cid = "dev-only-not-held-out"
    public = {"query": "public task input no hidden Oracle", "nonce": 7}
    oracle = {layer: {"oracle": layer} for layer in LAYERS}
    oracle["S4"] = {"oracle": "S4", "end": True}
    gold = {
        "protocol": "ISSUE1_PHASE1_GOLD_V1",
        "fixture_commit": "f" * 40,
        "materiality": 0.2,
        "cases": [{
            "case_id": cid, "oracle_layers": oracle,
            "label": True, "family": "development-only",
        }],
    }
    row = {"case_id": cid, "input_sha256": h(public), "arms": []}
    for arm in ARMS:
        trace = authority.replay(public, gold["cases"][0], arm, row["input_sha256"])
        row["arms"].append({
            "arm": arm, "input_sha256": row["input_sha256"],
            "layers": trace["layers"],
            "upstream": trace["upstream"],
            "stage_receipts": trace["stage_receipts"],
            "implementation": ("ORACLE_INTERVENTION" if arm.startswith("E_")
                               else "NATIVE_EC" if arm in ("B", "D") else "LLM"),
            "final_success": trace["final_success"],
        })
    raw = {
        "protocol": PROTOCOL, "fixture_commit": "f" * 40,
        "materiality": 0.2, "cases": [row],
    }
    return raw, gold, {cid: public}, authority


def repair_self_reported_hashes(row, arm):
    """Adversarial rehashing that fooled frozen v1; not a trusted replay."""
    layers = arm["layers"]
    for i, layer in enumerate(LAYERS):
        upstream = row["input_sha256"] if i == 0 else h(layers[LAYERS[i-1]])
        arm["upstream"][layer] = upstream
        arm["stage_receipts"][layer]["upstream_sha256"] = upstream
        arm["stage_receipts"][layer]["output_sha256"] = h(layers[layer])


class AEGateV2Test(unittest.TestCase):
    def setUp(self):
        self.raw, self.gold, self.public, self.authority = make_fixture()

    def audit(self):
        return verify(self.raw, self.gold, self.public, self.authority)

    def test_clean_matched_replay_is_diagnostic_not_scientific(self):
        result = self.audit()
        self.assertTrue(result["source_bound_deterministic_replay_verified"])
        self.assertEqual(result["replayed_stages"], 32)
        self.assertFalse(result["original_phase1_complete"])
        self.assertFalse(result["original_AC18_pass_automatically"])
        self.assertFalse(result["scientific_native_qualification"])

    def test_all_four_e_only_target_stage_is_oracle(self):
        self.audit()
        for arm in self.raw["cases"][0]["arms"][4:]:
            for layer in LAYERS:
                receipt = arm["stage_receipts"][layer]
                self.assertEqual(
                    receipt["oracle_intervention"], arm["arm"] == "E_" + layer)
                if layer != arm["arm"][2:]:
                    self.assertEqual(
                        receipt["engine_id"],
                        "llm_" + layer.lower())

    def test_reject_triple_nontarget_oracle_mutations_even_rehashed(self):
        for index, changed_layer in ((4, "S2"), (5, "S3"), (6, "S4")):
            with self.subTest(changed_layer=changed_layer):
                raw, gold, public, authority = make_fixture()
                row = raw["cases"][0]
                arm = row["arms"][index]
                arm["layers"][changed_layer] = {"additional_oracle_override": True}
                repair_self_reported_hashes(row, arm)
                # Historical v1 had the false positive; v2 must not.
                old = copy.deepcopy(raw)
                old["protocol"] = "ISSUE1_PHASE1_AE_RAW_V1"
                for case in old["cases"]:
                    for item in case["arms"]:
                        del item["stage_receipts"]
                self.assertTrue(
                    unsafe_structural_v1(old, gold)["all_arm_and_hash_gates_passed"])
                with self.assertRaisesRegex(
                    ValueError, "G8_STAGE_OUTPUT_REPLAY_MISMATCH"):
                    verify(raw, gold, public, authority)

    def test_self_authored_engine_identity_rejected(self):
        self.raw["cases"][0]["arms"][4]["stage_receipts"]["S2"][
            "engine_id"] = "untrusted_oracle_s2"
        with self.assertRaisesRegex(ValueError, "G8_RECEIPT_REPLAY_MISMATCH"):
            self.audit()

    def test_self_authored_fingerprint_rejected(self):
        self.raw["cases"][0]["arms"][4]["stage_receipts"]["S2"][
            "engine_fingerprint"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "G8_RECEIPT_REPLAY_MISMATCH"):
            self.audit()

    def test_missing_receipt_rejected(self):
        del self.raw["cases"][0]["arms"][4]["stage_receipts"]["S2"]
        with self.assertRaisesRegex(ValueError, "G8_RECEIPT_COVERAGE"):
            self.audit()

    def test_fake_source_pin_rejected(self):
        self.authority.engines["llm_s2"] = replace(
            self.authority.engines["llm_s2"], pinned_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "G8_ENGINE_SOURCE_PIN_MISMATCH"):
            self.audit()

    def test_callback_not_from_bound_source_rejected(self):
        import json
        self.authority.engines["llm_s2"] = replace(
            self.authority.engines["llm_s2"], fn=json.dumps)
        with self.assertRaisesRegex(
            (ValueError, TypeError), "G8_ENGINE_CALLBACK_NOT_FROM_PINNED_FILE"):
            self.audit()

    def test_missing_trusted_runner_rejected(self):
        with self.assertRaisesRegex(ValueError, "G8_TRUSTED_REPLAY_REQUIRED"):
            verify(self.raw, self.gold, self.public, None)

    def test_forged_final_outcome_rejected(self):
        item = self.raw["cases"][0]["arms"][0]
        item["final_success"] = not item["final_success"]
        with self.assertRaisesRegex(
            ValueError, "G8_FINAL_SUCCESS_REPLAY_MISMATCH"):
            self.audit()

    def test_public_input_mismatch_rejected(self):
        cid = self.raw["cases"][0]["case_id"]
        self.public[cid]["query"] = "altered task"
        with self.assertRaisesRegex(ValueError, "G8_PUBLIC_INPUT_HASH_MISMATCH"):
            self.audit()

    def test_duplicate_arm_rejected_by_legacy_gate(self):
        self.raw["cases"][0]["arms"][1]["arm"] = "A"
        with self.assertRaisesRegex(ValueError, "G10_DUPLICATE_OR_UNKNOWN_ARM"):
            self.audit()

    def test_mutated_upstream_rejected_by_legacy_gate(self):
        self.raw["cases"][0]["arms"][5]["upstream"]["S4"] = "tampered"
        with self.assertRaisesRegex(ValueError, "G4_BROKEN_LAYER_HASH_CHAIN"):
            self.audit()

    def test_attempt_to_pass_gold_into_normal_engine_fails(self):
        self.authority.engines["llm_s2"] = replace(
            self.authority.engines["llm_s2"], fn=illicit_gold_receiving_engine)
        with self.assertRaisesRegex(ValueError, "G8_STAGE_REPLAY_ERROR"):
            self.audit()

    def test_wrong_v1_protocol_not_silent_upcast(self):
        self.raw["protocol"] = "ISSUE1_PHASE1_AE_RAW_V1"
        with self.assertRaisesRegex(ValueError, "G8_PROTOCOL_V2_REQUIRED"):
            self.audit()


if __name__ == "__main__":
    unittest.main()
