---
name: workflow-current-state-capture
description: "Current-state capture workflow: orient a new owner to one bounded system, explain what it is and is not, and map the best next inspection path from code reality."
---
# Current State Capture Workflow

## Purpose
Orient a new owner to one bounded system, module, feature flow, or artifact cluster by capturing current reality before change work starts.

## Use When
- User needs "I'm new here" understanding for one subsystem or flow
- Code, config, docs, or artifacts exist but the current picture is fragmented
- User wants current behavior, boundaries, and reading order before making changes
- A bounded handoff artifact would reduce repeated rereading

## Do NOT Use When
- Broad repo mapping is the real blocker (use `workflow-project-discovery`)
- Root cause is still unknown and the task is debugging (use `workflow-systematic-debugging`)
- User needs a fresh architecture decision, not documentation from current reality
- A large documentation set rewrite is already clearly required (use `team-documentation`)

## Workflow
1. Inspect implementation and the tightest set of related docs or artifacts for the target area.
2. State what the thing is, what it is not, and where it ends.
3. List main moving parts, interfaces, truth sources, constraints, and current behavior.
4. Separate confirmed reality from contradictions, gaps, or unresolved areas.
5. Give the best reading or inspection order for someone new.
6. Recommend the next LP route only if it would materially help.
7. If the user wants persistence, save to `_artifacts/current-state-<slug>.md`.

## Default Output
```text
CURRENT STATE CAPTURE
=====================
Subject: system or module analyzed
What It Is: current responsibility, boundary, and purpose
What It Is NOT: explicit non-goals, neighboring concerns, or rejected interpretations
Moving Parts: key files, components, interfaces, and dependencies
Truth Sources: strongest code, config, docs, or artifacts to trust first
Current Behavior: what the implementation clearly does now
Constraints: important limits, assumptions, or invariants
Known Gaps: stale docs, contradictions, or unresolved questions
Read Next: best inspection order for a new owner
Recommended Next LP Route: follow-on LP route if needed, otherwise none
```

## Output Discipline
- Default to in-chat output unless the user asks for persistence.
- If `_artifacts/` does not exist and persistence is requested, ask where to save.
- Keep the capture focused on one system or slice at a time.

## Anti-Drift Rules
- Current-state capture is about reality, not aspirational redesign.
- Prefer code reality and strong truth sources over stale docs.
- Do not create first-class docs, ADR trees, or template directories by default.
- Prefer one tight capture over a sprawling doc rewrite.
- If the real need is ongoing documentation ownership, recommend `team-documentation`.
- Recommend follow-on routing back through LP instead of routing directly from this workflow.
