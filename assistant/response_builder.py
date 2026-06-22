"""Build API/UI response dictionaries from ranked results."""

from __future__ import annotations

from config import Settings
from db.database import Database
from db.models import SearchResult
from assistant.summariser import Summariser


class ResponseBuilder:
    """Assemble final user-facing response payloads."""

    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.summariser = Summariser(settings)

    def build(self, query: str, results: list[SearchResult], query_keywords: list[str]) -> dict[str, object]:
        """Build the final response dictionary including gap analysis."""

        max_score = max((result.score for result in results), default=1.0)
        output_results: list[dict[str, object]] = []
        seen_keywords: set[str] = set()
        for rank, result in enumerate(results, start=1):
            project = self.database.get_project(result.project_id)
            source_text = project.raw_text if project else result.content
            summary = self.summariser.summarise(source_text, query_keywords)
            keywords = list(summary["keywords"])
            seen_keywords.update(keywords)
            output_results.append(
                {
                    "rank": rank,
                    "title": result.title,
                    "filename": result.filename,
                    "date_modified": result.date_modified,
                    "relevance_score": round(result.score / max_score, 3) if max_score else 0.0,
                    "summary": summary["summary"],
                    "keywords": keywords,
                    "technologies": summary["technologies"],
                    "matching_excerpt": result.content,
                }
            )
        missing = [keyword for keyword in query_keywords if keyword not in seen_keywords]
        gap = "No previous projects found covering: none."
        if missing:
            gap = f"No previous projects found covering: {', '.join(missing)}. These may represent research gaps."
        return {"query": query, "total_results": len(output_results), "results": output_results, "gap_analysis": gap}
