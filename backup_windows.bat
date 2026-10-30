@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run install_windows.bat first.
  exit /b 1
)
if not exist backups mkdir backups
.venv\Scripts\python.exe -m app.backup_cli create --output backups/nile-one.sqlite.enc
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m app.backup_cli verify --input backups/nile-one.sqlite.enc
if errorlevel 1 exit /b 1
echo.
echo Encrypted backup created and verified.
echo Copy the backup AND keep the encryption key in a separate safe location.
pause
