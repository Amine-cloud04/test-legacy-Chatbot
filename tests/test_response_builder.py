"""Response builder tests."""

from __future__ import annotations

from datetime import datetime, timezone

from assistant.response_builder import ResponseBuilder
from assistant.query_processor import QueryProcessor
from config import Settings
from db.database import Database
from db.models import SearchResult


def test_response_builder_returns_answer_sources_and_evidence(tmp_path):
    settings = Settings(db_path=tmp_path / "kb.db", index_path=tmp_path / "bm25.pkl")
    now = datetime.now(timezone.utc).isoformat()
    with Database(settings.db_path) as database:
        database.init_schema()
        project_id = database.insert_project(
            "radar.docx",
            "Radar FPGA Project",
            "The radar project used FPGA signal processing for embedded detection.",
            "",
            "",
            now,
            "docx",
            9,
            now,
        )
        chunk_id = database.insert_chunks(
            project_id,
            ["The radar project used FPGA signal processing for embedded detection."],
        )[0]
        result = SearchResult(
            chunk_id=chunk_id,
            project_id=project_id,
            chunk_index=0,
            score=2.5,
            content="The radar project used FPGA signal processing for embedded detection.",
            title="Radar FPGA Project",
            filename="radar.docx",
            date_modified=now,
        )
        response = ResponseBuilder(settings, database).build("radar FPGA", [result], ["radar", "fpga"])

    assert response["answer"]
    assert response["confidence"] in {"medium", "high"}
    assert response["answer_provider"] in {"extractive", "remote-llm:llama3.2:3b"}
    assert response["sources"][0]["filename"] == "radar.docx"
    assert response["results"][0]["source_ref"] == "radar.docx, chunk 1"


def test_query_processor_filters_french_interrogatives():
    settings = Settings()
    parsed = QueryProcessor(settings).parse("Quels sont les risques principaux pour la navigation UAV ?")
    assert "quels" not in parsed.keywords
    assert "sont" not in parsed.keywords
    assert "risques" not in parsed.keywords
    assert "navigation" in parsed.keywords
    assert "uav" in parsed.keywords
