# When Updating

1. Keep `.claude/skills/` as the only Codex skill source.
2. Do not maintain duplicate Codex skill mirrors by hand.
3. Keep coordinator hot paths lean; if guidance can live in `README.md`, maintenance docs, or `references/`, move it out of runtime prompts.
4. Keep `description:` narrow so Codex routes precisely.
5. Re-measure word counts for `lead-producer/SKILL.md`, `.claude/CLAUDE.md`, and other hot-path files after coordinator edits.
6. Prefer deletions or wording swaps before adding new runtime protocol.
7. If you borrow materially from another pack, note it in `README.md`.
8. Turn philosophy into behavior rules; avoid values-only prose that does not change execution.
9. Keep reports decision-oriented and scannable; put the recommendation or verdict first when the format allows it.
10. For serious option reports, use shared decision criteria across alternatives.
11. Explicitly say what each option simplifies and what it makes more complex.
12. Tie recommendations to verified context, trade-off logic, or explicit assumptions.
13. Prefer reversible recommendations when confidence is below high.
14. Use product or domain context selectively; if it is unavailable or intentionally skipped, say so and lower confidence.
15. If a skill has `references/`, make sure Codex can load only the needed file.
16. Keep third-party comparison notes lean and singular; replace superseded comparison artifacts instead of accumulating them.
17. Update Codex-global docs and scripts when install shape changes.
18. Re-run `./scripts/install-codex.sh` or `.\scripts\install-codex.ps1`.
19. Restart Codex and smoke-test `lead-producer` on single-domain direct routing.
20. Smoke-test multi-domain synthesis.
21. Smoke-test cleanup/reduction with verification.
22. Smoke-test unknown bug routing to `workflow-systematic-debugging`.
23. Smoke-test debugging-result packaging to `workflow-issue-triage`.
24. Smoke-test that live incidents still route to `role-liveops-engineer` and `workflow-incident-response`.
25. Smoke-test LP suggested-play behavior on inherited repo / broad unknown prompts.
26. Smoke-test explicit current-state capture opt-in phrases like "help me understand the current state of this system" so LP routes immediately to `workflow-current-state-capture`.
27. Smoke-test legacy alias phrases like "use reverse documentation on this module" to confirm LP routes to `workflow-current-state-capture`.
28. Smoke-test explicit hardening phrases like "run the specialist hardening play" and "repeat until 9" to confirm LP routes to `workflow-specialist-hardening`.
29. Smoke-test clearly high-stakes or hard-to-reverse prompts so LP can route to `workflow-specialist-hardening` without over-triggering it on routine review.
30. Keep `README.md` mermaid flow, sample LP output, and workflow inventory aligned with the current `Route Now` / `Suggested Play` protocol.
31. Run a fresh-agent trace from `README.md` -> `.claude/CLAUDE.md` -> `lead-producer/SKILL.md` after workflow/routing changes and fix any contradiction before closing.
