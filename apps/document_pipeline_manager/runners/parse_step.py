"""
Parse Step Runner for Document Pipeline.

This module implements the parse step that extracts text content
from uploaded documents using the documents_parser module.
"""

from __future__ import annotations

import logging
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

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

    Supports both local filesystem and S3/MinIO storage backends.
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

            # Get local file path (downloads from S3 if needed)
            with self._get_local_file_path(document) as local_file_path:
                parsed_doc = parser.parse(file_path=local_file_path)

            # Update document with parsed content and metadata
            with transaction.atomic():
                document.title = parsed_doc.metadata.get("title", document.title)
                document.author = parsed_doc.metadata.get("author", document.author)
                document.parsed_content = parsed_doc.content  # Store parsed content for chunk step
                document.status = Document.Status.PROCESSING
                document.save(
                    update_fields=["title", "author", "parsed_content", "status", "updated_at"]
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

    @contextmanager
    def _get_local_file_path(self, document: Document) -> Generator[Path, None, None]:
        """
        Get a local file path for parsing.

        For local storage backend, returns the file path directly.
        For S3/MinIO storage backend, downloads the file to a temporary location
        and cleans up after use.

        Args:
            document: Document model instance with storage metadata.

        Yields:
            Path object pointing to a local file that can be parsed.

        Raises:
            ParseError: If file cannot be retrieved from storage.
        """
        storage_backend = document.storage_backend

        if storage_backend == "local":
            # For local storage, return the absolute path directly
            from django.conf import settings

            local_path = Path(settings.MEDIA_ROOT) / document.file_path
            if not local_path.exists():
                raise ParseError(f"File not found in local storage: {document.file_path}")
            logger.debug(f"[Pipeline] Using local file: {local_path}")
            yield local_path

        elif storage_backend == "s3":
            # For S3/MinIO storage, download to a temporary file
            temp_file = None
            try:
                # Get storage backend
                from apps.object_storage_controller.services.factory import get_storage_backend

                backend = get_storage_backend()

                # Download file content from S3
                logger.debug(
                    f"[Pipeline] Downloading file from S3: {document.file_path}"
                )
                file_content = backend.read(document.file_path)

                # Create temporary file with correct extension
                suffix = f".{document.file_type}"
                temp_file = tempfile.NamedTemporaryFile(
                    mode="wb",
                    suffix=suffix,
                    delete=False,
                )
                temp_file.write(file_content)
                temp_file.close()

                temp_path = Path(temp_file.name)
                logger.debug(
                    f"[Pipeline] Downloaded to temp file: {temp_path} "
                    f"({len(file_content)} bytes)"
                )
                yield temp_path

            finally:
                # Clean up temporary file
                if temp_file is not None:
                    try:
                        Path(temp_file.name).unlink(missing_ok=True)
                        logger.debug(f"[Pipeline] Cleaned up temp file: {temp_file.name}")
                    except Exception as e:
                        logger.warning(
                            f"[Pipeline] Failed to clean up temp file {temp_file.name}: {e}"
                        )

        else:
            raise ParseError(
                f"Unsupported storage backend: {storage_backend} for document {document.id}"
            )
