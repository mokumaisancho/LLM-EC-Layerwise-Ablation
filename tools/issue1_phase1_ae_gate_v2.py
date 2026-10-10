#!/usr/bin/env python3
"""Issue #61: target-only Oracle replay gate (v2, additive to frozen v1).

An untrusted raw trace or self-reported receipt NEVER establishes provenance.
A separately supplied, source-pinned deterministic replay authority executes
every non-Oracle stage again; only E's target stage reads hidden Oracle data.
Neither this structural re-execution nor synthetic tests establish science.
"""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from tools.issue1_phase1_ae_gate_v1 import ARMS, LAYERS, h, must, verify as verify_v1

PROTOCOL = "ISSUE1_PHASE1_AE_RAW_V2"
AUDIT_PROTOCOL = "ISSUE1_PHASE1_AE_AUDIT_V2"
PLAN = {
    "A": ("llm_s1", "llm_s2", "llm_s3", "llm_s4"),
    "B": ("llm_s1", "llm_s2", "ec_s3", "ec_s4"),
    "C": ("fixed_s1", "fixed_s2", "llm_s3", "llm_s4"),
    "D": ("fixed_s1", "fixed_s2", "ec_s3", "ec_s4"),
}
KINDS = {
    "llm_s1": "LLM", "llm_s2": "LLM",
    "llm_s3": "LLM", "llm_s4": "LLM",
    "fixed_s1": "FIXED", "fixed_s2": "FIXED",
    "ec_s3": "NATIVE_EC", "ec_s4": "NATIVE_EC",
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Binding:
    """Verifier-owned executable binding, NOT metadata copied from the raw."""
    engine_id: str
    kind: str
    source_file: Path
    pinned_sha256: str
    model_id: str
    seed: int
    parameters: Mapping
    fn: Callable

    def identity(self) -> dict:
        path = self.source_file
        must(path.is_file() and not path.is_symlink(), "G8_ENGINE_SOURCE_UNAVAILABLE")
        must(Path(inspect.getfile(self.fn)).resolve() == path.resolve(),
             "G8_ENGINE_CALLBACK_NOT_FROM_PINNED_FILE")
        actual = sha_bytes(path.read_bytes())
        must(actual == self.pinned_sha256 and len(actual) == 64,
             "G8_ENGINE_SOURCE_PIN_MISMATCH:" + self.engine_id)
        must(type(self.seed) is int and isinstance(self.model_id, str)
             and bool(self.model_id) and isinstance(self.parameters, Mapping),
             "G8_ENGINE_CONFIG_INVALID")
        return {
            "engine_id": self.engine_id, "kind": self.kind,
            "source_sha256": actual, "model_id": self.model_id,
            "seed": self.seed, "parameters": dict(self.parameters),
        }


class TrustedReplay:
    """Pretrusted local replay bindings are injected by the verifier/operator.

    This does not certify that a model is independent, oracle-blind, or that
    its frozen source is semantically valid; such evidence must be separate.
    """

    def __init__(self, engines: Mapping[str, Binding], judge: Binding):
        self.engines = dict(engines)
        self.judge = judge

    def seals(self) -> dict:
        must(set(self.engines) == set(KINDS), "G8_ENGINE_REGISTRY_INCOMPLETE")
        out = {}
        for engine_id, kind in KINDS.items():
            binding = self.engines[engine_id]
            must(binding.engine_id == engine_id and binding.kind == kind,
                 "G8_ENGINE_IDENTITY_INVALID:" + engine_id)
            out[engine_id] = h(binding.identity())
        must(self.judge.engine_id == "independent_judge"
             and self.judge.kind == "JUDGE", "G8_JUDGE_IDENTITY_INVALID")
        out["independent_judge"] = h(self.judge.identity())
        return out

    @staticmethod
    def base_engine(arm: str, layer_index: int) -> str:
        if arm.startswith("E_"):
            return PLAN["A"][layer_index]
        return PLAN[arm][layer_index]

    def replay(self, public_input: object, gold_case: dict, arm: str,
               input_sha256: str) -> dict:
        must(arm in ARMS, "G8_UNKNOWN_ARM")
        values, upstream, receipts = {}, {}, {}
        previous = None
        for index, layer in enumerate(LAYERS):
            stage_input_hash = input_sha256 if index == 0 else h(previous)
            upstream[layer] = stage_input_hash
            is_oracle = arm == "E_" + layer
            if is_oracle:
                output = copy.deepcopy(gold_case["oracle_layers"][layer])
                receipt = {
                    "engine_id": "ORACLE_TARGET_ONLY",
                    "engine_fingerprint": "SEALED_GOLD_V1",
                    "upstream_sha256": stage_input_hash,
                    "output_sha256": h(output),
                    "oracle_intervention": True,
                }
            else:
                engine_id = self.base_engine(arm, index)
                binding = self.engines[engine_id]
                identity = binding.identity()
                safe_public = copy.deepcopy(public_input)
                safe_previous = copy.deepcopy(previous)
                try:
                    output = binding.fn(
                        safe_public, safe_previous, binding.seed,
                        binding.model_id, copy.deepcopy(dict(binding.parameters)))
                    output_hash = h(output)
                except Exception as exc:
                    raise ValueError("G8_STAGE_REPLAY_ERROR:" + layer) from exc
                must(h(public_input) == input_sha256,
                     "G8_PUBLIC_INPUT_MUTATED")
                receipt = {
                    "engine_id": engine_id,
                    "engine_fingerprint": h(identity),
                    "upstream_sha256": stage_input_hash,
                    "output_sha256": output_hash,
                    "oracle_intervention": False,
                }
            values[layer] = output
            receipts[layer] = receipt
            previous = output
        judge = self.judge
        try:
            success = judge.fn(
                copy.deepcopy(public_input), copy.deepcopy(previous),
                copy.deepcopy(gold_case))
        except Exception as exc:
            raise ValueError("G8_JUDGE_REPLAY_ERROR") from exc
        must(type(success) is bool, "G8_JUDGE_RESULT_TYPE")
        return {
            "layers": values, "upstream": upstream,
            "stage_receipts": receipts, "final_success": success,
        }


def verify(raw: dict, hidden: dict, public_inputs: Mapping[str, object],
           trusted_replay: TrustedReplay | None) -> dict:
    must(isinstance(trusted_replay, TrustedReplay),
         "G8_TRUSTED_REPLAY_REQUIRED")
    must(isinstance(raw, dict) and raw.get("protocol") == PROTOCOL,
         "G8_PROTOCOL_V2_REQUIRED")
    must(isinstance(public_inputs, Mapping), "G8_PUBLIC_INPUTS_REQUIRED")

    # Run the unchanged legacy gate, never rewriting its accepted v1 format.
    raw_v1 = copy.deepcopy(raw)
    raw_v1["protocol"] = "ISSUE1_PHASE1_AE_RAW_V1"
    must(isinstance(raw_v1.get("cases"), list), "G8_CASES_MISSING")
    for row in raw_v1["cases"]:
        must(isinstance(row, dict) and isinstance(row.get("arms"), list),
             "G8_ARMS_MISSING")
        for item in row["arms"]:
            must(isinstance(item, dict) and set(item) ==
                 {"arm", "layers", "upstream", "stage_receipts",
                  "implementation", "input_sha256", "final_success"},
                 "G8_V2_ARM_SCHEMA")
            del item["stage_receipts"]
    legacy = verify_v1(raw_v1, hidden)

    gold_cases = {case["case_id"]: case for case in hidden["cases"]}
    must(set(public_inputs) == set(gold_cases), "G8_PUBLIC_INPUT_SET_MISMATCH")
    must(all(h(public_inputs[cid]) == row["input_sha256"]
             for row in raw["cases"] for cid in [row["case_id"]]),
         "G8_PUBLIC_INPUT_HASH_MISMATCH")

    before = trusted_replay.seals()
    input_seals = (h(raw), h(hidden), h(public_inputs))
    observed_stages = 0
    for row in raw["cases"]:
        cid = row["case_id"]
        for arm in row["arms"]:
            name = arm["arm"]
            must(isinstance(arm["stage_receipts"], dict) and
                 set(arm["stage_receipts"]) == set(LAYERS),
                 "G8_RECEIPT_COVERAGE:" + cid + ":" + name)
            expected = trusted_replay.replay(
                public_inputs[cid], gold_cases[cid], name, row["input_sha256"])
            for layer in LAYERS:
                label = ":" + cid + ":" + name + ":" + layer
                must(arm["layers"][layer] == expected["layers"][layer],
                     "G8_STAGE_OUTPUT_REPLAY_MISMATCH" + label)
                must(arm["upstream"][layer] == expected["upstream"][layer],
                     "G8_STAGE_UPSTREAM_REPLAY_MISMATCH" + label)
                must(arm["stage_receipts"][layer] ==
                     expected["stage_receipts"][layer],
                     "G8_RECEIPT_REPLAY_MISMATCH" + label)
                observed_stages += 1
            must(arm["final_success"] == expected["final_success"],
                 "G8_FINAL_SUCCESS_REPLAY_MISMATCH:" + cid + ":" + name)
    must(trusted_replay.seals() == before,
         "G8_REPLAY_ENGINE_CHANGED_DURING_VALIDATION")
    must((h(raw), h(hidden), h(public_inputs)) == input_seals,
         "G7_V2_INPUT_CHANGED_DURING_REPLAY")

    return {
        "protocol": AUDIT_PROTOCOL,
        "cases": legacy["cases"],
        "arms": legacy["arms"],
        "replayed_stages": observed_stages,
        "recomputed_oracle_gains": legacy["oracle_gains"],
        "material_layers_diagnostic_only": legacy["material_layers"],
        "source_bound_deterministic_replay_verified": True,
        "untrusted_raw_receipts_alone_sufficient": False,
        "scientific_native_qualification": False,
        "model_and_gold_independence_qualified": False,
        "original_AC18_pass_automatically": False,
        "original_phase1_complete": False,
        "source_pins": before,
    }
