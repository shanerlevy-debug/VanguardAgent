#!/usr/bin/env bash
# deploy.sh — Bash wrapper around scripts/deploy.py.
#
# Sets up a venv on first run, installs dependencies once (cached via a
# stamp file), then forwards all arguments to deploy.py. Re-runs are fast.
#
# Usage:
#   ./deploy.sh                              # full deploy
#   ./deploy.sh --dry-run                    # validate only
#   ./deploy.sh --skill understanding-foo    # re-upload one skill
#   ./deploy.sh --force-recreate slack-token # rotate token
set -euo pipefail

# Always run from this script's directory so paths resolve regardless of cwd.
cd "$(dirname "$0")"

VENV=".venv"
STAMP="$VENV/.deps-installed"
REQS="scripts/requirements.txt"

# Pick a python: prefer python3, fall back to python.
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "ERROR: Python 3.12+ not found on PATH. See docs/01-prerequisites.md." >&2
    exit 1
fi

# 1. Recreate venv if missing OR broken (no activate script — happens when an
#    earlier wrapper run failed midway through and left a partial dir).
if [ ! -d "$VENV" ] || { [ ! -f "$VENV/bin/activate" ] && [ ! -f "$VENV/Scripts/activate" ]; }; then
    if [ -d "$VENV" ]; then
        echo "[wrapper] Detected broken venv at $VENV; removing and recreating ..."
        rm -rf "$VENV"
    else
        echo "[wrapper] Creating venv at $VENV ..."
    fi
    "$PY" -m venv "$VENV"
fi

# 2. Activate venv.
# shellcheck disable=SC1091
source "$VENV/bin/activate" 2>/dev/null || source "$VENV/Scripts/activate"

# 3. Install deps if stamp is missing or older than requirements.txt.
if [ ! -f "$STAMP" ] || [ "$REQS" -nt "$STAMP" ]; then
    echo "[wrapper] Installing dependencies from $REQS ..."
    pip install --quiet --upgrade pip
    pip install --quiet -r "$REQS"
    touch "$STAMP"
fi

# 4. Run the deploy.
exec python scripts/deploy.py "$@"
