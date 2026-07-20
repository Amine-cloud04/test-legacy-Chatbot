@echo off
REM One-time offline install from USB wheelhouse (NO internet).
setlocal EnableExtensions
cd /d "%~dp0"

set PY=runtime\python\python.exe
set WH=runtime\wheelhouse
set REQ=requirements-usb.txt

if not exist "%PY%" (
  echo [FAIL] runtime\python\python.exe introuvable.
  echo Sur le PC personnel, lancez d'abord : pack_usb.sh
  exit /b 1
)

if not exist "%WH%\*.whl" (
  echo [FAIL] runtime\wheelhouse est vide.
  echo Sur le PC personnel, lancez : pack_usb.sh
  exit /b 1
)

echo === Installation hors ligne COMPLETE depuis la cle USB ===
echo (aucune connexion Internet requise)
if exist "runtime\python\get-pip.py" (
  echo Installation de pip (hors ligne)...
  "%PY%" "runtime\python\get-pip.py" --no-index --find-links="%WH%" --no-warn-script-location
  if errorlevel 1 (
    echo [FAIL] get-pip a echoue.
    exit /b 1
  )
)

echo Installation des bibliotheques (hors ligne)...
"%PY%" -m pip install --no-index --find-links="%WH%" -r "%REQ%"
if errorlevel 1 (
  echo [FAIL] pip install a echoue.
  exit /b 1
)

if not exist ".env.review" (
  if exist ".env.review.example" copy /Y ".env.review.example" ".env.review" >nul
)

if not exist "data" mkdir data

echo.
echo [OK] Installation terminee.
if exist "runtime\ollama\ollama.exe" (
  echo [OK] Ollama present sur la cle.
) else (
  echo [WARN] Ollama absent — re-packez avec ./pack_usb.sh sur le PC personnel.
)
if exist "runtime\ollama\models" (
  echo [OK] Modeles Ollama presents sur la cle.
) else (
  echo [WARN] Modeles absents — relancez ./pack_usb.sh sur le PC personnel.
)
echo.
echo Ensuite : demarrer.bat
endlocal
