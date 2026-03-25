---
name: team-frontend-team
description: "Frontend review team: UX quality, implementation health, accessibility, and frontend-backend integration in one recommendation. Use for UI features or frontend-heavy flows."
context: fork
---
# Frontend Team

## Purpose
Decide whether an interface is usable, implementable, accessible, and technically healthy to ship.

## Composition
- **role-ui-ux-designer**: flow quality, hierarchy, clarity, accessibility
- **role-frontend-engineer**: implementation quality, runtime behavior, state health
- **role-backend-engineer**: API and contract advisor for integration risk
- Synthesis: trade-offs, acceptance

## Use When
- Reviewing UI feature, screen, or frontend-heavy flow
- Checking accessibility, responsiveness, client-side architecture
- Evaluating frontend-backend integration quality

## Do NOT Use When
- Backend-only, infrastructure-only, or product-only
- Brand-definition with no implementation or UX question
- Narrow shadcn/ui method (use `workflow-shadcn-ui`)

## Workflow
1. Define critical user journey, key screens/states, and existing design patterns worth reusing.
2. Review UX, frontend implementation, and API dependence together.
3. When interaction, responsiveness, accessibility, browser state, or network/error behavior is in question, validate in a real browser with Playwright or an equivalent tool before trusting code-only review.
4. Performance, failure handling, accessibility, and AI slop risk are part of the same verdict.
5. Synthesize trade-offs into one frontend recommendation.

## Default Output
```text
FRONTEND TEAM REVIEW
====================
Journey: main user flow, friction points, existing design leverage
Implementation: state/rendering/integration risks
Quality: accessibility gaps, responsive/failure-state issues, AI slop risk
Recommendation: ship / revise / escalate, highest-priority fixes
```

## Conflict Resolution
- UI/UX Designer owns user-experience quality. Frontend Engineer owns implementation feasibility.
- When UX and implementation conflict, find the smallest UX change that resolves the technical constraint.

## Anti-Drift Rules
- Do not expand into backend redesign under frontend review label.
- Reuse proven design leverage before inventing new UI language.
- Call out AI slop risk explicitly when it appears.
- Accessibility and error states are shipping requirements, not nice-to-haves.
- Prefer real-browser evidence over code-only guesses when UI behavior is the question.
