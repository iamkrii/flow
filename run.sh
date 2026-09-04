#!/usr/bin/env bash
# Flow — installs everything needed (Python, Node, FE & BE packages),
# builds the frontend, then starts the server. (Linux + macOS)
set -e
cd "$(dirname "$0")"

have() { command -v "$1" >/dev/null 2>&1; }

# --- 1. Python 3 ---
if ! have python3; then
  echo "==> Installing Python 3..."
  if have apt-get; then sudo apt-get update && sudo apt-get install -y python3 python3-pip
  elif have brew; then brew install python
  else echo "Please install Python 3 from https://python.org and re-run."; exit 1; fi
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
python3 -m pip install -r backend/requirements.txt

# --- 4. Frontend packages + build (yarn if you have it, otherwise npm) ---
echo "==> Installing frontend packages & building..."
cd frontend
if have yarn; then yarn install && yarn build
else npm install && npm run build
fi
cd ..

# --- 5. Start the server ---
echo "==> Done. Server starting at http://localhost:8000"
uvicorn backend.main:app --reload --port 8000
