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
./scripts/install-codex.sh
```

## Windows (PowerShell)

```powershell
git clone https://github.com/saemihemma/lead-producer.git
Set-Location lead-producer
.\scripts\install-codex.ps1
```

Both scripts:

- create `~/.codex/skills` if needed
- link every skill folder from `.claude/skills/`
- are safe to rerun
- skip existing real directories they do not own
- verify that `codex` can actually execute from shell and warn if Windows app packaging is blocking it

## Verify

Restart Codex, then try:

```text
Use $lead-producer to investigate why reward claims intermittently fail after reconnect. Find the root cause before fixing.
```

If LP responds with a suggested play such as `workflow-project-discovery` or
`workflow-current-state-capture`, reply with the explicit LP opt-in phrase it
asks for, for example: `Use the current state capture play for this flow.`

If LP routes directly to `workflow-specialist-hardening`, let LP own the deeper
review loop rather than manually invoking extra specialists yourself.

## Windows Troubleshooting

If `codex --version` fails with `Access is denied`, this is usually a local Codex install or app-alias issue, not a repo issue.

Common signs:

- `Get-Command codex` resolves to a path under `C:\Program Files\WindowsApps\...`
- `%LOCALAPPDATA%\OpenAI\Codex\bin` is missing or stale
- skills are linked correctly under `~/.codex/skills`, but the `codex` command itself will not start

What to do:

1. Launch the Codex app once and try `codex --version` again.
2. If it still fails, reinstall Codex so the shell shim is restored.
3. Re-run `.\scripts\install-codex.ps1`, then repeat the verify step above.

## Updating

```bash
git pull
```

Because Codex points at the canonical repo folders, normal updates do not require a mirror sync
step. Pull latest changes and restart Codex if needed.

## Source of Truth

`.claude/skills/` is the only Codex skill source in this repo.
