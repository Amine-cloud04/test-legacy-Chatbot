"""Shared database and search data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProjectRecord:
    """A document-level record stored in SQLite."""

    id: int
    filename: str
    title: str
    raw_text: str
    author: str | None
    date_created: str | None
    date_modified: str | None
    file_type: str
    word_count: int
    ingested_at: str


@dataclass(slots=True)
class ChunkRecord:
    """A chunk-level record stored in SQLite."""

    id: int
    project_id: int
    chunk_index: int
    content: str


@dataclass(slots=True)
class SearchResult:
    """A ranked result returned by search engines."""

    chunk_id: int
    project_id: int
    score: float
    content: str
    title: str
    filename: str
    date_modified: str | None = None
