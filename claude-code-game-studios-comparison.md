# Claude Code Game Studios Comparison

Compared local pack files:
- `.claude/skills/lead-producer/SKILL.md`
- `.claude/CLAUDE.md`
- `README.md`
- `whenupdating.md`

Against these Claude Code Game Studios areas inspected locally:
- `README.md`, `CLAUDE.md`, `.claude/docs/agent-coordination-map.md`
- `.claude/agents/producer.md`
- `.claude/skills/start/SKILL.md`, `project-stage-detect/SKILL.md`, `reverse-document/SKILL.md`, `code-review/SKILL.md`
- `.claude/settings.json`, `.claude/hooks/*`, `.claude/rules/*`

Decision lens: keep the pack reusable, LP-first, and portable across Claude Code and Codex while only adding rigor that pays for its token cost.

## Steal Now
- **Suggested heavier plays through the coordinator.** The best idea here is not the whole studio hierarchy, but the pattern of noticing when a task needs discovery before judgment.
- **A discovery-first workflow for inherited repos.** Repo mapping, uncertainty reduction, and timeboxed R&D options are high-signal additions when kept lean.
- **A current-state capture play for bounded systems.** The useful part of reverse-documentation is orientation from reality, not doc-template ceremony.
- **Sharper examples and onboarding language in docs.** Their examples do a good job making orchestration legible without requiring users to memorize routing internals.

## Adapt Carefully
- **Producer-style orchestration.** Useful ideas about staged decision-making should live inside `lead-producer`, not as a second top-level coordinator.
- **Collaborative ask-before-write behavior.** Good philosophy, but too runtime-heavy and too Claude-shaped to adopt as core pack law.
- **Project-state analysis.** Helpful when framed as one discovery workflow, not as a project template with many artifact assumptions.

## Reject
- Full studio hierarchy with many direct-entry agents and slash commands.
- Hooks, path-scoped rules, and project-template governance as part of the portable core pack.
- Engine-specific specialist trees, document templates, and production folder conventions.
- Any workflow that quietly expands into long-lived template maintenance overhead.

## Net Changes Made
- Added `workflow-project-discovery` as a lean inherited-repo and uncertainty-reduction play.
- Reframed the reverse-documentation idea as `workflow-current-state-capture` so the public concept is bounded orientation, not doc production.
- Added `workflow-specialist-hardening` as the heavy review loop while keeping that rigor out of base Lead Producer.
- Updated Lead Producer and `.claude/CLAUDE.md` with a formal `Suggested Play` protocol.
- Updated README examples, counts, and inspiration credits to include Claude Code Game Studios.
- Folded durable maintenance lessons into `whenupdating.md` and superseded the older `gstack-comparison.md` note.

## Notes
- The useful ideas were mostly behavioral and orchestration-focused, not structural.
- Portability mattered more than fidelity: we recreated the value in a Codex-friendly form instead of copying Claude-specific packaging.
- The hardening loop is closer to the earlier gstack rigor idea than to Claude Code Game Studios, which is why it stays out of the LP hot path.
