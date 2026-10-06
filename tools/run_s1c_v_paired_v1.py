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

from generate_s1c_v_holdout import generate
from s1c_v_deterministic_discovery import predict as deterministic_predict
from score_s1c_v_denotational import aggregate

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
WORK = pathlib.Path("/tmp/s1c-v-v1")
OUT = ROOT / "results" / "function_boundary_s1c_v_paired_runtime.json"

PROTOCOL = "FUNCTION_BOUNDARY_S1C_V_PAIRED_V1"
TCC = "S1C_SEMANTIC_SPACE_TCC_V1"
ISSUE = 48
EXPECTED_TASKS = 8
EXPECTED_HELDOUT = 16
MATERIALITY = 0.20

EXPECTED_GIT_BLOBS = {
    "score_s1c_v_denotational.py": "efe940abe8c1643ed0ccbe665b7430610205cea5",
    "s1c_v_deterministic_discovery.py": "c853b27ce6f2149f6619ccd88fb662a8bdaba67e",
    "generate_s1c_v_holdout.py": "c9922f731d989e59148ba37083d02909ee65a584",
    "preflight_s1c_v.py": "6383f7336bb7ed08d6fbad1a6da1ebf1c8343426",
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
        ["python3", str(TOOLS / "preflight_s1c_v.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if p.returncode:
        raise RuntimeError("S1C_V_PREFLIGHT_FAILED:" + (p.stderr or p.stdout))
    data = json.loads(p.stdout)
    if data.get("terminal") != "S1C_V_PREINFERENCE_PASS" or data.get("pass") is not True:
        raise RuntimeError("S1C_V_PREFLIGHT_NOT_PASS")
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
    download(LLAMA_URL, arc, "s1c-v-v1/1")
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


def literal(text: str) -> str:
    return json.dumps(text)


def _alts(values: list[str]) -> str:
    return " | ".join(literal(x) for x in sorted(set(values)))


def _list_rule(item_rule: str, max_n: int, allow_empty: bool = True) -> str:
    rows = ['"[]"'] if allow_empty else []
    for n in range(1, max_n + 1):
        body = ' ws "," ws '.join([item_rule] * n)
        rows.append('"[" ws ' + body + ' ws "]"')
    return " | ".join(rows)


def grammar_for(task: dict[str, Any]) -> str:
    v = task["visible"]
    train_ids = [str(x["example_id"]) for x in v["training_examples"]]
    held_ids = [str(x["example_id"]) for x in v["heldout_examples"]]
    types = list(v.get("type_inventory", []))
    entities = sorted({
        str(eid)
        for ex in v["heldout_examples"]
        for eid in ex["entity_registry"]
    })
    slot_ids = [f"S{i:02d}" for i in range(1, 9)]

    type_item = _alts(types)
    member_item = _alts(train_ids)
    held_item = _alts(held_ids)
    entity_item = _alts(entities)
    slotid = _alts(slot_ids)

    return "\n".join([
        'root ::= ws "{" ws "\\"discovered_slots\\"" ws ":" ws slotlist ws "," ws "\\"heldout_assignments\\"" ws ":" ws assignlist ws "," ws "\\"abstentions\\"" ws ":" ws abstainlist ws "}" ws',
        'slotlist ::= ' + _list_rule("slot", 8, allow_empty=False),
        'slot ::= "{" ws "\\"slot_id\\"" ws ":" ws slotid ws "," ws "\\"arg_types\\"" ws ":" ws typelist ws "," ws "\\"training_members\\"" ws ":" ws memberlist ws "}"',
        'typelist ::= ' + _list_rule("typeitem", 2, allow_empty=True),
        'memberlist ::= ' + _list_rule("memberitem", 4, allow_empty=False),
        'assignlist ::= ' + _list_rule("assignment", 2, allow_empty=True),
        'assignment ::= "{" ws "\\"example_id\\"" ws ":" ws helditem ws "," ws "\\"slot_id\\"" ws ":" ws slotid ws "," ws "\\"arguments\\"" ws ":" ws arglist ws "," ws "\\"polarity\\"" ws ":" ws polarity ws "," ws "\\"modality\\"" ws ":" ws modality ws "}"',
        'arglist ::= ' + _list_rule("entityitem", 2, allow_empty=True),
        'abstainlist ::= ' + _list_rule("abstention", 2, allow_empty=True),
        'abstention ::= "{" ws "\\"example_id\\"" ws ":" ws helditem ws "," ws "\\"status\\"" ws ":" ws "\\"AMBIGUOUS\\"" ws "}"',
        'slotid ::= ' + slotid,
        'typeitem ::= ' + type_item,
        'memberitem ::= ' + member_item,
        'helditem ::= ' + held_item,
        'entityitem ::= ' + entity_item,
        'polarity ::= "\\"POS\\"" | "\\"NEG\\""',
        'modality ::= "\\"ASSERTED\\"" | "\\"REQUIRED\\"" | "\\"POSSIBLE\\""',
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


def qwen_predict(tasks: list[dict[str, Any]], server_url: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    system = (
        "Discover reusable semantic slots from the visible training examples without inventing canonical semantic names. "
        "The observable_behavior_signature is a neutral denotational supervision signal. Group training examples that denote the same reusable semantic slot. "
        "Assign arbitrary local slot IDs only; slot surface names have no meaning. Then ground each heldout raw-language example into one discovered slot using only visible evidence. "
        "Preserve argument order, polarity, and modality. Use AMBIGUOUS only when the heldout language does not determine one denotational assignment. "
        "Return only the required JSON object. Every training example must belong to exactly one discovered slot, and every heldout example must be either assigned once or abstained once."
    )
    predictions: dict[str, Any] = {}
    raw_rows: list[dict[str, Any]] = []
    for task in tasks:
        visible = task["visible"]
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
                "n_predict": 2048,
                "temperature": 0,
                "grammar": grammar_for(task),
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
        predictions[task["task_id"]] = parsed
        row = {
            "task_id": task["task_id"],
            "family": task["family"],
            "visible_sha256": visible_sha,
            "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "raw": raw,
            "prediction": parsed,
        }
        raw_rows.append(row)
        print("S1C_V_TASK=" + json.dumps(row, ensure_ascii=False, separators=(",", ":")), flush=True)
    return predictions, raw_rows


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    source_blobs = verify_frozen_sources()
    preflight = run_preflight()
    tasks = generate()
    if len(tasks) != EXPECTED_TASKS:
        raise RuntimeError("S1C_V_TASK_COUNT_MISMATCH")
    if sum(len(t["visible"]["heldout_examples"]) for t in tasks) != EXPECTED_HELDOUT:
        raise RuntimeError("S1C_V_HELDOUT_COUNT_MISMATCH")

    dataset_digest = sha_text(tasks)
    visible_hashes = {t["task_id"]: sha_text(t["visible"]) for t in tasks}

    deterministic_predictions = {
        t["task_id"]: deterministic_predict({"visible": t["visible"]})
        for t in tasks
    }
    deterministic = aggregate(tasks, deterministic_predictions)
    if deterministic.get("pass") is not True:
        raise RuntimeError("S1C_V_DETERMINISTIC_SCORE_FAILED")

    print("S1C_V_STATE=PREINFERENCE_PASS_MODEL_ACQUISITION_AUTHORIZED", flush=True)

    server_bin = acquire_runtime()
    model = WORK / MODEL_FILE
    download(MODEL_URL, model, "s1c-v-v1/1")
    if model.stat().st_size != MODEL_SIZE:
        raise RuntimeError("MODEL_SIZE_MISMATCH")
    if sha256_file(model) != MODEL_SHA:
        raise RuntimeError("MODEL_SHA_MISMATCH")

    log_path = WORK / "llama.log"
    log = log_path.open("w")
    server = subprocess.Popen(
        [
            str(server_bin), "-m", str(model), "-c", "8192", "-b", "64", "-ub", "64",
            "--threads", "1", "--no-warmup", "--host", "127.0.0.1", "--port", "18084",
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
                with urllib.request.urlopen("http://127.0.0.1:18084/health", timeout=2) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            log.flush()
            raise RuntimeError("LLAMA_NOT_READY:" + log_path.read_text(errors="replace")[-3000:])

        qwen_predictions, raw_rows = qwen_predict(tasks, "http://127.0.0.1:18084")
        qwen = aggregate(tasks, qwen_predictions)
        if qwen.get("pass") is not True:
            raise RuntimeError("S1C_V_QWEN_SCORE_FAILED")

        primary_keys = (
            "training_partition_pairwise_accuracy",
            "heldout_denotational_assignment_accuracy",
            "exact_discovery_and_grounding_rate",
        )
        deltas = {
            k: float(qwen["primary"][k]) - float(deterministic["primary"][k])
            for k in primary_keys
        }
        result = {
            "schema_version": "FUNCTION_BOUNDARY_S1C_V_PAIRED_ACTUAL_V1",
            "protocol": PROTOCOL,
            "tcc": TCC,
            "issue": ISSUE,
            "terminal": "V_PAIRED_METRICS_READY_AUDIT_REQUIRED",
            "dataset_digest": dataset_digest,
            "task_count": EXPECTED_TASKS,
            "heldout_count": EXPECTED_HELDOUT,
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
                "context_tokens": 8192,
                "grammar_policy": "contract-shape and visible-ID grammar only; no semantic partition or heldout answer encoded",
                "github_actions_used": False,
                "google_drive_used": False,
                "qwen3_4b_used": False,
            },
            "arms": {
                "deterministic": deterministic,
                "qwen25_1p5b": qwen,
            },
            "raw_qwen_rows": raw_rows,
            "primary_deltas_qwen_minus_deterministic": deltas,
            "materiality_abs": MATERIALITY,
            "final_branch_authorized": False,
            "required_next_gates": [
                "V08_INDEPENDENT_RAW_REPARSE",
                "V09_INDEPENDENT_METRIC_RECOMPUTE",
                "V10_SINGLE_BOUNDARY_UPDATE",
            ],
            "claim_limit": (
                "Semantic-slot discovery and heldout grounding inside the frozen denotational supervision contract only. "
                "No open-ended world-knowledge or unrestricted ontology invention claim is authorized."
            ),
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("S1C_V_TERMINAL=" + json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
    finally:
        if server.poll() is None:
            server.terminate()
        log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
