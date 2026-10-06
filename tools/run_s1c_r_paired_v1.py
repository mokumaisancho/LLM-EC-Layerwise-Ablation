#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import tarfile
import time
import urllib.request
from itertools import product
from typing import Any

from generate_s1c_r_holdout import generate
from s1c_r_deterministic_grounder import predict as deterministic_predict
from score_s1c_r_typed_ir import score_rows

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
WORK = pathlib.Path("/tmp/s1c-r-v1")
OUT = ROOT / "results" / "function_boundary_s1c_r_paired_runtime.json"

PROTOCOL = "FUNCTION_BOUNDARY_S1C_R_PAIRED_V1"
TCC = "S1C_SEMANTIC_SPACE_TCC_V1"
ISSUE = 48
EXPECTED_FIXTURES = 16
EXPECTED_FAMILIES = 8
MATERIALITY = 0.20

EXPECTED_GIT_BLOBS = {
    "score_s1c_r_typed_ir.py": "e10e0ab83ac75538659e5fb313efa20e8f5c8653",
    "s1c_r_deterministic_grounder.py": "74c6a9832bc7e5ab4594e0868e235a0106d4a0d6",
    "generate_s1c_r_holdout.py": "4cfca707a440e03d992f2a2ab35fb2d9293cf37e",
    "preflight_s1c_r.py": "bf2ae7a16d63fbc2d53a2d70ebb923dad7f8f175",
}

LLAMA_TAG = "b11146"
LLAMA_FILE = "llama-b11146-bin-ubuntu-x64.tar.gz"
LLAMA_URL = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/{LLAMA_FILE}"
LLAMA_SHA = "c150306eb16b5ab696f76a8bdf810c35fd98a24e82158742e6fa28f420ff8410"
MODEL_REPO = "bartowski/Qwen2.5-1.5B-Instruct-GGUF"
MODEL_FILE = "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
MODEL_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}"
MODEL_SHA = "1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370"
MODEL_SIZE = 986048768


def canon(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_text(v: Any) -> str:
    return hashlib.sha256(canon(v).encode()).hexdigest()


def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(raw)}\0".encode())
    h.update(raw)
    return h.hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_frozen_sources() -> dict[str, str]:
    actual: dict[str, str] = {}
    for name, expected in EXPECTED_GIT_BLOBS.items():
        path = TOOLS / name
        if not path.exists():
            raise RuntimeError(f"FROZEN_SOURCE_MISSING:{name}")
        got = git_blob_sha(path)
        actual[name] = got
        if got != expected:
            raise RuntimeError(f"FROZEN_SOURCE_DRIFT:{name}:{got}:{expected}")
    return actual


def run_preflight() -> dict[str, Any]:
    p = subprocess.run(
        ["python3", str(TOOLS / "preflight_s1c_r.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if p.returncode:
        raise RuntimeError("S1C_R_PREFLIGHT_FAILED:" + (p.stderr or p.stdout))
    data = json.loads(p.stdout)
    if data.get("terminal") != "S1C_R_PREINFERENCE_PASS" or data.get("pass") is not True:
        raise RuntimeError("S1C_R_PREFLIGHT_NOT_PASS")
    return data


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
    download(LLAMA_URL, arc, "s1c-r-v1/1")
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


def atom_literals(visible: dict[str, Any]) -> list[str]:
    registry = visible["entity_registry"]
    inventory = visible["opaque_semantic_inventory"]
    by_type: dict[str, list[str]] = {}
    for eid, item in registry.items():
        by_type.setdefault(item["type"], []).append(eid)
    rows: list[str] = []
    for pred, spec in sorted(inventory.items()):
        arg_types = spec["arg_types"]
        choices = [sorted(by_type.get(t, [])) for t in arg_types]
        if any(not x for x in choices):
            continue
        for args in product(*choices) if choices else [()]:
            for polarity in ("POS", "NEG"):
                for modality in ("ASSERTED", "REQUIRED", "POSSIBLE"):
                    atom = {
                        "predicate": pred,
                        "arguments": list(args),
                        "polarity": polarity,
                        "modality": modality,
                    }
                    rows.append(canon(atom))
    return sorted(set(rows))


def literal(text: str) -> str:
    return json.dumps(text)


def grammar_for(visible: dict[str, Any]) -> str:
    atoms = atom_literals(visible)
    atom_rule = " | ".join(literal(x) for x in atoms)
    return "\n".join([
        'root ::= ws "{" ws "\\\"status\\\"" ws ":" ws status ws "," ws "\\\"atoms\\\"" ws ":" ws atomlist ws "}" ws',
        'status ::= "\\\"OK\\\"" | "\\\"AMBIGUOUS\\\""',
        'atomlist ::= "[]" | "[" ws atom ws "]" | "[" ws atom ws "," ws atom ws "]" | "[" ws atom ws "," ws atom ws "," ws atom ws "]" | "[" ws atom ws "," ws atom ws "," ws atom ws "," ws atom ws "]"',
        "atom ::= " + atom_rule,
        'ws ::= [ \\t\\n\\r]*',
    ])


def post_json(url: str, payload: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def qwen_predict(fixtures: list[dict[str, Any]], server_url: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    system = (
        "Ground the raw natural-language evidence into the supplied opaque typed semantic inventory. "
        "Infer what each opaque predicate means only from the supplied demonstrations. "
        "Use only visible entity IDs, predicate IDs, type signatures, raw text, and demonstrations. "
        "Do not invent predicates or entities. Preserve relation direction, polarity, and modality. "
        "Return AMBIGUOUS with an empty atom list only when the evidence does not determine one typed interpretation. "
        "Return only the required JSON object."
    )
    predictions: dict[str, Any] = {}
    raw_rows: list[dict[str, Any]] = []
    for fixture in fixtures:
        visible = fixture["visible"]
        visible_sha = sha_text(visible)
        prompt = (
            "<|im_start|>system\n" + system + "<|im_end|>\n"
            "<|im_start|>user\n" + canon(visible) + "<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        response = post_json(
            server_url + "/completion",
            {
                "prompt": prompt,
                "n_predict": 512,
                "temperature": 0,
                "grammar": grammar_for(visible),
                "cache_prompt": False,
            },
        )
        raw = str(response.get("content", "")).strip()
        parsed = None
        try:
            x = json.loads(raw)
            if isinstance(x, dict):
                parsed = x
        except Exception:
            pass
        predictions[fixture["id"]] = parsed
        row = {
            "fixture_id": fixture["id"],
            "family": fixture["family"],
            "visible_sha256": visible_sha,
            "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "raw": raw,
            "prediction": parsed,
        }
        raw_rows.append(row)
        print("S1C_R_FIXTURE=" + json.dumps(row, ensure_ascii=False, separators=(",", ":")), flush=True)
    return predictions, raw_rows


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    source_blobs = verify_frozen_sources()
    preflight = run_preflight()
    fixtures = generate()
    if len(fixtures) != EXPECTED_FIXTURES or len({f["family"] for f in fixtures}) != EXPECTED_FAMILIES:
        raise RuntimeError("S1C_R_FIXTURE_COUNT_MISMATCH")

    holdout_digest = sha_text(fixtures)
    visible_hashes = {f["id"]: sha_text(f["visible"]) for f in fixtures}

    deterministic_predictions = {
        f["id"]: deterministic_predict({"visible": f["visible"]})
        for f in fixtures
    }
    deterministic = score_rows(fixtures, deterministic_predictions)
    if deterministic.get("pass") is not True:
        raise RuntimeError("S1C_R_DETERMINISTIC_SCORE_FAILED")

    print("S1C_R_STATE=PREINFERENCE_PASS_MODEL_ACQUISITION_AUTHORIZED", flush=True)

    server_bin = acquire_runtime()
    model = WORK / MODEL_FILE
    download(MODEL_URL, model, "s1c-r-v1/1")
    if model.stat().st_size != MODEL_SIZE:
        raise RuntimeError("MODEL_SIZE_MISMATCH")
    if sha256_file(model) != MODEL_SHA:
        raise RuntimeError("MODEL_SHA_MISMATCH")

    log_path = WORK / "llama.log"
    log = log_path.open("w")
    server = subprocess.Popen(
        [
            str(server_bin), "-m", str(model), "-c", "4096", "-b", "64", "-ub", "64",
            "--threads", "1", "--no-warmup", "--host", "127.0.0.1", "--port", "18083",
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
                with urllib.request.urlopen("http://127.0.0.1:18083/health", timeout=2) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            log.flush()
            raise RuntimeError("LLAMA_NOT_READY:" + log_path.read_text(errors="replace")[-3000:])

        qwen_predictions, raw_rows = qwen_predict(fixtures, "http://127.0.0.1:18083")
        qwen = score_rows(fixtures, qwen_predictions)
        if qwen.get("pass") is not True:
            raise RuntimeError("S1C_R_QWEN_SCORE_FAILED")

        result = {
            "schema_version": "FUNCTION_BOUNDARY_S1C_R_PAIRED_ACTUAL_V1",
            "protocol": PROTOCOL,
            "tcc": TCC,
            "issue": ISSUE,
            "terminal": "R_PAIRED_METRICS_READY_AUDIT_REQUIRED",
            "holdout_digest": holdout_digest,
            "fixture_count": EXPECTED_FIXTURES,
            "family_count": EXPECTED_FAMILIES,
            "source_blob_pins": source_blobs,
            "visible_hashes": visible_hashes,
            "preflight": preflight,
            "model": {
                "repository": MODEL_REPO,
                "file": MODEL_FILE,
                "size_bytes": MODEL_SIZE,
                "sha256": MODEL_SHA,
            },
            "runtime": {
                "llama_cpp_tag": LLAMA_TAG,
                "llama_cpp_asset_sha256": LLAMA_SHA,
                "temperature": 0,
                "context_tokens": 4096,
                "grammar_policy": "all type-valid visible atoms up to four; no semantic answer encoded",
                "github_actions_used": False,
                "google_drive_used": False,
                "qwen3_4b_used": False,
            },
            "arms": {
                "deterministic": deterministic,
                "qwen25_1p5b": qwen,
            },
            "raw_qwen_rows": raw_rows,
            "primary_deltas_qwen_minus_deterministic": {
                "semantic_slot_accuracy": (
                    float(qwen["primary"]["semantic_slot_accuracy"])
                    - float(deterministic["primary"]["semantic_slot_accuracy"])
                ),
                "exact_typed_ir_rate": (
                    float(qwen["primary"]["exact_typed_ir_rate"])
                    - float(deterministic["primary"]["exact_typed_ir_rate"])
                ),
            },
            "materiality_abs": MATERIALITY,
            "final_branch_authorized": False,
            "required_next_gates": [
                "R08_INDEPENDENT_RAW_REPARSE_AND_METRIC_RECOMPUTE",
                "R11_FIXED_B2_CAUSAL_REPLAY",
                "R12_NO_POST_RESULT_REPAIR",
            ],
            "claim_limit": (
                "Paired raw-language grounding inside a frozen opaque typed semantic inventory only. "
                "No vocabulary discovery, open-ended world knowledge, or final causal boundary claim is authorized before independent audit and fixed-B2 replay."
            ),
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("S1C_R_TERMINAL=" + json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
    finally:
        if server.poll() is None:
            server.terminate()
        log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
