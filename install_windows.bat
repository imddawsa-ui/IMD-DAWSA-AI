@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 or newer from python.org and enable the launcher.
  exit /b 1
)
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo Python 3.11 or newer is required.
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 exit /b 1
)
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
if not exist .env copy .env.example .env
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -c "import secrets,pathlib,re; p=pathlib.Path('.env'); s=p.read_text(encoding='utf-8'); key=secrets.token_urlsafe(48); s=re.sub(r'(?m)^AUTH_SECRET_KEY=.*$', 'AUTH_SECRET_KEY='+key, s) if re.search(r'(?m)^AUTH_SECRET_KEY=.*$', s) and not re.search(r'(?m)^AUTH_SECRET_KEY=.{32,}$', s) else s; p.write_text(s,encoding='utf-8')"
if errorlevel 1 exit /b 1
if not exist data mkdir data
echo.
echo Installation completed.
echo A unique local AUTH_SECRET_KEY was generated if one was not already configured.
echo Review .env. Email-based registration remains disabled until a real email provider is configured.
echo Next: install Ollama, run pull_model.bat once, then start_windows.bat.
echo Local-only server binding is 127.0.0.1.
pause
