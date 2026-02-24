"""
Document parsers package.

Provides parsers for different document types: PDF, DOCX, TXT.
"""

from __future__ import annotations

from .base import BaseParser, ParsedDocument
from .docx import DOCXParser
from .factory import ParserFactory
from .pdf import PDFParser
from .txt import TXTParser

__all__ = [
    "BaseParser",
    "ParsedDocument",
    "PDFParser",
    "DOCXParser",
    "TXTParser",
    "ParserFactory",
]
