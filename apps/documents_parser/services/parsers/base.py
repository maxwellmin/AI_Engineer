"""
Base parser interface and data classes for document parsing.

This module defines the abstract base class that all document parsers
must implement, as well as the ParsedDocument data class for
standardized parsing results.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParsedDocument:
    """
    Represents a parsed document with extracted text and metadata.

    Attributes:
        content: The complete extracted text content.
        page_count: Total number of pages in the document.
        metadata: Additional metadata extracted from the document.
        pages: Optional list of content split by page.
    """

    content: str
    page_count: int
    metadata: dict[str, Any]
    pages: list[str] | None = None


class BaseParser(ABC):
    """
    Abstract base class for document parsers.

    All document parsers (PDF, DOCX, TXT) must inherit from this class
    and implement the parse method.
    """

    @abstractmethod
    def parse(self, *, file_path: Path) -> ParsedDocument:
        """
        Parse a document and extract its text content.

        Args:
            file_path: Path to the document file.

        Returns:
            ParsedDocument with extracted content and metadata.

        Raises:
            ParsingError: If parsing fails.
            FileCorruptedError: If the file is corrupted.
            EncodingDetectionError: If encoding detection fails (TXT only).
        """
        ...

    @classmethod
    @abstractmethod
    def supports_file_type(cls) -> str:
        """
        Return the file type this parser supports.

        Returns:
            File type string (e.g., "pdf", "docx", "txt").
        """
        ...
