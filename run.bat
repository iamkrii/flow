@echo off
REM Flow — installs everything needed (Python, Node, FE ^& BE packages),
REM builds the frontend, then starts the server. (Windows)
cd /d "%~dp0"

REM --- 1. Python + project virtual environment ---
where python >nul 2>nul
if errorlevel 1 (
  echo ==^> Installing Python...
  winget install -e --id Python.Python.3.12
  echo NOTE: close and reopen this window so Windows picks up the new PATH, then run again.
  pause
  exit /b 1
)

REM Activate the project environment before installing or running anything else.
if not exist ".venv\Scripts\activate.bat" (
  echo ==^> Creating Python virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Could not create .venv. Ensure Python's venv module is installed.
    pause
    exit /b 1
  )
)

if /I not "%VIRTUAL_ENV%"=="%CD%\.venv" (
  echo ==^> Activating .venv...
  call .venv\Scripts\activate.bat
  if errorlevel 1 exit /b 1
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
python -m flask --app backend.main run --debug --host 0.0.0.0 --port 8000
pause
