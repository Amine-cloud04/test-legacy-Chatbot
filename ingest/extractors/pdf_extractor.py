"""PDF text extraction using pdfminer.six."""

from __future__ import annotations

import logging
from io import BytesIO

from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFSyntaxError

from ingest.extractors.base import ExtractedDocument

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDF documents page by page."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        """Extract text and simple heading sections from a PDF file."""

        sections: list[dict[str, str]] = []
        page_texts: list[str] = []
        page_number = 0
        while True:
            try:
                text = extract_text(BytesIO(file_bytes), page_numbers=[page_number]) or ""
            except (PDFSyntaxError, ValueError, TypeError) as exc:
                logger.warning("Could not extract page %s from %s: %s", page_number + 1, filename, exc)
                if page_number == 0:
                    return ExtractedDocument(title=filename, raw_text="", metadata=self._metadata(0, ""), sections=[])
                break
            if not text and page_number > 0:
                break
            if not text.strip():
                logger.warning("Skipping image-only or empty page %s in %s", page_number + 1, filename)
            else:
                page_texts.append(text.strip())
            page_number += 1
            if page_number > 5000:
                logger.warning("Stopped PDF extraction for %s after 5000 pages", filename)
                break

        raw_text = "\n\n".join(page_texts)
        sections = self._detect_sections(raw_text)
        return ExtractedDocument(title=filename, raw_text=raw_text, metadata=self._metadata(page_number, raw_text), sections=sections)

    def _metadata(self, page_count: int, raw_text: str) -> dict[str, object]:
        return {
            "author": None,
            "date_created": None,
            "date_modified": None,
            "page_count": page_count,
            "slide_count": None,
            "word_count": len(raw_text.split()),
        }

    def _detect_sections(self, raw_text: str) -> list[dict[str, str]]:
        sections: list[dict[str, str]] = []
        heading = "Document"
        buffer: list[str] = []
        lines = raw_text.splitlines()
        for index, line in enumerate(lines):
            stripped = line.strip()
            next_blank = index + 1 < len(lines) and not lines[index + 1].strip()
            is_heading = bool(stripped) and ((stripped.isupper() and len(stripped.split()) <= 12) or (next_blank and len(stripped.split()) <= 8))
            if is_heading and buffer:
                sections.append({"heading": heading, "content": "\n".join(buffer).strip()})
                heading = stripped
                buffer = []
            elif is_heading:
                heading = stripped
            elif stripped:
                buffer.append(stripped)
        if buffer:
            sections.append({"heading": heading, "content": "\n".join(buffer).strip()})
        return sections or [{"heading": "Document", "content": raw_text}]
