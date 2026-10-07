# #56 V5 Strict Explicit Command Grammar — Local Operator Guide

Status: verified only for **approved finite, single-entity English command templates**.
This is a conservative deterministic intent parser, not a general natural-language reasoner.

## Trust model and safety

- The repository-shipped `semantic_runtime/approved_policy_v5.json` is empty (default deny).
- Only an offline owner action may install an exact task + solver + command grammar approval into a **separate owner-controlled local bundle**.
- Never present the offline approval installer as a web endpoint.
- Use only `tools/semantic_runtime_cli_v5.py` for authorization-aware classification and execution; V1/V2/V4 paths are retained for compatibility but lack V5 grammar restrictions.
- An incoming task or solver modified by even one character fails its SHA256 approval.
- An IR forged with correct protocol fails V2 derivation/validation even if the operator-approved texts are intact.
- A sentence outside the grammar (negation, mixed instruction, multi-intent, Japanese, free-form ambiguity, trailing text, punctuation) is **abstained**. This does **not** prove the system understands ambiguity; it conservatively refuses unrecognized strings.
- Same-UID malicious code, compromised owner deployment, and authorized-but-incorrect operator policies are outside the verified trust boundary.

## Concrete insurance-claims illustration (entirely synthetic)

Four examples with before/after behavior discover two slots:
`Claim A activates review`; `Claim B opens review`
and `Claim C disables review`; `Claim D closes review`.

An operator-approved grammar for the two discovered partitions:
```json
{
  "protocol": "SEMANTIC_RUNTIME_EXPLICIT_GRAMMAR_V5",
  "actions": [
    {"action_id": "review_open", "training_members": ["T01","T02"],
     "templates": ["{entity} activates review", "{entity} opens review"]},
    {"action_id": "review_close", "training_members": ["T03","T04"],
     "templates": ["{entity} disables review", "{entity} closes review"]}
  ]
}
```

`Claim E opens review` -> known template, then cross-check lexical grounder,
approved solver, and IR before simulating `PENDING -> DONE`.

`The evidence is unresolved between Claim G opens review OR Claim G disables review`
(no colon) -> `ABSTAIN_UNSUPPORTED_OR_AMBIGUOUS`; no execution, even if the legacy
lexical grounder guesses a slot. No real claims system is connected.

## Installation workflow (opt-in operator action)

With an owner-controlled copy of the `semantic_runtime` directory that
includes `constrained_v5.py` and `approved_policy_v5.json`, and with
the task, solver, grammar files reviewed by the owner:

```sh
python3 tools/install_semantic_runtime_policy_v5.py \
  --bundle-dir "$HOME/semantic-runtime-v5/demo/semantic_runtime" \
  --policy-id review-safe \
  --task "$HOME/semantic-runtime-v5/demo/task.json" \
  --solver "$HOME/semantic-runtime-v5/demo/solver.json" \
  --grammar "$HOME/semantic-runtime-v5/demo/grammar.json"

python3 "$HOME/semantic-runtime-v5/demo/tools/semantic_runtime_cli_v5.py" \
  classify "$HOME/semantic-runtime-v5/demo/task.json" \
  "$HOME/semantic-runtime-v5/demo/solver.json" --policy-id review-safe

python3 "$HOME/semantic-runtime-v5/demo/tools/semantic_runtime_cli_v5.py" \
  execute "$HOME/semantic-runtime-v5/demo/ir.json" \
  "$HOME/semantic-runtime-v5/demo/task.json" \
  "$HOME/semantic-runtime-v5/demo/solver.json" --policy-id review-safe
```

The installer requires a default-deny manifest. A deployed approved manifest
is not implicitly overwritten: replace it only via a separately reviewed
release. Avoid running the approval installer on the default-deny base package.

## Verified qualification

- V5 real installed-policy regression: 12/12, with an independent 16-heldout synthetic corpus.
- Frozen V4, V2 and V1: 13/13, 15/15 and 10/10.
- Frozen research pins 21/21 and product pins 11/11.
- Pinned SUITE evaluator and ECv4 frontier completed their independent gates.
- Authorized macOS 14.4.1 test: reproduced V4's wrong H03 assignment to S02;
  V5 abstained H03 and **rejected execution even with a task/solver-specific approval
  for H03**. Known commands H01/H02 remained actionable.
- No persistent daemon, no new Python dependency, no real business mutation,
  and no permission elevation. Base V5 policy has zero approvals; separately
  isolated approved-execution and blocked-H03 test bundles each have scoped approvals.
- Evidence: `results/issue56_v5_final_acceptance_2026-10-08.json`.

Qualification is bounded to the declared grammar, **not** full Japanese
understanding, unconstrained free text, unseen business domains or general LLM replacement.
