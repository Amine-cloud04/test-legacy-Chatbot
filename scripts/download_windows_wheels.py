"""Download Windows wheels into a local wheelhouse (run on personal PC with internet)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def download_wheels(wheelhouse: Path, python_version: str = "3.12") -> None:
    """Download win_amd64 binary wheels for requirements-usb.txt plus pip tooling."""

    wheelhouse.mkdir(parents=True, exist_ok=True)
    requirements = ROOT / "requirements-usb.txt"
    if not requirements.is_file():
        raise SystemExit(f"Missing {requirements}")

    py_ver = python_version if "." in python_version else f"{python_version[0]}.{python_version[1:]}"
    abi = f"cp{py_ver.replace('.', '')}"

    base = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "-d",
        str(wheelhouse),
        "--platform",
        "win_amd64",
        "--python-version",
        py_ver,
        "--implementation",
        "cp",
        "--abi",
        abi,
        "--only-binary=:all:",
    ]

    print("Downloading pip/setuptools/wheel for offline get-pip...")
    subprocess.check_call([*base, "pip", "setuptools", "wheel"])

    print("Downloading application requirements...")
    subprocess.check_call([*base, "-r", str(requirements)])
    count = len(list(wheelhouse.glob("*.whl"))) + len(list(wheelhouse.glob("*.tar.gz")))
    print(f"Wheelhouse: {count} fichier(s) dans {wheelhouse}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Télécharger les dépendances Windows hors ligne.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "safran-usb" / "runtime" / "wheelhouse",
        help="Dossier wheelhouse",
    )
    parser.add_argument("--python-version", default="3.12")
    args = parser.parse_args()
    download_wheels(args.output, args.python_version)


if __name__ == "__main__":
    main()
