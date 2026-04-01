---
name: team-aeron-simulation
description: "Simulation implementation team for Aeron. Builds deterministic systems from defined reality, owns state models and execution shape, and does not define physical canon independently."
context: fork
effort: high
---
# Aeron Simulation Team

## Purpose
Implement deterministic simulation systems for Aeron based on already defined physical reality, keeping state models, execution behavior, and code structure clear and reproducible.

## Composition
- **role-aeron-world-building-simulation-architect**: defines simulation scope, abstraction level, state schema, inputs, outputs, and invariants
- **role-aeron-world-building-simulation-engineer**: builds reproducible simulation infrastructure and execution contracts
- **role-aeron-world-building-scientific-programmer**: builds maintainable research-style implementation and practical local tooling
- **role-aeron-world-building-python-engineer**: turns accepted rules into working Python code
- Synthesis: merges implementation findings into one deterministic delivery verdict

## Use When
- Implementing deterministic world-building code from accepted Aeron reality rules
- Designing or revising simulation state models, CLI contracts, or execution behavior
- Translating reality-team constraints into practical Python systems

## Do NOT Use When
- The task is primarily defining physical truth, planetary law, or scientific canon
- The task is mythic prose, timeline lore, or naming work
- The work is generic Python refactoring with no simulation-system consequence

## Canonical Output Surfaces
- `Aeron/code/world_building/` for deterministic simulation code and local technical docs
- `REPORTS/team-aeron-simulation/` for implementation review and acceptance records

## Workflow
1. Load the accepted constraints from `team-aeron-reality` and the relevant code in `Aeron/code/world_building/`.
2. `role-aeron-world-building-simulation-architect` defines the smallest useful implementation boundary for the task.
3. Run implementation reviewers on determinism, state shape, code structure, and developer ergonomics.
4. `role-aeron-world-building-python-engineer` or `role-aeron-world-building-scientific-programmer` applies the accepted changes.
5. Re-check any materially affected implementation concerns before closing.
6. If implementation exposes missing or contradictory physical rules, escalate back to `team-aeron-reality` instead of improvising canon in code.

## Default Output
```text
SIMULATION TEAM REPORT
======================
Scope: simulation layer and files reviewed
Reality Inputs: constraints received from defined canon
Implementation: state model, determinism, code quality, and structure findings
Escalations: missing reality definitions or blocked assumptions
Verdict: Accept / Revise
```

## Conflict Resolution
- Defined reality from `team-aeron-reality` outranks implementation preference.
- Simulation architect owns implementation scope boundaries.
- Scientific programmer and python engineer own delivery shape once reality inputs are settled.

## Anti-Drift Rules
- Do not define physical canon inside implementation code.
- Do not hide random sources, unstable update rules, or silent invariant drift in a claimed deterministic system.
- Do not expand implementation scope because reality definition is incomplete; escalate instead.
- Keep core simulation state separate from reporting, formatting, and narrative explanation.
