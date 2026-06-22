"""Optional local vector search backed by sentence-transformers and FAISS."""

from __future__ import annotations

import logging
from pathlib import Path

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
        if self.settings.embedding_model_path is None or not self.settings.embedding_model_path.exists():
            logger.warning("Embedding model path is not configured or unavailable")
            return False
        if self.model is None:
            self.model = SentenceTransformer(str(self.settings.embedding_model_path))
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
        ids_path = Path(str(index_path) + ".chunk_ids.npy")
        if not index_path.exists() or not ids_path.exists():
            logger.warning("Vector index is missing")
            return []
        index = faiss.read_index(str(index_path))
        self.chunk_ids = [int(x) for x in np.load(ids_path)]
        query_embedding = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        scores, positions = index.search(query_embedding, top_k)
        results: list[SearchResult] = []
        for score, position in zip(scores[0], positions[0]):
            if position < 0 or position >= len(self.chunk_ids):
                continue
            row = self.database.fetchone(
                """
                SELECT c.id AS chunk_id, c.project_id, c.content, p.title, p.filename, p.date_modified
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
                        score=float(score),
                        content=str(row["content"]),
                        title=str(row["title"] or row["filename"]),
                        filename=str(row["filename"]),
                        date_modified=row["date_modified"],
                    )
                )
        return results
