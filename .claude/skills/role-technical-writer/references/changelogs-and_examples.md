# Changelogs and Example Hygiene
Short reference for release notes, migration guidance, and example quality in this skill pack.

## Use This Reference When
- install steps or supported hosts change
- route ids, aliases, or opt-in phrases change
- README, install guides, or skill examples need updates
- a release needs upgrade notes for existing users

## Changelog Guidance
Capture only user-visible changes:
- setup commands for Claude Code or Codex
- supported hosts or platform assumptions
- route ids, aliases, or suggested-play phrasing
- installer behavior, smoke-test expectations, or source-of-truth wording
- added, removed, or renamed shipped artifacts

Recommended format:
```markdown
## [version-or-date]
### Changed
- What changed for users
### Fixed
- What was broken and what is now correct
### Removed
- What no longer ships or should no longer be used
### Migration Notes
- Old command or phrase -> new command or phrase
- Any follow-up action a user must take
```

## Migration Notes
Write migration notes whenever a user would otherwise copy an outdated command, prompt, or path.

Good migration note:
```markdown
- Windows Codex install now uses `powershell -ExecutionPolicy Bypass -File .\scripts\install-codex.ps1`.
  This bypass is process-scoped and does not change machine-wide PowerShell policy.
```

## Example Hygiene
Examples in this pack should be:
- host-specific when syntax differs between Claude Code and Codex
- copy-paste ready from a fresh checkout
- limited to real skill ids, real repo paths, and real behavior in this repo
- explicit about when a reply is expected to route directly vs suggest a play

Do not:
- use fake API products, fake docs trees, or placeholder external domains
- leave relative Markdown links pointing to files this repo does not ship
- mix Claude and Codex syntax in one example block
- show sample LP output that contradicts the actual LP output contract

## Pre-Publish Checks
Before publishing docs that include examples or release notes:
1. Re-run the commands exactly as written on the intended host.
2. Verify every referenced file path and relative Markdown link exists.
3. Verify every mentioned skill id exists in `.claude/skills/`.
4. Keep counts and host-specific entrypoints aligned across README, host guides, and skills.
