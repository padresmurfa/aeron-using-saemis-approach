#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_ROOT="$REPO_ROOT/.claude/skills"
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
TARGET_ROOT="$CODEX_ROOT/skills"

if [ ! -d "$SOURCE_ROOT" ]; then
  echo "ERROR: canonical skill source not found: $SOURCE_ROOT" >&2
  exit 1
fi

warn() {
  echo "WARNING: $*" >&2
}

fail_lines() {
  for line in "$@"; do
    echo "ERROR: $line" >&2
  done
  exit 1
}

normalize_dir() {
  (
    cd "$1" 2>/dev/null
    pwd -P
  )
}

resolve_link_target() {
  local link_path="$1"
  local link_target

  link_target="$(readlink "$link_path")" || return 1

  if [[ "$link_target" = /* ]]; then
    normalize_dir "$link_target"
  else
    normalize_dir "$(dirname "$link_path")/$link_target"
  fi
}

test_codex_cli() {
  local command_path
  local version_output

  if ! command_path="$(command -v codex 2>/dev/null)"; then
    fail_lines "Codex CLI was not found in PATH. Launch Codex once or reinstall it before running this installer."
  fi

  if version_output="$("$command_path" --version 2>&1)"; then
    echo "Verified Codex CLI: $(printf '%s\n' "$version_output" | head -n 1)"
    return
  fi

  if [[ "$command_path" == *WindowsApps* ]]; then
    fail_lines \
      "Codex CLI is present but did not execute cleanly from shell." \
      "Resolved path: $command_path" \
      "This usually means the Windows Store app alias exists but direct shell execution is blocked." \
      "Open Codex once or reinstall it so a working shim appears under %LOCALAPPDATA%\\OpenAI\\Codex\\bin, then rerun codex --version."
  fi

  fail_lines \
    "Codex CLI is present but did not execute cleanly from shell." \
    "Resolved path: $command_path"
}

test_codex_cli

mkdir -p "$TARGET_ROOT"

linked=0
skipped=0

for skill_dir in "$SOURCE_ROOT"/*; do
  [ -d "$skill_dir" ] || continue
  [ -f "$skill_dir/SKILL.md" ] || continue

  skill_name="$(basename "$skill_dir")"
  target="$TARGET_ROOT/$skill_name"
  skill_real="$(normalize_dir "$skill_dir")"

  if [ -L "$target" ]; then
    if existing_real="$(resolve_link_target "$target")" && [ "$existing_real" = "$skill_real" ]; then
      rm -f "$target"
    else
      echo "Skipping $skill_name: $target exists and points outside this repo."
      skipped=$((skipped + 1))
      continue
    fi
  elif [ -e "$target" ]; then
    echo "Skipping $skill_name: $target exists and is not a symlink."
    skipped=$((skipped + 1))
    continue
  fi

  ln -s "$skill_dir" "$target"
  echo "Linked $skill_name"
  linked=$((linked + 1))
done

echo
echo "Linked $linked skills into $TARGET_ROOT"
if [ "$skipped" -gt 0 ]; then
  echo "Skipped $skipped existing non-owned or non-link target(s)."
fi
