@echo off
REM Prefer USB portable Python (runtime\python) over a local .venv
setlocal
cd /d "%~dp0"

if exist "runtime\python\python.exe" (
  set "PYTHON_EXE=runtime\python\python.exe"
) else if exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
  set "PYTHON_EXE=python"
)
