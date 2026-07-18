"""Build API/UI response dictionaries from ranked results."""

from __future__ import annotations

from config import Settings
from db.database import Database
from db.models import SearchResult
from assistant.answer_generator import AnswerGenerator
from assistant.summariser import Summariser
from typing import Callable
import re


class ResponseBuilder:
    """Assemble final user-facing response payloads."""

    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.summariser = Summariser(settings)
        self.answer_generator = AnswerGenerator(settings)

    def build(
        self,
        query: str,
        results: list[SearchResult],
        query_keywords: list[str],
        on_chunk: Callable[[str], None] | None = None,
    ) -> dict[str, object]:
        """Build the final response dictionary including gap analysis."""

        max_score = max((result.score for result in results), default=1.0)
        generated_answer = self.answer_generator.generate(query, results, query_keywords, on_chunk=on_chunk)
        output_results: list[dict[str, object]] = []
        seen_keywords: set[str] = set()
        seen_tokens: set[str] = set()
        for rank, result in enumerate(results, start=1):
            project = self.database.get_project(result.project_id)
            source_text = project.raw_text if project else result.content
            summary = self.summariser.summarise(source_text, query_keywords)
            keywords = list(summary["keywords"])
            seen_keywords.update(keywords)
            seen_tokens.update(self._token_set(source_text))
            output_results.append(
                {
                    "rank": rank,
                    "title": result.title,
                    "filename": result.filename,
                    "date_modified": result.date_modified,
                    "relevance_score": round(result.score / max_score, 3) if max_score else 0.0,
                    "source_ref": f"{result.filename}, chunk {result.chunk_index + 1}",
                    "summary": summary["summary"],
                    "keywords": keywords,
                    "technologies": summary["technologies"],
                    "matching_excerpt": result.content,
                }
            )
        missing = [keyword for keyword in query_keywords if keyword.lower() not in seen_keywords and keyword.lower() not in seen_tokens]
        gap = "Aucun projet antérieur ne couvre : aucun terme."
        if missing:
            gap = f"Aucun projet antérieur ne couvre : {', '.join(missing)}. Ces termes peuvent révéler des écarts de recherche."
        sources = self._sources(results)
        return {
            "query": query,
            "answer": generated_answer.answer,
            "confidence": generated_answer.confidence,
            "limitations": generated_answer.limitations,
            "answer_provider": generated_answer.provider,
            "total_results": len(output_results),
            "sources": sources,
            "results": output_results,
            "gap_analysis": gap,
        }

    def _sources(self, results: list[SearchResult]) -> list[dict[str, object]]:
        sources: dict[int, dict[str, object]] = {}
        for result in results:
            source = sources.setdefault(
                result.project_id,
                {
                    "title": result.title,
                    "filename": result.filename,
                    "date_modified": result.date_modified,
                    "chunks": [],
                },
            )
            source["chunks"].append(result.chunk_index + 1)
        for source in sources.values():
            source["chunks"] = sorted(set(source["chunks"]))
        return list(sources.values())

    def _token_set(self, text: str) -> set[str]:
        """Return a normalized token set for gap analysis."""

        return {
            token.lower()
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]+", text)
            if len(token) > 1
        }
