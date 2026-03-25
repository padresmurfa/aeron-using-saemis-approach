---
name: workflow-specialist-hardening
description: "High-rigor review loop: run 3 contextualized specialist passes per round, score the work, and keep hardening it until the quality bar is met or a real decision blocks progress."
context: fork
effort: high
---
# Specialist Hardening Workflow

## Purpose
Push high-stakes work through repeated specialist review rounds until it is strong enough to ship, clearly blocked by a user decision, or no longer improving.

## Use When
- User explicitly asks for hardening, deep specialist review, or "repeat until 9"
- Lead Producer judges the task high-stakes, hard-to-reverse, or launch-critical
- A first-pass recommendation needs adversarial tightening before acceptance
- Quality matters more than token thrift

## Do NOT Use When
- A quick single-pass review is enough
- Broad repo or system understanding is still missing
- Root cause is still unknown and the task is debugging
- User only wants a lightweight recommendation

## Round Setup
1. Select exactly 3 reviewer slots from existing roles or teams.
2. Reviewer mix must include:
   - one primary domain owner
   - one adversarial or constraint-checking perspective
   - one complementary perspective likely to improve the result
3. Reuse the existing index. Do not invent custom reviewers.

## Review Loop
1. Read the current state and any prior round deltas before scoring.
2. Each reviewer returns:
   - score from 1-10
   - blockers
   - highest-value improvements
   - `What It Is`
   - `What It Is NOT`
3. Merge overlaps and prioritize the improvements most likely to raise quality.
4. Tighten the recommendation or artifact.
5. Repeat while material improvements remain.

## Stop Rules
- Stop when average score is `>= 9.0` and no material unresolved issues remain.
- Use `8.5+` per reviewer as a soft benchmark, not a hard fail rule.
- Stop early if:
  - further progress requires a user decision
  - evidence is too weak to improve responsibly
  - two consecutive rounds produce no material improvement

## Default Output
```text
SPECIALIST HARDENING REPORT
===========================
Round: current round number and focus
Reviewer Mix: 3 reviewer slots and why they were chosen
Scores: per-reviewer scores, average, trend vs prior round
What It Is: stabilized recommendation, artifact, or boundary
What It Is NOT: explicit non-goals, rejected interpretations, or false confidence
Blockers: issues still preventing acceptance
Highest-Value Improvements: next changes most likely to raise quality
Status: continue / quality bar reached / user decision needed / evidence blocked
Recommendation: current best version and next action
```

## Anti-Drift Rules
- Exactly 3 reviewer slots per round. No quiet expansion.
- Do not let scoring replace reasoning; scores must be justified by concrete concerns.
- Do not game the score by silently narrowing scope or deleting hard questions.
- Keep looping only while the next round can materially improve the result.
- This workflow is intentionally token-hungry when activated. Do not optimize it for thrift at the expense of rigor.
