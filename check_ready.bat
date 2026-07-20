@echo off
setlocal
cd /d "%~dp0"

if exist "runtime\python\python.exe" (
  set "PY=runtime\python\python.exe"
) else if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

set SAFRAN_MODE=review
if exist ".env.review" set SAFRAN_ENV_FILE=.env.review

"%PY%" scripts\check_ready.py %*
