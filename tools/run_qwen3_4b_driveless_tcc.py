#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

MODEL_NAME = "Qwen3-4B-Q4_K_M.gguf"
EXPECTED_SIZE = 2_497_280_256
EXPECTED_SHA256 = "7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5"
CANDIDATES = (64 << 20, 32 << 20, 16 << 20, 8 << 20, 4 << 20)
GGUF_MAGIC = b"GGUF"

TERMINAL_PASS = "PASS_MODEL_READY"
TERMINALS = {
    TERMINAL_PASS,
    "INVALID_TRANSFER_CONTRACT",
    "TRANSPORT_BLOCKED",
    "INTEGRITY_FAILED",
    "SANDBOX_RESOURCE_LIMIT",
    "RUNTIME_UNAVAILABLE",
    "SMOKE_FAILED",
}

class TransportError(RuntimeError):
    pass

class IntegrityError(RuntimeError):
    pass

@dataclass(frozen=True)
class ModelContract:
    name: str = MODEL_NAME
    size: int = EXPECTED_SIZE
    sha256: str = EXPECTED_SHA256


def sha256_path(path: Path, block: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def _header_int(headers, name: str) -> int:
    raw = headers.get(name)
    if raw is None:
        raise IntegrityError(f"MISSING_HEADER:{name}")
    try:
        return int(raw)
    except ValueError as exc:
        raise IntegrityError(f"INVALID_HEADER:{name}={raw}") from exc


def fetch_part(
    base_url: str,
    index: int,
    part_bytes: int,
    contract: ModelContract,
    timeout: float,
    sink: Callable[[bytes, int], None] | None = None,
) -> dict:
    total = (contract.size + part_bytes - 1) // part_bytes
    if index < 0 or index >= total:
        raise ValueError(f"index out of range: {index}/{total}")
    expected_start = index * part_bytes
    expected_len = min(part_bytes, contract.size - expected_start)
    expected_end = expected_start + expected_len - 1
    query = urllib.parse.urlencode({"index": index, "part_bytes": part_bytes})
    url = f"{base_url.rstrip('/')}/part.bin?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "qwen3-4b-driveless-tcc/1.0"})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if status != 200:
                raise TransportError(f"HTTP_STATUS:{status}")
            headers = resp.headers
            declared_index = _header_int(headers, "X-Part-Index")
            declared_total = _header_int(headers, "X-Total-Parts")
            declared_start = _header_int(headers, "X-Byte-Start")
            declared_end = _header_int(headers, "X-Byte-End")
            declared_len = _header_int(headers, "X-Byte-Length")
            declared_part_bytes = _header_int(headers, "X-Part-Bytes")
            declared_model_size = _header_int(headers, "X-Model-Size")
            declared_part_sha = headers.get("X-Part-SHA256")
            declared_model_sha = headers.get("X-Model-SHA256")
            if (
                declared_index != index
                or declared_total != total
                or declared_start != expected_start
                or declared_end != expected_end
                or declared_len != expected_len
                or declared_part_bytes != part_bytes
                or declared_model_size != contract.size
                or declared_model_sha != contract.sha256
                or not declared_part_sha
            ):
                raise IntegrityError("HEADER_CONTRACT_MISMATCH")
            h = hashlib.sha256()
            received = 0
            while True:
                buf = resp.read(1 << 20)
                if not buf:
                    break
                if sink is not None:
                    sink(buf, expected_start + received)
                h.update(buf)
                received += len(buf)
            digest = h.hexdigest()
            if received != expected_len:
                raise IntegrityError(f"BYTE_LENGTH_MISMATCH:{received}!={expected_len}")
            if digest != declared_part_sha:
                raise IntegrityError(f"PART_SHA_MISMATCH:{digest}!={declared_part_sha}")
            return {
                "index": index,
                "total_parts": total,
                "part_bytes": part_bytes,
                "byte_start": expected_start,
                "byte_end": expected_end,
                "byte_length": expected_len,
                "sha256": digest,
                "elapsed_s": round(time.monotonic() - started, 3),
            }
    except IntegrityError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        raise TransportError(str(exc)) from exc


def retry_twice(fn: Callable[[], dict]) -> dict:
    first: Exception | None = None
    for attempt in (1, 2):
        try:
            out = fn()
            out["attempt"] = attempt
            return out
        except (TransportError, IntegrityError) as exc:
            if first is None:
                first = exc
            if attempt == 2:
                raise
    raise AssertionError(first)


def choose_chunk_size(
    probe: Callable[[int], dict], candidates: Iterable[int] = CANDIDATES
) -> tuple[int | None, list[dict], str | None]:
    evidence: list[dict] = []
    for size in candidates:
        try:
            result = retry_twice(lambda size=size: probe(size))
            evidence.append({"part_bytes": size, "status": "PASS", **result})
            return size, evidence, None
        except IntegrityError as exc:
            evidence.append({"part_bytes": size, "status": "INTEGRITY_FAILED", "error": str(exc)})
            return None, evidence, "INTEGRITY_FAILED"
        except TransportError as exc:
            evidence.append({"part_bytes": size, "status": "TRANSPORT_FAILED_AFTER_RETRY", "error": str(exc)})
    return None, evidence, "TRANSPORT_BLOCKED"


def precheck_disk(target: Path, contract: ModelContract) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(target.parent)
    reserve = 2 << 30
    required = contract.size + reserve
    return {
        "free_bytes": usage.free,
        "required_bytes": required,
        "model_bytes": contract.size,
        "reserve_bytes": reserve,
        "pass": usage.free >= required,
    }


def _pwrite_sink(fd: int) -> Callable[[bytes, int], None]:
    def sink(data: bytes, offset: int) -> None:
        view = memoryview(data)
        written = 0
        while written < len(view):
            n = os.pwrite(fd, view[written:], offset + written)
            if n <= 0:
                raise OSError("pwrite returned <=0")
            written += n
    return sink


def transfer_candidate(
    base_url: str,
    part_bytes: int,
    target_partial: Path,
    contract: ModelContract,
    timeout: float,
) -> dict:
    total = (contract.size + part_bytes - 1) // part_bytes
    target_partial.unlink(missing_ok=True)
    fd = os.open(target_partial, os.O_CREAT | os.O_RDWR | os.O_TRUNC, 0o600)
    os.ftruncate(fd, contract.size)
    sink = _pwrite_sink(fd)
    part_evidence: list[dict] = []
    started = time.monotonic()
    try:
        for index in range(total):
            try:
                result = retry_twice(
                    lambda index=index: fetch_part(
                        base_url, index, part_bytes, contract, timeout, sink=sink
                    )
                )
                part_evidence.append(result)
            except IntegrityError:
                raise
            except TransportError as exc:
                raise TransportError(f"PART_{index}:{exc}") from exc
        os.fsync(fd)
    finally:
        os.close(fd)
    return {
        "part_bytes": part_bytes,
        "total_parts": total,
        "parts_verified": len(part_evidence),
        "transfer_elapsed_s": round(time.monotonic() - started, 3),
        "part_evidence": part_evidence,
    }


def verify_whole(path: Path, contract: ModelContract) -> dict:
    size = path.stat().st_size
    with path.open("rb") as f:
        magic = f.read(4)
    digest = sha256_path(path)
    passed = size == contract.size and magic == GGUF_MAGIC and digest == contract.sha256
    return {
        "size": size,
        "sha256": digest,
        "magic": magic.decode("ascii", errors="replace"),
        "pass": passed,
    }


def smoke(llama_cli: Path, model: Path, timeout: float) -> dict:
    if not llama_cli.exists():
        return {"pass": False, "terminal": "RUNTIME_UNAVAILABLE", "error": f"missing:{llama_cli}"}
    cmd = [
        str(llama_cli), "-m", str(model), "-p", "Return exactly: SANDBOX_LLM_OK",
        "-n", "16", "--temp", "0", "-no-cnv"
    ]
    started = time.monotonic()
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return {"pass": False, "terminal": "SMOKE_FAILED", "error": f"timeout:{exc}"}
    merged = (cp.stdout or "") + "\n" + (cp.stderr or "")
    passed = cp.returncode == 0 and "SANDBOX_LLM_OK" in merged
    return {
        "pass": passed,
        "terminal": TERMINAL_PASS if passed else "SMOKE_FAILED",
        "exit_code": cp.returncode,
        "elapsed_s": round(time.monotonic() - started, 3),
        "contains_expected": "SANDBOX_LLM_OK" in merged,
        "stdout_tail": (cp.stdout or "")[-2000:],
        "stderr_tail": (cp.stderr or "")[-2000:],
    }


def run_tcc(base_url: str, output: Path, llama_cli: Path, timeout: float) -> dict:
    contract = ModelContract()
    report: dict = {
        "schema_version": "QWEN3_4B_DRIVELESS_TCC_RUN_V1",
        "states": [],
        "hard_constraints": {
            "google_drive_allowed": False,
            "google_sheets_allowed": False,
            "manual_mid_run_tuning_allowed": False,
            "github_actions_enabled": False,
        },
        "model": contract.__dict__,
        "candidate_part_bytes_desc": list(CANDIDATES),
    }

    def enter(state: str, **data):
        report["states"].append({"state": state, **data})

    enter("PRECHECK")
    disk = precheck_disk(output, contract)
    report["disk"] = disk
    if not disk["pass"]:
        report.update({"terminal": "SANDBOX_RESOURCE_LIMIT", "pass": False})
        return report

    enter("SIZE_PROBE")
    chosen, probe_evidence, probe_terminal = choose_chunk_size(
        lambda part_bytes: fetch_part(base_url, 0, part_bytes, contract, timeout)
    )
    report["probe_evidence"] = probe_evidence
    if chosen is None:
        report.update({"terminal": probe_terminal or "TRANSPORT_BLOCKED", "pass": False})
        return report

    enter("FREEZE_CHUNK_SIZE", part_bytes=chosen)
    report["frozen_part_bytes"] = chosen

    partial = output.with_suffix(output.suffix + ".partial")
    chosen_index = list(CANDIDATES).index(chosen)
    transfer_errors: list[dict] = []
    for part_bytes in CANDIDATES[chosen_index:]:
        enter("TRANSFER", part_bytes=part_bytes)
        try:
            transfer = transfer_candidate(base_url, part_bytes, partial, contract, timeout)
            report["transfer"] = transfer
            report["frozen_part_bytes"] = part_bytes
            break
        except IntegrityError as exc:
            partial.unlink(missing_ok=True)
            report.update({"terminal": "INTEGRITY_FAILED", "pass": False, "error": str(exc)})
            return report
        except TransportError as exc:
            transfer_errors.append({"part_bytes": part_bytes, "error": str(exc)})
            partial.unlink(missing_ok=True)
    else:
        report.update({"terminal": "TRANSPORT_BLOCKED", "pass": False, "transfer_errors": transfer_errors})
        return report
    report["transfer_errors"] = transfer_errors

    enter("WHOLE_VERIFY")
    whole = verify_whole(partial, contract)
    report["whole_verify"] = whole
    if not whole["pass"]:
        partial.unlink(missing_ok=True)
        report.update({"terminal": "INTEGRITY_FAILED", "pass": False})
        return report
    os.replace(partial, output)

    enter("LLAMA_SMOKE")
    smoke_result = smoke(llama_cli, output, timeout=max(timeout, 300.0))
    report["smoke"] = smoke_result
    if not smoke_result["pass"]:
        report.update({"terminal": smoke_result["terminal"], "pass": False})
        return report

    enter("EXIT_GATE")
    report.update({"terminal": TERMINAL_PASS, "pass": True, "output": str(output)})
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://qwen3-4b-range-temp.onrender.com")
    ap.add_argument("--output", type=Path, default=Path("/mnt/data/Qwen3-4B-Q4_K_M.gguf"))
    ap.add_argument("--llama-cli", type=Path, default=Path("/mnt/data/llama-b10936/llama-b10936/llama-cli"))
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--report", type=Path, default=Path("/mnt/data/qwen3_4b_driveless_tcc_report.json"))
    args = ap.parse_args()
    report = run_tcc(args.base_url, args.output, args.llama_cli, args.timeout)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("pass") else 2

if __name__ == "__main__":
    raise SystemExit(main())
