"""
Parse Step Runner for Document Pipeline.

This module implements the parse step that extracts text content
from uploaded documents using the documents_parser module.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from django.db import transaction

from apps.document_pipeline_manager.constants import PipelineStepName, PipelineStepOrder
from apps.document_pipeline_manager.dto import StepResult
from apps.document_pipeline_manager.exceptions import ParseError
from apps.document_pipeline_manager.runners.base import BaseStepRunner
from apps.documents_parser.models import Document
from apps.documents_parser.services.parsers.factory import ParserFactory

logger = logging.getLogger(__name__)


class ParseStepRunner(BaseStepRunner):
    """
    Parse step runner that extracts text from documents.

    This step:
    1. Retrieves the document from the database
    2. Gets the appropriate parser for the file type
    3. Parses the document to extract text content
    4. Updates the document with extracted metadata
    """

    step_name = PipelineStepName.PARSE.value
    step_order = PipelineStepOrder.PARSE

    def execute(self, document_id: str, **kwargs) -> StepResult:
        """
        Execute the parse step.

        Args:
            document_id: UUID of the document to parse.

        Returns:
            StepResult with parsing outcome and metadata.
        """
        start_time = self._get_start_time()
        self._log_start(document_id)

        try:
            # Get document
            try:
                document = Document.objects.get(id=document_id)
            except Document.DoesNotExist:
                error_msg = f"Document '{document_id}' not found"
                self._log_failure(document_id, error_msg)
                return self._create_failure_result(error_msg)

            # Check if file type is supported
            if not ParserFactory.is_supported(file_type=document.file_type):
                error_msg = f"Unsupported file type: {document.file_type}"
                self._log_failure(document_id, error_msg)
                return self._create_failure_result(error_msg)

            # Get appropriate parser
            parser = ParserFactory.get_parser(file_type=document.file_type)

            # Parse the document
            file_path = Path(document.file_path)
            parsed_doc = parser.parse(file_path=file_path)

            # Update document with parsed content and metadata
            with transaction.atomic():
                document.title = parsed_doc.metadata.get("title", document.title)
                document.author = parsed_doc.metadata.get("author", document.author)
                document.status = Document.Status.PROCESSING
                document.save(
                    update_fields=["title", "author", "status", "updated_at"]
                )

            duration_ms = self._calculate_duration_ms(start_time)
            self._log_complete(document_id, duration_ms)

            # Prepare output data
            output_data = {
                "content_length": len(parsed_doc.content),
                "page_count": parsed_doc.page_count,
                "title": parsed_doc.metadata.get("title", ""),
                "author": parsed_doc.metadata.get("author", ""),
                "file_type": document.file_type,
                "metadata": parsed_doc.metadata,
            }

            logger.debug(
                f"[Pipeline] Parsed document {document_id}: "
                f"{output_data['content_length']} chars, {output_data['page_count']} pages"
            )

            return self._create_success_result(output_data, duration_ms)

        except Exception as e:
            error_msg = f"Parse error: {str(e)}"
            self._log_failure(document_id, error_msg)
            logger.exception(f"[Pipeline] Parse step failed for document {document_id}")
            return self._create_failure_result(
                error_msg, self._calculate_duration_ms(start_time)
            )
