#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python
fi
if [ ! -d .venv ]; then
  "$PY" -m venv .venv
fi
# Source the correct activate script depending on platform
if [ -f .venv/bin/activate ]; then
  # Unix-like venv
  # shellcheck disable=SC1091
  . .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
  # Windows venv (Git Bash / MSYS)
  # shellcheck disable=SC1091
  . .venv/Scripts/activate
else
  echo "No activate script found; creating venv with $PY and retrying..." >&2
  "$PY" -m venv .venv
  if [ -f .venv/bin/activate ]; then
    . .venv/bin/activate
  elif [ -f .venv/Scripts/activate ]; then
    . .venv/Scripts/activate
  else
    echo "Failed to create virtualenv or locate activate script." >&2
    exit 1
  fi
fi
VENV_PY=".venv/bin/python"
if [ -f .venv/Scripts/python.exe ]; then
  VENV_PY=".venv/Scripts/python.exe"
elif [ -f .venv/Scripts/python ]; then
  VENV_PY=".venv/Scripts/python"
fi
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt
exec "$VENV_PY" app.py
 1c0dce200b3a7691e168cbf9e38f908992a9caf8
