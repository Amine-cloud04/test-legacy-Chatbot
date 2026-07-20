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

"%PY%" scripts\setup_offline.py %*
