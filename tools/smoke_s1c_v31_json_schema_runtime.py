#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import tarfile
import time
import urllib.request
from typing import Any

from generate_s1c_v31_corpus import generate
from s1c_v31_json_schema import canonical_positive, schema_for

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
WORK = pathlib.Path("/tmp/s1c-v31-schema-smoke")

PROTOCOL = "S1C_V31_SYNTHETIC_JSON_SCHEMA_RUNTIME_SMOKE_V1"

LLAMA_TAG = "b11146"
LLAMA_FILE = "llama-b11146-bin-ubuntu-x64.tar.gz"
LLAMA_URL = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}"
LLAMA_SHA = "c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410"
MODEL_REPO = "bartowski/Qwen2.5-1.5B-Instruct-GGUF"
MODEL_FILE = "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
MODEL_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}"
MODEL_SHA = "1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370"
MODEL_SIZE = 986048768


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: pathlib.Path, ua: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=240) as r, dest.open("wb") as out:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def acquire_runtime() -> pathlib.Path:
    arc = WORK / LLAMA_FILE
    download(LLAMA_URL, arc, "s1c-v31-schema-smoke/1")
    if sha256_file(arc) != LLAMA_SHA:
        raise RuntimeError("LLAMA_SHA_MISMATCH")
    target = WORK / "llama"
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(arc, "r:gz") as tf:
        tf.extractall(target, filter="data")
    hits = list(target.rglob("llama-server"))
    if not hits:
        raise RuntimeError("LLAMA_SERVER_NOT_FOUND")
    hits[0].chmod(0o755)
    return hits[0]


def post_json(url: str, payload: dict[str, Any], timeout: int = 600) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def run_preflight() -> dict[str, Any]:
    p = subprocess.run(
        ["python3", str(TOOLS / "preflight_s1c_v31.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if p.returncode:
        raise RuntimeError("V31_PREFLIGHT_FAILED:" + (p.stderr or p.stdout))
    data = json.loads(p.stdout)
    if data.get("terminal") != "S1C_V31_PREFLIGHT_PASS" or data.get("pass") is not True:
        raise RuntimeError("V31_PREFLIGHT_NOT_PASS")
    return data


def _assert_minimal_shape(raw: str, parsed: Any) -> None:
    if not isinstance(parsed, dict):
        raise RuntimeError("SYNTHETIC_OUTPUT_NOT_OBJECT")
    if set(parsed) != {"slot_id", "probe_id", "bits"}:
        raise RuntimeError("SYNTHETIC_OUTPUT_KEYS_INVALID")
    if parsed["slot_id"] != "S01" or parsed["probe_id"] != "Q03":
        raise RuntimeError("SYNTHETIC_ENUM_CONSTRAINT_FAILED")
    bits = parsed["bits"]
    if not isinstance(bits, list) or len(bits) != 3 or any(x not in (0, 1) for x in bits):
        raise RuntimeError("SYNTHETIC_BITS_INVALID")
    if '"slot_id":S01' in raw or '"probe_id":Q03' in raw:
        raise RuntimeError("BARE_JSON_STRING_ID_REAPPEARED")


def _assert_actual_schema_shape(task: dict[str, Any], raw: str, parsed: Any) -> None:
    if not isinstance(parsed, dict):
        raise RuntimeError("ACTUAL_SCHEMA_OUTPUT_NOT_OBJECT")
    if set(parsed) != {"discovered_slots", "heldout_assignments", "abstentions"}:
        raise RuntimeError("ACTUAL_SCHEMA_TOP_LEVEL_KEYS_INVALID")
    if not isinstance(parsed["discovered_slots"], list) or not (1 <= len(parsed["discovered_slots"]) <= 4):
        raise RuntimeError("ACTUAL_SCHEMA_SLOT_LIST_INVALID")
    for slot in parsed["discovered_slots"]:
        if not isinstance(slot, dict):
            raise RuntimeError("ACTUAL_SCHEMA_SLOT_NOT_OBJECT")
        if set(slot) != {"slot_id", "arg_types", "training_members", "evaluation_probe_predictions"}:
            raise RuntimeError("ACTUAL_SCHEMA_SLOT_KEYS_INVALID")
        if slot["slot_id"] not in {"S01", "S02", "S03", "S04"}:
            raise RuntimeError("ACTUAL_SCHEMA_SLOT_ID_INVALID")
        probes = slot["evaluation_probe_predictions"]
        if not isinstance(probes, list) or len(probes) != 4:
            raise RuntimeError("ACTUAL_SCHEMA_PROBE_LIST_INVALID")
        for row in probes:
            if row.get("probe_id") not in {"Q03", "Q05", "Q06", "Q07"}:
                raise RuntimeError("ACTUAL_SCHEMA_PROBE_ID_INVALID")
            bits = row.get("predicted_after")
            if not isinstance(bits, list) or len(bits) != 3 or any(x not in (0,1) for x in bits):
                raise RuntimeError("ACTUAL_SCHEMA_PROBE_BITS_INVALID")
    if '"slot_id":S0' in raw:
        raise RuntimeError("ACTUAL_SCHEMA_BARE_SLOT_ID_REAPPEARED")


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    preflight = run_preflight()
    tasks = generate()
    if len(tasks) != 8:
        raise RuntimeError("V31_TASK_COUNT_MISMATCH")
    task = tasks[0]

    server_bin = acquire_runtime()
    model = WORK / MODEL_FILE
    download(MODEL_URL, model, "s1c-v31-schema-smoke/1")
    if model.stat().st_size != MODEL_SIZE:
        raise RuntimeError("MODEL_SIZE_MISMATCH")
    if sha256_file(model) != MODEL_SHA:
        raise RuntimeError("MODEL_SHA_MISMATCH")

    log_path = WORK / "llama.log"
    log = log_path.open("w")
    server = subprocess.Popen(
        [
            str(server_bin), "-m", str(model), "-c", "4096", "-b", "64", "-ub", "64",
            "--threads", "1", "--no-warmup", "--host", "127.0.0.1", "--port", "18085",
        ],
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        ready = False
        for _ in range(240):
            if server.poll() is not None:
                break
            try:
                with urllib.request.urlopen("http://127.0.0.1:18085/health", timeout=2) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            log.flush()
            raise RuntimeError("LLAMA_NOT_READY:" + log_path.read_text(errors="replace")[-3000:])

        minimal_schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["slot_id", "probe_id", "bits"],
            "properties": {
                "slot_id": {"type": "string", "const": "S01"},
                "probe_id": {"type": "string", "const": "Q03"},
                "bits": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 3,
                    "items": {"type": "integer", "enum": [0, 1]},
                },
            },
        }
        p1 = "<|im_start|>system\nReturn only one JSON object satisfying the schema.<|im_end|>\n<|im_start|>user\nEmit slot S01, probe Q03, and any three binary bits.<|im_end|>\n<|im_start|>assistant\n"
        r1 = post_json(
            "http://127.0.0.1:18085/completion",
            {"prompt": p1, "n_predict": 128, "temperature": 0, "json_schema": minimal_schema, "cache_prompt": False},
        )
        raw1 = str(r1.get("content", "")).strip()
        try:
            parsed1 = json.loads(raw1)
        except Exception as exc:
            raise RuntimeError("SYNTHETIC_JSON_PARSE_FAILED:" + raw1[:500]) from exc
        _assert_minimal_shape(raw1, parsed1)

        schema = schema_for(task)
        canonical = canonical_positive(task)
        p2 = (
            "<|im_start|>system\nReturn only one JSON object satisfying the provided schema. "
            "This is a format smoke test, not a reasoning task.<|im_end|>\n"
            "<|im_start|>user\nProduce a schema-valid object. For reliability you may copy this valid example exactly:\n"
            + json.dumps(canonical, ensure_ascii=False, separators=(",", ":"))
            + "<|im_end|>\n<|im_start|>assistant\n"
        )
        r2 = post_json(
            "http://127.0.0.1:18085/completion",
            {"prompt": p2, "n_predict": 1400, "temperature": 0, "json_schema": schema, "cache_prompt": False},
        )
        raw2 = str(r2.get("content", "")).strip()
        try:
            parsed2 = json.loads(raw2)
        except Exception as exc:
            raise RuntimeError("ACTUAL_SCHEMA_JSON_PARSE_FAILED:" + raw2[:500]) from exc
        _assert_actual_schema_shape(task, raw2, parsed2)

        out = {
            "protocol": PROTOCOL,
            "pass": True,
            "terminal": "S1C_V31_SYNTHETIC_JSON_SCHEMA_RUNTIME_SMOKE_PASS",
            "preflight_terminal": preflight["terminal"],
            "runtime": {
                "llama_cpp_tag": LLAMA_TAG,
                "llama_cpp_asset_sha256": LLAMA_SHA,
                "model_file": MODEL_FILE,
                "model_sha256": MODEL_SHA,
                "temperature": 0,
                "endpoint": "/completion",
                "constraint_field": "json_schema",
            },
            "minimal_schema": {
                "raw_sha256": hashlib.sha256(raw1.encode()).hexdigest(),
                "parsed": parsed1,
                "bare_string_id_regression": False,
            },
            "actual_v31_schema": {
                "task_id": task["task_id"],
                "raw_sha256": hashlib.sha256(raw2.encode()).hexdigest(),
                "top_level_keys": sorted(parsed2),
                "slot_count": len(parsed2["discovered_slots"]),
                "bare_slot_id_regression": False,
            },
            "scientific_measurement_performed": False,
            "paired_model_inference_authorized": True,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    finally:
        if server.poll() is None:
            server.terminate()
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())
