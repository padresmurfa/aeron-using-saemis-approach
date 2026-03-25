# Install Agent Skills for Codex

Codex can install directly from the canonical skill source in this repo. There is no need to
maintain a second Codex-only skill tree.

If you use `superpowers` or any other external overlay packs, install those separately. This file
only covers this repo's local skill pack.

## Prerequisites

- [OpenAI Codex](https://openai.com/codex) installed
- this repo cloned locally

## macOS / Linux

```bash
git clone https://github.com/saemihemma/lead-producer.git
cd lead-producer
bash ./scripts/install-codex.sh
```

## Windows (PowerShell)

```powershell
git clone https://github.com/saemihemma/lead-producer.git
Set-Location lead-producer
powershell -ExecutionPolicy Bypass -File .\scripts\install-codex.ps1
```

The Windows command uses a process-scoped execution policy bypass. It does not change your
machine-wide PowerShell policy.

Both scripts:

- install into `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise `~/.codex/skills`
- verify that `codex` executes from shell before linking skills
- link every skill folder from `.claude/skills/`
- refresh repo-owned links on rerun
- skip existing non-link targets and external links with a warning
- keep a live link to this clone, so moving or deleting the repo breaks the installed skills

If the `codex` preflight fails, the installer stops and tells you to fix the local Codex setup
before retrying.

## Verify

Restart Codex, then try this direct-route smoke test:

These are simple manual checks so you can confirm the pack is wired up the way you expect.

```text
Use $lead-producer to review this onboarding guide for clarity and accuracy.
```

Manual smoke expectation: first lines include `Route Now: team-documentation` and
`Suggested Play: none`

Optional routing smoke checks:

```text
Use $lead-producer to assess this inherited repo and suggest the right discovery play before implementation.
```

Manual smoke expectation: first lines include `Route Now: none` and
`Suggested Play: workflow-project-discovery`

If LP suggests `workflow-project-discovery`, reply with:

```text
Use the project discovery play.
```

```text
Use $lead-producer to run the specialist hardening play on this launch-critical payout rollback plan. Repeat until 9.
```

Manual smoke expectation: first lines include `Route Now: workflow-specialist-hardening` and
`Suggested Play: none`

## Windows Troubleshooting

If PowerShell blocks local scripts, use the process-scoped bypass command above. It is a session
level workaround, not a machine-wide policy change.

If `codex --version` fails with `Access is denied`, this is usually a local Codex install or app-alias issue, not a repo issue.

Common signs:

- `Get-Command codex` resolves to a path under `C:\Program Files\WindowsApps\...`
- `%LOCALAPPDATA%\OpenAI\Codex\bin` is missing or stale
- skills are linked correctly under `~/.codex/skills`, but the `codex` command itself will not start

What to do:

1. Launch the Codex app once and try `codex --version` again.
2. If it still fails, reinstall Codex so the shell shim is restored.
3. Re-run `powershell -ExecutionPolicy Bypass -File .\scripts\install-codex.ps1`, then repeat the verify step above.

## Updating

```bash
git pull
bash ./scripts/install-codex.sh
```

```powershell
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\install-codex.ps1
```

Because Codex points at the canonical repo folders, updates keep using this clone as the source of
truth. Pull latest changes, rerun the installer for your host, and restart Codex if needed.

Windows is in good shape. On macOS or Linux, just do a quick first-run check after installing and
make sure the first LP prompt behaves as expected.

## Source of Truth

`.claude/skills/` is the only Codex skill source in this repo. This file is the Codex host guide;
`.claude/CLAUDE.md` is Claude Code host guidance; `.claude/skills/lead-producer/SKILL.md` is the
runtime routing canon.
