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

if "%~1"=="" (
  echo Usage: sync_from_folder.bat C:\path\to\OneDrive\SharePointLibrary [--reset]
  exit /b 2
)

"%PY%" scripts\sync_from_folder.py --path %*
