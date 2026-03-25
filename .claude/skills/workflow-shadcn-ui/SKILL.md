---
name: workflow-shadcn-ui
description: "shadcn/ui component workflow: component selection, theming, accessibility, and current-doc routing for React/Tailwind/shadcn work."
---
# shadcn/ui Workflow

## Purpose
Narrow method for shadcn/ui work: current docs, component composition, theming discipline, accessibility.

## Use When
- Task explicitly mentions shadcn/ui
- React/Tailwind screen should be built from shadcn primitives
- Question is which components, how to compose, how to theme
- Brand fidelity matters for design system consistency

## Do NOT Use When
- Generic frontend work with no shadcn dependency
- Full architecture design
- Pure visual brand direction (use `team-brand-team`)
- Broader implementation review (use `role-frontend-engineer`)

## Current Docs Rule
Treat shadcn/ui details as fast-moving. Use official docs whenever:
- Component APIs may have changed
- Installation/setup steps matter
- Theming or composition behavior is version-sensitive

Do not freeze volatile library details into long local prose.

## Workflow
1. Confirm screen or component goal.
2. Choose smallest set of shadcn primitives that fit.
3. Check current docs before assuming API or setup details.
4. For interactive states, responsive behavior, accessibility, or browser-specific issues, validate in a real browser with Playwright or an equivalent tool.
5. Review accessibility, theming, composition quality.
6. Hand to Frontend Team when task goes beyond narrow method guidance.

## Default Output
```text
SHADCN/UI PLAN
==============
Goal: screen or component intent
Component Shape: chosen primitives, why they fit
Docs to Check: current APIs/setup to verify
Quality Checks: accessibility, theming consistency, responsive behavior
Pairings: frontend owner, brand owner if needed
```

## Anti-Patterns
- Treating shadcn/ui as a full design system by itself.
- Adding custom wrappers before base primitives prove insufficient.
- Copying stale library rules instead of checking current docs.

## Output Discipline
- Follow the Default Output structure as both minimum and maximum. Do not add extra sections.
- Keep findings concise: 2-5 points per section.

## Anti-Drift Rules
- Do not treat shadcn/ui as a full design system. It is a component library.
- Check current docs before assuming API details. Do not freeze stale library info.
- Do not add custom wrappers before base primitives prove insufficient.
- This workflow handles shadcn/ui method, not broader frontend architecture.
- Do not treat static code review as enough evidence when browser behavior is the question.
