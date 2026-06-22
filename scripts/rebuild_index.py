"""Rebuild BM25 and optional vector indexes from the existing database."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings
from db.database import Database
from search.bm25_engine import BM25Engine
from search.vector_engine import VECTOR_AVAILABLE, VectorEngine


def main() -> None:
    """Rebuild available search indexes."""

    settings = Settings.from_env()
    with Database(settings.db_path) as database:
        database.init_schema()
        chunks = database.get_all_chunks()
        texts = [chunk.content for chunk in chunks]
        BM25Engine(settings, database).build_index(texts)
        if settings.use_vector_search and VECTOR_AVAILABLE:
            VectorEngine(settings, database).build_index(texts)
    print(f"Rebuilt indexes for {len(chunks)} chunks")


if __name__ == "__main__":
    main()
