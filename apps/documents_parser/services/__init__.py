"""
Document parser services package.

Provides file storage, hash calculation, deduplication, parsing,
and chunking services.
"""

from __future__ import annotations

from .chunking import ChunkingConfig, ChunkResult, TextSplitter
from .deduplication import (
    DeduplicationResult,
    check_duplicate,
    get_documents_by_hash,
    get_user_documents_by_hash,
)
from .hash import (
    calculate_content_hash,
    calculate_file_hash,
    calculate_uploaded_file_hash,
)
from .parsers import (
    BaseParser,
    DOCXParser,
    PDFParser,
    ParsedDocument,
    ParserFactory,
    TXTParser,
)
from .storage import (
    StorageResult,
    delete_file,
    file_exists,
    get_storage_path,
    save_file,
    validate_file,
)

__all__ = [
    # Storage
    "StorageResult",
    "delete_file",
    "file_exists",
    "get_storage_path",
    "save_file",
    "validate_file",
    # Hash
    "calculate_content_hash",
    "calculate_file_hash",
    "calculate_uploaded_file_hash",
    # Deduplication
    "DeduplicationResult",
    "check_duplicate",
    "get_documents_by_hash",
    "get_user_documents_by_hash",
    # Parsers
    "BaseParser",
    "ParsedDocument",
    "PDFParser",
    "DOCXParser",
    "TXTParser",
    "ParserFactory",
    # Chunking
    "ChunkingConfig",
    "ChunkResult",
    "TextSplitter",
]
