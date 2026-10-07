# Semantic Runtime Product MVP

Status: `PRODUCT_MVP_COMPLETE`

## Public API

```python
from semantic_runtime import discover_and_ground, execute_validated_ir

ir = discover_and_ground(task_contract)
result = execute_validated_ir(ir, solver_contract)
```

The package is deterministic and fail-closed. It does not import scorer, Oracle, corpus generator, hidden reference table, model runtime, Google Drive, or GitHub Actions.

## CLI

```bash
python tools/semantic_runtime_cli.py discover-ground task.json > ir.json
python tools/semantic_runtime_cli.py execute ir.json solver.json
```

Invalid contracts return exit code `3` and a `FAIL_CLOSED` JSON error.

## Contracts

- Task: `schemas/semantic_runtime_task_v1.json`
- Semantic IR: `schemas/semantic_runtime_ir_v1.json`
- Solver adapter: `schemas/semantic_runtime_solver_v1.json`

The task API also accepts the audited V3.2 public envelope (`task_id`, `structural_descriptor`, `visible`) for compatibility.

## Supported boundary

Supported:
- finite typed/auditable semantic or transition hypothesis spaces;
- deterministic two-slot partition discovery under the current 64-function coordinate-wise hypothesis class;
- raw-language grounding into discovered local slots;
- explicit ambiguity abstention;
- deterministic downstream operator execution.

Not established:
- unrestricted ontology invention;
- open-ended world-knowledge acquisition;
- replacement of arbitrary LLM reasoning;
- equivalence to larger LLMs.

## Safety / integrity

Production code rejects hidden/Oracle-bearing keys, validates exact training partition and heldout coverage, and refuses non-identifiable discovery.

`tools/preflight_product_semantic_runtime.py` pins 21 frozen research assets and blocks:
- research byte drift;
- scorer/Oracle/generator imports into production;
- extracted core drift;
- schema failure;
- regression failure;
- non-deterministic output.

## Evidence

- P01 implementation/preflight: `results/product_runtime_p01_repair_2026-10-08.json`
- P02 audited V3.2 compatibility: `results/product_runtime_p02_regression_2026-10-08.json`
- P03 final evidence: `results/product_runtime_mvp_complete_2026-10-08.json`

Governance: SUITE + ECv4, issue #54.
