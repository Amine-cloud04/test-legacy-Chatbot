"""Post-search reranking heuristics."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import re

from config import Settings
from db.models import SearchResult


class Ranker:
    """Apply recency and title-match boosts to search results."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        """Return top configured reranked results."""

        query_tokens = {token.lower() for token in re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9\-]+", query)}
        reranked: list[SearchResult] = []
        for result in results:
            score = result.score * (1 + 0.1 * self._recency_factor(result.date_modified))
            title_tokens = {token.lower() for token in re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9\-]+", result.title)}
            if query_tokens & title_tokens:
                score *= 1.2
            reranked.append(replace(result, score=score))
        return sorted(reranked, key=lambda result: result.score, reverse=True)[: self.settings.rerank_top_k]

    def _recency_factor(self, date_modified: str | None) -> float:
        if not date_modified:
            return 0.0
        try:
            modified = datetime.fromisoformat(date_modified.replace("Z", "+00:00"))
            if modified.tzinfo is None:
                modified = modified.replace(tzinfo=timezone.utc)
        except ValueError:
            return 0.0
        age_days = (datetime.now(timezone.utc) - modified).days
        if age_days <= 365 * 2:
            return 1.0
        if age_days <= 365 * 5:
            return 0.5
        return 0.0
