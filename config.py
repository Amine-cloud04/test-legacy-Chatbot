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

DEFAULT_EMBEDDING_MODELS = (
    "BAAI/bge-m3",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "intfloat/multilingual-e5-base",
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
    embedding_model_name: str = ""
    embedding_model_candidates: tuple[str, ...] = field(default_factory=lambda: DEFAULT_EMBEDDING_MODELS)
    local_llm_path: Path | None = None
    local_llm_service_url: str = "http://127.0.0.1:11434"
    local_llm_service_model: str = "llama3.2:3b"
    local_llm_backend: str = "ctransformers"
    local_llm_model_type: str = "mistral"
    local_llm_max_new_tokens: int = 320
    local_llm_context_chars: int = 6000
    local_llm_timeout: int = 60
    max_chunk_size: int = 640
    chunk_overlap: int = 100
    top_k: int = 20
    rerank_top_k: int = 5
    use_vector_search: bool = False
    tech_terms: tuple[str, ...] = field(default_factory=lambda: DEFAULT_TECH_TERMS)

    @classmethod
    def from_env(cls, env_file: Path | str | None = ".env") -> "Settings":
        """Create settings from environment variables, loading env_file when present."""

        if env_file:
            load_dotenv(env_file)

        embedding_path = os.getenv("EMBEDDING_MODEL_PATH", "").strip()
        embedding_name = os.getenv("EMBEDDING_MODEL_NAME", "").strip()
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
            embedding_model_name=embedding_name,
            embedding_model_candidates=(
                tuple(t.strip() for t in os.getenv("EMBEDDING_MODEL_CANDIDATES", "").split(",") if t.strip())
                or DEFAULT_EMBEDDING_MODELS
            ),
            local_llm_path=Path(llm_path) if llm_path else None,
            local_llm_service_url=os.getenv("LOCAL_LLM_SERVICE_URL", "").strip() or "http://127.0.0.1:11434",
            local_llm_service_model=os.getenv("LOCAL_LLM_SERVICE_MODEL", "llama3.2:3b"),
            local_llm_backend=os.getenv("LOCAL_LLM_BACKEND", "ctransformers"),
            local_llm_model_type=os.getenv("LOCAL_LLM_MODEL_TYPE", "mistral"),
            local_llm_max_new_tokens=int(os.getenv("LOCAL_LLM_MAX_NEW_TOKENS", "320")),
            local_llm_context_chars=int(os.getenv("LOCAL_LLM_CONTEXT_CHARS", "6000")),
            local_llm_timeout=int(os.getenv("LOCAL_LLM_TIMEOUT", "60")),
            max_chunk_size=int(os.getenv("MAX_CHUNK_SIZE", "640")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100")),
            top_k=int(os.getenv("TOP_K", "20")),
            rerank_top_k=int(os.getenv("RERANK_TOP_K", "5")),
            use_vector_search=use_vector and (bool(embedding_path) or bool(embedding_name)),
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
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "")
EMBEDDING_MODEL_CANDIDATES = DEFAULT_EMBEDDING_MODELS
LOCAL_LLM_PATH = os.getenv("LOCAL_LLM_PATH", "")
LOCAL_LLM_SERVICE_URL = os.getenv("LOCAL_LLM_SERVICE_URL", "http://127.0.0.1:11434")
LOCAL_LLM_SERVICE_MODEL = os.getenv("LOCAL_LLM_SERVICE_MODEL", "llama3.2:3b")
LOCAL_LLM_BACKEND = os.getenv("LOCAL_LLM_BACKEND", "ctransformers")
LOCAL_LLM_MODEL_TYPE = os.getenv("LOCAL_LLM_MODEL_TYPE", "mistral")
MAX_CHUNK_SIZE = 640
CHUNK_OVERLAP = 100
TOP_K = 20
RERANK_TOP_K = 5
USE_VECTOR_SEARCH = False
