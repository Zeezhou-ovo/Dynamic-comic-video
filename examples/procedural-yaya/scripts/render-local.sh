#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

NODE_BIN=${NODE_BIN:-$(command -v node || true)}

if [ ! -x "$NODE_BIN" ]; then
  echo "Node.js is unavailable" >&2
  exit 1
fi

if [ -z "${CHROME_PATH:-}" ]; then
  for candidate in .browser/chromium-*/chrome-mac-arm64/Google\ Chrome\ for\ Testing.app/Contents/MacOS/Google\ Chrome\ for\ Testing; do
    if [ -x "$candidate" ]; then
      CHROME_PATH=$candidate
      break
    fi
  done
fi

if [ -n "${CHROME_PATH:-}" ]; then
  case "$CHROME_PATH" in
    /*) ;;
    *) CHROME_PATH="$(pwd)/$CHROME_PATH" ;;
  esac
fi

"$NODE_BIN" scripts/production.mjs sync >/dev/null
PATH="$(pwd)/.tools:$PATH" CHROME_PATH="${CHROME_PATH:-}" "$NODE_BIN" render.mjs "$@"
