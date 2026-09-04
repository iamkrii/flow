@echo off
REM Flow — installs everything needed (Python, Node, FE ^& BE packages),
REM builds the frontend, then starts the server. (Windows)
cd /d "%~dp0"

REM --- 1. Python (installed via winget if missing) ---
where python >nul 2>nul
if errorlevel 1 (
  echo ==^> Installing Python...
  winget install -e --id Python.Python.3.12
  echo NOTE: close and reopen this window so Windows picks up the new PATH, then run again.
  pause
  exit /b 1
)

REM --- 2. Node.js ---
where node >nul 2>nul
if errorlevel 1 (
  echo ==^> Installing Node.js...
  winget install -e --id OpenJS.NodeJS.LTS
  echo NOTE: close and reopen this window so Windows picks up the new PATH, then run again.
  pause
  exit /b 1
)

REM --- 3. Backend packages ---
echo ==^> Installing backend packages (pip)...
python -m pip install -r backend\requirements.txt

REM --- 4. Frontend packages + build (yarn if present, else npm) ---
echo ==^> Installing frontend packages ^& building...
cd frontend
where yarn >nul 2>nul
if %errorlevel%==0 (
  call yarn install || call npm install
  call yarn build || call npm run build
) else (
  call npm install
  call npm run build
)
cd ..

REM --- 5. Start the server ---
echo ==^> Done. Server starting at http://localhost:8000
uvicorn backend.main:app --reload --port 8000
pause
