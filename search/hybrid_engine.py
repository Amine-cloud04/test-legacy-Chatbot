"""Hybrid BM25 plus vector search with reciprocal rank fusion."""

from __future__ import annotations

from dataclasses import replace

from config import Settings
from db.database import Database
from db.models import SearchResult
from search.bm25_engine import BM25Engine
from search.vector_engine import VECTOR_AVAILABLE, VectorEngine


class HybridEngine:
    """Combine BM25 and vector results, falling back to BM25 when vectors are disabled."""

    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.bm25 = BM25Engine(settings, database)
        self.vector = VectorEngine(settings, database)

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        """Search and merge results using Reciprocal Rank Fusion."""

        if not self.settings.use_vector_search or not VECTOR_AVAILABLE:
            return self.bm25.search(query, top_k)
        bm25_results = self.bm25.search(query, top_k * 2)
        vector_results = self.vector.search(query, top_k * 2)
        fused: dict[int, SearchResult] = {}
        for result_set in (bm25_results, vector_results):
            for rank, result in enumerate(result_set, start=1):
                score = 1.0 / (60 + rank)
                if result.chunk_id in fused:
                    fused[result.chunk_id].score += score
                else:
                    fused[result.chunk_id] = replace(result, score=score)
        return sorted(fused.values(), key=lambda result: result.score, reverse=True)[:top_k]
