#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_ROOT="${1:-${CODEX_HOME:-$HOME/.codex}/skills/dynamic-comic-video}"
PAINTED_ROOT="$(dirname "$INSTALL_ROOT")/code-painted-video"

mkdir -p "$INSTALL_ROOT" "$PAINTED_ROOT"
if [ "$(cd "$REPO_ROOT" && pwd)" != "$(cd "$INSTALL_ROOT" && pwd)" ]; then
  find "$REPO_ROOT" -mindepth 1 -maxdepth 1 \
    ! -name .git ! -name .venv ! -name node_modules ! -name projects \
    ! -name renderer ! -name manga-renderer ! -name skills -exec cp -R {} "$INSTALL_ROOT" \;
fi
if [ "$(cd "$REPO_ROOT/skills/code-painted-video" && pwd)" != "$(cd "$PAINTED_ROOT" && pwd)" ]; then
  cp -R "$REPO_ROOT/skills/code-painted-video/." "$PAINTED_ROOT/"
fi
echo "Ready. Remotion Skill: $INSTALL_ROOT"
echo "Ready. Code-painted Skill: $PAINTED_ROOT"
echo "Copy the painted-frame starter outside the Skill folder for each new code-painted video."
