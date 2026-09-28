#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_ROOT="${1:-${CODEX_HOME:-$HOME/.codex}/skills/dynamic-comic-video}"

mkdir -p "$INSTALL_ROOT"
if [ "$(cd "$REPO_ROOT" && pwd)" != "$(cd "$INSTALL_ROOT" && pwd)" ]; then
  find "$REPO_ROOT" -mindepth 1 -maxdepth 1 \
    ! -name .git ! -name .venv ! -name node_modules ! -name projects \
    ! -name renderer ! -name manga-renderer -exec cp -R {} "$INSTALL_ROOT" \;
fi
echo "Ready. Skill: $INSTALL_ROOT"
echo "Copy assets/painted-frame-starter outside the Skill folder for each new video."
echo "Install Node and browser dependencies inside that video project."
