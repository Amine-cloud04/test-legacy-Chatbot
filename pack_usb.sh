#!/usr/bin/env bash
# Build a COMPLETE Windows USB bundle: app + Python + wheels + Ollama + model.
# Run on your PERSONAL PC (internet required). Company PC needs nothing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

MODEL="${OLLAMA_MODEL:-llama3.2:3b}"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "=== 1/3 Empaquetage du projet ==="
python scripts/pack_for_usb.py --output dist/safran-usb

echo
echo "=== 2/3 Runtime Windows (Python + libs + Ollama) ==="
python scripts/download_windows_runtime.py --bundle dist/safran-usb --with-ollama

echo
echo "=== 3/3 Modele Ollama hors ligne ($MODEL) ==="
python scripts/pull_usb_model.py --bundle dist/safran-usb --model "$MODEL"

# Refresh launchers / docs at bundle root
cp -f USB_LIRE_MOI.txt dist/safran-usb/
for f in demarrer.bat setup_offline.bat sync_from_folder.bat check_ready.bat run_review.bat install_offline.bat; do
  cp -f "$f" "dist/safran-usb/$f"
done

# Default review env inside bundle
if [[ ! -f dist/safran-usb/.env.review ]]; then
  cp -f .env.review.example dist/safran-usb/.env.review
fi

SIZE="$(du -sh dist/safran-usb | awk '{print $1}')"
echo
echo "============================================"
echo " TERMINE — bundle COMPLET"
echo " Taille : $SIZE"
echo " Dossier a copier sur la cle USB :"
echo "   $ROOT/dist/safran-usb"
echo
echo " Sur le PC entreprise (rien a installer depuis le web) :"
echo "   1) install_offline.bat   (une fois)"
echo "   2) demarrer.bat"
echo "============================================"
