@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
  echo Run install_windows.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
