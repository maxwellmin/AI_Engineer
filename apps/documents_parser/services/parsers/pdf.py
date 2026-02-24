"""
PDF file parser implementation.

This module provides a parser for PDF files using pypdf library.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from apps.documents_parser.exceptions import FileCorruptedError, ParsingError
from apps.documents_parser.services.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """
    Parser for PDF files.

    Extracts text content from PDF files using pypdf library.
    Supports multi-page documents and preserves page information.
    """

    @classmethod
    def supports_file_type(cls) -> str:
        """Return the supported file type."""
        return "pdf"

    def parse(self, *, file_path: Path) -> ParsedDocument:
        """
        Parse a PDF file and extract its text content.

        Args:
            file_path: Path to the PDF file.

        Returns:
            ParsedDocument with extracted content and page information.

        Raises:
            FileCorruptedError: If the PDF file is corrupted or cannot be read.
            ParsingError: If parsing fails for other reasons (e.g., encrypted PDF).
        """
        logger.debug(f"Parsing PDF file: {file_path}")

        if not file_path.exists():
            raise FileCorruptedError(f"File not found: {file_path}")

        try:
            reader = PdfReader(str(file_path))
        except PdfReadError as e:
            logger.error(f"Failed to open PDF file {file_path}: {e}")
            raise FileCorruptedError(f"Failed to open PDF file: {file_path}") from e
        except OSError as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise FileCorruptedError(f"Failed to read file: {file_path}") from e

        # Check if PDF is encrypted
        if reader.is_encrypted:
            logger.error(f"PDF file is encrypted: {file_path}")
            raise ParsingError(f"PDF file is encrypted and cannot be parsed: {file_path}")

        page_count = len(reader.pages)
        logger.debug(f"PDF has {page_count} pages")

        pages: list[str] = []
        metadata: dict[str, Any] = {
            "page_count": page_count,
            "file_size": file_path.stat().st_size,
        }

        # Extract metadata from PDF
        if reader.metadata:
            pdf_meta = reader.metadata
            if pdf_meta.title:
                metadata["title"] = pdf_meta.title
            if pdf_meta.author:
                metadata["author"] = pdf_meta.author
            if pdf_meta.subject:
                metadata["subject"] = pdf_meta.subject
            if pdf_meta.creator:
                metadata["creator"] = pdf_meta.creator

        # Extract text from each page
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
                pages.append(page_text.strip())
                logger.debug(f"Extracted text from page {page_num}: {len(page_text)} chars")
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
                pages.append("")

        # Combine all pages
        full_content = "\n\n".join(page for page in pages if page)

        logger.info(f"Successfully parsed PDF file: {file_path} ({len(full_content)} chars, {page_count} pages)")

        return ParsedDocument(
            content=full_content,
            page_count=page_count,
            metadata=metadata,
            pages=pages,
        )
