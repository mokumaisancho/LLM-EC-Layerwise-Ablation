# Semantic Runtime V4: operator-authorized execution

**Qualified code-level state:** `ISSUE55_CODE_ACCEPTANCE_COMPLETE` (2026-10-08).
**Actual Mac installation:** not performed or attested.

## Execution boundary

For externally supplied IR, only use
`semantic_runtime.execution_v4.execute_authorized_ir(ir, task, solver, policy_id)`
or `tools/semantic_runtime_cli_v4.py execute IR TASK SOLVER --policy-id ID`.

Do not expose V1 `execute_validated_ir(ir, solver)` or V2
`execute_validated_ir(ir, task, solver)` as a remotely callable execution endpoint.
Their existence is retained only to preserve frozen research/product pins.

V4 refuses all execution by default: the shipped
`semantic_runtime/approved_policy_v3.json` contains **zero approvals**.
It accepts only a pair of exact task and solver digests in an installed
operator-owned manifest, then re-derives and validates the IR. It does not
accept a request-controlled policy file or perform privileged operations.

## Opt-in local installation (operator only)

Create an isolated owner-controlled bundle on the managed computer. For example,
from the repository root:

```sh
mkdir -p "$HOME/semantic-runtime-v4/tools"
chmod 700 "$HOME/semantic-runtime-v4"
cp -R semantic_runtime "$HOME/semantic-runtime-v4/"
cp tools/semantic_runtime_cli_v4.py "$HOME/semantic-runtime-v4/tools/"
python3 tools/install_semantic_runtime_policy_v4.py \
  --bundle-dir "$HOME/semantic-runtime-v4/semantic_runtime" \
  --policy-id my-approved-task \
  --task /path/to/approved-task.json \
  --solver /path/to/approved-solver.json
python3 "$HOME/semantic-runtime-v4/tools/semantic_runtime_cli_v4.py" \
  execute /path/to/ir.json /path/to/approved-task.json \
  /path/to/approved-solver.json --policy-id my-approved-task
```

The installer requires a default-deny manifest and refuses implicit overwrite;
the installed approval is an atomic mode-0600 file update. It requires no sudo,
no authorization bypass, and no third-party target. To change an approval,
start from a new isolated default-deny bundle, version and test it, then swap
the controlled deployment. Do not serve the installer as a network API.

Operator approval must be granted deliberately: no example task/solver is
approved in the committed repository. Keep the source bundle, its parent
directories, its Python interpreter and the executing user under your control.
Same-UID hostile processes or a compromised package are outside the guaranteed
security boundary.

## Verified gates

- Real **non-mocked** installed approval in an isolated owner-owned bundle
  (Render Linux): 13/13 V4 checks, including symlink/permission tampering,
  changed task/solver, forged IR, and default deny.
- V2 forged-IR regression: 15/15; V3 policy regression: 7/7;
  frozen V1 regression: 10/10.
- Product pins: 11/11; research pins: 21/21 unchanged.
- Original pinned SUITE gate: PASS; original pinned ECv4 dynamic frontier:
  REPAIR -> REGRESSION -> EVIDENCE; invalid authority/digest blocked.
- Result: `results/issue55_v4_final_acceptance_2026-10-08.json`.

This is a **code-level trust-boundary acceptance**, not a claim that the actual
user's Mac or production deployment has already been tested. No external
world-knowledge, open-ended ontology, or arbitrary LLM replacement is implied.
