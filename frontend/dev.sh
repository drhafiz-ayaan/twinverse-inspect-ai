#!/usr/bin/env bash
# Start the Next.js dev server with nvm's Node on PATH.
#
# Node is installed via nvm (README D-006), which puts it under ~/.nvm rather
# than a system path. A login shell picks it up from .bashrc; anything that
# spawns the server non-interactively does not — and Turbopack spawns its own
# worker processes, which then fail with "spawning node pooled process: No
# such file or directory" even when the parent was launched by absolute path.
#
# Sourcing nvm here fixes it for the whole process tree.
set -euo pipefail

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
fi

if ! command -v node >/dev/null 2>&1; then
  echo "node not found. Install it with:" >&2
  echo "  nvm install 20 && nvm alias default 20" >&2
  exit 1
fi

cd "$(dirname "$0")"
exec npm run dev -- "$@"
