#!/usr/bin/env bash
# Offline literature review — no SharePoint access.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export SAFRAN_MODE=review
if [[ -f .env.review ]]; then
  export SAFRAN_ENV_FILE=.env.review
elif [[ -f .env ]]; then
  export SAFRAN_ENV_FILE=.env
  echo "Note: .env.review missing; falling back to .env (SharePoint vars ignored in review mode if SAFRAN_MODE=review)."
else
  echo "Missing .env.review — copy .env.review.example to .env.review"
  exit 1
fi

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "Lancement de la revue hors ligne (127.0.0.1)..."
echo "Astuce : démarrez Ollama pour des réponses générées (sinon mode extractif)."
exec streamlit run ui/app.py --server.address 127.0.0.1 --server.headless true
