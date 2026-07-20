"""Sync a local SharePoint/OneDrive folder into the offline knowledge base.

Primary workflow for company PCs where SharePoint is opened in the browser
(SSO). Sync the library to a local folder (OneDrive Sync or Download), then
run this script. Review mode never needs SharePoint credentials.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from db.database import Database
from ingest.pipeline import IngestPipeline
from ingest.sync_manifest import SyncManifest, default_manifest_path, write_manifest


def main() -> None:
    """Ingest a local folder and write data/sync_manifest.json."""

    parser = argparse.ArgumentParser(
        description=(
            "Index documents from a local folder (e.g. OneDrive-synced SharePoint library) "
            "and write a sync manifest for offline review."
        )
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Folder containing PDF, DOCX, and PPTX files (defaults to LOCAL_DOCS_PATH).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the database before ingesting.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Env file to load (defaults to SAFRAN_ENV_FILE or .env).",
    )
    args = parser.parse_args()

    settings = Settings.from_env(args.env_file)
    if args.path is not None:
        settings.local_docs_path = args.path

    source = Path(settings.local_docs_path)
    if not source.is_dir():
        print(f"Source folder does not exist: {source}")
        print("Sync or download the SharePoint library on your company PC, then pass --path.")
        raise SystemExit(2)

    with Database(settings.db_path) as database:
        database.init_schema()
        if args.reset:
            database.reset()
        summary = IngestPipeline(settings, database).run("local")
        stats = database.stats()

    manifest = SyncManifest.create(
        source_path=source,
        mode="local_folder",
        processed=summary.processed,
        skipped=summary.skipped,
        failed=summary.failed,
        projects=int(stats["projects"]),
        chunks=int(stats["chunks"]),
    )
    manifest_path = settings.sync_manifest_path or default_manifest_path(settings.db_path)
    write_manifest(manifest_path, manifest)

    print(f"processed\tskipped\tfailed\n{summary.processed}\t{summary.skipped}\t{summary.failed}")
    print(f"manifest\t{manifest_path}")
    print(f"synced_at\t{manifest.synced_at}")
    print(f"source\t{manifest.source_path}")


if __name__ == "__main__":
    main()
