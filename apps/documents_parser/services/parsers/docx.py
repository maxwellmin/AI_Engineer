"""
DOCX file parser implementation.

This module provides a parser for Microsoft Word documents (.docx)
using python-docx library.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from apps.documents_parser.exceptions import FileCorruptedError, ParsingError
from apps.documents_parser.services.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class DOCXParser(BaseParser):
    """
    Parser for Microsoft Word documents (.docx).

    Extracts text content from paragraphs and tables.
    Tables are converted to simple text format.
    """

    @classmethod
    def supports_file_type(cls) -> str:
        """Return the supported file type."""
        return "docx"

    def parse(self, *, file_path: Path) -> ParsedDocument:
        """
        Parse a DOCX file and extract its text content.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            ParsedDocument with extracted content.

        Raises:
            FileCorruptedError: If the DOCX file is corrupted or cannot be read.
            ParsingError: If parsing fails for other reasons.
        """
        logger.debug(f"Parsing DOCX file: {file_path}")

        if not file_path.exists():
            raise FileCorruptedError(f"File not found: {file_path}")

        try:
            document = Document(str(file_path))
        except PackageNotFoundError as e:
            logger.error(f"Invalid DOCX file {file_path}: {e}")
            raise FileCorruptedError(f"Invalid DOCX file: {file_path}") from e
        except Exception as e:
            logger.error(f"Failed to open DOCX file {file_path}: {e}")
            raise FileCorruptedError(f"Failed to open DOCX file: {file_path}") from e

        content_parts: list[str] = []
        metadata: dict[str, Any] = {
            "file_size": file_path.stat().st_size,
            "paragraph_count": 0,
            "table_count": 0,
        }

        # Extract core properties
        if document.core_properties:
            props = document.core_properties
            if props.title:
                metadata["title"] = props.title
            if props.author:
                metadata["author"] = props.author
            if props.subject:
                metadata["subject"] = props.subject

        # Extract text from paragraphs
        paragraph_count = 0
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                content_parts.append(text)
                paragraph_count += 1

        metadata["paragraph_count"] = paragraph_count
        logger.debug(f"Extracted {paragraph_count} paragraphs")

        # Extract text from tables
        table_count = 0
        for table in document.tables:
            table_text = self._extract_table_text(table)
            if table_text:
                content_parts.append(table_text)
                table_count += 1

        metadata["table_count"] = table_count
        logger.debug(f"Extracted {table_count} tables")

        # Combine all content
        full_content = "\n\n".join(content_parts)

        # Estimate page count (rough estimate: ~3000 chars per page)
        estimated_page_count = max(1, len(full_content) // 3000)

        logger.info(f"Successfully parsed DOCX file: {file_path} ({len(full_content)} chars)")

        return ParsedDocument(
            content=full_content,
            page_count=estimated_page_count,
            metadata=metadata,
        )

    def _extract_table_text(self, table) -> str:
        """
        Extract text from a table in a simple format.

        Args:
            table: docx table object.

        Returns:
            Formatted table text string.
        """
        rows_text: list[str] = []

        for row in table.rows:
            cells_text: list[str] = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    cells_text.append(cell_text)

            if cells_text:
                rows_text.append(" | ".join(cells_text))

        if not rows_text:
            return ""

        # Format as a simple table
        separator = "-" * 40
        return f"{separator}\n" + "\n".join(rows_text) + f"\n{separator}"
