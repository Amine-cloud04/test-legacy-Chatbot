"""Build a clean Windows USB bundle (no secrets, no Linux venv)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "models",
    "dist",
    "runtime",
}
EXCLUDE_FILE_SUFFIXES = {".pyc", ".pyo", ".db", ".pkl", ".index", ".gguf", ".ggml"}
EXCLUDE_FILE_NAMES = {".env", ".env.review", "sync_manifest.json"}


def _should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    parts = set(rel.parts)
    if parts & EXCLUDE_DIR_NAMES:
        return True
    if path.is_file() and path.name in EXCLUDE_FILE_NAMES:
        return True
    if path.is_file() and path.suffix in EXCLUDE_FILE_SUFFIXES:
        return True
    if path.is_file() and path.name.endswith(".chunk_ids.npy"):
        return True
    return False


def copy_project(dest: Path) -> None:
    """Copy application files into dest."""

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    for src in ROOT.rglob("*"):
        if _should_skip(src, ROOT):
            continue
        if src.is_dir():
            continue
        rel = src.relative_to(ROOT)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)

    # Ensure empty runtime / data placeholders exist in the bundle
    (dest / "runtime" / "python").mkdir(parents=True, exist_ok=True)
    (dest / "runtime" / "ollama").mkdir(parents=True, exist_ok=True)
    (dest / "runtime" / "wheelhouse").mkdir(parents=True, exist_ok=True)
    (dest / "data").mkdir(parents=True, exist_ok=True)
    (dest / "runtime" / "python" / "PUT_PORTABLE_PYTHON_HERE.txt").write_text(
        "Placez ici le Python portable Windows (python.exe à la racine de ce dossier).\n"
        "Sur le PC personnel, lancez : python scripts/download_windows_runtime.py\n",
        encoding="utf-8",
    )
    (dest / "runtime" / "ollama" / "PUT_OLLAMA_HERE.txt").write_text(
        "Placez ici ollama.exe (Windows), puis le modèle sera dans models/.\n"
        "Sur le PC personnel, lancez : python scripts/download_windows_runtime.py --with-ollama\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Préparer le dossier à copier sur clé USB Windows.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "safran-usb",
        help="Dossier de sortie (défaut : dist/safran-usb)",
    )
    parser.add_argument(
        "--download-wheels",
        action="store_true",
        help="Télécharger aussi les wheels Windows dans runtime/wheelhouse",
    )
    parser.add_argument(
        "--python-version",
        default="3.12",
        help="Version Python cible Windows pour les wheels (défaut : 3.12)",
    )
    args = parser.parse_args()

    dest = args.output.resolve()
    print(f"Préparation du bundle USB → {dest}")
    copy_project(dest)
    # Prefer USB requirements inside the bundle
    shutil.copy2(ROOT / "requirements-usb.txt", dest / "requirements-usb.txt")
    shutil.copy2(ROOT / "USB_LIRE_MOI.txt", dest / "USB_LIRE_MOI.txt")

    if args.download_wheels:
        sys.path.insert(0, str(ROOT))
        from scripts.download_windows_wheels import download_wheels

        download_wheels(dest / "runtime" / "wheelhouse", args.python_version)

    print()
    print("Bundle prêt.")
    print("Étapes suivantes (PC personnel, avec Internet) :")
    print(f"  1. python scripts/download_windows_runtime.py --bundle \"{dest}\"")
    print(f"  2. Copier tout le dossier sur la clé USB chiffrée")
    print("  3. Sur le PC entreprise : install_offline.bat puis demarrer.bat")


if __name__ == "__main__":
    main()
