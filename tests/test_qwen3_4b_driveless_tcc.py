import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "run_qwen3_4b_driveless_tcc.py"
spec = importlib.util.spec_from_file_location("qwen3_driveless_tcc", SCRIPT)
assert spec and spec.loader
tcc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tcc
spec.loader.exec_module(tcc)


def test_probe_picks_largest_success():
    calls = []

    def probe(size):
        calls.append(size)
        if size == tcc.CANDIDATES[0]:
            raise tcc.TransportError("too large")
        return {"ok": True}

    chosen, evidence, terminal = tcc.choose_chunk_size(probe)
    assert chosen == tcc.CANDIDATES[1]
    assert terminal is None
    assert calls == [tcc.CANDIDATES[0], tcc.CANDIDATES[0], tcc.CANDIDATES[1]]
    assert evidence[0]["status"] == "TRANSPORT_FAILED_AFTER_RETRY"
    assert evidence[1]["status"] == "PASS"


def test_integrity_failure_is_fail_closed():
    def probe(_size):
        raise tcc.IntegrityError("sha")

    chosen, evidence, terminal = tcc.choose_chunk_size(probe)
    assert chosen is None
    assert terminal == "INTEGRITY_FAILED"
    assert evidence[0]["status"] == "INTEGRITY_FAILED"


def test_all_transport_failures_are_blocked():
    def probe(_size):
        raise tcc.TransportError("blocked")

    chosen, evidence, terminal = tcc.choose_chunk_size(probe)
    assert chosen is None
    assert terminal == "TRANSPORT_BLOCKED"
    assert len(evidence) == len(tcc.CANDIDATES)


def test_terminal_set_is_closed():
    assert tcc.TERMINAL_PASS in tcc.TERMINALS
    assert "TRANSPORT_BLOCKED" in tcc.TERMINALS
    assert "INTEGRITY_FAILED" in tcc.TERMINALS
    assert "SANDBOX_RESOURCE_LIMIT" in tcc.TERMINALS
    assert "RUNTIME_UNAVAILABLE" in tcc.TERMINALS
    assert "SMOKE_FAILED" in tcc.TERMINALS
