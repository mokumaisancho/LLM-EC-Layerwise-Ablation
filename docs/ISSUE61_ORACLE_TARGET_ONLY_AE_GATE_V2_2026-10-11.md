# Issue #61 — Oracle target-only replay gate v2 (2026-10-11)

Scope: **original Issue #1 Phase1 S1–S4 only**. Frozen v1 and TCC v10
remain unchanged. This is a **partial implementation** of #61, not a claim
that original A–E has run scientifically or that #59/#60 is resolved.

## Why this version exists

The older \`issue1_phase1_ae_gate_v1.py\` checks E interventions only for
same **earlier** layers, a target layer that matches Oracle gold, and an
internally consistent SHA chain. Changing an **additional later layer** in
E_S1 or E_S2 or E_S3 can pass its structural gate after rehashing. Such a
trace must never count as a single-layer causal intervention.

## Implementation / invocation

- \`tools/issue1_phase1_ae_gate_v2.py\` is additive and has its own
  \`ISSUE1_PHASE1_AE_RAW_V2\` contract.
- \`verify(raw, gold, public_inputs, trusted_replay)\` **requires** the
  verifier/operator to provide a \`TrustedReplay\` object with executable,
  source-file SHA-pinned \`Binding\` objects. Merely providing JSON receipts,
  even with coherent hashes, is insufficient; missing authority fails
  \`G8_TRUSTED_REPLAY_REQUIRED\`.
- At each stage, the verifier independently reruns the **fixed** plan:
  A/B share LLM S1/S2, C/D share fixed S1/S2, B/D run EC S3/S4, and each
  E_Si inherits **A's unchanged engines everywhere except target Si**.
  Stages after Si naturally consume the changed Si output but may not
  replace their own method or engine. **Do not require downstream outputs
  to equal A**; their changed inputs can legitimately change results.
- Every replayed stage is checked against the submitted output, upstream
  SHA and execution receipt, including actual engine fingerprint,
  source-file digest, model, seed, parameters and actual callback symbol/source fingerprint. The trusted judge
  independently recomputes final_success. Public input SHA binds cases.
- Source identity is checked before and after the full replay; v1 legacy
  gates remain additive (not removed). Output is always
  \`original_AC18_pass_automatically=False\` and
  \`original_phase1_complete=False\`.

Development tests:

\`\`\`sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_issue1_phase1_ae_gate_v2
\`\`\`

The 17 tests cover a clean matched eight-arm replay and hostile cases with
extra E_S1→S2, E_S2→S3, E_S3→S4 substitutions after internally consistent
SHA rehashing. They also reject forged engine identifiers and fingerprints,
missing receipts, source code pin mismatch, callback code from another file or swapped within the same file,
missing authority, forged final outcome, altered public input, duplicate arm,
corrupted upstream hash, mid-replay raw mutation, and a stage callback that attempts to receive
Oracle gold as an extra parameter.

## Authority limits; no silent science promotion

These are **development-only deterministic toy engines**, not actual LLM or
native EC outputs. The registry is pretrusted **by the caller**; this code
does not independently establish external custody of the source, runtime
binary/process, LLM inference provenance or Oracle label independence.
Ordinary Python callbacks could access global state, disk or network;
argument isolation alone is **not proof of Oracle blindness**. Repeating
a live nondeterministic LLM call may not reproduce the exact output.
A signed/custody-controlled producer or genuinely isolated, externally
attested inference runner is still required for scientific #61 closure.

A cached model output, unsigned manifest, development fixture, caller-chosen
fingerprint, or internally consistent replay receipt is not such proof.
Any real-science acceptance for these sources must **fail closed** until
that independent authority and unseen labels are available.

## Original AC/MVP dependencies (unchanged)

| Work gate | Depends on | Current state |
|---|---|---|
| W0 original frozen definition; AC20 DAG | original Issue #1 source seals | verified in v10 |
| W4B native S3 admissibility (#59) | legitimate semantic authority, held-out S3 cases | **OPEN** |
| W4C native S4 complete obligations (#60) | independently complete source-grounded inventory | **OPEN** |
| W5 target-only E provenance (#61) | versioned v2 replay + externally trusted real runner | **v2 synthetic controls PASS; real proof OPEN** |
| W5 actual matched A/B/C/D/E | #59 + #60 + #61 real source authority | **BLOCKED** |
| W6 all original 18 required AC | W5 and original layerwise metrics, threshold 0.20 | **2/18 proven; no promotion** |

AC-07/16/17 require actual controlled layerwise evidence, not this synthetic
gate's return flag. The original AC-10 and AC-18 remain post-MVP; no
additional research topics, 13 optional proof AC or 120 documents are
introduced into this Phase1 MVP.

**Stop point**: do not close #61 or Issue #1 on these tests. Next,
independently qualify a real immutable inference source, real stage receipts,
Oracle custody and non-target engine identity; then run v2 on all real A–E
cases without gold available to any non-target model.

## TCC v11 executable successor

The separate `tools/run_issue1_original_phase1_tcc_v11.py` compiles a
new 9-node/12-edge TCC graph. It executes the unchanged v10 baseline,
runs all 17 v2 adversarial tests as an automatic regression gate,
conditionally audits an in-process pretrusted A–E trace, checks pinned
Git blobs before/after and returns `blocked_native` for #59/#60.
Invalid E extra interventions through an actual replay authority route to
`blocked_integrity` rather than silently assigning PASS. Calling it via
CLI without a verifier-provisioned trusted authority never upgrades A–E.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_original_phase1_tcc_v11.py \
  --tcc-root /private/tmp/llmec-tcc-generator-reference-20261009 \
  --native-successor /private/tmp/issue1-ec-native-layerwise-20261010
```

The pinned paths above are local test checkout examples, not dependencies
that should be substituted with synthetic source claims.
