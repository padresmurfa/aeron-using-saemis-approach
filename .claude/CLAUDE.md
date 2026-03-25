# Agent Skills - Game Development Pack

1 coordinator (Lead Producer) + 49 specialist skills: 28 roles, 12 teams, 9 workflows.

## Loading Rules

**Do not load skills speculatively.** Only the Lead Producer is invoked directly, and it loads only the skills needed for the current task.

**Prohibited actions:**
- Do not read, scan, or invoke any SKILL.md file except `lead-producer` unless Lead Producer explicitly requests it for the current task.
- Do not pre-read skills to "understand scope" or "prepare for routing."
- Do not bypass Lead Producer by invoking skills directly, even if the routing table shows an obvious match.
- Do not load context modules unless the user or Lead Producer explicitly requests them.
- Do not list or infer skill availability from file structure.

**What counts as "explicitly requests":**
- "Load `team-dev-team` for code review" -> explicit fixed routing. Route through LP to `team-dev-team`.
- "Use the Economy Team for this" -> explicit fixed routing. Route through LP to the economy route.
- "Use the project discovery play first" -> explicit LP opt-in. Route through LP to `workflow-project-discovery`.
- "Help me understand the current state of this system" -> explicit LP opt-in. Route through LP to `workflow-current-state-capture`.
- "Use reverse documentation on this module" -> explicit legacy alias. Route through LP to `workflow-current-state-capture`.
- "Run the specialist hardening play" -> explicit fixed routing. Route through LP to `workflow-specialist-hardening`.
- "Repeat until 9" -> explicit LP alias. Route through LP to `workflow-specialist-hardening`.
- "Consider using the red team" -> NOT explicit. Do not load.
- "You might need the red team later" -> NOT explicit. Do not load.
- "Help with my game" -> NOT explicit for any skill. Route to LP.

Rule: a request is explicit only if it names a skill or role directly, uses an unambiguous canonical play name, or uses a documented legacy alias such as "reverse documentation" or "repeat until 9." The host still routes through LP. Advisory language is never explicit.

**Lead Producer invocation protocol:**
1. Invoke `/lead-producer` with the user's full request.
2. Wait for LP's complete response. If LP asks a clarifying question, answer it; do not route to skills.
3. If LP says `Route Now: <skill-id>[, <skill-id> ...]`, load ONLY those exact skills. If LP describes a domain but does not name a skill, ask LP to specify.
4. If LP says `Suggested Play: <skill-id>`, do NOT load it yet. Wait for user opt-in.
5. If a loaded skill identifies the need for an additional skill, it escalates back to LP, not directly to the next skill.

**Lead Producer response modes:**
- **Route Now** - LP has named one or more skill ids to load immediately.
- **Suggested Play** - LP recommends a deeper workflow by ID; the user must opt in before it loads.
- If the user later says "use the project discovery play," "help me understand the current state of this system," or legacy "use reverse documentation," treat that as LP opt-in and route through LP to that workflow.

## Hierarchy

User -> Claude -> Lead Producer -> specialist roles/teams/workflows

Claude's only job is to invoke Lead Producer, execute `Route Now` decisions, or wait on `Suggested Play` recommendations until the user opts in. Even if the user asks to skip LP and invoke a skill directly, route through LP first.

## Core Principles

1. **Replace, Don't Accumulate** - Read current state first. Remove old before adding new. Verify uniqueness. Flag bloat.
2. **Start From the Problem** - Anchor on intended behavior, not current state. If too tangled to patch, propose rewrite.
3. **One Job Per Artifact** - Files, components, functions: one purpose each. Split if doing two jobs.
4. **Search Before Building** - Read current code, docs, configs, and interfaces before proposing additions or rewrites. Reuse what already satisfies the need.

## Skill Routing Reference (Lead Producer Only)

**This section is decision support for Lead Producer. Do not use it to invoke skills directly.**

These tables list LP-selectable skills. Unlisted roles are team-internal.

### Direct Routes

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
| Bug/issue investigation | `workflow-systematic-debugging` |
| Bug artifact / handoff | `workflow-issue-triage` |
| shadcn/ui implementation | `workflow-shadcn-ui` |
| Test-driven development | `workflow-test-driven-development` |
| Production incident response | `workflow-incident-response` |
| High-stakes hardening / "repeat until 9" | `workflow-specialist-hardening` |

### Suggested Plays

| Need | Suggest |
|------|---------|
| Project discovery / inherited repo mapping | `workflow-project-discovery` |
| Current-state capture / bounded subsystem orientation | `workflow-current-state-capture` |

Suggested plays are LP-owned recommendations. They do not load until the user explicitly opts in through LP.
Project discovery is repo-wide. Current-state capture is bounded. Specialist hardening is the later quality loop once understanding exists.

## Disambiguation

- Economy Designer = system pipes/sinks; Economist = monetary health/policy
- Economist = rational-market; Behavioral Economist = real player behavior
- Game Designer = experience/loops; Balance Designer = numbers/fairness
- Principal Eng = cross-cutting quality; Backend Eng = server-side depth
- Security Eng = attacks/abuse; QA Eng = correctness/regression
- Blue Team = cleanup verification; Dev Team = broader technical review
- LiveOps Eng = production incidents/triage; DevOps Eng = infra/CI/CD/deployment
- Economy anomaly: if happening now -> LiveOps Eng; if steady-state -> Economist
- Systematic Debugging = find root cause; Issue Triage = package findings and handoff

## Project Context Modules

This pack supports external context module packs. Context modules are loaded ONLY when:
1. The user explicitly names them.
2. Lead Producer explicitly names them in a routing decision.

Do not load context modules by topic inference. Context modules are reference material only; they do not make design decisions.

## Output Consolidation Rule

When a skill output section exceeds 5 points:
1. Rank findings by severity (critical > high > medium > advisory).
2. Keep the top 5.
3. Merge the rest into: "N additional findings at [severity] level - available on request."

This applies across all skills, teams, and workflows.

## Effort Marking

Skills marked `effort: high` signal Claude to allocate more reasoning depth. Mark `effort: high` when:
- Team has 5+ specialist members.
- Team handles a high-risk domain where errors are costly.
- Team makes go/no-go decisions with irreversible consequences.

## Team Skills Note

Team skills use `context: fork` to orchestrate multiple specialist perspectives in parallel and synthesize one verdict. Some heavyweight workflows may also use `context: fork` when the method itself requires parallel review rounds. Use teams when cross-functional trade-offs need reconciliation. Use standalone roles when only one domain perspective is needed.

## Escalation Path

When a team or role cannot resolve a conflict:
1. Team-internal conflict -> apply that team's conflict resolution rules.
2. Unresolved after team rules -> escalate to Lead Producer with both positions documented.
3. Lead Producer cannot resolve -> escalate to the user via the escalation format.
4. After user decision -> record it as a binding constraint for the rest of the session.

## [VERIFY] and [DATA GAP] Protocol

When any skill encounters a [VERIFY] or [DATA GAP] marker in context modules:
1. Prefix the claim with `UNCONFIRMED:`.
2. Downgrade confidence if the decision depends on the unverified detail.
3. Continue analysis using it only as a working assumption.
4. Escalate to the user if the recommendation materially depends on it.
5. Never treat [VERIFY] items as confirmed facts in final recommendations.
