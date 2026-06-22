"""End-to-end ingestion pipeline for local folders and SharePoint libraries."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

from config import Settings
from db.database import Database
from ingest.extractors.base import ExtractedDocument
from ingest.extractors.docx_extractor import DOCXExtractor
from ingest.extractors.pdf_extractor import PDFExtractor
from ingest.extractors.pptx_extractor import PPTXExtractor
from ingest.sharepoint_client import SharePointClient
from search.bm25_engine import BM25Engine

logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx"}


@dataclass(slots=True)
class IngestSummary:
    """Counts emitted by a completed ingestion run."""

    processed: int = 0
    skipped: int = 0
    failed: int = 0


class IngestPipeline:
    """Ingest documents, chunk text, persist records, and rebuild the BM25 index."""

    def __init__(self, settings: Settings, database: Database | None = None) -> None:
        self.settings = settings
        self.database = database or Database(settings.db_path)
        self.extractors = {
            ".pdf": PDFExtractor(),
            ".docx": DOCXExtractor(),
            ".pptx": PPTXExtractor(),
        }

    def run(self, source: str = "local") -> IngestSummary:
        """Run ingestion from 'local' or 'sharepoint'."""

        self.database.init_schema()
        files = self._local_files() if source == "local" else self._sharepoint_files()
        summary = IngestSummary()
        for item in tqdm(files, desc="Ingesting documents"):
            try:
                filename, file_bytes, modified_date = item
                if not file_bytes:
                    summary.failed += 1
                    continue
                if self.database.project_exists(filename, modified_date):
                    summary.skipped += 1
                    continue
                extension = Path(filename).suffix.lower()
                extractor = self.extractors.get(extension)
                if extractor is None:
                    summary.skipped += 1
                    continue
                document = extractor.extract(file_bytes, filename)
                self._store_document(filename, extension, document, modified_date)
                summary.processed += 1
            except (OSError, ValueError, RuntimeError) as exc:
                logger.error("Failed to ingest %s: %s", item[0] if item else "unknown", exc)
                summary.failed += 1
        self._rebuild_bm25()
        logger.info("Ingestion complete: %s processed, %s skipped, %s failed", summary.processed, summary.skipped, summary.failed)
        return summary

    def _local_files(self) -> list[tuple[str, bytes, str]]:
        root = self.settings.local_docs_path
        if not root.exists():
            logger.warning("Local docs path does not exist: %s", root)
            return []
        files: list[tuple[str, bytes, str]] = []
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                try:
                    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
                    files.append((path.name, path.read_bytes(), modified))
                except OSError as exc:
                    logger.error("Could not read local file %s: %s", path, exc)
        return files

    def _sharepoint_files(self) -> list[tuple[str, bytes, str]]:
        client = SharePointClient(self.settings)
        file_urls = client.list_files(self.settings.sharepoint_library)
        files: list[tuple[str, bytes, str]] = []
        for file_url in file_urls:
            extension = Path(file_url).suffix.lower()
            if extension not in SUPPORTED_EXTENSIONS:
                continue
            file_bytes = client.download_file(file_url)
            files.append((Path(file_url).name, file_bytes, None or ""))
        return files

    def _store_document(self, filename: str, extension: str, document: ExtractedDocument, modified_date: str | None) -> None:
        metadata = document.metadata
        date_modified = str(metadata.get("date_modified") or modified_date or "")
        project_id = self.database.insert_project(
            filename=filename,
            title=document.title,
            raw_text=document.raw_text,
            author=str(metadata.get("author") or ""),
            date_created=str(metadata.get("date_created") or ""),
            date_modified=date_modified,
            file_type=extension.lstrip("."),
            word_count=int(metadata.get("word_count") or len(document.raw_text.split())),
            ingested_at=datetime.now(timezone.utc).isoformat(),
        )
        chunks = self.chunk_text(document.raw_text, self.settings.max_chunk_size, self.settings.chunk_overlap)
        self.database.insert_chunks(project_id, chunks)
        self.database.insert_keywords(project_id, self._keywords(document.raw_text))

    def chunk_text(self, text: str, max_size: int, overlap: int) -> list[str]:
        """Split text into overlapping word windows."""

        words = text.split()
        if not words:
            return []
        chunks: list[str] = []
        step = max(1, max_size - overlap)
        for start in range(0, len(words), step):
            chunk = " ".join(words[start : start + max_size])
            if chunk:
                chunks.append(chunk)
            if start + max_size >= len(words):
                break
        return chunks

    def _keywords(self, text: str, limit: int = 25) -> list[str]:
        counts: dict[str, int] = {}
        for token in (t.strip(".,;:!?()[]{}\"'").lower() for t in text.split()):
            if len(token) >= 4:
                counts[token] = counts.get(token, 0) + 1
        return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]

    def _rebuild_bm25(self) -> None:
        chunks = self.database.get_all_chunks()
        engine = BM25Engine(self.settings, self.database)
        engine.build_index([chunk.content for chunk in chunks])
