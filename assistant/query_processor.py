"""Rule-based query parsing with no runtime downloads."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from config import Settings


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "before", "by", "for", "from", "in", "is",
    "of", "on", "or", "show", "the", "to", "what", "which", "with", "about", "after",
}


@dataclass(slots=True)
class ParsedQuery:
    """Structured representation of a user search query."""

    raw_query: str
    keywords: list[str] = field(default_factory=list)
    date_filters: dict[str, str] = field(default_factory=dict)
    technology_terms: list[str] = field(default_factory=list)


class QueryProcessor:
    """Extract keywords, simple date filters, and technology terms from queries."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def parse(self, query: str) -> ParsedQuery:
        """Parse a natural language query into structured filters."""

        tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]+", query.lower())
        keywords = [token for token in tokens if token not in STOPWORDS and len(token) > 1]
        date_filters: dict[str, str] = {}
        for pattern, key in ((r"before\s+(\d{4})", "before"), (r"after\s+(\d{4})", "after"), (r"in\s+(\d{4})", "in")):
            match = re.search(pattern, query.lower())
            if match:
                date_filters[key] = match.group(1)
        lower_query = query.lower()
        technologies = [term for term in self.settings.tech_terms if term.lower() in lower_query]
        return ParsedQuery(raw_query=query, keywords=keywords, date_filters=date_filters, technology_terms=technologies)
