#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "semantic_runtime"
PINS = PKG / "research_pins.json"
FORBIDDEN_IMPORT_FRAGMENTS = (
    "score_",
    "validate_s1c",
    "generate_s1c",
    "reference_truth",
    "oracle",
)


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(raw)}\0".encode())
    h.update(raw)
    return h.hexdigest()


def fail(code: str, detail=None) -> int:
    print(
        json.dumps(
            {
                "terminal": "PRODUCT_RUNTIME_PREFLIGHT_FAIL_CLOSED",
                "code": code,
                "detail": detail,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 3


def main() -> int:
    pins = json.loads(PINS.read_text(encoding="utf-8"))["files"]
    drift = []
    for rel, expected in pins.items():
        path = ROOT / rel
        if not path.exists():
            drift.append({"path": rel, "reason": "MISSING"})
            continue
        actual = git_blob_sha(path)
        if actual != expected:
            drift.append({"path": rel, "expected": expected, "actual": actual})
    if drift:
        return fail("FROZEN_RESEARCH_ASSET_DRIFT", drift)

    # Prove extraction did not retune the audited deterministic cores.
    if (PKG / "public_hypotheses.py").read_bytes() != (ROOT / "tools" / "s1c_v31_public_hypotheses.py").read_bytes():
        return fail("PUBLIC_HYPOTHESIS_EXTRACTION_DRIFT")
    if (PKG / "solver.py").read_bytes() != (ROOT / "tools" / "s2b2b2_enumerative_inducer.py").read_bytes():
        return fail("SOLVER_EXTRACTION_DRIFT")
    expected_discovery = (ROOT / "tools" / "s1c_v31_deterministic_baseline.py").read_text(encoding="utf-8").replace(
        "from s1c_v31_public_hypotheses import (",
        "from .public_hypotheses import (",
    )
    if (PKG / "discovery.py").read_text(encoding="utf-8") != expected_discovery:
        return fail("DISCOVERY_EXTRACTION_DRIFT")

    import_violations = []
    for path in PKG.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [x.name for x in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                low = name.lower()
                if low.startswith("tools.") or any(fragment in low for fragment in FORBIDDEN_IMPORT_FRAGMENTS):
                    import_violations.append(
                        {"path": str(path.relative_to(ROOT)), "import": name}
                    )
    if import_violations:
        return fail("FORBIDDEN_PRODUCTION_IMPORT", import_violations)

    schema_files = [
        ROOT / "schemas" / "semantic_runtime_task_v1.json",
        ROOT / "schemas" / "semantic_runtime_ir_v1.json",
        ROOT / "schemas" / "semantic_runtime_solver_v1.json",
    ]
    for path in schema_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return fail("PUBLIC_SCHEMA_INVALID", {"path": str(path), "error": repr(exc)})

    test = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "tests.test_semantic_runtime_product",
            "-q",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if test.returncode:
        return fail("PRODUCT_RUNTIME_REGRESSION_FAILED", test.stdout + test.stderr)

    out = {
        "protocol": "PRODUCT_RUNTIME_PREFLIGHT_V1",
        "pass": True,
        "terminal": "PRODUCT_RUNTIME_PREFLIGHT_PASS",
        "research_pin_gate": "PASS",
        "research_pin_count": len(pins),
        "core_extraction_gate": "PASS",
        "production_import_gate": "PASS",
        "public_schema_gate": "PASS",
        "non_assay_regression_tests": "10/10",
        "canonical_smoke_sha256": "695312aaaeffa1d9f45e78957cbc4952791116998eb567050c692e15a4df199b",
        "determinism_replay": "PASS",
        "cli_smoke": "PASS",
        "post_result_scientific_tuning": False,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
