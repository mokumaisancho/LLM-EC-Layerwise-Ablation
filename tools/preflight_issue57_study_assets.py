#!/usr/bin/env python3
"""Issue #57: gold-blind external-study readiness; never certifies provenance.

Reads public cases, a salted *commitment*, arm output envelopes and a seal.
Never opens private gold, its nonce, source labels, or model inference engines.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evaluation.quality_blind_v2 import (
    ARMS, SEAL_PROTOCOL, BlindProtocolError, sha, unique_object_pairs,
    validate_public, validate_arm,
)

def read(path: Path):
    if not path.is_file():
        raise BlindProtocolError("REQUIRED_FILE_MISSING")
    if path.stat().st_size > 16_000_000:
        raise BlindProtocolError("INPUT_TOO_LARGE")
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=unique_object_pairs)

def sha_file(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect_study(directory: Path | None):
    result = {"stage": "PUBLIC_CORPUS", "machine_structural_complete": False,
              "external_gold_independence_verified": False,
              "provenance_custody_verified": False, "genuine_inference_verified": False,
              "quality_preservation_certified": False, "scientific_four_arm_run": "NOT_ESTABLISHED",
              "stages": {}, "blockers": []}
    if directory is None or not directory.is_dir():
        result["blockers"].append("EXTERNAL_STUDY_DIR_MISSING")
        return result
    names = ["public.json", "gold_precommit.json"] + [name + ".json" for name in ARMS] + ["seal.json"]
    missing = [name for name in names if not (directory / name).is_file()]
    result["present_filenames"] = [name for name in names if name not in missing]
    if missing:
        result["blockers"] += ["MISSING_FILE:" + name for name in missing]
    if "public.json" in missing:
        return result
    try:
        public = read(directory / "public.json")
        cases = validate_public(public)
        result["stages"]["public"] = {
            "status": "STRUCTURE_PASS_INDEPENDENCE_UNVERIFIED",
            "study_id": public["study_id"], "case_count": len(cases),
            "sha256": sha(public), "file_sha256": sha_file(directory / "public.json")}
    except (BlindProtocolError, ValueError, TypeError, KeyError, OSError) as exc:
        result["blockers"].append("PUBLIC_INVALID:" + str(exc)[:120])
        return result
    result["stage"] = "GOLD_PRECOMMIT"
    if "gold_precommit.json" in missing:
        return result
    try:
        pre = read(directory / "gold_precommit.json")
        keys = {"protocol", "study_id", "public_sha256", "gold_commitment"}
        if not isinstance(pre, dict) or set(pre) != keys or pre["protocol"] != "CAPABILITY_GOLD_PRECOMMIT_V2":
            raise BlindProtocolError("PRECOMMIT_SCHEMA_INVALID")
        if pre["study_id"] != public["study_id"] or pre["public_sha256"] != sha(public):
            raise BlindProtocolError("PRECOMMIT_PUBLIC_DRIFT")
        if not isinstance(pre["gold_commitment"], str) or re.fullmatch("[0-9a-f]{64}", pre["gold_commitment"]) is None:
            raise BlindProtocolError("PRECOMMIT_DIGEST_INVALID")
        result["stages"]["precommit"] = {
            "status": "COMMITMENT_PRESENT_NOT_CHRONOLOGY_PROOF",
            "file_sha256": sha_file(directory / "gold_precommit.json")}
    except (BlindProtocolError, ValueError, TypeError, KeyError, OSError) as exc:
        result["blockers"].append("PRECOMMIT_INVALID:" + str(exc)[:120])
        return result
    result["stage"] = "FOUR_ARM_RAW"
    arms = {}
    for name in ARMS:
        if name + ".json" in missing:
            continue
        try:
            arm = read(directory / (name + ".json"))
            validate_arm(arm, public)
            if arm["arm"] != name:
                raise BlindProtocolError("ARM_NAME_MISMATCH")
            ref = arm["model_or_runtime_ref"]
            if "SYNTHETIC" in ref.upper() or "MOCK" in ref.upper() or "TEST_NOT_REAL" in ref.upper():
                raise BlindProtocolError("SYNTHETIC_ARM_PLACEHOLDER")
            arms[name] = arm
            result["stages"][name] = {
                "status": "SOURCE_PIN_SELF_ATTESTED_NOT_INFERENCE_PROOF",
                "rows": len(arm["raw_rows"]), "envelope_sha256": sha(arm),
                "file_sha256": sha_file(directory / (name + ".json"))}
        except (BlindProtocolError, ValueError, TypeError, KeyError, OSError) as exc:
            result["blockers"].append("ARM_INVALID:" + name + ":" + str(exc)[:100])
    if set(arms) != set(ARMS):
        return result
    result["stage"] = "FROZEN_SEAL"
    if "seal.json" in missing:
        return result
    try:
        seal = read(directory / "seal.json")
        keys = {"protocol", "study_id", "public_sha256", "gold_commitment",
                "arm_raw_commitments", "gold_access_after_arms", "independent_review"}
        if not isinstance(seal, dict) or set(seal) != keys or seal["protocol"] != SEAL_PROTOCOL:
            raise BlindProtocolError("SEAL_SCHEMA_INVALID")
        if seal["study_id"] != public["study_id"] or seal["public_sha256"] != sha(public):
            raise BlindProtocolError("SEAL_PUBLIC_DRIFT")
        if seal["gold_commitment"] != pre["gold_commitment"]:
            raise BlindProtocolError("SEAL_GOLD_COMMITMENT_DRIFT")
        if not isinstance(seal["arm_raw_commitments"], dict) or set(seal["arm_raw_commitments"]) != set(ARMS):
            raise BlindProtocolError("SEAL_FOUR_ARMS_REQUIRED")
        if any(seal["arm_raw_commitments"][name] != sha(arms[name]) for name in ARMS):
            raise BlindProtocolError("SEAL_RAW_ARM_DRIFT")
        if seal["gold_access_after_arms"] is not True:
            raise BlindProtocolError("SEAL_GOLD_ACCESS_ORDER_ASSERTION_MISSING")
        if not isinstance(seal["independent_review"], dict) or set(seal["independent_review"]) != {"status", "review_ref"}:
            raise BlindProtocolError("REVIEW_SCHEMA_INVALID")
        result["stages"]["seal"] = {
            "status": "HASH_MATCH_ONLY_NOT_INDEPENDENT_TIMELINE_PROOF",
            "file_sha256": sha_file(directory / "seal.json")}
    except (BlindProtocolError, ValueError, TypeError, KeyError, OSError) as exc:
        result["blockers"].append("SEAL_INVALID:" + str(exc)[:120])
        return result
    result["stage"] = "INDEPENDENT_PROVENANCE_REVIEW"
    result["machine_structural_complete"] = not result["blockers"]
    result["blockers"].append("EXTERNAL_REVIEW_REQUIRED_UNSEEN_AND_REAL_INFERENCE_UNPROVEN")
    return result

def inspect_ollama_model(root: Path | None, model: str):
    report = {"name": model, "selected_as_llm0": False,
              "manifest_present": False, "model_bytes_present": False,
              "runtime_inference_performed": False, "sha256_of_bytes_verified": False,
              "readiness": "NOT_CONFIGURED"}
    if root is None:
        return report
    if not re.fullmatch(r"[a-zA-Z0-9._-]+(?:/[a-zA-Z0-9._-]+){1,3}", model):
        report["readiness"] = "INVALID_MODEL_NAME"
        return report
    path = root / "manifests/registry.ollama.ai/library" / model
    if not path.is_file():
        report["readiness"] = "MANIFEST_MISSING"
        return report
    report["manifest_present"] = True
    try:
        manifest = read(path)
        layers = [x for x in manifest["layers"] if x.get("mediaType") == "application/vnd.ollama.image.model"]
        if len(layers) != 1:
            raise ValueError("MODEL_LAYER_COUNT_INVALID")
        layer = layers[0]
        if re.fullmatch("sha256:[0-9a-f]{64}", layer["digest"]) is None:
            raise ValueError("MODEL_SHA_INVALID")
        digest = layer["digest"].split(":")[1]
        size = layer["size"]
        blob = root / "blobs" / ("sha256-" + digest)
        report.update({"layer_digest": layer["digest"], "declared_size": size,
                       "model_bytes_present": blob.is_file() and blob.stat().st_size == size})
        report["readiness"] = "BYTES_PRESENT_HASH_NOT_VERIFIED" if report["model_bytes_present"] else "STORAGE_BLOB_MISSING_OR_WRONG_SIZE"
    except (KeyError, IndexError, OSError, TypeError, ValueError) as exc:
        report["readiness"] = "MANIFEST_UNUSABLE:" + type(exc).__name__
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--study-dir", type=Path)
    p.add_argument("--ollama-root", type=Path)
    p.add_argument("--ollama-model", default="qwen2.5/1.5b")
    a = p.parse_args()
    study = inspect_study(a.study_dir)
    result = {
        "protocol": "ISSUE57_GOLD_BLIND_READINESS_V1",
        "study": study,
        "llm0_candidate_asset_diagnostic": inspect_ollama_model(a.ollama_root, a.ollama_model),
        "v4_default_repo_policy_approved": False,
        "single_repo": "mokumaisancho/LLM-EC-Layerwise-Ablation",
        "closed_loop_feedback_from_gold_allowed": False,
        "no_gold_read": True, "no_model_inference": True,
        "scientific_comparison": "NOT_RUN",
        "quality_preservation_certified": False,
        "terminal": "REAL_FOUR_ARM_STUDY_AWAITING_INDEPENDENT_EVIDENCE"
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
