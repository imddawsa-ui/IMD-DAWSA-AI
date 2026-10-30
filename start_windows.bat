@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run install_windows.bat first.
  exit /b 1
)
if not exist .env (
  echo Missing .env. Run install_windows.bat first.
  exit /b 1
)
.venv\Scripts\python.exe -c "from pathlib import Path; import re,sys; s=Path('.env').read_text(encoding='utf-8'); m=re.search(r'(?m)^AUTH_SECRET_KEY=(.*)$',s); sys.exit(0 if m and len(m.group(1).strip())>=32 else 1)"
if errorlevel 1 (
  echo AUTH_SECRET_KEY is missing or too short. Run install_windows.bat.
  exit /b 1
)
echo Starting NILE ONE HUMAN locally at http://127.0.0.1:8000
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
