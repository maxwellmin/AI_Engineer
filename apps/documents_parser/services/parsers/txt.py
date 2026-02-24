"""
TXT file parser implementation.

This module provides a parser for plain text files with automatic
encoding detection using chardet.
"""

from __future__ import annotations

import logging
from pathlib import Path

import chardet

from apps.documents_parser.exceptions import (
    EncodingDetectionError,
    FileCorruptedError,
    ParsingError,
)
from apps.documents_parser.services.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class TXTParser(BaseParser):
    """
    Parser for plain text files.

    Supports automatic encoding detection for various encodings
    including UTF-8, GBK, GB2312, and Latin-1.
    """

    # Common encodings to try if auto-detection fails
    FALLBACK_ENCODINGS: list[str] = ["utf-8", "gbk", "gb2312", "latin-1"]

    @classmethod
    def supports_file_type(cls) -> str:
        """Return the supported file type."""
        return "txt"

    def parse(self, *, file_path: Path) -> ParsedDocument:
        """
        Parse a text file and extract its content.

        Args:
            file_path: Path to the text file.

        Returns:
            ParsedDocument with the file content.

        Raises:
            FileCorruptedError: If the file cannot be read.
            EncodingDetectionError: If encoding detection fails.
            ParsingError: If parsing fails for other reasons.
        """
        logger.debug(f"Parsing TXT file: {file_path}")

        if not file_path.exists():
            raise FileCorruptedError(f"File not found: {file_path}")

        try:
            raw_content = file_path.read_bytes()
        except OSError as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise FileCorruptedError(f"Failed to read file: {file_path}") from e

        if not raw_content:
            # Empty file
            logger.debug(f"Empty file: {file_path}")
            return ParsedDocument(
                content="",
                page_count=1,
                metadata={"file_size": 0, "encoding": "utf-8"},
            )

        # Detect encoding
        encoding = self._detect_encoding(raw_content)
        logger.debug(f"Detected encoding: {encoding}")

        # Decode content
        try:
            content = raw_content.decode(encoding)
        except UnicodeDecodeError as e:
            logger.warning(f"Failed to decode with {encoding}, trying fallbacks: {e}")
            content = self._decode_with_fallbacks(raw_content)

        # Count lines for metadata
        line_count = content.count("\n") + 1 if content else 0

        logger.info(f"Successfully parsed TXT file: {file_path} ({len(content)} chars)")

        return ParsedDocument(
            content=content,
            page_count=1,
            metadata={
                "file_size": len(raw_content),
                "encoding": encoding,
                "line_count": line_count,
                "char_count": len(content),
            },
        )

    def _detect_encoding(self, raw_content: bytes) -> str:
        """
        Detect the encoding of raw bytes using chardet.

        Args:
            raw_content: Raw bytes to analyze.

        Returns:
            Detected encoding string.

        Raises:
            EncodingDetectionError: If encoding cannot be detected.
        """
        try:
            result = chardet.detect(raw_content)
            encoding = result.get("encoding")

            if not encoding:
                logger.warning("chardet returned no encoding, using utf-8")
                return "utf-8"

            # Normalize encoding name
            encoding = encoding.lower().replace("-", "_")

            # Handle common aliases
            encoding_map = {
                "gb2312": "gbk",  # GBK is a superset of GB2312
                "ascii": "utf-8",  # ASCII is a subset of UTF-8
            }
            encoding = encoding_map.get(encoding, encoding)

            confidence = result.get("confidence", 0)
            logger.debug(f"Encoding detection: {encoding} (confidence: {confidence})")

            return encoding

        except Exception as e:
            logger.error(f"Encoding detection failed: {e}")
            raise EncodingDetectionError(
                f"Failed to detect encoding: {e}"
            ) from e

    def _decode_with_fallbacks(self, raw_content: bytes) -> str:
        """
        Try decoding with fallback encodings.

        Args:
            raw_content: Raw bytes to decode.

        Returns:
            Decoded string.

        Raises:
            EncodingDetectionError: If all decodings fail.
        """
        for encoding in self.FALLBACK_ENCODINGS:
            try:
                content = raw_content.decode(encoding)
                logger.debug(f"Successfully decoded with fallback encoding: {encoding}")
                return content
            except UnicodeDecodeError:
                continue

        # Last resort: decode with errors='replace'
        logger.warning("All decodings failed, using utf-8 with replacement")
        return raw_content.decode("utf-8", errors="replace")
