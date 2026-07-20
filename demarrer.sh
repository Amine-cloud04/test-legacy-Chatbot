#!/usr/bin/env bash
# Menu principal — PC entreprise : configurer, synchroniser, vérifier, revoir.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "============================================"
echo " Assistant de connaissances Safran"
echo " PC entreprise — dossier local → revue hors ligne"
echo "============================================"
echo "  1) Configurer (.env.review)"
echo "  2) Synchroniser un dossier SharePoint/OneDrive"
echo "  3) Vérifier que tout est prêt"
echo "  4) Lancer la revue hors ligne"
echo "  5) Quitter"
echo "============================================"
read -r -p "Choix [1-5] : " choice

case "${choice}" in
  1)
    exec python scripts/setup_offline.py
    ;;
  2)
    read -r -p "Chemin du dossier local : " folder
    if [[ -z "${folder}" ]]; then
      echo "Chemin vide."
      exit 2
    fi
    read -r -p "Réinitialiser la base ? [o/N] : " reset
    if [[ "${reset}" =~ ^[oOyY]$ ]]; then
      exec python scripts/sync_from_folder.py --path "${folder}" --reset
    else
      exec python scripts/sync_from_folder.py --path "${folder}"
    fi
    ;;
  3)
    export SAFRAN_MODE=review
    export SAFRAN_ENV_FILE=.env.review
    exec python scripts/check_ready.py
    ;;
  4)
    exec ./run_review.sh
    ;;
  5)
    exit 0
    ;;
  *)
    echo "Choix invalide."
    exit 2
    ;;
esac
