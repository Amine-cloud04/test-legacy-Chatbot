"""CLI for ingesting documents from a local folder."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from db.database import Database
from ingest.pipeline import IngestPipeline

logger = logging.getLogger(__name__)


def main() -> None:
    """Parse CLI arguments and run local ingestion."""

    parser = argparse.ArgumentParser(description="Ingest local documents into the knowledge base.")
    parser.add_argument("--path", type=Path, default=None, help="Folder containing PDF, DOCX, and PPTX files.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the database before ingesting.")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.path:
        settings.local_docs_path = args.path
    with Database(settings.db_path) as database:
        database.init_schema()
        if args.reset:
            database.reset()
        summary = IngestPipeline(settings, database).run("local")
    print(f"processed\tskipped\tfailed\n{summary.processed}\t{summary.skipped}\t{summary.failed}")


if __name__ == "__main__":
    main()
