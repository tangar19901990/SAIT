@echo off
setlocal
cd /d "%~dp0"

if not exist .venv (
  echo [1/3] Creating Python environment...
  py -3 -m venv .venv || goto :error
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip || goto :error
  python -m pip install -r requirements.txt || goto :error
  python -m playwright install chromium || goto :error
) else (
  call .venv\Scripts\activate.bat
)

echo [2/3] Starting SAIT...
python -m app.main
if errorlevel 1 goto :error

echo [3/3] SAIT closed normally.
pause
exit /b 0

:error
echo.
echo SAIT STARTUP ERROR. The line above shows the reason.
pause
exit /b 1
