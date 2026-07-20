#!/usr/bin/env bash
# Index a local SharePoint/OneDrive folder on a company PC, then go offline.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: ./sync_from_folder.sh /path/to/OneDrive/SharePointLibrary [--reset]"
  echo "On a company PC: sync the library via the browser/OneDrive, then point --path at that folder."
  exit 2
fi

PATH_ARG="$1"
shift
exec python scripts/sync_from_folder.py --path "$PATH_ARG" "$@"
