"""CLI for ingesting documents from SharePoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from db.database import Database
from ingest.pipeline import IngestPipeline
from ingest.sharepoint_client import SharePointClient
from ingest.sync_manifest import SyncManifest, default_manifest_path, write_manifest


def missing_sharepoint_settings(settings: Settings) -> list[str]:
    """Return missing SharePoint environment variable names."""

    missing: list[str] = []
    if not settings.sharepoint_url:
        missing.append("SHAREPOINT_URL")
    if not settings.sharepoint_username:
        missing.append("SHAREPOINT_USERNAME")
    if not settings.sharepoint_password:
        missing.append("SHAREPOINT_PASSWORD")
    if not settings.sharepoint_library:
        missing.append("SHAREPOINT_LIBRARY")
    return missing


def main() -> None:
    """Run SharePoint ingestion."""

    parser = argparse.ArgumentParser(description="Ingest configured SharePoint library.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the database before ingesting.")
    parser.add_argument("--check", action="store_true", help="Only test the SharePoint connection and list a few files.")
    args = parser.parse_args()
    settings = Settings.from_env()
    missing = missing_sharepoint_settings(settings)
    if missing:
        print("Missing SharePoint configuration values:")
        for name in missing:
            print(f"- {name}")
        print("\nCreate a .env file from .env.example and fill in these values.")
        raise SystemExit(2)
    if args.check:
        client = SharePointClient(settings)
        files = client.list_files(settings.sharepoint_library)
        if not files:
            print(f"Connected, but found 0 files in {settings.sharepoint_library}.")
            print("Check the library name, permissions, or whether the library contains supported documents.")
            return
        print(f"Connected. Found {len(files)} files in {settings.sharepoint_library}.")
        for file_url in files[:10]:
            print(file_url)
        return
    with Database(settings.db_path) as database:
        database.init_schema()
        if args.reset:
            database.reset()
        summary = IngestPipeline(settings, database).run("sharepoint")
        stats = database.stats()

    manifest = SyncManifest.create(
        source_path=settings.sharepoint_url or "sharepoint",
        mode="sharepoint",
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


if __name__ == "__main__":
    main()
