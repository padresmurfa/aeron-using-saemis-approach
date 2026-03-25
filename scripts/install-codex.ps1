$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SourceRoot = Join-Path $RepoRoot ".claude\skills"
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$TargetRoot = Join-Path $CodexRoot "skills"

if (-not (Test-Path $SourceRoot)) {
    Write-Error "Canonical skill source not found: $SourceRoot"
    exit 1
}

function Get-NormalizedPath {
    param([string]$Path)

    return [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $Path).Path)
}

function Test-RepoOwnedLink {
    param(
        [string]$LinkPath,
        [string]$ExpectedTarget
    )

    $item = Get-Item -Force $LinkPath -ErrorAction Stop
    $isReparsePoint = ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0

    if (-not $isReparsePoint) {
        return $false
    }

    $linkTarget = @($item.Target) | Select-Object -First 1
    if (-not $linkTarget) {
        return $false
    }

    try {
        return (Get-NormalizedPath $linkTarget) -eq (Get-NormalizedPath $ExpectedTarget)
    }
    catch {
        return $false
    }
}

function Test-CodexCli {
    $command = Get-Command codex -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Codex CLI was not found in PATH. Launch Codex once or reinstall it before running this installer."
    }

    try {
        $versionOutput = & $command.Source --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Verified Codex CLI: $($versionOutput | Select-Object -First 1)"
            return
        }
    }
    catch {
        # fall through to warning below
    }

    $message = @(
        "Codex CLI is present but did not execute cleanly from shell."
        "Resolved path: $($command.Source)"
    )
    if ($command.Source -like '*WindowsApps*') {
        $message += "This usually means the Windows Store app alias exists but direct shell execution is blocked."
        $message += "Open Codex once or reinstall it so a working shim appears under %LOCALAPPDATA%\\OpenAI\\Codex\\bin, then rerun `codex --version`."
    }

    throw ($message -join [Environment]::NewLine)
}

Test-CodexCli

New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null

$linked = 0
$skipped = 0

Get-ChildItem -Path $SourceRoot -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
    ForEach-Object {
        $target = Join-Path $TargetRoot $_.Name

        if (Test-Path $target) {
            $item = Get-Item -Force $target
            $isReparsePoint = ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0

            if ($isReparsePoint) {
                if (Test-RepoOwnedLink -LinkPath $target -ExpectedTarget $_.FullName) {
                    cmd /c rmdir "$target" | Out-Null
                }
                else {
                    Write-Warning "Skipping $($_.Name): $target exists and points outside this repo."
                    $skipped++
                    return
                }
            }
            else {
                Write-Host "Skipping $($_.Name): $target exists and is not a junction/symlink."
                $skipped++
                return
            }
        }

        cmd /c mklink /J "$target" "$($_.FullName)" | Out-Null
        Write-Host "Linked $($_.Name)"
        $linked++
    }

Write-Host ""
Write-Host "Linked $linked skills into $TargetRoot"
if ($skipped -gt 0) {
    Write-Host "Skipped $skipped existing non-owned or non-link target(s)."
}
