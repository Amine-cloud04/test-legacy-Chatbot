#!/usr/bin/env bash
# Preflight checks before offline review.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export SAFRAN_MODE=review
if [[ -f .env.review ]]; then
  export SAFRAN_ENV_FILE=.env.review
fi

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec python scripts/check_ready.py "$@"
