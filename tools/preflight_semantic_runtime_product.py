#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "semantic_runtime"
PINS = PKG / "research_pins.json"
SCHEMAS = (
    ROOT / "schemas" / "semantic_runtime_task_v1.json",
    ROOT / "schemas" / "semantic_runtime_ir_v1.json",
    ROOT / "schemas" / "semantic_runtime_solver_v1.json",
)
PRODUCT_FILES = (
    PKG / "__init__.py",
    PKG / "public_hypotheses.py",
    PKG / "discovery.py",
    PKG / "solver.py",
    PKG / "runtime.py",
    ROOT / "tools" / "semantic_runtime_cli.py",
)
FORBIDDEN_IMPORT_TOKENS = (
    "score_",
    "validate_",
    "generate_",
    "reference_truth",
    "oracle",
    "corpus",
)
ALLOWED_PRODUCT_PREFIXES = (
    "semantic_runtime",
)


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(raw)}\0".encode())
    h.update(raw)
    return h.hexdigest()


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level:
                mod = "." * node.level + mod
            out.append(mod)
    return sorted(set(out))


def main() -> int:
    failures: list[dict] = []
    checks: dict[str, bool] = {}

    pins = json.loads(PINS.read_text(encoding="utf-8"))
    pin_rows = []
    for rel, expected in sorted(pins["files"].items()):
        path = ROOT / rel
        actual = git_blob_sha(path) if path.exists() else None
        ok = actual == expected
        pin_rows.append({"path": rel, "expected": expected, "actual": actual, "pass": ok})
        if not ok:
            failures.append({"gate": "FROZEN_RESEARCH_ASSET_DRIFT", "path": rel})
    checks["research_pins_21_of_21"] = len(pin_rows) == 21 and all(x["pass"] for x in pin_rows)

    import_rows = []
    for path in PRODUCT_FILES:
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            failures.append({"gate": "PRODUCT_PY_COMPILE", "path": str(path.relative_to(ROOT)), "detail": str(exc)})
            continue
        mods = imported_modules(path)
        bad = []
        for mod in mods:
            low = mod.lower()
            if any(token in low for token in FORBIDDEN_IMPORT_TOKENS):
                bad.append(mod)
        import_rows.append({"path": str(path.relative_to(ROOT)), "imports": mods, "forbidden": bad})
        if bad:
            failures.append({"gate": "PRODUCTION_IMPORTS_RESEARCH_TEST_AUTHORITY", "path": str(path.relative_to(ROOT)), "imports": bad})
    checks["product_python_compiles"] = len(import_rows) == len(PRODUCT_FILES)
    checks["production_import_leakage_zero"] = all(not x["forbidden"] for x in import_rows)

    schema_rows = []
    for path in SCHEMAS:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ok = isinstance(data, dict) and data.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        except Exception:
            ok = False
        schema_rows.append({"path": str(path.relative_to(ROOT)), "pass": ok})
        if not ok:
            failures.append({"gate": "PUBLIC_SCHEMA_PARSE", "path": str(path.relative_to(ROOT))})
    checks["public_schemas_3_of_3"] = all(x["pass"] for x in schema_rows)

    test = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "tests.test_semantic_runtime_product"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    checks["non_assay_product_smoke"] = test.returncode == 0
    if test.returncode:
        failures.append({"gate": "NON_ASSAY_PRODUCT_SMOKE", "detail": (test.stdout + "\n" + test.stderr)[-8000:]})

    checks["no_github_actions_dependency"] = not (ROOT / ".github" / "workflows" / "semantic_runtime.yml").exists()
    checks["no_google_drive_dependency"] = all(
        "google" not in " ".join(row["imports"]).lower() and "drive" not in " ".join(row["imports"]).lower()
        for row in import_rows
    )

    passed = all(checks.values()) and not failures
    out = {
        "protocol": "SEMANTIC_RUNTIME_PRODUCT_P01_PREFLIGHT_V1",
        "issue": 54,
        "ecv4_phase": "I54:REPAIR",
        "pass": passed,
        "terminal": "PRODUCT_P01_IMPLEMENT_RUNTIME_PASS" if passed else "PRODUCT_P01_IMPLEMENT_RUNTIME_FAIL_CLOSED",
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "research_pin_rows": pin_rows,
        "production_import_rows": import_rows,
        "schema_rows": schema_rows,
        "test_stdout_tail": test.stdout[-6000:],
        "test_stderr_tail": test.stderr[-6000:],
        "next_ecv4_phase": "I54:REGRESSION" if passed else "I54:REPAIR",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
