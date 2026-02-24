"""
Tests for document parsers.

This module tests PDF, DOCX, TXT parsers and ParserFactory.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents_parser.exceptions import (
    EncodingDetectionError,
    FileCorruptedError,
    ParsingError,
    UnsupportedFileTypeError,
)
from apps.documents_parser.services.parsers import (
    DOCXParser,
    PDFParser,
    ParserFactory,
    TXTParser,
)
from apps.documents_parser.services.parsers.base import ParsedDocument


# =============================================================================
# TXTParser Tests
# =============================================================================


class TestTXTParser:
    """Tests for TXTParser."""

    @pytest.fixture
    def parser(self):
        """Create a TXTParser instance."""
        return TXTParser()

    @pytest.fixture
    def sample_txt_utf8(self, tmp_path):
        """Create a sample UTF-8 text file."""
        file_path = tmp_path / "test_utf8.txt"
        file_path.write_text("Hello, World!\nThis is a test file.", encoding="utf-8")
        return file_path

    @pytest.fixture
    def sample_txt_gbk(self, tmp_path):
        """Create a sample GBK encoded text file."""
        file_path = tmp_path / "test_gbk.txt"
        content = "你好，世界！\n这是一个测试文件。"
        file_path.write_bytes(content.encode("gbk"))
        return file_path

    @pytest.fixture
    def sample_txt_empty(self, tmp_path):
        """Create an empty text file."""
        file_path = tmp_path / "empty.txt"
        file_path.write_text("")
        return file_path

    def test_supports_file_type(self, parser):
        """Test that TXTParser supports 'txt' file type."""
        assert parser.supports_file_type() == "txt"

    def test_parse_utf8_file(self, parser, sample_txt_utf8):
        """Test parsing a UTF-8 encoded text file."""
        result = parser.parse(file_path=sample_txt_utf8)

        assert isinstance(result, ParsedDocument)
        assert "Hello, World!" in result.content
        assert result.page_count == 1
        assert result.metadata["encoding"] == "utf-8"

    def test_parse_gbk_file(self, parser, sample_txt_gbk):
        """Test parsing a GBK encoded text file."""
        result = parser.parse(file_path=sample_txt_gbk)

        assert isinstance(result, ParsedDocument)
        assert "你好" in result.content
        assert result.page_count == 1

    def test_parse_empty_file(self, parser, sample_txt_empty):
        """Test parsing an empty text file."""
        result = parser.parse(file_path=sample_txt_empty)

        assert isinstance(result, ParsedDocument)
        assert result.content == ""
        assert result.page_count == 1

    def test_parse_nonexistent_file_raises_error(self, parser):
        """Test that parsing a nonexistent file raises FileCorruptedError."""
        with pytest.raises(FileCorruptedError):
            parser.parse(file_path=Path("/nonexistent/file.txt"))

    def test_parse_returns_correct_metadata(self, parser, sample_txt_utf8):
        """Test that parsed document has correct metadata."""
        result = parser.parse(file_path=sample_txt_utf8)

        assert "file_size" in result.metadata
        assert "encoding" in result.metadata
        assert "char_count" in result.metadata
        assert "line_count" in result.metadata


# =============================================================================
# PDFParser Tests
# =============================================================================


class TestPDFParser:
    """Tests for PDFParser."""

    @pytest.fixture
    def parser(self):
        """Create a PDFParser instance."""
        return PDFParser()

    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """Create a minimal valid PDF file for testing."""
        # Use pypdf to create a simple PDF
        from pypdf import PdfWriter

        pdf_path = tmp_path / "test.pdf"
        writer = PdfWriter()

        # Add a page with text
        writer.add_blank_page(width=612, height=792)
        # Note: pypdf doesn't easily add text, so this is a minimal blank PDF
        # In real scenarios, you'd have PDFs with actual content

        with open(pdf_path, "wb") as f:
            writer.write(f)

        return pdf_path

    def test_supports_file_type(self, parser):
        """Test that PDFParser supports 'pdf' file type."""
        assert parser.supports_file_type() == "pdf"

    def test_parse_valid_pdf(self, parser, sample_pdf):
        """Test parsing a valid PDF file."""
        result = parser.parse(file_path=sample_pdf)

        assert isinstance(result, ParsedDocument)
        assert result.page_count == 1

    def test_parse_nonexistent_file_raises_error(self, parser):
        """Test that parsing a nonexistent file raises FileCorruptedError."""
        with pytest.raises(FileCorruptedError):
            parser.parse(file_path=Path("/nonexistent/file.pdf"))

    def test_parse_invalid_pdf_raises_error(self, parser, tmp_path):
        """Test that parsing an invalid PDF raises FileCorruptedError."""
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("Not a valid PDF")

        with pytest.raises(FileCorruptedError):
            parser.parse(file_path=invalid_pdf)

    def test_parse_returns_metadata(self, parser, sample_pdf):
        """Test that parsed document has metadata."""
        result = parser.parse(file_path=sample_pdf)

        assert "page_count" in result.metadata
        assert "file_size" in result.metadata


# =============================================================================
# DOCXParser Tests
# =============================================================================


class TestDOCXParser:
    """Tests for DOCXParser."""

    @pytest.fixture
    def parser(self):
        """Create a DOCXParser instance."""
        return DOCXParser()

    @pytest.fixture
    def sample_docx(self, tmp_path):
        """Create a sample DOCX file for testing."""
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()

        # Add some paragraphs
        doc.add_paragraph("First paragraph content.")
        doc.add_paragraph("Second paragraph content.")

        # Add a table
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Cell 1"
        table.cell(0, 1).text = "Cell 2"
        table.cell(1, 0).text = "Cell 3"
        table.cell(1, 1).text = "Cell 4"

        doc.save(str(docx_path))
        return docx_path

    def test_supports_file_type(self, parser):
        """Test that DOCXParser supports 'docx' file type."""
        assert parser.supports_file_type() == "docx"

    def test_parse_valid_docx(self, parser, sample_docx):
        """Test parsing a valid DOCX file."""
        result = parser.parse(file_path=sample_docx)

        assert isinstance(result, ParsedDocument)
        assert "First paragraph content" in result.content
        assert "Second paragraph content" in result.content

    def test_parse_nonexistent_file_raises_error(self, parser):
        """Test that parsing a nonexistent file raises FileCorruptedError."""
        with pytest.raises(FileCorruptedError):
            parser.parse(file_path=Path("/nonexistent/file.docx"))

    def test_parse_invalid_docx_raises_error(self, parser, tmp_path):
        """Test that parsing an invalid DOCX raises FileCorruptedError."""
        invalid_docx = tmp_path / "invalid.docx"
        invalid_docx.write_text("Not a valid DOCX")

        with pytest.raises(FileCorruptedError):
            parser.parse(file_path=invalid_docx)

    def test_parse_extracts_table_content(self, parser, sample_docx):
        """Test that DOCX parser extracts table content."""
        result = parser.parse(file_path=sample_docx)

        assert "Cell 1" in result.content
        assert "Cell 2" in result.content

    def test_parse_returns_metadata(self, parser, sample_docx):
        """Test that parsed document has metadata."""
        result = parser.parse(file_path=sample_docx)

        assert "paragraph_count" in result.metadata
        assert "table_count" in result.metadata
        assert result.metadata["paragraph_count"] == 2


# =============================================================================
# ParserFactory Tests
# =============================================================================


class TestParserFactory:
    """Tests for ParserFactory."""

    def test_get_parser_for_pdf(self):
        """Test getting parser for PDF file type."""
        parser = ParserFactory.get_parser(file_type="pdf")
        assert isinstance(parser, PDFParser)

    def test_get_parser_for_docx(self):
        """Test getting parser for DOCX file type."""
        parser = ParserFactory.get_parser(file_type="docx")
        assert isinstance(parser, DOCXParser)

    def test_get_parser_for_doc(self):
        """Test getting parser for DOC file type (alias for DOCX)."""
        parser = ParserFactory.get_parser(file_type="doc")
        assert isinstance(parser, DOCXParser)

    def test_get_parser_for_txt(self):
        """Test getting parser for TXT file type."""
        parser = ParserFactory.get_parser(file_type="txt")
        assert isinstance(parser, TXTParser)

    def test_get_parser_for_md(self):
        """Test getting parser for MD file type (uses TXT parser)."""
        parser = ParserFactory.get_parser(file_type="md")
        assert isinstance(parser, TXTParser)

    def test_get_parser_with_dot_prefix(self):
        """Test getting parser with file type having dot prefix."""
        parser = ParserFactory.get_parser(file_type=".pdf")
        assert isinstance(parser, PDFParser)

    def test_get_parser_with_uppercase(self):
        """Test getting parser with uppercase file type."""
        parser = ParserFactory.get_parser(file_type="PDF")
        assert isinstance(parser, PDFParser)

    def test_get_parser_unsupported_type_raises_error(self):
        """Test that unsupported file type raises UnsupportedFileTypeError."""
        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            ParserFactory.get_parser(file_type="xyz")

        assert "xyz" in str(exc_info.value)

    def test_get_supported_types(self):
        """Test getting list of supported file types."""
        supported = ParserFactory.get_supported_types()

        assert "pdf" in supported
        assert "docx" in supported
        assert "txt" in supported
        assert "md" in supported

    def test_is_supported(self):
        """Test checking if file type is supported."""
        assert ParserFactory.is_supported(file_type="pdf") is True
        assert ParserFactory.is_supported(file_type="xyz") is False

    def test_register_parser(self):
        """Test registering a custom parser."""
        # Create a mock parser
        class CustomParser(TXTParser):
            @classmethod
            def supports_file_type(cls) -> str:
                return "custom"

        ParserFactory.register_parser(file_type="custom", parser_class=CustomParser)

        parser = ParserFactory.get_parser(file_type="custom")
        assert isinstance(parser, CustomParser)
