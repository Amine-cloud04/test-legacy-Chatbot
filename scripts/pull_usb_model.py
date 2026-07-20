"""Pull an Ollama model into the USB bundle (personal PC, online).

Starts a temporary Ollama server bound to a dedicated port and models dir so
weights are stored on the USB path — not in the system Ollama service.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "llama3.2:3b"
TEMP_HOST = "127.0.0.1:11435"


def _ollama_bin() -> str:
    found = shutil.which("ollama")
    if not found:
        raise SystemExit(
            "Ollama n'est pas installé sur ce PC personnel.\n"
            "Installez-le depuis https://ollama.com puis relancez ./pack_usb.sh"
        )
    return found


def _models_nonempty(models_dir: Path) -> bool:
    if not models_dir.is_dir():
        return False
    return any(p.is_file() and p.stat().st_size > 1024 for p in models_dir.rglob("*"))


def pull_model(models_dir: Path, model: str) -> None:
    """Download model weights into models_dir using a private Ollama server."""

    models_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = str(models_dir)
    env["OLLAMA_HOST"] = TEMP_HOST
    # Keep manifests/blobs under the USB tree as well when supported
    env["HOME"] = str(models_dir.parent / "home")
    (models_dir.parent / "home").mkdir(parents=True, exist_ok=True)

    print(f"Serveur Ollama temporaire sur {TEMP_HOST}")
    print(f"Stockage modèle : {models_dir}")
    server = subprocess.Popen(
        [_ollama_bin(), "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(40):
            time.sleep(0.5)
            probe = subprocess.run(
                [_ollama_bin(), "list"],
                env=env,
                capture_output=True,
                text=True,
            )
            if probe.returncode == 0:
                break
        else:
            raise SystemExit("Impossible de démarrer le serveur Ollama temporaire.")

        print(f"Téléchargement du modèle {model} (quelques Go, une seule fois)...")
        subprocess.check_call([_ollama_bin(), "pull", model], env=env)

        # Newer Ollama may store under HOME/.ollama — copy into models_dir if needed
        home_store = Path(env["HOME"]) / ".ollama"
        if home_store.is_dir() and not _models_nonempty(models_dir):
            print(f"Copie depuis {home_store} → {models_dir}")
            for item in home_store.iterdir():
                dest = models_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

        if not _models_nonempty(models_dir) and not _models_nonempty(home_store):
            raise SystemExit(
                "Le modèle n'a pas été écrit sur la clé USB. Vérifiez Ollama et relancez."
            )

        (models_dir / "READY.txt").write_text(
            f"Modèle Ollama prêt : {model}\n"
            f"Utilisé hors ligne via OLLAMA_MODELS / OLLAMA_HOST sur la clé USB.\n",
            encoding="utf-8",
        )
        print("Modèle prêt sur la clé USB.")
    finally:
        server.send_signal(signal.SIGTERM)
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="Télécharger le modèle Ollama dans le bundle USB.")
    parser.add_argument("--bundle", type=Path, default=ROOT / "dist" / "safran-usb")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    models_dir = args.bundle.resolve() / "runtime" / "ollama" / "models"
    pull_model(models_dir, args.model)


if __name__ == "__main__":
    main()
