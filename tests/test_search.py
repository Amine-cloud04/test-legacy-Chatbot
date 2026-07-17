"""Search engine tests."""

from __future__ import annotations

from datetime import datetime, timezone

from config import Settings
from db.database import Database
from search.bm25_engine import BM25Engine


def test_bm25_ranks_most_relevant_chunk_first(tmp_path):
    settings = Settings(db_path=tmp_path / "kb.db", index_path=tmp_path / "bm25.pkl")
    with Database(settings.db_path) as database:
        database.init_schema()
        project_id = database.insert_project(
            "radar.docx", "Radar FPGA Project", "", "", "", datetime.now(timezone.utc).isoformat(), "docx", 10, datetime.now(timezone.utc).isoformat()
        )
        chunks = [
            "radar radar fpga signal processing",
            "coffee logistics meeting notes",
            "uav navigation sensors",
            "thermal camera tests",
            "mechanical bracket analysis",
        ]
        database.insert_chunks(project_id, chunks)
        engine = BM25Engine(settings, database)
        engine.build_index(chunks)
        results = engine.search("radar fpga", 3)
    assert results
    assert results[0].content == "radar radar fpga signal processing"
    assert results[0].chunk_index == 0
