"""Common extractor interface and extracted document model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class ExtractedDocument:
    """Text and metadata extracted from one source document."""

    title: str
    raw_text: str
    metadata: dict[str, object] = field(default_factory=dict)
    sections: list[dict[str, str]] = field(default_factory=list)


class BaseExtractor(Protocol):
    """Common interface implemented by all document extractors."""

    def extract(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        """Extract text, metadata, and logical sections from a file."""
        ...
