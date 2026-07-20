@echo off
REM Offline review — EVERYTHING from USB (Python + Ollama + model + app).
setlocal EnableExtensions
cd /d "%~dp0"

set SAFRAN_MODE=review
if exist ".env.review" (
  set SAFRAN_ENV_FILE=.env.review
) else (
  echo Missing .env.review — lancez install_offline.bat d'abord
  exit /b 1
)

if exist "runtime\python\python.exe" (
  set "PY=runtime\python\python.exe"
) else (
  echo Python portable introuvable. Lancez install_offline.bat une fois.
  exit /b 1
)

REM Force Ollama to use ONLY data on this USB stick
set "OLLAMA_MODELS=%~dp0runtime\ollama\models"
set "OLLAMA_HOST=127.0.0.1:11434"
if exist "%~dp0runtime\ollama\home" (
  set "HOME=%~dp0runtime\ollama\home"
  set "USERPROFILE=%~dp0runtime\ollama\home"
)

if not exist "runtime\ollama\ollama.exe" (
  echo [FAIL] ollama.exe manquant sur la cle. Relancez ./pack_usb.sh sur le PC personnel.
  exit /b 1
)

echo Demarrage d'Ollama depuis la cle USB (modele inclus)...
start "safran-ollama" /MIN "runtime\ollama\ollama.exe" serve
timeout /t 4 /nobreak >nul

echo Lancement de la revue hors ligne (127.0.0.1)...
"%PY%" -m streamlit run ui/app.py --server.address 127.0.0.1 --server.headless true
endlocal
