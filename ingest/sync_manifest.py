"""Persist and load the last corpus sync metadata for offline review."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class SyncManifest:
    """Snapshot written after a successful folder or SharePoint sync."""

    synced_at: str
    source_path: str
    mode: str
    processed: int
    skipped: int
    failed: int
    projects: int = 0
    chunks: int = 0

    @classmethod
    def create(
        cls,
        *,
        source_path: Path | str,
        mode: str,
        processed: int,
        skipped: int,
        failed: int,
        projects: int = 0,
        chunks: int = 0,
    ) -> "SyncManifest":
        """Build a manifest stamped with the current UTC time."""

        return cls(
            synced_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            source_path=str(Path(source_path).resolve()),
            mode=mode,
            processed=processed,
            skipped=skipped,
            failed=failed,
            projects=projects,
            chunks=chunks,
        )


def default_manifest_path(db_path: Path) -> Path:
    """Place the manifest next to the SQLite database."""

    return Path(db_path).resolve().with_name("sync_manifest.json")


def write_manifest(path: Path, manifest: SyncManifest) -> Path:
    """Write manifest JSON to disk and return the path."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(manifest), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_manifest(path: Path) -> SyncManifest | None:
    """Load a sync manifest, or return None if missing/invalid."""

    path = Path(path)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return SyncManifest(
            synced_at=str(payload["synced_at"]),
            source_path=str(payload["source_path"]),
            mode=str(payload["mode"]),
            processed=int(payload.get("processed", 0)),
            skipped=int(payload.get("skipped", 0)),
            failed=int(payload.get("failed", 0)),
            projects=int(payload.get("projects", 0)),
            chunks=int(payload.get("chunks", 0)),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def format_manifest_caption(manifest: SyncManifest | None) -> str:
    """French one-line caption for the Streamlit sidebar."""

    if manifest is None:
        return "Dernière synchro dossier : jamais"
    when = manifest.synced_at.replace("T", " ").replace("+00:00", " UTC")
    label = "dossier local" if manifest.mode == "local_folder" else manifest.mode
    return f"Dernière synchro ({label}) : {when}"
