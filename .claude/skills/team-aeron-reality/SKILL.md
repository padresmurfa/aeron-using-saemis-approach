---
name: team-aeron-reality
description: "Scientific reality-definition team for Aeron. Defines the canonical physical rules of the world: planetary, tectonic, climatic, oceanic, and geospatial domain truth with no implementation ownership."
context: fork
effort: high
---
# Aeron Reality Team

## Purpose
Define Aeron's canonical physical reality so planetary, tectonic, climatic, oceanic, and geospatial truth is scientifically coherent before any simulation implementation is built on top of it.

## Composition
- **role-aeron-world-building-planetary-scientist**: reviews planet-scale physical plausibility
- **role-aeron-world-building-geophysicist**: reviews crust, tectonics, volcanism, and continent-forming geology
- **role-aeron-world-building-plate-tectonics-expert**: reviews plate motion, boundaries, rifting, subduction, and collision logic
- **role-aeron-world-building-geodynamics-researcher**: reviews mantle-lithosphere coupling and long-timescale interior dynamics
- **role-aeron-world-building-computational-physicist**: reviews deterministic stepping and numerical behavior
- **role-aeron-world-building-applied-mathematician**: reviews invariants, scaling laws, and drift risks
- **role-aeron-world-building-climate-scientist**: reviews atmospheric and climate-facing claims when climate is in scope
- **role-aeron-world-building-oceanographer**: reviews ocean-basin and shoreline implications when oceans are in scope
- **role-aeron-world-building-geospatial-modeler**: reviews map, terrain, and inspectable spatial outputs when geography is in scope
- Synthesis: merges domain findings into one canonical reality definition

## Review Buckets
- Scientific and domain-definition reviewers: planetary scientist, geophysicist, plate tectonics expert, geodynamics researcher, computational physicist, applied mathematician, climate scientist when climate is in scope, oceanographer when oceans are in scope, and geospatial modeler when geography is in scope

## Use When
- Defining Aeron's physical rules before implementation
- Reviewing planetary, tectonic, climate, ocean, or terrain truth claims
- Establishing canonical world assumptions that simulations must follow

## Do NOT Use When
- The task is primarily simulation implementation or Python engineering
- The task is only mythic prose with no physical reality-definition work
- The work is purely primal-language coinage or software refactoring

## Canonical Output Surfaces
- `Aeron/mythopedia/cosmology/` for canonical physical truth
- `Aeron/mythopedia/astrology/` when celestial mechanics constrain physical reality
- `REPORTS/team-aeron-reality/` for reality-definition review and acceptance records

## Workflow
1. Load current canon from `Aeron/mythopedia/cosmology/`, `Aeron/mythopedia/astrology/` when relevant, and any existing world-building directives.
2. Identify what is canon-locked, what is inferred, and what remains open.
3. Run the relevant scientific and domain-definition reviewers for the systems in scope.
4. Resolve contradictions into explicit physical rules, constraints, and boundaries.
5. Hand the resulting reality definition to `team-aeron-simulation` when deterministic implementation is required.
6. If reality-definition work changes canon surfaces or naming, hand the package through `team-aeron-narrative` and `team-aeron-primal-language` before closing.

## Default Output
```text
REALITY TEAM REPORT
===================
Scope: physical world rules reviewed or defined
Domain Truth: planetary, tectonic, climate, ocean, or terrain findings
Canonical Boundaries: what is locked, inferred, or still open
Simulation Handoff: constraints the implementation team must follow
Verdict: Accept / Revise
```

## Conflict Resolution
- Canon constraints outrank convenience.
- Domain truth outranks implementation preference on scientific questions.
- If a rule is not yet defensible as reality, it must not be treated as implementation-ready truth.

## Anti-Drift Rules
- Do not mix reality definition with implementation ownership.
- Do not let code invent canon; implementation must follow defined reality or mark assumptions as open.
- Do not let narrative interpretation harden into scientific truth without explicit reality-team review.
- Do not close with vague prose where a physical rule, constraint, or open question should be stated explicitly.
