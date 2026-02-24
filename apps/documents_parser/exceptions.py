"""
Custom exceptions for document parser module.

This module defines exception classes for document parsing operations
including encoding detection, parsing errors, and file handling.
"""

from __future__ import annotations


class DocumentParserError(Exception):
    """Base exception for document parser errors."""

    def __init__(self, message: str = "Document parser error") -> None:
        self.message = message
        super().__init__(self.message)


class ParsingError(DocumentParserError):
    """Raised when document parsing fails."""

    def __init__(self, message: str = "Failed to parse document") -> None:
        super().__init__(message)


class EncodingDetectionError(ParsingError):
    """Raised when file encoding detection fails."""

    def __init__(self, message: str = "Failed to detect file encoding") -> None:
        super().__init__(message)


class UnsupportedFileTypeError(ParsingError):
    """Raised when an unsupported file type is provided."""

    def __init__(
        self, file_type: str | None = None, message: str | None = None
    ) -> None:
        if message is None:
            if file_type:
                message = f"Unsupported file type: {file_type}"
            else:
                message = "Unsupported file type"
        super().__init__(message)


class FileCorruptedError(ParsingError):
    """Raised when a file is corrupted or cannot be read."""

    def __init__(self, message: str = "File is corrupted or cannot be read") -> None:
        super().__init__(message)
