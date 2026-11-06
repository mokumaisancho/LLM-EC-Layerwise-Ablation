---
name: evidence-to-next-action
description: A domain-independent framework for deciding what to do next. Use for research, engineering, operations, business analysis, project delivery, personal planning, or any multi-step task when the user asks for next steps, blockers, realistic priorities, feasibility, status, completion, or whether a proposal actually advances the goal. Ground decisions in current evidence, distinguish end goals from immediate decisions, inventory newly enabled capabilities, and choose the smallest feasible action that changes a decision. Avoid ambitious leaps, unnecessary new work, and fake completeness.
---

# Evidence → situation → next action

## Principle

**Do not jump from the ultimate aspiration to the next task. Do not jump from a remaining defect to a high-priority task.**

First reconstruct the current situation from evidence, identify what the achieved result **now enables**, relate that capability to the *next necessary outcome*, and select the least-cost feasible step that answers a consequential question.

The same procedure must work without changing the algorithm for research, business, technology, product, operations, and policy questions. Domain-specific examples are only test cases, never the skill's conceptual framework.

## Trigger

Apply whenever the request contains a form of "what next?", "continue", "what remains?", "what is blocking?", "is this enough?", "is the plan appropriate?", "what can we do with this?", "evaluate feasibility", "make this less ambitious", or "define a realistic plan". Especially apply after an earlier assistant-proposed next step is challenged.

### Non-goals

Do not invent a larger goal, start a new PoC for its own sake, build a new algorithm without a demonstrated need, ask again for facts already supplied, or force the user into a form. Do not confuse a safety/release/closure criterion with the prerequisite for exploratory work. No unnecessary source code examples.

## Procedure (invariant sequence)

### 0. Preserve the user's goal and the present decision

Separate three levels. Record exactly one sentence for each:

- **Ultimate outcome (G):** the user's durable purpose. It may be aspirational and not yet directly testable.
- **Nearest useful outcome (M):** the next capability, artifact, decision, or measurable condition that would genuinely contribute to G, using what already exists.
- **Immediate decision (D):** one question whose answer changes which action should be performed now.

Never assume G, M, and D are the same task. A proposal is **misaligned** if it aims at G directly without explaining the necessary intermediate M and its dependencies. If an accepted original acceptance criterion exists, preserve it; narrow only the *scope of a checkpoint*, not the original objective.

### 1. Establish the current factual baseline

Retrieve or read existing work before recommending more. Produce an internal **evidence ledger** for material claims:

| Claim / current result | Status | Evidence/source | Scope and assumptions | What it enables / cannot establish |
|---|---|---|---|---|
| ... | VERIFIED / OBSERVED / DERIVED / INFERRED / HYPOTHESIS / UNKNOWN / NOT_RUN | exact artifact or user input | which objects, conditions, and date | bounded implication; explicit limit |

Do not upgrade **OBSERVED** or synthetic/retrospective success to general, independently reproduced, or production proof. Do not call unknown zero or treat an unrun validation as PASS. Conflicting, incomplete, or stale evidence must remain visible and receive a concrete follow-up if decision-critical.

### 2. Translate results into newly available options

Before listing problems, ask the **affordance questions**:

- What *new information* do we have?
- What can we now **observe, distinguish, predict, compare, decide, execute, verify, reuse, or automate** that was previously unavailable?
- Which of these can be used immediately with current assets? Which require one more input? Which are outside the result's validity?
- Is the proposed next task really a use of the newly established capability, or an unrelated new aspiration?

Categorize options as:
- **READY**: directly supported by current evidence/assets, no new method necessary.
- **ONE-GAP**: one explicit input/operation/verification needed.
- **MULTI-GAP**: several unresolved dependencies.
- **UNSUPPORTED**: no evidence of feasibility in this setting.

Keep capability (what can logically be done), implementation (what actually exists), and verification (what has been observed to work) distinct.

### 2b. **Atomic-granularity gate: mandatory before suggesting a task**

The previous procedure can still hide a giant leap inside terms like "validate usefulness", "measure end-to-end", "integrate", or "solve the next issue". **A one-sentence action is not necessarily a small action.** Decompose any proposal until each step has one unambiguous transformation and one independently checkable output.

**Three simultaneous resolutions:**

- **System layers** (what object is being discussed): raw source/real-world process; representation or model; learner/constructor; execution interface; consumer/use case; evaluator; deployment/authority. Different layers may share terminology but are not interchangeable.
- **Claims** (what relationship is asserted): existence, discovery, identification, equivalence, usefulness, improvement, generalization, acceptance. Proof of a claim at one layer **does not** establish the next claim.
- **Operations** (what is being done now): inspect an existing artifact; read one interface; compute one quantity; test one relationship; compare one baseline; decide whether to proceed. An operation requiring two new unknown components is too large unless they can be checked independently.

For every critical proposed transition A → B, make a tiny **edge record**:

| Field | Exact question |
|---|---|
| Input | Which specific data/artifact and whose version? |
| Operation | What *single* transformation, observation, or decision occurs? |
| Output | Which object or single measured fact is produced? |
| Prerequisite | Which assumptions/capabilities must *already* hold? |
| Evidence | Is this edge observed, mathematically derived, only proposed, or untested? |
| Check | What minimal independent check could falsify this edge? |
| Cost | Which acquisition / transformation / verification / repeated-use costs belong to this edge? |
| Decision | What exact choice becomes possible after this edge is checked? |

**Stop if an edge has missing prerequisite or unverifiable output**; subdivide it rather than bypassing it with a larger task. Do not demand implementation when a static inspection, algebraic check, or two-case contrast already resolves the decision.

**Counterfactual and denominator check:** For any claimed gain, ask "*relative to exactly which no-change baseline?*" Separate logical state-space size, **reachable** states under the actual input/initialization contract, encoded memory footprint, per-step operations, initial transformation cost, model acquisition cost, independent verification cost, and number of uses. These measures cannot substitute for one another. Ask "*what would still be possible without the new artifact?*" If a capability existed already, the new artifact's contribution is unproven until compared with that baseline.

**Working granularity tests:** A next action fails this gate when it contains:
- multiple independent success criteria connected by "and" without intermediate checks;
- a change of layer (e.g. discovered model → raw-input projection → runtime speedup) without a proven mapping;
- a model-sized result interpreted as a workload-sized improvement without measuring the workload;
- a proposed experiment that requires first inventing new data, new evaluation goals, and new verification tools;
- a claimed blocker for an optional later phase promoted to an immediate dependency;
- a next step whose first concrete act cannot be named *with existing artifacts*.

**Reconstruct the smallest useful causal chain:** first establish the input/output meaning of a result; then whether the next intended operation can use that result *as is*; then test the single missing link; only then compare larger utility or cost. If the current model already answers the question, report the answer, not another PoC.

**Mandatory terminal checkpoint:** Before committing to execution, output internally:
`Given [existing artifact], applying [one existing operation] produces [one checkable result], which answers [one decision] under [explicit scope].`
If it cannot be filled without inventing more components or assumptions, the step is still too coarse.

### 3. Build a dependency and gap picture (not merely a task list)

For each nearest outcome M, list its **necessary inputs and capabilities**. Mark each as PRESENT, PARTIAL, MISSING, or UNKNOWN and attach evidence.

Separate gap types to avoid solving the wrong problem:
- **Definition**: desired outcome, acceptance condition, constraints unclear.
- **Information**: necessary observation, source, context, or input missing.
- **Method**: no usable approach known for a demonstrated need.
- **Implementation**: method known, necessary execution component absent.
- **Verification**: candidate exists but evidence of correctness insufficient.
- **Utility**: correct output obtained but business/research value or cost advantage unproven.
- **Deployment/authority**: release, policy, operational custody, or external certification missing.

**Blocker test:** call X a *current blocking dependency* only if (i) X is necessary for M on all presently credible paths, (ii) X is not satisfied, (iii) no usable alternative avoids X, and (iv) X prevents the next useful decision/action now. Otherwise classify as **later**, **optional**, **risk**, or **unverified**. If no single blocker dominates, say so rather than inventing one.

A release certification might block going live, not a bounded experiment; generalization might block a broad claim, not a specific correctly scoped result.

### 4. Generate a few genuinely different actions

Produce at most three candidate actions, each connected explicitly to M:

1. **REUSE / APPLY** known results, tools, methods, assets, or existing functionality.
2. **INSPECT / CALCULATE / SMALL TEST** to settle one decision-critical unknown.
3. **ADAPT / IMPLEMENT / RESEARCH** only the missing component confirmed necessary.

Order is a preference, not a mandate. Sometimes no work is needed: record the conclusion and proceed to the next useful outcome.

For each action, determine:
- Prerequisites already satisfied? Required information/tool actually available?
- What concrete output can it create *in this turn or in a bounded execution*?
- Will its result change the next decision? If not, it is unnecessary.
- Expected contribution to M and ultimately G, not merely completion of the task itself.
- Cost, risk, reversibility, external dependencies, and independent check.
- What existing work it duplicates and why duplication would be justified.

### 5. Evaluate feasibility before ambition

Use an **ordinal decision matrix**, not fabricated percentages:

| Candidate action | Contribution to M | Prerequisites | Feasibility | Cost/effort | Verification | Decision value |
|---|---|---|---|---|---|---|
| A | direct/indirect/none | met/partial/missing | high/conditional/low/unknown | evidenced/unknown | independent/partial/none | changes decision? |

Default priority: **necessary + feasible + low-dependency + verifiable + decision-changing + reuse-friendly**.

**Hard gates:** reject or defer an action when any of these holds:
- Not logically linked to the nearest outcome.
- Requires solving multiple speculative prerequisites when a simpler action exists.
- Uses inaccessible data/tools or cannot be validated.
- Recreates available capability without a reason.
- Claims success solely because an artifact exists or a test stops.
- Raises the original scope or acceptance criterion without explicit authorization.

Do not invent probabilities or arbitrary scores. State conditional feasibility where warranted.

### 5b. Reassess task size at the interface boundary

Do a reverse check **before** announcing the next action: list every input and output interface crossed. More than one unresolved interface means there must be intermediate checkpoints. Select the *earliest unverified edge necessary to decide anything useful*, not the final downstream experiment. Reject the "do it all end-to-end" default when inputs, representation semantics, or the no-change baseline are not yet established.

### 6. Choose the shortest decision-changing next action

Select **one** action only, unless the user explicitly asks for parallel independent tracks. Specify:

- **Input**: exact existing data/assets and what is genuinely missing.
- **Operation**: observable and limited work, with preferred existing method.
- **Output**: what evidence/artifact will be obtained.
- **Decision rule**: what PASS, FAIL, or UNKNOWN will mean, including scope.
- **Why now**: one sentence identifying the dependency unlocked.
- **Not now**: at most two attractive but premature directions and their *activation trigger*.

Prefer a small local calculation over a new integrated system; a read-only inspection over a rewrite; one discriminating test over an open-ended research program. Do not demand a complete proof of an aspirational final goal as a condition for a small intermediate step.

### 7. Execute and update rather than endlessly propose

If the user authorized execution and tools are available, perform the selected bounded action now. If the action is blocked, do the closest meaningful inspection/calculation and identify its exact unmet input. Never promise asynchronous future work.

After action, record:
- **New fact** and citation/artifact.
- **What changed** in capability or uncertainty.
- **Which earlier assumption or blocker was invalidated**.
- **Which next decision is now unlocked**.
- **Remaining unknowns** and exact triggers for reconsideration.

Do not keep stacking new plans without closing the present decision.

## Internal quality checks (must pass before reply)

1. Could this same method work for a software release, a process improvement, a scientific experiment, and a purchase choice **without changing its core steps**?
2. Did I distinguish final goal, nearest useful outcome, and current decision?
3. Did I derive actual affordances of known results *before* inventing new tasks?
4. Is every claimed blocker a **necessary dependency now** rather than simply an unsolved problem?
5. Is the chosen action feasible with present information/resources and small enough to verify?
6. What would I learn from success, failure, and inconclusive evidence?
7. Did I reuse existing work and preserve previous constraints and original acceptance criteria?
8. Did I avoid conflating a milestone PASS with final-goal completion or a production release?
9. Is the next action the shortest that **changes the decision**, not just the most impressive?
10. Have I separated source, representation, acquisition, execution and evaluation so one claim cannot masquerade as another?
11. Does every proposed action have **one** defined input, one operation, one output, one independent check and one decision?
12. Is the claimed improvement normalized to the *actual relevant denominator and baseline* (e.g. reachable cases, repeated calls, whole cost), not an attractive but irrelevant big number?
13. Have I identified the first missing interface instead of prescribing the whole downstream workflow?

If any answer fails, revise the recommendation **before** proposing execution.

## Response format (compact)

Present in this order, using one table only if it clarifies a real comparison:

1. **結論** — what is actually known and what the next decision is.
2. **現在地** — evidence-supported results and immediately enabled options.
3. **差分・依存性** — one nearest outcome, missing link, blockers vs deferred issues.
4. **手段比較** — 2–3 options with feasibility, benefit and cost.
5. **次の1アクション** — exact input, work, output, PASS/FAIL/UNKNOWN and rationale.

Use diagrams only for genuinely branched dependencies. Avoid new code unless requested. Identify assumptions explicitly; do not silently broaden scope.

## Generic examples and checks

See [TEST_CASES.md](TEST_CASES.md) for unrelated fields testing the same decision sequence. Examples are for evaluating the method, not as domain-specific instructions.
