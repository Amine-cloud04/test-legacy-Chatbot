"""Optional local vector search backed by sentence-transformers and FAISS."""

from __future__ import annotations

import logging
from pathlib import Path
from functools import lru_cache

import numpy as np

from config import Settings
from db.database import Database
from db.models import SearchResult

logger = logging.getLogger(__name__)

try:
    import faiss
    from sentence_transformers import SentenceTransformer

    VECTOR_AVAILABLE = True
except ImportError:
    faiss = None
    SentenceTransformer = None
    VECTOR_AVAILABLE = False


class VectorEngine:
    """Build and query a local FAISS vector index when optional dependencies exist."""

    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.model = None
        self.chunk_ids: list[int] = []

    def _load_model(self) -> bool:
        if not VECTOR_AVAILABLE:
            logger.warning("Vector search dependencies are unavailable")
            return False
        model = _get_sentence_transformer(self.settings.embedding_model_path, self.settings.embedding_model_name, self.settings.embedding_model_candidates)
        if model is None:
            logger.warning("Embedding model is not available locally")
            return False
        self.model = model
        return True

    def build_index(self, chunks: list[str]) -> None:
        """Encode chunks and save a FAISS inner-product index."""

        if not self._load_model() or not chunks:
            return
        embeddings = self.model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        self.settings.vector_index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(self.settings.vector_index_path))
        self.chunk_ids = [record.id for record in self.database.get_all_chunks()]
        np.save(str(self.settings.vector_index_path) + ".chunk_ids.npy", np.array(self.chunk_ids, dtype=np.int64))

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        """Search the FAISS index, returning an empty list when vectors are disabled."""

        if not self._load_model():
            return []
        index_path = Path(self.settings.vector_index_path)
        index_data = _load_vector_index(index_path, index_path.stat().st_mtime_ns if index_path.exists() else 0)
        if index_data is None:
            logger.warning("Vector index is missing")
            return []
        index, self.chunk_ids = index_data
        query_embedding = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        scores, positions = index.search(query_embedding, top_k)
        results: list[SearchResult] = []
        for score, position in zip(scores[0], positions[0]):
            if position < 0 or position >= len(self.chunk_ids):
                continue
            row = self.database.fetchone(
                """
                SELECT c.id AS chunk_id, c.project_id, c.chunk_index, c.content, p.title, p.filename, p.date_modified
                FROM chunks c JOIN projects p ON p.id = c.project_id
                WHERE c.id = ?
                """,
                (self.chunk_ids[int(position)],),
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


@lru_cache(maxsize=2)
def _get_sentence_transformer(
    embedding_model_path: Path | None,
    embedding_model_name: str,
    embedding_model_candidates: tuple[str, ...],
):
    """Load one multilingual embedding model once per process."""

    if embedding_model_path is not None and embedding_model_path.exists():
        try:
            return SentenceTransformer(str(embedding_model_path))
        except Exception as exc:  # pragma: no cover - defensive cache guard
            logger.warning("Could not load embedding model path %s: %s", embedding_model_path, exc)
            return None

    candidates = [embedding_model_name] if embedding_model_name else []
    candidates.extend(candidate for candidate in embedding_model_candidates if candidate and candidate not in candidates)
    for candidate in candidates:
        try:
            return SentenceTransformer(candidate)
        except Exception as exc:
            logger.info("Embedding candidate %s unavailable locally: %s", candidate, exc)
    return None


@lru_cache(maxsize=8)
def _load_vector_index(index_path: Path, mtime_ns: int) -> tuple[object, list[int]] | None:
    """Load the FAISS index and chunk ids once per file version."""

    ids_path = Path(str(index_path) + ".chunk_ids.npy")
    if not index_path.exists() or not ids_path.exists():
        return None
    try:
        index = faiss.read_index(str(index_path))
        chunk_ids = [int(x) for x in np.load(ids_path)]
    except Exception as exc:  # pragma: no cover - defensive cache guard
        logger.warning("Could not read vector index %s: %s", index_path, exc)
        return None
    return index, chunk_ids
