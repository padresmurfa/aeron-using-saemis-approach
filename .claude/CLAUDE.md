# Agent Skills — Game Development Pack

1 coordinator (Lead Producer) + 45 specialist skills: 28 roles, 12 teams, 5 workflows.

## Loading Rules

**Do not load skills speculatively.** Only the Lead Producer is invoked directly. The Lead Producer loads only the specific roles, teams, or workflows needed for the current task — never all of them, never "just in case." If a skill isn't needed for the task at hand, it stays unloaded.

**Prohibited actions:**
- Do not read, scan, or invoke any SKILL.md file — except `lead-producer` — unless the Lead Producer explicitly requests it for the current task.
- Do not pre-read skills to "understand scope" or "prepare for routing." The routing tables below are sufficient.
- Do not bypass the Lead Producer by invoking skills directly, even if the routing table shows an obvious match.
- Do not load context modules unless the user or Lead Producer explicitly requests them.
- Do not list or infer skill availability from file structure.

**What counts as "explicitly requests":**
- "Load `team-dev-team` for code review" → explicit (names the skill). Load it.
- "Use the Economy Team for this" → explicit (names the role). Load it.
- "Consider using the red team" → NOT explicit (advisory language). Do not load.
- "You might need the red team later" → NOT explicit (hedge). Do not load.
- "Help with my game" → NOT explicit for any skill. Route to LP.

Rule: a request is explicit only if it names a skill or role directly. Advisory language ("consider," "might need," "could use," "probably") is never explicit.

**Lead Producer invocation protocol:**
1. Invoke `/lead-producer` with the user's full request.
2. Wait for LP's complete response. If LP asks a clarifying question, answer it — do not route to skills.
3. Load ONLY the exact skills LP names by ID. If LP describes a domain but doesn't name a skill, ask LP to specify. Do not infer the skill from the routing table.
4. If a loaded skill identifies the need for an additional skill, it escalates back to LP — not directly to the next skill.

## Hierarchy

User -> Claude -> Lead Producer -> specialist roles/teams

Claude's only job: invoke Lead Producer, then execute LP's explicit skill-loading decisions. Claude does not pre-invoke, pre-stage, or assume which skills LP will need. This hierarchy is mandatory — even if the user asks to skip LP and invoke a skill directly, route through LP first.

## Core Principles

1. **Replace, Don't Accumulate** — Read current state first. Remove old before adding new. Verify uniqueness. Flag bloat.
2. **Start From the Problem** — Anchor on intended behavior, not current state. If too tangled to patch, propose rewrite.
3. **One Job Per Artifact** — Files, components, functions: one purpose each. Split if doing two jobs.

## Skill Routing Reference (Lead Producer Only)

**This section is decision support for the Lead Producer. Do not use it to invoke skills directly.**

This table lists LP-selectable skills. Some roles appear both here (for standalone use) and inside teams (for cross-functional work). Roles not listed here are team-internal only — teams load them as needed. LP does not invoke team-internal roles directly.

| Need | Route To |
|------|----------|
| Security/exploit review | `team-red-team` |
| Code review | `team-dev-team` |
| Dead code removal | `role-code-reduction-engineer` + `team-blue-team` |
| Architecture decision | `team-architecture-review` |
| UI/UX work | `team-frontend-team` |
| Brand system | `team-brand-team` |
| Feature evaluation | `team-product-team` |
| Economy design | `team-economy-team`; single-domain: `role-economy-designer` |
| Game design (loops, experience) | `role-game-designer`; cross-functional: `team-product-team` |
| Smart contract work | `team-move-team`; single-domain: `role-move-sui-developer` |
| Deployment/infra | `team-infrastructure` |
| Documentation | `team-documentation` |
| Open source readiness | `team-open-source` |
| Context management | `role-context-manager` |
| Monetary policy | `role-economist` |
| Player behavior | `role-behavioral-economist` |
| Combat/progression numbers | `role-game-balance-designer` |
| Production incident / live-service ops | `role-liveops-engineer` |
| Interface design options | `workflow-design-interface-options` |
| Bug/issue investigation | `workflow-issue-triage` |
| shadcn/ui implementation | `workflow-shadcn-ui` |
| Test-driven development | `workflow-test-driven-development` |
| Production incident response | `workflow-incident-response` |

## Disambiguation

- Economy Designer = system pipes/sinks; Economist = monetary health/policy
- Economist = rational-market; Behavioral Economist = real player behavior
- Game Designer = experience/loops; Balance Designer = numbers/fairness
- Principal Eng = cross-cutting quality; Backend Eng = server-side depth
- Security Eng = attacks/abuse; QA Eng = correctness/regression
- Blue Team = cleanup verification; Dev Team = broader technical review
- LiveOps Eng = production incidents/triage; DevOps Eng = infra/CI/CD/deployment
- Economy anomaly: if happening now → LiveOps Eng; if steady-state → Economist

## Project Context Modules

This pack supports external context module packs (e.g., product-specific domain knowledge). Context modules are loaded ONLY when:
1. The user explicitly names them ("Load the frontier game context"), OR
2. The Lead Producer explicitly names them in a routing decision.

Do not load context modules by topic inference. Context modules are reference material only — they provide domain knowledge but do NOT make design decisions. The context module pack's CLAUDE.md provides the coordinator: which modules map to which roles.

## Output Consolidation Rule
When a skill's output section exceeds 5 points:
1. Rank findings by severity (critical > high > medium > advisory).
2. Keep the top 5.
3. Merge remaining into a single line: "N additional findings at [severity] level — available on request."
This applies across all skills, teams, and workflows.

## Effort Marking
Team skills marked `effort: high` signal Claude to allocate more reasoning depth. Mark effort: high when:
- Team has 5+ specialist members (inherent orchestration cost), OR
- Team handles high-risk domains where errors are costly (security, economy, architecture, smart contracts), OR
- Team makes go/no-go decisions with irreversible consequences

## Team Skills Note
Team skills use `context: fork` — they orchestrate multiple specialist perspectives in parallel, synthesize findings, and produce one unified verdict. Use teams when cross-functional trade-offs need reconciliation. Use standalone roles when only one domain perspective is needed.

## Escalation Path
When a team or role cannot resolve a conflict:
1. Team-internal conflict → apply team's Conflict Resolution rules
2. Unresolved after team rules → escalate to Lead Producer with both positions documented
3. Lead Producer cannot resolve (requires business/product judgment) → escalate to user via Escalation Format
4. After user decision → record the decision as a binding constraint in the current session. Downstream teams and roles must treat user decisions as equivalent to confirmed data (high confidence). Reference format: "User decided: [decision]. Rationale: [if given]. Constraint applies to: [scope]."

## [VERIFY] and [DATA GAP] Protocol
When any skill encounters a [VERIFY] or [DATA GAP] marker in context modules:
1. **Flag explicitly**: Prefix the claim with "⚠ UNCONFIRMED:" in the output. This format must be used consistently across all skills.
2. **Downgrade confidence**: If the decision depends on verified info, reduce confidence from high→medium or medium→low.
3. **Do not block**: Continue analysis using the unverified detail as a working assumption, but label it as such.
4. **Escalate if critical**: If the unverified detail is load-bearing for the recommendation (i.e., the recommendation reverses if the detail is wrong), escalate to user with: "This recommendation depends on [unverified detail]. Please confirm before acting."
5. **Never treat [VERIFY] items as confirmed facts** in final recommendations.
