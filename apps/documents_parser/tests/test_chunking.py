"""
Tests for text chunking service.

This module tests TextSplitter, ChunkResult, and ChunkingConfig.
"""

from __future__ import annotations

import pytest

from apps.documents_parser.services.chunking import (
    ChunkingConfig,
    ChunkResult,
    TextSplitter,
)


# =============================================================================
# TextSplitter Tests
# =============================================================================


class TestTextSplitter:
    """Tests for TextSplitter service."""

    @pytest.fixture
    def default_splitter(self):
        """Create a TextSplitter with default config."""
        return TextSplitter()

    @pytest.fixture
    def custom_splitter(self):
        """Create a TextSplitter with custom config."""
        config = ChunkingConfig(
            chunk_size=100,
            chunk_overlap=20,
        )
        return TextSplitter(config=config)

    def test_split_empty_content(self, default_splitter):
        """Test splitting empty content returns empty list."""
        result = default_splitter.split(content="")
        assert result == []

    def test_split_whitespace_only(self, default_splitter):
        """Test splitting whitespace-only content returns empty list."""
        result = default_splitter.split(content="   \n\n   ")
        assert result == []

    def test_split_short_content_single_chunk(self, default_splitter):
        """Test that content shorter than chunk_size returns single chunk."""
        content = "This is a short text."
        result = default_splitter.split(content=content)

        assert len(result) == 1
        assert result[0].content == content
        assert result[0].index == 0

    def test_split_long_content_multiple_chunks(self, custom_splitter):
        """Test that long content is split into multiple chunks."""
        # Create content longer than chunk_size (100 chars)
        content = "A" * 300
        result = custom_splitter.split(content=content)

        assert len(result) > 1
        # Verify indices are sequential
        indices = [chunk.index for chunk in result]
        assert indices == list(range(len(result)))

    def test_split_preserves_content_integrity(self, custom_splitter):
        """Test that split content can be reconstructed."""
        content = "This is sentence one. This is sentence two. This is sentence three."
        result = custom_splitter.split(content=content)

        # Reconstruct content from chunks (simplified check)
        combined = " ".join(chunk.content for chunk in result)
        # Original words should be present
        assert "sentence one" in combined
        assert "sentence two" in combined
        assert "sentence three" in combined

    def test_split_returns_chunk_result_objects(self, default_splitter):
        """Test that split returns ChunkResult objects with correct attributes."""
        content = "Test content for chunking."
        result = default_splitter.split(content=content)

        assert len(result) >= 1
        chunk = result[0]

        assert isinstance(chunk, ChunkResult)
        assert hasattr(chunk, "content")
        assert hasattr(chunk, "index")
        assert hasattr(chunk, "char_count")
        assert hasattr(chunk, "token_count")

    def test_split_with_page_mappings(self, default_splitter):
        """Test that page mappings are correctly applied to chunks."""
        content = "Page 1 content. Page 2 content. Page 3 content."
        page_mappings = [
            {"start": 0, "end": 15, "page": 1},
            {"start": 15, "end": 30, "page": 2},
            {"start": 30, "end": 45, "page": 3},
        ]

        result = default_splitter.split(
            content=content,
            page_mappings=page_mappings,
        )

        # Check that chunks have page numbers assigned
        for chunk in result:
            if chunk.page_number is not None:
                assert isinstance(chunk.page_number, int)
                assert 1 <= chunk.page_number <= 3

    def test_char_count_matches_content_length(self, default_splitter):
        """Test that char_count matches actual content length."""
        content = "Test content for verification."
        result = default_splitter.split(content=content)

        for chunk in result:
            assert chunk.char_count == len(chunk.content)

    def test_estimate_tokens_english(self, default_splitter):
        """Test token estimation for English text."""
        # English: roughly 4 chars per token
        text = "Hello World"  # 11 chars
        tokens = default_splitter.estimate_tokens(text=text)

        assert tokens >= 1
        assert tokens <= 11  # Should be less than char count

    def test_estimate_tokens_chinese(self, default_splitter):
        """Test token estimation for Chinese text."""
        # Chinese: 1 char = 1 token
        text = "你好世界"  # 4 chars
        tokens = default_splitter.estimate_tokens(text=text)

        assert tokens == 4

    def test_estimate_tokens_mixed(self, default_splitter):
        """Test token estimation for mixed Chinese/English text."""
        text = "Hello 世界"  # 6 English chars + 2 Chinese chars
        tokens = default_splitter.estimate_tokens(text=text)

        # Chinese chars count as 1 token each
        # English chars: 6 // 4 = 1 token (roughly)
        # Total should be around 3
        assert tokens >= 2

    def test_estimate_tokens_empty(self, default_splitter):
        """Test token estimation for empty text."""
        tokens = default_splitter.estimate_tokens(text="")
        assert tokens == 0

    def test_config_property(self, custom_splitter):
        """Test that config property returns the configuration."""
        config = custom_splitter.config

        assert isinstance(config, ChunkingConfig)
        assert config.chunk_size == 100
        assert config.chunk_overlap == 20


# =============================================================================
# ChunkingConfig Tests
# =============================================================================


class TestChunkingConfig:
    """Tests for ChunkingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ChunkingConfig()

        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.separators is None

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ChunkingConfig(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n", " "],
        )

        assert config.chunk_size == 500
        assert config.chunk_overlap == 50
        assert config.separators == ["\n", " "]

    def test_frozen(self):
        """Test that ChunkingConfig is immutable."""
        config = ChunkingConfig()

        with pytest.raises(AttributeError):
            config.chunk_size = 2000  # type: ignore


# =============================================================================
# ChunkResult Tests
# =============================================================================


class TestChunkResult:
    """Tests for ChunkResult dataclass."""

    def test_required_fields(self):
        """Test creating ChunkResult with required fields."""
        result = ChunkResult(
            content="Test content",
            index=0,
            char_count=12,
            token_count=3,
        )

        assert result.content == "Test content"
        assert result.index == 0
        assert result.char_count == 12
        assert result.token_count == 3
        assert result.page_number is None

    def test_with_page_number(self):
        """Test creating ChunkResult with page number."""
        result = ChunkResult(
            content="Test content",
            index=0,
            char_count=12,
            token_count=3,
            page_number=5,
        )

        assert result.page_number == 5

    def test_frozen(self):
        """Test that ChunkResult is immutable."""
        result = ChunkResult(
            content="Test",
            index=0,
            char_count=4,
            token_count=1,
        )

        with pytest.raises(AttributeError):
            result.content = "Modified"  # type: ignore
