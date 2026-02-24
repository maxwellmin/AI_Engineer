"""
Text chunking package.

Provides text splitting services for document chunking.
"""

from __future__ import annotations

from .splitter import ChunkingConfig, ChunkResult, TextSplitter

__all__ = [
    "ChunkingConfig",
    "ChunkResult",
    "TextSplitter",
]
