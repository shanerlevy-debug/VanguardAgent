#!/usr/bin/env bash
# onboard.sh — interactive onboarding wrapper.
#
# Same pattern as deploy.sh: creates venv on first run, installs deps,
# then runs onboard.py. All args forwarded.
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"
STAMP="$VENV/.deps-installed"
REQS="scripts/requirements.txt"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "ERROR: Python 3.12+ not found on PATH. See docs/01-prerequisites.md." >&2
    exit 1
fi

# Recreate venv if missing OR broken (no activate script — happens when an
# earlier wrapper run failed midway through and left a partial dir).
if [ ! -d "$VENV" ] || { [ ! -f "$VENV/bin/activate" ] && [ ! -f "$VENV/Scripts/activate" ]; }; then
    if [ -d "$VENV" ]; then
        echo "[wrapper] Detected broken venv at $VENV; removing and recreating ..."
        rm -rf "$VENV"
    else
        echo "[wrapper] Creating venv at $VENV ..."
    fi
    "$PY" -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate" 2>/dev/null || source "$VENV/Scripts/activate"

if [ ! -f "$STAMP" ] || [ "$REQS" -nt "$STAMP" ]; then
    echo "[wrapper] Installing dependencies from $REQS ..."
    pip install --quiet --upgrade pip
    pip install --quiet -r "$REQS"
    touch "$STAMP"
fi

exec python scripts/onboard.py "$@"
