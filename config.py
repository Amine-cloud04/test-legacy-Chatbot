"""Application configuration for the Safran R&D Knowledge Assistant."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


DEFAULT_TECH_TERMS = (
    "radar",
    "avionics",
    "fpga",
    "uav",
    "imu",
    "gnss",
    "lidar",
    "computer vision",
    "embedded",
    "navigation",
    "sensor fusion",
    "machine learning",
    "ai",
    "electronics",
    "optronics",
    "inertial",
)


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables and an optional .env file."""

    sharepoint_url: str = ""
    sharepoint_username: str = ""
    sharepoint_password: str = ""
    sharepoint_library: str = ""
    local_docs_path: Path = Path("./sample_docs")
    db_path: Path = Path("./data/knowledge_base.db")
    index_path: Path = Path("./data/bm25_index.pkl")
    vector_index_path: Path = Path("./data/faiss.index")
    embedding_model_path: Path | None = None
    local_llm_path: Path | None = None
    max_chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 10
    rerank_top_k: int = 5
    use_vector_search: bool = False
    tech_terms: tuple[str, ...] = field(default_factory=lambda: DEFAULT_TECH_TERMS)

    @classmethod
    def from_env(cls, env_file: Path | str | None = ".env") -> "Settings":
        """Create settings from environment variables, loading env_file when present."""

        if env_file:
            load_dotenv(env_file)

        embedding_path = os.getenv("EMBEDDING_MODEL_PATH", "").strip()
        llm_path = os.getenv("LOCAL_LLM_PATH", "").strip()
        tech_terms = os.getenv("TECH_TERMS", "").strip()
        use_vector = os.getenv("USE_VECTOR_SEARCH", "false").lower() in {"1", "true", "yes", "on"}

        return cls(
            sharepoint_url=os.getenv("SHAREPOINT_URL", ""),
            sharepoint_username=os.getenv("SHAREPOINT_USERNAME", ""),
            sharepoint_password=os.getenv("SHAREPOINT_PASSWORD", ""),
            sharepoint_library=os.getenv("SHAREPOINT_LIBRARY", ""),
            local_docs_path=Path(os.getenv("LOCAL_DOCS_PATH", "./sample_docs")),
            db_path=Path(os.getenv("DB_PATH", "./data/knowledge_base.db")),
            index_path=Path(os.getenv("INDEX_PATH", "./data/bm25_index.pkl")),
            vector_index_path=Path(os.getenv("VECTOR_INDEX_PATH", "./data/faiss.index")),
            embedding_model_path=Path(embedding_path) if embedding_path else None,
            local_llm_path=Path(llm_path) if llm_path else None,
            max_chunk_size=int(os.getenv("MAX_CHUNK_SIZE", "512")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "64")),
            top_k=int(os.getenv("TOP_K", "10")),
            rerank_top_k=int(os.getenv("RERANK_TOP_K", "5")),
            use_vector_search=use_vector and bool(embedding_path),
            tech_terms=tuple(t.strip() for t in tech_terms.split(",") if t.strip()) or DEFAULT_TECH_TERMS,
        )


SHAREPOINT_URL = os.getenv("SHAREPOINT_URL", "")
SHAREPOINT_USERNAME = os.getenv("SHAREPOINT_USERNAME", "")
SHAREPOINT_PASSWORD = os.getenv("SHAREPOINT_PASSWORD", "")
SHAREPOINT_LIBRARY = os.getenv("SHAREPOINT_LIBRARY", "")
LOCAL_DOCS_PATH = Path(os.getenv("LOCAL_DOCS_PATH", "./sample_docs"))
DB_PATH = Path(os.getenv("DB_PATH", "./data/knowledge_base.db"))
INDEX_PATH = Path(os.getenv("INDEX_PATH", "./data/bm25_index.pkl"))
VECTOR_INDEX_PATH = Path(os.getenv("VECTOR_INDEX_PATH", "./data/faiss.index"))
EMBEDDING_MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH", "")
MAX_CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
TOP_K = 10
RERANK_TOP_K = 5
USE_VECTOR_SEARCH = False
