---
name: team-brand-team
description: "Brand system team: tone, positioning, visual rules, and cross-surface identity standards. Use when defining or tightening brand consistency across product, docs, and community."
context: fork
effort: medium
---
# Brand Team

## Purpose
Own identity standards, not raw implementation. Turn vague taste questions into a usable system other teams can apply consistently.

## Composition
- **role-brand-strategist**: brand voice, positioning, visual rules
- **role-ui-ux-designer**: ensures brand works in real interfaces
- **role-technical-writer**: verbal guidance portable into docs and copy
- **role-community-developer**: brand survives community-facing surfaces
- Synthesis: trade-offs, keeps team lean
- **role-frontend-engineer** (optional): when implementation realism matters

## Use When
- Defining a brand system
- Aligning voice and visual identity across product, docs, community
- Applying brand standards for launch, redesign, or new surface
- Resolving UI/docs/messaging inconsistency

## Do NOT Use When
- Raw frontend implementation (use `team-frontend-team`)
- Feature prioritization (use `team-product-team`)
- Pure docs with no brand question (use `team-documentation`)

## Workflow
1. Define or load brand truth from one canonical file.
2. Align voice, visuals, cross-surface rules.
3. Stress-test against actual UI, docs, community usage.
4. Write/update canonical brand artifact (default `brand/BRAND_SYSTEM.md`).
5. Produce small implementation handoff.

## Default Output
```text
BRAND TEAM BRIEF
================
Canonical File: brand/BRAND_SYSTEM.md
Brand Truth: positioning, voice, visual principles
Consistency Risks: current mismatches, surfaces likely to drift
Application Rules: product UI, docs, community/ecosystem
Handoff: frontend actions, documentation actions, open constraints
```

## Conflict Resolution
- Brand Strategist owns voice, positioning, and visual rules. UI/UX Designer owns interface feasibility.
- Technical Writer owns verbal specificity. Community Developer owns community-surface applicability.
- When brand aspiration conflicts with implementation reality, find the smallest brand adaptation that maintains identity.

## Anti-Drift Rules
- Brand is rules, not decoration. If output is vague adjectives without application guidance, it failed.
- Do not expand into product strategy under brand review label.
- One canonical brand file, not multiple competing sources of truth.
