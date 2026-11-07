---
name: experiment-cycle-governor
description: Automatically trigger for iterative research/PoCs, "continue the experiment", result reviews, progress drift, or whether another test is justified. Require PRE hypothesis/alternative/prediction and POST measured change to the original goal before another PoC is admitted. This is a local route to the central Skills repository.
---

# Research experiment cycle — local routing alias

**Canonical full skill**: [mokumaisancho/Skills/skills/experiment-cycle-governor/SKILL.md](https://github.com/mokumaisancho/Skills/blob/main/skills/experiment-cycle-governor/SKILL.md).

If the connected skills repository is accessible, read the full canonical skill. If it is not accessible, enforce these minimal controls directly:

1. Preserve the original issue/goal/AC, current evidence and the *nearest* decision; do not invent a new research objective.
2. **Before** a new test: state hypothesis, a credible alternative, falsifying prediction, fair baseline, one observable, verifier, budget and stop condition. If the result cannot change the next decision, **NO NEW TEST**.
3. **After** results: compare the actual measurement with the pre-frozen prediction. If the prediction was not actually registered before execution, explicitly state `PRE_MISSING` and never invent it retrospectively.
4. Score *incremental* progress: newly testable vs newly verified original AC; corrected misconception; remaining uncertainty; actual cost. A PASS or another PoC number alone is not progress.
5. Choose exactly one CONTINUE / REUSE / REPAIR / PIVOT / STOP / HOLD disposition. **CONTINUE requires a fresh specific decision-changing PRE**, not an automatic next PoC.
6. Avoid new files/issues unless they update the existing single decision; preserve source/evidence SHA and independent measurement scope.

Related selector: [.agents/skills/evidence-to-next-action/SKILL.md](../evidence-to-next-action/SKILL.md). The central skill includes an optional structural validator, examples, and richer state accounting.

**Important:** a GitHub file and AGENTS.md routing hint are not proof that ChatGPT automatically installs/loads this skill across all conversations. Only an agent host that actually reads this file is governed by it.
