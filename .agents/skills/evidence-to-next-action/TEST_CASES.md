# Cross-domain adversarial checks for evidence-to-next-action

The skill should produce the same *logic* in each case. These are **example acceptance tests**, not a claim that any external system was actually executed or verified.

## Case A — Enterprise system integration

**Current result:** An As-Is process map and interview notes exist. **Final goal:** safely launch a migrated process.

**Incorrect next step:** "Migrate all integrations now," or "prove the whole rollout is production ready."

**Correct reasoning:**
- Known: process stages and stakeholder-reported exceptions. Unknown: which mapped steps are actually implemented in the new system.
- Immediate affordance: compare current process requirements to an implementation inventory; spot missing handoffs.
- Nearest useful outcome: a traced scope gap for one high-risk handoff.
- Next decision: Does one critical handoff have traceable implemented behavior and independent UAT evidence?
- Smallest action: match one handoff's requirement, actual implementation and test evidence; if no evidence, mark UNKNOWN and request precisely that.
- Blocker classification: full regulator signoff may be a launch blocker, not a blocker to a one-handoff gap review.
- PASS/FAIL: trace and evidence for this handoff exists vs a missing implementation/test. Not proof of complete rollout readiness.

## Case B — Scientific or algorithmic result

**Current result:** A bounded state model reproduces existing observations. **Final goal:** identify a small general generating principle.

**Incorrect next step:** "Demonstrate broad general intelligence" or "rewrite the whole reasoning framework."

**Correct reasoning:**
- New affordance: inspect state distinctions, predict outputs under permitted actions, identify what would discriminate alternatives.
- Nearest useful outcome: show what additional observable information one model-derived action can yield.
- Smallest action: compute one distinguishing observation or find that the present interface cannot distinguish the alternatives.
- Deferral: broad generalization, new NN, or full workflow integration until a specific lower-level requirement fails.
- Do not claim a small state model itself establishes intelligent goal selection.

## Case C — Operations incident

**Current result:** Three timed failures and system logs exist. **Final goal:** restore stable operations and prevent recurrence.

**Incorrect next step:** "Rebuild the infrastructure" or "prove there can never be an outage."

**Correct reasoning:**
- Baseline: record the error signature, timestamps and conditions already measured.
- New affordance: correlate incidents with one configuration change or load threshold.
- Nearest useful outcome: distinguish two plausible root causes.
- Smallest feasible action: inspect a single discriminating log/metric from the already recorded incidents; if missing, run one reversible controlled test.
- Negative result must eliminate or narrow a causal hypothesis; avoid changes that produce logs but no decision.
- Blocker: unknown root cause blocks definitive permanent fix, but not data collection or a rollback decision.

## Case D — Product evaluation

**Current result:** Prices, technical specifications and a shortlist of three models are available. **Final goal:** buy a reliable item under user constraints.

**Incorrect next step:** "Research every brand" or "prove which product is objectively best."

**Correct reasoning:**
- New affordance: filter options by hard constraints and compare only the surviving alternatives.
- Nearest useful outcome: decide between two still-eligible models.
- Smallest action: verify the *single missing discriminating property* (e.g., replacement component availability) for those two products.
- If property changes the shortlist, revise it. Otherwise make the decision with declared tradeoffs.
- Do not equate any residual uncertain product detail with a purchase blocker.

## Case E — Evidence completeness and release gate

**Current result:** A partial test suite passes, and a draft integration is present. **Final goal:** production approval.

**Incorrect next step:** mark release PASS, or demand full certification before any bounded development diagnostic.

**Correct reasoning:**
- Near-term development can continue under a scoped experimental PASS.
- Production acceptance remains blocked if independent release requirements or true end-to-end regression are missing.
- The single next action depends on the *actual decision being made*: if "Can we continue exploring?", reuse scoped evidence. If "Can we release?", identify the first mandatory missing acceptance proof.
- Explicitly distinguish safety-critical release blocker from exploratory research uncertainty.

## Cross-domain pass/fail rubric

A valid answer for each case must:
1. Preserve the ultimate objective but not promote it to the next action.
2. Explain one *new ability* made possible by the current result.
3. Identify the *nearest required outcome* and its actual missing dependency.
4. Offer a smallest feasible and verifiable action using existing materials.
5. Distinguish blocker, future requirement and optional improvement.
6. State what would change based on PASS/FAIL/UNKNOWN.
7. Not introduce unverified numerical benefit estimates, fabricated completeness or unnecessary new development.

Fail if the recommended action is merely "research more", "develop full AI", "perform all tests", or "collect complete evidence" without linking its exact information gap to the present decision.

## Granularity regression tests — reject hidden leaps

These tests specifically catch "one sentence, many assumptions" recommendations.

### G1: Large representation but tiny reachable workload
- **Evidence:** underlying system declares (2^{128}) possible bit patterns, but a fixed reset and permitted actions visit only four source states.
- **Bad conclusion:** "we compressed (2^{128}) reachable states to four and therefore accelerated projection".
- **Required decomposition:** (a) state encoding width; (b) global potential state count; (c) states reachable from actual reset; (d) learned observational equivalence classes; (e) whether a raw-input-to-model mapping exists; (f) whether the workload is repeated state transitions or new raw-state queries; (g) actual comparison with the simplest direct baseline.
- **Smallest first action:** inspect the source transition under its actual reset/actions and calculate reachable source states. **Do not start** an end-to-end cost benchmark while the denominator and input contract are unclear.
- **Pass:** says reachable 4→learned 4 for that fixed-run workload, while noting a 128-bit *representation width* and any wider quotient claim separately.
- **Fail:** treats logical state-space cardinality as real observed compression.

### G2: Correct model but no raw-input mapping
- **Evidence:** a learner produced a small input/output automaton starting at a known reset; no `phi(raw_state)` mapper was learned.
- **Bad conclusion:** "any newly supplied raw input can now be projected and processed".
- **Required decomposition:** separate history-tracked model state from a model state inferred from arbitrary fresh input.
- **Smallest first action:** examine whether the user’s intended use supplies a reset+action history or raw state snapshots. If snapshots are required, **the mapping is a new missing interface**; if histories suffice, direct model-state tracking needs no additional mapper.
- **Pass:** identifies the first missing interface conditionally instead of automatically building projection code.

### G3: Apparent runtime speedup from an expensive baseline
- **Evidence:** two implementations give identical output, but the source version uses a high-overhead wrapper or repeated recomputation.
- **Bad conclusion:** "the learned model has proven a causal computational advantage".
- **Required decomposition:** identify the direct optimized baseline, acquisition/proof costs, repeated call count, feature extraction and cache effects.
- **Smallest first action:** compare *one* direct lower-overhead source path to the learned path before building full amortized infrastructure.
- **Pass:** labels any raw-speed result as implementation-specific until the counterfactual is tested.

### G4: Distinct project milestone and final release
- **Evidence:** functional component passes a sandbox test; production compliance review is outstanding.
- **Bad conclusion:** "the entire project is blocked, so do not continue feature inspection".
- **Smallest first action:** classify whether the present decision concerns exploratory component work or production release. Only the latter requires complete compliance as a current blocker.

### G5: Unknown input and a speculative grand solution
- **Evidence:** a useful partial artifact exists, but the system's next input contract is unclear.
- **Bad conclusion:** "train a more powerful general model" or "run an unfamiliar-task benchmark".
- **Smallest first action:** name the single missing input→operation edge, inspect current interface, and choose one bounded check.
- **Pass:** refuses to formulate a multi-stage experiment until its first interface is established.

## Granularity signoff

For any suggested next step, the reviewer must be able to complete a one-line check:

`EXISTING_INPUT -> ONE_OPERATION -> ONE_OBSERVABLE_OUTPUT -> ONE_PASS_FAIL_UNKNOWN_DECISION`.

If this requires implicit extra data, new authority, new benchmark, new compiler, another algorithm, or a second acceptance condition, split the action and choose the earliest decision-critical edge. The downstream steps stay pending.
