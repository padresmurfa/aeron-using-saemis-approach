---
name: workflow-test-driven-development
description: "TDD workflow adapter: routes local domain owners into strict test-first execution while preserving domain expertise and context modules."
---
# Test-Driven Development Workflow

## Purpose
Repo-local adapter for test-first implementation. Routes the right domain owner into strict TDD execution.

## Use When
- Feature or bugfix should execute under strict TDD without losing domain expertise
- Dev Team, QA, Principal Engineer, Move Team, or Frontend Team needs disciplined implementation
- Project context modules should stay in scope during coding

## Do NOT Use When
- Task is pure architecture exploration with no implementation
- Best next step is root-cause debugging
- Change is trivial enough to skip TDD overlay

## Default Route
Combine the relevant domain owner with TDD discipline:
- TDD + `team-dev-team` — general implementation
- TDD + `role-qa-engineer` — acceptance criteria focus
- TDD + `role-principal-software-engineer` — interface quality focus
- TDD + `team-move-team` — specialized on-chain work
- TDD + `team-frontend-team` — frontend implementation

## Anti-Patterns
- Using this as a standalone TDD doctrine instead of routing to domain owners
- Skipping domain expertise on smart contracts, UI, or architecture-heavy work

## Minimal TDD Discipline (When Superpowers Pack Unavailable)
If no external TDD overlay is installed, apply this minimal discipline:
1. Write a failing test that captures the expected behavior first.
2. Implement the simplest code that makes the test pass.
3. Refactor without breaking the test.
4. Repeat for each behavior slice.

## Reference Map
- `references/tests.md` - behavior-first test selection and assertion strategy
- `references/mocking.md` - mocking scope, isolation trade-offs, and fake design
- `references/refactoring.md` - safe cleanup after green tests
- `references/interface-design.md` - interface shaping under TDD pressure
- `references/deep-modules.md` - protecting module boundaries while iterating

## Anti-Drift Rules
- This workflow routes domain owners into TDD execution. It does not replace domain expertise.
- If superpowers TDD overlay is unavailable, use the minimal discipline above rather than skipping TDD entirely.
- Do not use TDD ceremony as a reason to skip domain-specific constraints (smart contract invariants, project context, etc.).
- Load references and context modules only when the current test cycle requires them. Do not pre-load "just in case."
