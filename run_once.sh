#!/usr/bin/env bash
# run_once.sh — bash wrapper around scripts/run_once.py.
#
# Activates the project venv (created by deploy.sh) and forwards all
# arguments. Run AFTER a successful deploy.
#
# Usage:
#   ./run_once.sh                     # standard kickoff
#   ./run_once.sh --kickoff "..."     # custom kickoff message
#   ./run_once.sh --dry-run           # tell agent to log, not post
#   ./run_once.sh --no-stream         # send kickoff and exit
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"

if [ ! -d "$VENV" ] || { [ ! -f "$VENV/bin/activate" ] && [ ! -f "$VENV/Scripts/activate" ]; }; then
    echo "ERROR: no working venv at $VENV — run ./deploy.sh first." >&2
    exit 1
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate" 2>/dev/null || source "$VENV/Scripts/activate"

exec python scripts/run_once.py "$@"
