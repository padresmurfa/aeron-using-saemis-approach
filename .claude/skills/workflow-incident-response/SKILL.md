---
name: workflow-incident-response
description: "Production incident workflow: detect, triage, fix, verify, postmortem. Use when something is broken in production and needs structured response with clear handoff artifacts."
---
# Incident Response Workflow

## Purpose
Structured process for production incidents. Turns chaos into a sequence: detect → triage → act → verify → learn. Produces a durable incident report artifact.

## Use When
- Live production incident (service down, exploit active, economy anomaly, data corruption)
- Post-incident: need to document what happened and prevent recurrence
- Pre-launch: rehearsing incident response readiness

## Do NOT Use When
- Bug investigation in development (use `workflow-systematic-debugging`)
- Proactive security review (use `team-red-team`)
- Infrastructure design (use `team-infrastructure`)
- Issue is already resolved and just needs documentation

## Roles Involved
- **role-liveops-engineer**: owns triage, severity, player-impact, action decision
- **role-devops-engineer**: owns deployment, rollback execution, monitoring
- **role-security-engineer**: joins if exploit or abuse is involved
- **role-analytics-engineer**: joins if metrics anomaly or data integrity is involved
- **role-community-developer**: owns player communication if impact is player-visible

## Workflow

### Phase 1: Detect & Classify
1. Confirm the incident is real (not false alarm or monitoring artifact).
2. Classify severity using LiveOps Engineer's framework: critical / high / medium / low.
3. Determine trend: getting worse, stable, or self-resolving.
4. Identify blast radius from LiveOps triage: which systems, how many players, which regions.

### Phase 2: Triage & Decide
5. LiveOps Engineer assesses options: hotfix, rollback, degrade, monitor.
6. For on-chain incidents: check contract state, pause mechanisms, off-chain mitigation.
7. Choose action. LiveOps must specify rollback plan if the fix itself fails.
8. If severity is critical and action is irreversible, escalate to user before executing.
9. If "monitor" is chosen, define the escalation trigger (metric, threshold, timeframe). If trigger fires, return to step 2 for re-triage.

### Phase 3: Act & Verify
10. DevOps executes chosen action.
11. Verify fix: confirm the specific failure signal has stopped.
12. Monitor for secondary effects (did the fix break something else?).
13. If fix fails or creates secondary issues: DevOps alerts LiveOps immediately for re-triage (return to step 5 with new information).
14. If player-visible: Community Developer acknowledges issue immediately; delays technical explanation until root cause is clear.

### Phase 4: Postmortem
Owned by LiveOps Engineer, with input from each role on their phase.
15. Document timeline: detection → triage → action → resolution.
16. Identify root cause. Separate confirmed cause from hypotheses. Label confidence (high/medium/low).
17. List recurrence prevention actions with owners and deadlines.
18. Record what went well and what was slow.

## Default Artifact
Persist to `_artifacts/incident-<date>-<slug>.md`:

```text
INCIDENT REPORT
===============
Summary: one-sentence description
Severity: critical / high / medium / low
Duration: detection time → resolution time
Player Impact: who, how many, harm reversibility

Timeline:
- [time] detected by [signal]
- [time] triaged as [severity]
- [time] action taken: [what]
- [time] verified resolved

Root Cause: [confirmed / hypothesis — confidence: high/medium/low]
Action Taken: [hotfix / rollback / degrade / monitor]
On-Chain Impact: [contract state affected? pause used? migration needed?]
Recurrence Prevention: [actions with owners and deadlines]
Lessons: [what went well, what was slow]
```

## Anti-Drift Rules
- This workflow is for live incidents, not retrospective analysis of old bugs.
- Phase 1 and 2 must complete before Phase 3. Do not fix before you understand what you're fixing.
- Every action requires a rollback plan. No exceptions.
- Postmortem is not optional. Skip it and you'll fight the same fire again.
- Separate confirmed root cause from hypotheses. Label confidence as high, medium, or low based on the evidence behind each claim, and prefix material unverified assumptions with `UNCONFIRMED:`.
