@echo off
setlocal
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama was not found. Install the free Ollama application first: https://ollama.com/download
  exit /b 1
)
ollama list
echo.
echo Downloading the configured lightweight default model: qwen2.5:3b
echo This requires internet access and free disk space. CPU inference may be slow on 8 GB RAM.
ollama pull qwen2.5:3b
if errorlevel 1 (
  echo Model download failed. Check internet connectivity and available disk space.
  exit /b 1
)
echo Model is downloaded. Start Ollama, then run start_windows.bat.
pause
