# Repository agent guidance

This repository contains multiple research and engineering workstreams. The assistant must preserve each issue's original objective and not confuse partial PoC progress with final acceptance.

## Domain-independent next-step decisions

For requests about priorities, current situation, blockers, progress, feasibility, realistic next steps, or how to apply existing results, **read and apply**:

[canonical Skills/evidence-to-next-action](https://github.com/mokumaisancho/Skills/blob/main/skills/evidence-to-next-action/SKILL.md) (fallback local snapshot: [.agents/skills/evidence-to-next-action/SKILL.md](.agents/skills/evidence-to-next-action/SKILL.md))

The private `mokumaisancho/Skills/skills/evidence-to-next-action/` is the canonical source; the repository-local file is a migrated snapshot, not an independent maintenance authority. The host must explicitly load the skill; this GitHub link alone cannot automatically install it in chat. For deeper technical root-cause verification, reuse the distinct canonical `dependency-bottleneck-audit` skill.

This is a general decision process, not a directive to conduct a specific experiment or to prioritize the GEN001 project. It applies to every domain and workstream when the decision trigger matches.

Essential behavior:
- Distinguish the user's ultimate goal, nearest required intermediate result, and **immediate decision**.
- Retrieve current evidence and inventory the **capabilities/options made possible by achieved work** before creating new tasks.
- Identify dependencies and gaps; call something a blocking dependency only if it is necessary now on all credible feasible paths.
- Prefer reuse of existing outputs, inspection and a small discriminating test to speculative broad construction.
- Choose **one** feasible decision-changing action with observable PASS, FAIL and UNKNOWN outcomes.
- Avoid overstating results, inventing completion, or promoting domain-specific operational/release conditions into universal prerequisites for exploratory analysis.
- When action is authorized, execute what is possible; record observed results and limitations separately.

Legacy [.agents/skills/situation-model-next-step/SKILL.md](.agents/skills/situation-model-next-step/SKILL.md) is only a redirect. The general skill is the authoritative one for next-step analysis.

## General boundaries

Follow user-specified scope, access, privacy, repository and completion requirements. Do not silently change original acceptance criteria. Protect read-only or draft state unless writes are expressly requested. No production/release PASS on the basis of synthetic or partial tests alone.
