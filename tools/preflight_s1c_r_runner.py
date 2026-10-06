#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

EXPECTED_BLOBS = {
    "score_s1c_r_typed_ir.py": "e10e0ab83ac75538659e5fb313efa20e8f5c8653",
    "s1c_r_deterministic_grounder.py": "74c6a9832bc7e5ab4594e0868e235a0106d4a0d6",
    "generate_s1c_r_holdout.py": "4cfca707a440e03d992f2a2ab35fb2d9293cf37e",
    "preflight_s1c_r.py": "bf2ae7a16d63fbc2d53a2d70ebb923dad7f8f175",
    "run_s1c_r_paired_v1.py": "113862e97ab156471bb3150e4344b4c8b33d9286",
}


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(raw)}\0".encode())
    h.update(raw)
    return h.hexdigest()


def fail(detail: str) -> int:
    print(json.dumps({"terminal": "S1C_R_RUNNER_PREFLIGHT_FAIL_CLOSED", "detail": detail}, indent=2))
    return 3


def main() -> int:
    for name, expected in EXPECTED_BLOBS.items():
        path = TOOLS / name
        if not path.exists():
            return fail("missing:" + name)
        got = git_blob_sha(path)
        if got != expected:
            return fail(f"blob_drift:{name}:{got}:{expected}")
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            return fail(f"py_compile:{name}:{exc}")

    sys.path.insert(0, str(TOOLS))
    try:
        import run_s1c_r_paired_v1 as runner
        import generate_s1c_r_holdout as generator
        import score_s1c_r_typed_ir as scorer
        import s1c_r_deterministic_grounder as grounder
    except Exception as exc:
        return fail("import:" + repr(exc))

    p = subprocess.run(
        [sys.executable, str(TOOLS / "preflight_s1c_r.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if p.returncode:
        return fail("scientific_preflight:" + (p.stderr or p.stdout))
    try:
        scientific = json.loads(p.stdout)
    except Exception as exc:
        return fail("scientific_preflight_parse:" + repr(exc))
    if scientific.get("terminal") != "S1C_R_PREINFERENCE_PASS":
        return fail("scientific_preflight_not_pass")

    fixtures = generator.generate()
    if len(fixtures) != 16 or len({f["family"] for f in fixtures}) != 8:
        return fail("fixture_count")

    grammar_checks = []
    det_predictions = {}
    for f in fixtures:
        grammar = runner.grammar_for(f["visible"])
        if not grammar or "oracle" in grammar.lower() or "family" in grammar.lower():
            return fail("grammar_leakage:" + f["id"])
        for hidden in ("stable", "verified", "assigned_to", "depends_on"):
            if hidden in grammar.lower():
                return fail("grammar_hidden_semantics:" + f["id"] + ":" + hidden)
        literals = runner.atom_literals(f["visible"])
        if not literals:
            return fail("grammar_empty_atom_space:" + f["id"])
        grammar_checks.append({"fixture_id": f["id"], "atom_literal_count": len(literals)})
        det_predictions[f["id"]] = grounder.predict({"visible": f["visible"]})

    det_score = scorer.score_rows(fixtures, det_predictions)
    if det_score.get("pass") is not True:
        return fail("deterministic_score_failed")

    out = {
        "terminal": "S1C_R_RUNNER_PREFLIGHT_PASS",
        "protocol": "S1C_SEMANTIC_SPACE_TCC_V1",
        "issue": 48,
        "blob_pins": EXPECTED_BLOBS,
        "fixture_count": len(fixtures),
        "family_count": len({f["family"] for f in fixtures}),
        "grammar_checks": grammar_checks,
        "deterministic_preinference_primary": det_score["primary"],
        "deterministic_preinference_secondary": det_score["secondary"],
        "scientific_preflight_terminal": scientific["terminal"],
        "model_inference_executed": False,
        "model_acquisition_authorized": True,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
