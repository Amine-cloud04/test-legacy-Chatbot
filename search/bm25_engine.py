"""BM25 keyword search backed by rank_bm25."""

from __future__ import annotations

import logging
import pickle
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

from config import Settings
from db.database import Database
from db.models import SearchResult

logger = logging.getLogger(__name__)


class BM25Engine:
    """Build, persist, and query a BM25 index over stored chunks."""

    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.index: BM25Okapi | None = None
        self.chunk_ids: list[int] = []

    def build_index(self, chunks: list[str]) -> None:
        """Tokenise chunks, build BM25, and pickle the index with chunk ids."""

        records = self.database.get_all_chunks()
        self.chunk_ids = [record.id for record in records]
        corpus = [self._tokenise(chunk) for chunk in chunks]
        self.index = BM25Okapi(corpus) if corpus else None
        self.settings.index_path.parent.mkdir(parents=True, exist_ok=True)
        with self.settings.index_path.open("wb") as handle:
            pickle.dump({"index": self.index, "chunk_ids": self.chunk_ids}, handle)

    def load_index(self) -> bool:
        """Load a previously pickled BM25 index."""

        path = Path(self.settings.index_path)
        loaded = _load_bm25_index(path, path.stat().st_mtime_ns if path.exists() else 0)
        if loaded is None:
            logger.warning("BM25 index does not exist at %s", path)
            return False
        self.index, self.chunk_ids = loaded
        return self.index is not None

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        """Search the BM25 index and return enriched SearchResult objects."""

        if self.index is None and not self.load_index():
            return []
        if self.index is None:
            return []
        scores = self.index.get_scores(self._tokenise(query))
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:top_k]
        results: list[SearchResult] = []
        for index_position, score in ranked:
            if score <= 0 or index_position >= len(self.chunk_ids):
                continue
            row = self.database.fetchone(
                """
                SELECT c.id AS chunk_id, c.project_id, c.chunk_index, c.content, p.title, p.filename, p.date_modified
                FROM chunks c
                JOIN projects p ON p.id = c.project_id
                WHERE c.id = ?
                """,
                (self.chunk_ids[index_position],),
            )
            if row:
                results.append(
                    SearchResult(
                        chunk_id=int(row["chunk_id"]),
                        project_id=int(row["project_id"]),
                        chunk_index=int(row["chunk_index"]),
                        score=float(score),
                        content=str(row["content"]),
                        title=str(row["title"] or row["filename"]),
                        filename=str(row["filename"]),
                        date_modified=row["date_modified"],
                    )
                )
        return results

    def _tokenise(self, text: str) -> list[str]:
        return [token.strip(".,;:!?()[]{}\"'").lower() for token in text.split() if token.strip()]


@lru_cache(maxsize=8)
def _load_bm25_index(index_path: Path, mtime_ns: int) -> tuple[BM25Okapi | None, list[int]] | None:
    """Load the pickled BM25 index once per file version."""

    if not index_path.exists():
        return None
    try:
        with index_path.open("rb") as handle:
            payload = pickle.load(handle)
    except Exception as exc:  # pragma: no cover - defensive cache guard
        logger.warning("Could not read BM25 index %s: %s", index_path, exc)
        return None
    index = payload.get("index")
    chunk_ids = list(payload.get("chunk_ids") or [])
    return index, chunk_ids
