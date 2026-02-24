"""
Text splitting service for document chunking.

This module provides text chunking functionality using LangChain's
RecursiveCharacterTextSplitter with support for Chinese text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChunkResult:
    """
    Represents a single text chunk with metadata.

    Attributes:
        content: The text content of the chunk.
        index: The index of this chunk in the document.
        char_count: Number of characters in the chunk.
        token_count: Estimated token count.
        page_number: Optional source page number.
    """

    content: str
    index: int
    char_count: int
    token_count: int
    page_number: int | None = None


@dataclass(frozen=True)
class ChunkingConfig:
    """
    Configuration for text chunking.

    Attributes:
        chunk_size: Maximum size of each chunk in characters.
        chunk_overlap: Number of characters to overlap between chunks.
        separators: Custom separators for splitting. If None, uses defaults.
    """

    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: list[str] | None = None


class TextSplitter:
    """
    Service for splitting text into chunks.

    Uses RecursiveCharacterTextSplitter with optimized separators
    for both Chinese and English text.
    """

    # Default separators optimized for mixed Chinese/English content
    DEFAULT_SEPARATORS: list[str] = [
        "\n\n",  # Paragraph break
        "\n",  # Line break
        "。",  # Chinese period
        "！",  # Chinese exclamation
        "？",  # Chinese question
        "；",  # Chinese semicolon
        ".",  # English period
        "!",  # English exclamation
        "?",  # English question
        ";",  # English semicolon
        "，",  # Chinese comma
        ",",  # English comma
        " ",  # Space
        "",  # Character-level split
    ]

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        """
        Initialize the text splitter.

        Args:
            config: Chunking configuration. Uses defaults if not provided.
        """
        self._config = config or ChunkingConfig()

        separators = self._config.separators or self.DEFAULT_SEPARATORS

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._config.chunk_size,
            chunk_overlap=self._config.chunk_overlap,
            separators=separators,
            length_function=len,
            is_separator_regex=False,
        )

        logger.debug(
            f"Initialized TextSplitter with chunk_size={self._config.chunk_size}, "
            f"chunk_overlap={self._config.chunk_overlap}"
        )

    @property
    def config(self) -> ChunkingConfig:
        """Get the current chunking configuration."""
        return self._config

    def split(
        self,
        *,
        content: str,
        page_mappings: list[dict[str, int]] | None = None,
    ) -> list[ChunkResult]:
        """
        Split text content into chunks.

        Args:
            content: The text content to split.
            page_mappings: Optional list of dicts with 'start', 'end', 'page' keys
                          mapping character positions to page numbers.

        Returns:
            List of ChunkResult objects with content and metadata.
        """
        if not content or not content.strip():
            logger.debug("Empty content, returning empty chunks list")
            return []

        # Split the text
        chunks = self._splitter.split_text(content)
        logger.info(f"Split content into {len(chunks)} chunks")

        results: list[ChunkResult] = []

        for index, chunk_content in enumerate(chunks):
            char_count = len(chunk_content)
            token_count = self.estimate_tokens(text=chunk_content)

            # Determine page number from mappings if available
            page_number = None
            if page_mappings:
                # Find the starting position of this chunk in the original content
                start_pos = content.find(chunk_content)
                if start_pos != -1:
                    page_number = self._find_page_for_position(
                        position=start_pos,
                        page_mappings=page_mappings,
                    )

            result = ChunkResult(
                content=chunk_content,
                index=index,
                char_count=char_count,
                token_count=token_count,
                page_number=page_number,
            )
            results.append(result)

        return results

    def estimate_tokens(self, *, text: str) -> int:
        """
        Estimate the number of tokens in text.

        Uses a simple heuristic:
        - Chinese characters: 1 token per character
        - English words: ~0.25 tokens per character (4 chars per word avg)

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0

        # Count Chinese characters
        chinese_pattern = re.compile(r"[\u4e00-\u9fff]")
        chinese_count = len(chinese_pattern.findall(text))

        # Count non-Chinese characters
        non_chinese_text = chinese_pattern.sub("", text)
        non_chinese_count = len(non_chinese_text)

        # Estimate tokens: Chinese = 1:1, English = 1:0.25
        estimated_tokens = chinese_count + (non_chinese_count // 4)

        return max(1, estimated_tokens)

    def _find_page_for_position(
        self,
        *,
        position: int,
        page_mappings: list[dict[str, int]],
    ) -> int | None:
        """
        Find the page number for a character position.

        Args:
            position: Character position in the document.
            page_mappings: List of page mapping dicts.

        Returns:
            Page number if found, None otherwise.
        """
        for mapping in page_mappings:
            start = mapping.get("start", 0)
            end = mapping.get("end", float("inf"))
            page = mapping.get("page", 1)

            if start <= position < end:
                return page

        return None
