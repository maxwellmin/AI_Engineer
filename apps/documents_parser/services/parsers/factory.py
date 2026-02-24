"""
Parser factory for document parsing.

This module provides a factory class that selects the appropriate
parser based on file type.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from apps.documents_parser.exceptions import UnsupportedFileTypeError
from apps.documents_parser.services.parsers.base import BaseParser
from apps.documents_parser.services.parsers.docx import DOCXParser
from apps.documents_parser.services.parsers.pdf import PDFParser
from apps.documents_parser.services.parsers.txt import TXTParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Factory for creating document parsers.

    Maps file types to their corresponding parser implementations.
    """

    _parsers: ClassVar[dict[str, type[BaseParser]]] = {
        "pdf": PDFParser,
        "docx": DOCXParser,
        "doc": DOCXParser,
        "txt": TXTParser,
        "md": TXTParser,
    }

    @classmethod
    def get_parser(cls, *, file_type: str) -> BaseParser:
        """
        Get a parser instance for the specified file type.

        Args:
            file_type: The file type/extension (e.g., "pdf", "docx", "txt").

        Returns:
            Parser instance for the file type.

        Raises:
            UnsupportedFileTypeError: If the file type is not supported.
        """
        # Normalize file type to lowercase
        normalized_type = file_type.lower().strip()

        # Remove leading dot if present
        if normalized_type.startswith("."):
            normalized_type = normalized_type[1:]

        parser_class = cls._parsers.get(normalized_type)

        if parser_class is None:
            supported = cls.get_supported_types()
            logger.warning(
                f"Unsupported file type: {file_type}. Supported types: {supported}"
            )
            raise UnsupportedFileTypeError(
                file_type=file_type,
                message=f"Unsupported file type: {file_type}. Supported types: {supported}",
            )

        logger.debug(f"Selected parser {parser_class.__name__} for file type: {file_type}")
        return parser_class()

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """
        Get a list of supported file types.

        Returns:
            List of supported file type strings.
        """
        return list(cls._parsers.keys())

    @classmethod
    def is_supported(cls, *, file_type: str) -> bool:
        """
        Check if a file type is supported.

        Args:
            file_type: The file type to check.

        Returns:
            True if the file type is supported, False otherwise.
        """
        normalized_type = file_type.lower().strip()
        if normalized_type.startswith("."):
            normalized_type = normalized_type[1:]
        return normalized_type in cls._parsers

    @classmethod
    def register_parser(cls, *, file_type: str, parser_class: type[BaseParser]) -> None:
        """
        Register a parser for a file type.

        This allows extending the factory with custom parsers.

        Args:
            file_type: The file type to register.
            parser_class: The parser class to use for this file type.
        """
        normalized_type = file_type.lower().strip()
        if normalized_type.startswith("."):
            normalized_type = normalized_type[1:]

        cls._parsers[normalized_type] = parser_class
        logger.info(f"Registered parser {parser_class.__name__} for file type: {normalized_type}")
