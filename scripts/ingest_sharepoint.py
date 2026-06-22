"""CLI for ingesting documents from SharePoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from db.database import Database
from ingest.sharepoint_client import SharePointClient
from ingest.pipeline import IngestPipeline


def main() -> None:
    """Run SharePoint ingestion."""

    parser = argparse.ArgumentParser(description="Ingest configured SharePoint library.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the database before ingesting.")
    parser.add_argument("--check", action="store_true", help="Only test the SharePoint connection and list a few files.")
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.check:
        client = SharePointClient(settings)
        files = client.list_files(settings.sharepoint_library)
        print(f"Connected. Found {len(files)} files in {settings.sharepoint_library}.")
        for file_url in files[:10]:
            print(file_url)
        return
    with Database(settings.db_path) as database:
        database.init_schema()
        if args.reset:
            database.reset()
        summary = IngestPipeline(settings, database).run("sharepoint")
    print(f"processed\tskipped\tfailed\n{summary.processed}\t{summary.skipped}\t{summary.failed}")


if __name__ == "__main__":
    main()
