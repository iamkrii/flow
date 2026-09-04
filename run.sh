#!/usr/bin/env bash
# Flow — installs everything needed (Python, Node, FE & BE packages),
# builds the frontend, then starts the server. (Linux + macOS)
set -e
cd "$(dirname "$0")"

have() { command -v "$1" >/dev/null 2>&1; }

# --- 1. Python 3 + project virtual environment ---
if ! have python3; then
  echo "==> Installing Python 3..."
  if have apt-get; then sudo apt-get update && sudo apt-get install -y python3 python3-pip
  elif have brew; then brew install python
  else echo "Please install Python 3 from https://python.org and re-run."; exit 1; fi
fi

# Activate the project environment before installing or running anything else.
if [ ! -f ".venv/bin/activate" ]; then
  echo "==> Creating Python virtual environment..."
  if ! python3 -m venv .venv; then
    if have apt-get; then
      echo "==> Installing Python venv support..."
      sudo apt-get update && sudo apt-get install -y python3-venv
      python3 -m venv .venv
    else
      echo "Could not create .venv. Ensure Python's venv module is installed."
      exit 1
    fi
  fi
fi

if [ "${VIRTUAL_ENV:-}" != "$PWD/.venv" ]; then
  echo "==> Activating .venv..."
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# --- 2. Node.js (+ npm) ---
if ! have node; then
  echo "==> Installing Node.js..."
  if have apt-get; then sudo apt-get install -y nodejs npm
  elif have brew; then brew install node
  else echo "Please install Node.js from https://nodejs.org and re-run."; exit 1; fi
fi

# --- 3. Backend packages ---
echo "==> Installing backend packages (pip)..."
python -m pip install -r backend/requirements.txt

# --- 4. Frontend packages + build (yarn if you have it, otherwise npm) ---
echo "==> Installing frontend packages & building..."
cd frontend
if have yarn; then yarn install && yarn build
else npm install && npm run build
fi
cd ..

# --- 5. Start the server ---
echo "==> Done. Server starting at http://localhost:8000"
python -m flask --app backend.main run --debug --host 0.0.0.0 --port 8000
