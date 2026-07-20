"""One-time offline setup: .env.review, data/ folder, next-step hints (French)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Prepare the project for company-PC folder sync + offline review."""

    parser = argparse.ArgumentParser(description="Configurer le mode revue hors ligne.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Écraser .env.review s'il existe déjà.",
    )
    args = parser.parse_args()

    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    example = ROOT / ".env.review.example"
    target = ROOT / ".env.review"
    if not example.is_file():
        print(f"Fichier manquant : {example}")
        raise SystemExit(2)

    if target.exists() and not args.force:
        print(f".env.review existe déjà ({target})")
    else:
        shutil.copyfile(example, target)
        print(f"Créé : {target}")

    venv_ok = (ROOT / ".venv").is_dir()
    print()
    print("=== Configuration hors ligne ===")
    print(f"Dossier data     : {data_dir}")
    print(f"Environnement    : {'.venv OK' if venv_ok else 'ABSENT — lancez : python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt'}")
    print()
    print("Étapes suivantes (PC entreprise) :")
    print("  1. Ouvrir SharePoint dans le navigateur, synchroniser/télécharger la bibliothèque.")
    print('  2. ./sync_from_folder.sh "/chemin/vers/le/dossier" --reset')
    print("  3. Démarrer Ollama, puis ./run_review.sh")
    print("  4. Ou lancer : ./demarrer.sh")
    print()
    print("Vérification : ./check_ready.sh")


if __name__ == "__main__":
    main()
