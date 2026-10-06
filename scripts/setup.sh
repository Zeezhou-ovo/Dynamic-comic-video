#!/usr/bin/env bash
# Install the dynamic-comic-video skill for any AI agent.
#
#   bash scripts/setup.sh                      # check the environment only
#   bash scripts/setup.sh --dest <skill dir>   # also copy the skill there (repeatable)
#   bash scripts/setup.sh <skill dir>          # same as --dest (older usage)
#
# The skill is agent-neutral: SKILL.md plus local Python/Node scripts. Copy it
# into whatever skill folder your AI tool reads, or just point the agent at
# SKILL.md in this repository.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTS=()

usage() {
  sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dest) [ $# -ge 2 ] || { usage; exit 2; }; DESTS+=("$2"); shift 2 ;;
    --dest=*) DESTS+=("${1#--dest=}"); shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "Unknown option: $1" >&2; usage; exit 2 ;;
    *) DESTS+=("$1"); shift ;;
  esac
done

for dest in "${DESTS[@]+"${DESTS[@]}"}"; do
  mkdir -p "$dest"
  if [ "$(cd "$REPO_ROOT" && pwd)" != "$(cd "$dest" && pwd)" ]; then
    find "$REPO_ROOT" -mindepth 1 -maxdepth 1 \
      ! -name .git ! -name .venv ! -name node_modules ! -name projects \
      ! -name renderer ! -name manga-renderer -exec cp -R {} "$dest" \;
  fi
  echo "Installed skill: $(cd "$dest" && pwd)/SKILL.md"
done

if [ ${#DESTS[@]} -eq 0 ]; then
  echo "No copy made. Point your AI agent at: $REPO_ROOT/SKILL.md"
  echo "(or rerun with --dest <the skill folder your AI tool reads>)"
fi

PYTHON="$(command -v python3 || command -v python || true)"
if [ -n "$PYTHON" ]; then
  echo "Environment check (fix commands are listed for anything missing):"
  "$PYTHON" "$REPO_ROOT/scripts/doctor.py" || true
else
  echo "Python 3.10+ not found; install it, then run: pip install -r requirements.txt" >&2
fi
for tool in ffmpeg ffprobe; do
  command -v "$tool" >/dev/null 2>&1 || echo "Note: $tool not found; preview loudness and the delivery gate need it." >&2
done
