"""End-to-end ingestion pipeline for local folders and SharePoint libraries."""

from __future__ import annotations

import logging
import sqlite3
import re
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
                extension = Path(filename).suffix.lower()
                extractor = self.extractors.get(extension)
                if extractor is None:
                    summary.skipped += 1
                    continue
                document = extractor.extract(file_bytes, filename)
                if self._store_document(filename, extension, document, modified_date):
                    summary.processed += 1
                else:
                    summary.skipped += 1
            except (OSError, ValueError, RuntimeError, sqlite3.DatabaseError) as exc:
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

    def _store_document(self, filename: str, extension: str, document: ExtractedDocument, modified_date: str | None) -> bool:
        metadata = document.metadata
        date_modified = str(metadata.get("date_modified") or modified_date or "")
        if self.database.project_exists(filename, date_modified):
            return False
        try:
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
            chunks = self.chunk_document(document, filename, self.settings.max_chunk_size, self.settings.chunk_overlap)
            self.database.insert_chunks(project_id, chunks)
            self.database.insert_keywords(project_id, self._keywords(document.raw_text))
        except sqlite3.IntegrityError:
            logger.info("Skipping duplicate document %s with modified date %s", filename, date_modified)
            return False
        return True

    def chunk_document(self, document: ExtractedDocument, filename: str, max_size: int, overlap: int) -> list[str]:
        """Split a document into metadata-rich overlapping character chunks."""

        chunks: list[str] = []
        for section_index, section in enumerate(document.sections or [{"heading": "Document", "content": document.raw_text}]):
            heading = str(section.get("heading") or "Document").strip()
            content = str(section.get("content") or "").strip()
            if not content:
                continue
            for chunk_index, chunk_body in enumerate(self._chunk_text(content, max_size, overlap)):
                metadata_line = self._chunk_metadata_line(
                    filename=filename,
                    title=document.title,
                    section=heading,
                    section_index=section_index,
                    chunk_index=chunk_index,
                    document=document,
                )
                chunks.append(f"{metadata_line}\n{chunk_body}".strip())
        if chunks:
            return chunks
        fallback = document.raw_text.strip()
        if not fallback:
            return []
        metadata_line = self._chunk_metadata_line(
            filename=filename,
            title=document.title,
            section="Document",
            section_index=0,
            chunk_index=0,
            document=document,
        )
        return [f"{metadata_line}\n{fallback}".strip()]

    def _chunk_text(self, text: str, max_size: int, overlap: int) -> list[str]:
        """Split text into overlapping character windows on sentence boundaries when possible."""

        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []
        if len(text) <= max_size:
            return [text]

        chunks: list[str] = []
        start = 0
        text_length = len(text)
        overlap = max(0, min(overlap, max_size - 1))
        step = max(1, max_size - overlap)
        while start < text_length:
            end = min(text_length, start + max_size)
            if end < text_length:
                pivot = max(start + max_size // 2, start + 1)
                candidates = [text.rfind(sep, start + 1, end) for sep in (". ", "! ", "? ", "\n", "; ", " - ")]
                split_at = max((candidate for candidate in candidates if candidate > pivot), default=-1)
                if split_at > start:
                    end = split_at + 1
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= text_length:
                break
            start = max(0, end - overlap)
            if start >= text_length:
                break
            if step and end - start < 10:
                start = min(text_length, start + step)
        return chunks

    def _chunk_metadata_line(
        self,
        filename: str,
        title: str,
        section: str,
        section_index: int,
        chunk_index: int,
        document: ExtractedDocument,
    ) -> str:
        """Return a compact provenance line for a stored chunk."""

        page_count = document.metadata.get("page_count")
        slide_count = document.metadata.get("slide_count")
        page_hint = ""
        if section.lower().startswith("page "):
            page_hint = f"Page {section.split()[-1]}"
        elif slide_count:
            page_hint = f"Slide {section_index + 1}"
        elif page_count:
            page_hint = f"Page {section_index + 1}"
        provenance = [f"Source: {filename}", f"Titre: {title or filename}", f"Section: {section}"]
        if page_hint:
            provenance.append(page_hint)
        provenance.append(f"Chunk: {chunk_index + 1}")
        return "[" + " | ".join(provenance) + "]"

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
