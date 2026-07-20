"""Preflight checks before offline literature review (French output)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from config import Settings
from ingest.sync_manifest import format_manifest_caption, load_manifest

ROOT = Path(__file__).resolve().parents[1]


def _ok(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"[OK]   {label}{suffix}")


def _warn(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"[WARN] {label}{suffix}")


def _fail(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"[FAIL] {label}{suffix}")


def check_ollama(url: str, timeout: float = 3.0) -> bool:
    """Return True if Ollama responds on the configured URL."""

    try:
        response = httpx.get(f"{url.rstrip('/')}/api/tags", timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def main() -> None:
    """Print readiness status and exit 0 if review can start (Ollama optional)."""

    parser = argparse.ArgumentParser(description="Vérifier que la revue hors ligne est prête.")
    parser.add_argument(
        "--require-ollama",
        action="store_true",
        help="Échouer si Ollama n'est pas joignable.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Fichier d'environnement (défaut : .env.review si présent).",
    )
    args = parser.parse_args()

    env_file = args.env_file
    if env_file is None:
        review = ROOT / ".env.review"
        env_file = review if review.is_file() else ROOT / ".env"

    hard_fail = False
    soft_warn = False

    print("=== Vérification revue hors ligne ===")
    print(f"Racine : {ROOT}")
    print(f"Env    : {env_file}")
    print()

    if not env_file.is_file():
        _fail(".env.review", "absent — lancez ./setup_offline.sh")
        hard_fail = True
    else:
        _ok("Fichier d'environnement", str(env_file.name))

    if (ROOT / ".venv").is_dir():
        _ok("Environnement Python", ".venv")
    else:
        _warn("Environnement Python", ".venv absent")
        soft_warn = True

    settings = Settings.from_env(env_file if env_file.is_file() else None)
    # Force review semantics for this check when using .env.review
    if env_file.name == ".env.review":
        settings.review_mode = True
        settings.sharepoint_password = ""

    if settings.db_path.is_file():
        _ok("Base SQLite", str(settings.db_path))
    else:
        _fail("Base SQLite", f"absente ({settings.db_path}) — lancez ./sync_from_folder.sh")
        hard_fail = True

    if settings.index_path.is_file():
        _ok("Index BM25", str(settings.index_path))
    else:
        _warn("Index BM25", f"absent ({settings.index_path}) — la recherche lexicale peut échouer")
        soft_warn = True

    manifest = load_manifest(settings.sync_manifest_path) if settings.sync_manifest_path else None
    if manifest is None:
        _warn("Manifeste de synchro", "jamais — lancez ./sync_from_folder.sh")
        soft_warn = True
    else:
        _ok("Manifeste de synchro", format_manifest_caption(manifest))
        print(f"       Source : {manifest.source_path}")

    if settings.sharepoint_password:
        _warn("Secrets SharePoint", "un mot de passe est chargé — préférez .env.review sans credentials")
        soft_warn = True
    else:
        _ok("Secrets SharePoint", "aucun mot de passe chargé")

    ollama_url = settings.local_llm_service_url
    if not ollama_url:
        _warn("Ollama", "URL non configurée — réponses extractives uniquement")
        soft_warn = True
        ollama_ok = False
    elif check_ollama(ollama_url):
        _ok("Ollama", f"joignable ({ollama_url}), modèle attendu : {settings.local_llm_service_model}")
        ollama_ok = True
    else:
        _warn("Ollama", f"injoignable ({ollama_url}) — démarrez Ollama ou utilisez le mode extractif")
        soft_warn = True
        ollama_ok = False

    print()
    if hard_fail:
        print("Résultat : PAS PRÊT — corrigez les [FAIL] ci-dessus.")
        raise SystemExit(1)
    if args.require_ollama and not ollama_ok:
        print("Résultat : PAS PRÊT — Ollama requis (--require-ollama).")
        raise SystemExit(1)
    if soft_warn:
        print("Résultat : PRÊT AVEC RÉSERVES — vous pouvez lancer ./run_review.sh")
    else:
        print("Résultat : PRÊT — lancez ./run_review.sh")


if __name__ == "__main__":
    main()
