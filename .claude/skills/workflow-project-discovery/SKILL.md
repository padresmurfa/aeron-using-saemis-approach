---
name: workflow-project-discovery
description: "Project discovery workflow: inspect an inherited or unclear repo, map major unknowns, and recommend the right timeboxed next investigation instead of guessing."
---
# Project Discovery Workflow

## Purpose
Create shared situational awareness before design, implementation, or review work goes wide. Turn a vague or inherited project into a short list of concrete next plays.

## Use When
- Repo is inherited, large, or poorly mapped
- User asks for discovery, an R&D pass, or "understand this project first"
- Broad unknowns make direct implementation or review premature
- Major systems, docs, tests, or ownership boundaries are unclear

## Do NOT Use When
- Immediate bug investigation is the real task (use `workflow-systematic-debugging`)
- Architecture decision is already tightly scoped (use `team-architecture-review`)
- One bounded system needs current-reality orientation more than repo-wide mapping (use `workflow-current-state-capture`)
- User already has a narrow implementation slice ready to execute

## Workflow
1. Inspect repo shape, major systems, active artifacts, and obvious boundaries.
2. Identify the top unknowns blocking confident execution.
3. Separate missing facts from preference or strategy questions.
4. Offer 2-3 timeboxed next plays sized to the uncertainty:
   - quick audit
   - focused architecture or subsystem spike
   - broader R&D or discovery pass
5. Recommend the smallest play that meaningfully reduces risk.

## Default Output
```text
PROJECT DISCOVERY REPORT
========================
Current State: repo shape, major systems, artifact maturity, useful existing signals
Top Unknowns: highest-risk things not yet understood
Options: 2-3 timeboxed plays with what each would clarify
Recommendation: smallest next play worth doing now
Next Step: what to inspect next, what decision to make, or recommended next LP route
```

## Output Discipline
- Default to in-chat output only.
- Do not create durable files unless the user explicitly asks.
- Keep options timeboxed and decision-oriented, not open-ended research wishlists.

## Anti-Drift Rules
- Discovery is for reducing uncertainty, not backdoor architecture work.
- Name what already exists before proposing more process.
- Recommend the smallest play that changes the next decision.
- Do not auto-chain into follow-on workflows.
- If a follow-on skill is warranted, recommend it back to LP instead of routing directly.
