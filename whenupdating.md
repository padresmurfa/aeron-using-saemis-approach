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
17. Update Codex docs and scripts when install shape changes.
18. Update Claude quick-start docs when host setup changes.
19. Re-run `bash ./scripts/install-codex.sh` or `powershell -ExecutionPolicy Bypass -File .\scripts\install-codex.ps1`.
20. Verify installer parity: same `CODEX_HOME` handling, same `codex` preflight, same rerun semantics.
21. Smoke-test repo-owned link refresh and external-link skip behavior.
22. Restart Codex and smoke-test `lead-producer` on single-domain direct routing.
23. Smoke-test multi-domain synthesis.
24. Smoke-test cleanup/reduction with verification.
25. Smoke-test unknown bug routing to `workflow-systematic-debugging`.
26. Smoke-test debugging-result packaging to `workflow-issue-triage`.
27. Smoke-test that live incidents still route to `role-liveops-engineer` and `workflow-incident-response`.
28. Smoke-test LP suggested-play behavior on inherited repo / broad unknown prompts.
29. Smoke-test explicit current-state capture opt-in phrases like "help me understand the current state of this system" so LP routes immediately to `workflow-current-state-capture`.
30. Smoke-test legacy alias phrases like "use reverse documentation on this module" to confirm LP routes to `workflow-current-state-capture`.
31. Smoke-test explicit hardening phrases like "run the specialist hardening play" and "repeat until 9" to confirm LP routes to `workflow-specialist-hardening`.
32. Smoke-test clearly high-stakes or hard-to-reverse prompts so LP can route to `workflow-specialist-hardening` without over-triggering it on routine review.
33. Smoke-test Claude quick-start commands on Windows and macOS/Linux, or note the missing host evidence plainly.
34. If macOS/Linux behavior has not been checked yet, say that directly instead of overexplaining it.
35. Keep `README.md` mermaid flow, sample LP output, workflow inventory, and host-specific setup steps aligned with current LP behavior.
36. Keep runtime-critical `[VERIFY]` and evidence rules in skill files, not only host docs.
37. Run a relative Markdown link check across shipped docs and references.
38. Run a fresh-agent trace from `README.md` -> relevant host guide -> `lead-producer/SKILL.md` after workflow/routing changes and fix any contradiction before closing.
