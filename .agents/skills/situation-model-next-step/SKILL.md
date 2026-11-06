---
name: situation-model-next-step
description: Use when a research PoC has produced a small state model, learned dynamics, latent representation, causal abstraction, or partial result, and the next experiment is unclear or excessively ambitious. Inventory what the model already enables, identify missing prerequisites and a single decision-point blocker, then propose only the nearest evidence-backed next action. Especially relevant to GEN001, ECv4.4, and multi-stage AI/NN research. Do not mistake compression, test PASS or workflow closure for novel reasoning capacity.
---

# Situation-model-first research decision skill

## Core rule

**Do not jump from “a small situation model was found” to “solve unfamiliar problems”.**
A situation model is an information-bearing representation and transition system, not an objective, decision policy, or proof of intelligence. First derive the *specific new operations it enables*, then add only the missing capability required by the research's **existing** goal.

Do not introduce a new ambitious goal just to justify a PoC. Do not substitute compliance/closure machinery for progress on the original scientific problem. Do not equate an abstract state-count reduction with saved runtime or generalization.

## Mandatory inputs (reuse, never request a known answer again)

Record these six fields, marking **UNKNOWN** without inventing details:
1. **Original decision**: the smallest existing research question and its acceptance condition, not a newly invented task.
2. **State-model contract**: model type, state variables or equivalence classes, actions, observation/output, reset/initial history, and valid horizon.
3. **Acquisition**: learned/handcrafted/known dynamics; precise boundary between learner input and verifier's privileged truth; references to original artifacts.
4. **Evidence grade**: independently measured, mathematically derived under assumptions, retrospectively tested, synthetic, externally held-out, or untested. Source/version IDs.
5. **Unresolved facts**: unknown present state, missing operations, missing goal/utility, hidden variables, unknown time scale, partial proof.
6. **Resources**: acquisition/encoding/transformation/learning/verification/operation costs; unknown expenses are UNKNOWN, not zero.

## Decision procedure (always perform in order)

### 1. Reconstruct the *situation*, not only a problem list
Capture: what was known before the model, what new information the model contains, and which alternatives remain observationally indistinguishable. Distinguish the **world state x**, the learned **abstract state z**, current **belief/possible states B**, and observed output **y**. If only y is known, do **not** assume z is known.

Explicitly note which observations/inputs/reset contracts make the representation sufficient. For a candidate abstraction, future preservation is conditional on a specified output and action scope; outside that scope, result is UNKNOWN.

### 2. Translate the model to a capabilities ledger
Evaluate each row using **DIRECT**, **STANDARD-ALGORITHM**, **NEEDS-ADDITIONAL-INFORMATION**, **UNSUPPORTED**, or **UNKNOWN**.

| Level | Capability | Existing model is sufficient if… | Additional input or method | Smallest validation |
|---|---|---|---|---|
| C0 | State naming, compressing equivalent histories | state encoding + reachable semantics defined | none | compare two histories giving same abstract state |
| C1 | Predict observable output after an action | starting abstract state/belief + valid action + transition known | state tracking or reset/action history | one-step output prediction vs reference |
| C2 | Compare futures, identify ambiguous states | alternatives, valid actions, observable future available | standard distinguishing-sequence search | shortest action suffix separating a state pair, or proven unidentifiable |
| C3 | Detect mismatch/anomaly and refine model | predicted and actual observable stream available | independent new observation | disagreement -> witness; no silent PASS |
| C4 | Enumerate reachability/operational constraints | transition graph and externally defined target property known | standard graph search / safety predicate | bounded reachable/not-reachable + certificate |
| C5 | Select actions toward a user-defined objective | explicit goal, cost and risk model provided | planning/control algorithm | one bounded, predeclared target in the same domain |
| C6 | Novel domain reasoning/generalization | additional assumptions and external evidence | research hypothesis; new domain and separate verifier | defer until an actual lower-level requirement fails |

**C2, not C6**, is often the first genuinely useful capability after discovery of a finite state model. An output-only observation may not uniquely identify the present abstract state; a *discriminating operation* can resolve the ambiguity.

Preserve the difference between: (i) what the model logically enables; (ii) what code actually implemented; (iii) what independent evidence validated; (iv) what remains only prospective.

### 3. Perform a dependency-gap check
For each proposed function, ask: What exact extra information does it need? Does the existing model already contain it? Can a standard deterministic algorithm supply the missing operation? Is the supposed blocker an actual prerequisite for the next test, or merely for a later production/EC closure?

Choose **one** nearest missing link in the original critical path. Record other issues as **deferred by explicit condition**; do not promote them all to P0. E.g., an external normative obligation inventory may block production S4 closure, **not** synthetic finite-state predictive-model inspection.

### 4. Pick one minimum *next action* using a strict gate
Prefer in this order:
1. **No new test**: existing evidence already establishes the capability; document and reuse it.
2. **Calculation over the discovered model**: table, reachable set, ambiguity class, shortest separating input, counterexample.
3. **One independent observation/experiment**: compare the predicted effect with the source, report PASS/FAIL/UNKNOWN, and stop at the smallest useful decision point.
4. **Existing algorithm** only if a specific capability gap is proven: automata L*/AALpy for finite resettable output behavior; CEGIS/SyGuS for bounded synthesis with a verifier; SINDy/Koopman methods only for compatible continuous dynamics. Do not launch them together.
5. **New algorithm/NN** only if no reused technique covers a demonstrated need; quantify its expected improvement and remaining risk first.

Never propose a general novel-task benchmark, new objective invention, giant LLM compression, full ECv4.4 integration, or open-world proof obligation as the first move merely because a small model exists.

### 5. Evidence, costs, and decision status
For each action, state: observed vs derived vs hypothesized, test setup, correct scope, comparison baseline, independent witness, and actual marginal cost. Distinguish search/state savings from model-learning cost and runtime performance. If no valid independent test, mark UNKNOWN rather than PASS. Never upgrade a scoped synthetic PASS to external generalization.

### 6. A single next decision
Always conclude with **one** of:
- **REUSE**: model already supplies the capability; no experiment needed.
- **TEST**: one smallest missing function with fixed prediction, observable and verifier.
- **REPAIR**: specific counterexample; exact model contract to amend.
- **HOLD**: missing genuinely necessary information (name what and who can supply it).
- **DEFER**: not on current critical path, with its reactivation trigger.

A rejected idea must explain **why it is premature**, not just be silently dropped.

## User-facing output contract (compact, Japanese)
Use this order, ordinarily no more than ~25–40 lines:
1. **結論** — original goal and current highest-supported capability.
2. **状況モデルの能力表** — direct/derived/needs extra/untested, with evidence.
3. **能力を使う順序・単一依存** — nearest step only; state identification before planning.
4. **次の最小アクション** — precise input, process, outcome, failure meaning, no code unless asked.
5. **延期するもの** — one sentence listing trigger(s), plus artifacts/provenance if touched.

Only create Mermaid if it makes a genuinely tangled dependency clearer; do not add diagrams for simple linear logic.

## Quality tripwires

- If an action needs knowing the abstract present state, **ask how it was identified**: reset + action history, sensor inference, or belief set. Observation value alone may be ambiguous.
- If a model combines states observationally, **do not assert** internal physical/causal coordinates were recovered.
- If the learner's equivalence oracle has privileged knowledge, **do not call** discovery fully black-box without qualification.
- If every action sequence considered is inside the original contract, **do not claim** out-of-domain generalization.
- If the new model uses fewer states, **do not claim** lower time, RAM or total program complexity without measurement.
- If evidence/source/obligation completeness is required for production closure, **do not conflate** it with an exploratory closed-world PoC.
- If the assistant previously proposed too large a PoC, make the missing intermediate capability explicit and correct the plan before writing additional code.

## Project reference

For GEN001 read [the filled assessment](../../../research/MINIMAL_GENERATIVE_REASONER_2026-11-05/SITUATION_MODEL_CAPABILITY_AUDIT_2026-11-07.md), [PoC7](../../../research/MINIMAL_GENERATIVE_REASONER_2026-11-05/poc/POC7_FINDINGS.md) and [original research goal](../../../research/MINIMAL_GENERATIVE_REASONER_2026-11-05/README.md). Keep ECv4.4 as optional evidence controller, not a prerequisite for understanding what the learned model can do.
