---
name: situation-model-next-step
description: Legacy alias for earlier domain-specific next-step advice. For all goal, blocker, progress, feasibility, or next-action questions, use the generic evidence-to-next-action skill instead, including when the context involves a state model.
---

# Replaced by general decision-analysis skill

The old version overfitted the problem to small state models and research PoCs. **It should no longer determine the next task** or introduce its domain-specific assumptions.

Use [evidence-to-next-action](../evidence-to-next-action/SKILL.md) for the entire reasoning process. That skill applies uniformly to research, systems engineering, project delivery, operations, business analysis and practical choices.

A state model is only an input artifact to the generic steps:
1. Separate durable goal, nearest useful outcome and immediate decision.
2. Reconstruct evidence, newly enabled options and real dependencies.
3. Test whether the purported blocker is necessary *now*.
4. Select the most feasible, decision-changing small step.

Do not jump directly from a state model to unknown-problem solving; do not make this restriction the only concern. This file remains only to redirect references already pointing to the former skill.
