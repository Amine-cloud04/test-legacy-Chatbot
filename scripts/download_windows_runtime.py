"""Download portable Windows Python (and optionally Ollama) into a USB bundle.

Run on your personal PC with internet. Company PC must not use the web.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

# CPython embeddable (amd64) — adjust patch version if the URL 404s.
PYTHON_VERSION = "3.12.8"
PYTHON_EMBED_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
)
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"


def _download(url: str, dest: Path) -> None:
    print(f"Téléchargement : {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "safran-knowledge-assistant-usb-packager"})
    with urlopen(req, timeout=120) as response:
        dest.write_bytes(response.read())
    print(f"Enregistré : {dest} ({dest.stat().st_size // (1024 * 1024)} Mo)")


def install_embeddable_python(python_dir: Path) -> None:
    """Fetch Windows embeddable CPython and enable site-packages + pip."""

    if python_dir.exists():
        shutil.rmtree(python_dir)
    python_dir.mkdir(parents=True)

    zip_path = python_dir / "python-embed.zip"
    _download(PYTHON_EMBED_URL, zip_path)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(python_dir)
    zip_path.unlink(missing_ok=True)

    # Enable import site in the ._pth file
    pth_files = list(python_dir.glob("python*._pth"))
    if not pth_files:
        raise SystemExit("Fichier python*._pth introuvable dans le Python embeddable.")
    pth = pth_files[0]
    text = pth.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        if line.strip().startswith("#import site"):
            lines.append("import site")
        else:
            lines.append(line)
    if "import site" not in lines:
        lines.append("import site")
    pth.write_text("\n".join(lines) + "\n", encoding="utf-8")

    get_pip = python_dir / "get-pip.py"
    _download(GET_PIP_URL, get_pip)
    print("Note: get-pip.py sera exécuté sur le PC Windows via install_offline.bat")
    (python_dir / "READY.txt").write_text(
        f"Python embeddable {PYTHON_VERSION} Windows amd64\n"
        "Sur le PC entreprise, lancez install_offline.bat\n",
        encoding="utf-8",
    )


def download_ollama_windows(ollama_dir: Path) -> None:
    """Download the latest Ollama Windows amd64 zip from GitHub releases."""

    if ollama_dir.exists():
        shutil.rmtree(ollama_dir)
    ollama_dir.mkdir(parents=True)

    api = "https://api.github.com/repos/ollama/ollama/releases/latest"
    req = Request(api, headers={"User-Agent": "safran-knowledge-assistant-usb-packager"})
    with urlopen(req, timeout=60) as response:
        release = json.loads(response.read().decode("utf-8"))

    asset_url = None
    asset_name = None
    # Prefer the standard CPU/CUDA Windows build, never the MLX or ROCm variants.
    preferred_names = (
        "ollama-windows-amd64.zip",
        "OllamaSetup.exe",  # fallback installer (less ideal)
    )
    assets = {a.get("name", ""): a for a in release.get("assets", [])}
    for name in preferred_names:
        if name in assets and name.endswith(".zip"):
            asset_url = assets[name].get("browser_download_url")
            asset_name = name
            break
    if not asset_url:
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            lower = name.lower()
            if (
                lower.startswith("ollama-windows-amd64")
                and lower.endswith(".zip")
                and "mlx" not in lower
                and "rocm" not in lower
            ):
                asset_url = asset.get("browser_download_url")
                asset_name = name
                break
    if not asset_url:
        tag = release.get("tag_name", "v0.6.5")
        asset_name = "ollama-windows-amd64.zip"
        asset_url = f"https://github.com/ollama/ollama/releases/download/{tag}/{asset_name}"

    zip_path = ollama_dir / (asset_name or "ollama-windows.zip")
    _download(asset_url, zip_path)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(ollama_dir)
    zip_path.unlink(missing_ok=True)

    # Normalize layout: ensure ollama.exe is directly under runtime/ollama/
    exe = ollama_dir / "ollama.exe"
    if not exe.is_file():
        found = list(ollama_dir.rglob("ollama.exe"))
        if found:
            target = ollama_dir / "ollama.exe"
            if found[0].resolve() != target.resolve():
                shutil.copy2(found[0], target)

    (ollama_dir / "READY.txt").write_text(
        "Ollama Windows extrait.\n"
        "Les poids de modèle doivent être dans runtime/ollama/models (via pack_usb.sh).\n",
        encoding="utf-8",
    )
    print(f"Ollama extrait dans {ollama_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Télécharger Python/Ollama Windows pour la clé USB.")
    parser.add_argument(
        "--bundle",
        type=Path,
        default=ROOT / "dist" / "safran-usb",
        help="Racine du bundle USB",
    )
    parser.add_argument("--with-ollama", action="store_true", help="Télécharger aussi Ollama Windows")
    parser.add_argument("--skip-python", action="store_true", help="Ne pas télécharger Python")
    parser.add_argument("--python-version-wheels", default="3.12", help="Version pour pip download")
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    bundle.mkdir(parents=True, exist_ok=True)

    if not args.skip_python:
        install_embeddable_python(bundle / "runtime" / "python")

    # Always refresh Windows wheels into the bundle
    sys.path.insert(0, str(ROOT))
    from scripts.download_windows_wheels import download_wheels

    download_wheels(bundle / "runtime" / "wheelhouse", args.python_version_wheels)

    if args.with_ollama:
        download_ollama_windows(bundle / "runtime" / "ollama")

    print()
    print("Runtime Windows prêt dans le bundle.")
    print(f"Dossier : {bundle}")
    print("Copiez ce dossier sur la clé USB, puis sur le PC entreprise lancez install_offline.bat")


if __name__ == "__main__":
    main()
