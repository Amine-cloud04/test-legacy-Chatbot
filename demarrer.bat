@echo off
REM Menu principal — PC entreprise / cle USB.
setlocal
cd /d "%~dp0"

if exist "runtime\python\python.exe" (
  set "PY=runtime\python\python.exe"
) else if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo ============================================
echo  Assistant de connaissances Safran
echo  Cle USB / PC entreprise — hors ligne
echo ============================================
echo   1) Configurer (.env.review)
echo   2) Synchroniser un dossier SharePoint/OneDrive
echo   3) Verifier que tout est pret
echo   4) Lancer la revue hors ligne
echo   5) Quitter
echo ============================================
set /p choice="Choix [1-5] : "

if "%choice%"=="1" (
  "%PY%" scripts\setup_offline.py
  goto :eof
)
if "%choice%"=="2" (
  set /p folder="Chemin du dossier local : "
  if "%folder%"=="" (
    echo Chemin vide.
    exit /b 2
  )
  set /p reset="Reinitialiser la base ? [o/N] : "
  if /i "%reset%"=="o" (
    "%PY%" scripts\sync_from_folder.py --path "%folder%" --reset
  ) else (
    "%PY%" scripts\sync_from_folder.py --path "%folder%"
  )
  goto :eof
)
if "%choice%"=="3" (
  set SAFRAN_MODE=review
  set SAFRAN_ENV_FILE=.env.review
  "%PY%" scripts\check_ready.py
  goto :eof
)
if "%choice%"=="4" (
  call run_review.bat
  goto :eof
)
if "%choice%"=="5" (
  exit /b 0
)

echo Choix invalide.
exit /b 2
